---
title: Running Linux Kubernetes Nodes on FreeBSD bhyve
description: >-
  A practical guide to the host setup, Linux guest image, boot process, networking, and validation steps.
keywords:
  - bhyve Kubernetes
  - FreeBSD Linux guest
  - SoftCloud Node Linux
---

# Running Linux Kubernetes Nodes on FreeBSD bhyve

This guide provides a validated, reproducible procedure for running Linux Kubernetes worker nodes inside virtual machines managed by FreeBSD `bhyve`. It details host prerequisites, virtual disk and network configuration, UEFI guest firmware boot flow, container runtime provisioning, and cluster enrollment.

## 1. Purpose and Status

- **Objective**: Deploy lightweight, single-purpose Linux guest virtual machines on FreeBSD to serve as Kubernetes worker nodes running containerized workloads.
- **Implementation Status**: Validated in laboratory environments.
  - **Validated**: UEFI firmware boot, virtio-net bridge integration, containerd 1.7 runtime, Cilium CNI pod-to-pod networking, and node registration.
  - **Experimental / In Progress**: Live migration across FreeBSD hosts, SR-IOV passthrough for multi-gigabit workloads, and automated disk snapshot synchronization.
- **Scope**: Designed for FreeBSD 14-RELEASE series hosts operating dedicated virtual bridges for Kubernetes node interconnects.

## 2. Tested Environment

The configurations in this guide were validated against the following specific software and firmware baselines:

| Component | Specification / Version | Notes |
| :--- | :--- | :--- |
| **Host Operating System** | FreeBSD 14.1-RELEASE-p3 (`amd64`) | GENERIC kernel with `vmm.ko` and `nmdm.ko` loaded |
| **Virtualization Hypervisor** | FreeBSD `bhyve` (`usr/sbin/bhyve`) | Standard base system binary |
| **Guest Firmware** | EDK II / UEFI firmware (`BHYVE_UEFI.fd`) | From `sysutils/edk2-bhyve` (edk2-stable202308) |
| **Guest Operating System** | SoftCloud Node Linux 2024.1 (`x86_64`) | Minimal immutable rootfs with systemd-boot |
| **Guest Kernel** | Linux 6.6.32-lts (Unified Kernel Image) | Built with virtio and eBPF support enabled |
| **Container Runtime** | `containerd` v1.7.18 | `systemd` cgroup driver enabled |
| **Kubernetes Version** | Kubernetes v1.30.2 (`kubelet`, `kubeadm`) | Standard upstream binaries |
| **Pod Network (CNI)** | Cilium v1.15.5 | eBPF tunnel mode (VXLAN) over virtio-net |

## 3. Architecture

The node virtualization model establishes a clean boundary between the FreeBSD storage/network control plane and the Linux container execution environment:

```
+-----------------------------------------------------------------+
|                       FreeBSD 14.1 Host                         |
|                                                                 |
|  +-------------------+               +-----------------------+  |
|  |   ZFS Pool (zroot)|               |    FreeBSD Bridge     |  |
|  |  zroot/bhyve/node1|               |     vm-bridge0        |  |
|  +---------+---------+               +-----------+-----------+  |
|            | zvol (/dev/zvol/...)                |              |
|            |                                     |              |
|  +---------v-------------------------------------v-----------+  |
|  |                      bhyve Process                        |  |
|  |  +-----------------------------------------------------+  |  |
|  |  | Guest UEFI Firmware (BHYVE_UEFI.fd)                 |  |  |
|  |  |   -> Reads ESP FAT32 partition                      |  |  |
|  |  |   -> Executes Unified Kernel Image (linux.efi)      |  |  |
|  |  +--------------------------+--------------------------+  |  |
|  |                             |                             |  |
|  |  +--------------------------v--------------------------+  |  |
|  |  | SoftCloud Node Linux (Guest VM)                    |  |  |
|  |  |  - virtio-blk (Root Filesystem)                     |  |  |
|  |  |  - virtio-net (eth0 -> vm-bridge0 via tap0)        |  |  |
|  |  |  - containerd (Container Runtime)                   |  |  |
|  |  |  - kubelet + Cilium CNI (Pod Workloads)             |  |  |
|  |  +-----------------------------------------------------+  |  |
|  +-----------------------------------------------------------+  |
+-----------------------------------------------------------------+
```

### Storage Boundary
The guest disk resides on a dedicated ZFS volume (`zvol`) created with an 8 KB or 16 KB volume block size matching the guest filesystem alignment. The zvol is presented to the virtual machine as a `virtio-blk` device.

### Network Boundary
The host maintains a virtual Ethernet bridge (`vm-bridge0`). Each bhyve guest connects to the bridge via an allocated tap interface (`tap0`). The guest interacts with this link as a high-throughput `virtio-net` Ethernet adapter (`eth0`).

### Boot Boundary
The host initiates `bhyve` passing the EDK II UEFI bootrom. The firmware initializes virtual PCI devices, discovers the GPT EFI System Partition (ESP) on the virtio block device, and launches the Unified Kernel Image (`linux.efi`) residing at `EFI/BOOT/BOOTX64.EFI`.

## 4. Host Setup and Image Preparation

### 4.1 Host Kernel Modules and Network Setup

On the FreeBSD host, enable virtualization support and configure the bridge:

```sh
# Load required kernel modules
kldload -n vmm
kldload -n nmdm
kldload -n if_tap
kldload -n if_bridge

# Ensure modules load on boot in /boot/loader.conf
sysrc -f /boot/loader.conf vmm_load="YES"
sysrc -f /boot/loader.conf nmdm_load="YES"
sysrc -f /boot/loader.conf if_tap_load="YES"
sysrc -f /boot/loader.conf if_bridge_load="YES"

# Create the persistent internal bridge for VM nodes
sysrc cloned_interfaces+="bridge0 tap0"
sysrc ifconfig_bridge0="inet 10.240.0.1/24 addm tap0 up"
sysrc ifconfig_tap0="up"

# Bring interfaces up immediately
ifconfig bridge0 create inet 10.240.0.1/24 up
ifconfig tap0 create up
ifconfig bridge0 addm tap0
```

### 4.2 Storage Preparation

Create a dedicated 20 GB ZFS volume for the guest node:

```sh
zfs create -V 20G -s -o volblocksize=16k zroot/bhyve/node-linux-01
```

### 4.3 Image Acquisition and Verification

Fetch the verified SoftCloud Node Linux base raw image and write it to the zvol:

```sh
# Download release image and SHA256 checksums
fetch https://github.com/soft-cloud-dev/linux/releases/download/v2024.1/softcloud-node-linux-2024.1.raw.xz
fetch https://github.com/soft-cloud-dev/linux/releases/download/v2024.1/SHA256SUMS

# Verify SHA256 checksum
sha256 -c SHA256SUMS softcloud-node-linux-2024.1.raw.xz

# Decompress directly to the ZFS volume
xzcat softcloud-node-linux-2024.1.raw.xz | dd of=/dev/zvol/zroot/bhyve/node-linux-01 bs=1M status=progress
```

## 5. Guest Startup and Boot Flow

Understanding the bhyve boot mechanism prevents initialization failures:
- A `bhyve` command invoking `-l bootrom,...` does **not** perform an in-kernel direct ELF/bzImage load.
- Instead, it initializes the virtual CPU into x86 reset vector pointing to the UEFI firmware (`BHYVE_UEFI.fd`).
- The UEFI firmware initializes virtual PCI buses, locates block devices, reads the FAT32 EFI System Partition (ESP), and launches the default bootloader or Unified Kernel Image (`EFI/BOOT/BOOTX64.EFI`).

### 5.1 Launch Script

Run the virtual machine with 2 vCPUs, 4 GB RAM, UEFI firmware, virtual console over `nmdm`, virtio network, and virtio block storage:

```sh
#!/bin/sh
set -eu

VM_NAME="k8s-node-01"
FIRMWARE="/usr/local/share/uefi-firmware/BHYVE_UEFI.fd"
DISK="/dev/zvol/zroot/bhyve/node-linux-01"
TAP="tap0"
CONSOLE="/dev/nmdm-k8s01A"

# Clean any existing instance
bhyvectl --destroy --vm="${VM_NAME}" 2>/dev/null || true

# Execute bhyve
bhyve -A -H -P \
  -c cpus=2 \
  -m 4096M \
  -s 0:0,hostbridge \
  -s 1:0,lpc \
  -s 2:0,virtio-blk,"${DISK}" \
  -s 3:0,virtio-net,"${TAP}" \
  -s 4:0,virtio-rnd \
  -l bootrom,"${FIRMWARE}" \
  -l com1,"${CONSOLE}" \
  "${VM_NAME}"
```

### 5.2 Console Access and Expected Boot Behavior

To view the guest console during startup, attach to the corresponding `nmdm` device using `cu`:

```sh
cu -l /dev/nmdm-k8s01B -s 115200
```

Expected boot sequence on console:
1. `TianoCore EDK II` firmware banner and memory initialization.
2. UEFI Boot Manager: locating `FS0:\EFI\BOOT\BOOTX64.EFI`.
3. SoftCloud UKI loader executing Linux kernel 6.6 with embedded command line (`console=ttyS0,115200 root=LABEL=SC_ROOT rw`).
4. Systemd initialization and DHCP acquisition on `eth0` (receiving `10.240.0.10/24`).
5. Login prompt: `SoftCloud Node Linux 2024.1 (ttyS0)`.

## 6. Kubernetes and Networking Configuration

Once logged into the guest node, complete runtime configuration and cluster join.

### 6.1 Kernel Parameters and containerd

Verify that network bridging and forwarding parameters are active inside the Linux guest:

```sh
cat <<EOF | sudo tee /etc/sysctl.d/99-kubernetes-cri.conf
net.bridge.bridge-nf-call-iptables  = 1
net.ipv4.ip_forward                 = 1
net.bridge.bridge-nf-call-ip6tables = 1
EOF

sudo sysctl --system
```

Verify `containerd` is running with `SystemdCgroup = true`:

```sh
sudo containerd config default | grep -A 5 "SystemdCgroup"
# Ensure:
# [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options]
#   SystemdCgroup = true
sudo systemctl restart containerd
```

### 6.2 Cluster Enrollment via kubeadm

Join the worker node to your existing Kubernetes control plane:

```sh
sudo kubeadm join 10.240.0.2:6443 \
  --token <token> \
  --discovery-token-ca-cert-hash sha256:<ca-hash> \
  --node-name k8s-bhyve-node-01
```

### 6.3 Cilium CNI Verification

Cilium attaches to `eth0` via eBPF. Confirm the Cilium agent pod initializes without eBPF map allocation errors on the virtio interface:

```sh
kubectl get nodes -o wide
# k8s-bhyve-node-01   Ready    <none>   10m   v1.30.2   10.240.0.10   SoftCloud Node Linux 2024.1   6.6.32-lts   containerd://1.7.18
```

## 7. Verification and Validation Procedures

Execute the following verification checklist to confirm health:

1. **Host-Side Resource Consumption**:
   ```sh
   # On FreeBSD host:
   bhyvectl --vm=k8s-node-01 --get-stats
   ```
2. **Pod-to-Pod Connectivity**:
   ```sh
   # Run diagnostic probe across nodes
   kubectl run test-pod --image=busybox:1.36 --restart=Never -- sleep 3600
   kubectl exec -it test-pod -- ping -c 3 10.240.0.1
   ```
3. **Storage I/O Sanity**:
   ```sh
   # Inside guest:
   dd if=/dev/zero of=/var/tmp/test.img bs=1M count=512 conv=fdatasync
   rm /var/tmp/test.img
   ```

## 8. Troubleshooting and Limitations

| Issue | Root Cause | Remediation |
| :--- | :--- | :--- |
| **Guest hangs before kernel output** | UEFI firmware cannot find bootable FAT32 ESP partition or NVRAM state is corrupt. | Verify disk partition table using `gpart show /dev/zvol/zroot/bhyve/node-linux-01`. Ensure the first partition has type `efi`. If using persistent NVRAM, clear the `.vars` file. |
| **No network traffic between guest and host** | Host `tap` interface is not added to the bridge or tap has not been set to `up`. | Run `ifconfig bridge0` to confirm `tap0` is in the member list and has status `active`. Run `ifconfig tap0 up`. |
| **MTU fragmentation in Pod Network** | Virtio MTU (1500) does not account for VXLAN/Geneve encapsulation overhead (50 bytes). | Configure Cilium MTU explicitly: `cilium config set mtu 1450` or adjust host tap MTU to 1550 if jumbo frames are supported across the physical network. |
| **Clock drift across guest execution** | Missing virtual PTP / KVM clock driver synchronization in bhyve. | Enable `chrony` or `systemd-timesyncd` in the guest pointing to the FreeBSD host bridge IP (`10.240.0.1`) running an NTP server. |

### Limitations
- **Live Migration**: Not currently supported by base FreeBSD `bhyve`. Node maintenance requires draining the Kubernetes node (`kubectl drain`) before stopping the VM.
- **Nested Virtualization**: Running hardware-accelerated VMs inside the guest Linux node is experimental on bhyve AMD/Intel drivers.
