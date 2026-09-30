# Introduction

SoftCloud Node Linux provides an open, deterministic operating system architecture engineered specifically for Kubernetes worker and control-plane nodes hosted inside FreeBSD `bhyve` virtual machines.

Published at [linux.softcloud.dev](https://linux.softcloud.dev/), this platform establishes the normative contracts, build specifications, and operational adoption plans that govern the lifecycle of containerized infrastructure within the Software Cloud ecosystem.

---

## The Challenge of Hypervisor-Managed Kubernetes Nodes

Running Kubernetes clusters across virtualized laboratory and production environments frequently exposes systemic friction when utilizing generic, general-purpose Linux distributions:

1. **Upstream Dependency & Version Drift**:
   Standard cloud images rely on moving repository tags (`latest`, `stable`), dynamically resolving packages during machine provisioning. This breaks reproducible testing and introduces non-deterministic kernel and runtime behaviors across cluster nodes.

2. **Heavily Bloated & Fragile Initialization**:
   Conventional `cloud-init` engines introduce sprawling Python dependency trees, slow startup times, and complex state machines prone to race conditions (e.g., relying on `systemd-udev-settle` or failing to establish networking before daemon activation).

3. **Hypervisor & Firmware Coupling**:
   Many cloud distributions assume persistent UEFI NVRAM variables to retain bootloader state. In ephemeral, hypervisor-managed VM environments like FreeBSD `bhyve`, NVRAM stores are often reset or stateless, leading to unbootable nodes upon migration or cold restart.

4. **eBPF & Cilium CNI Prerequisite Mismatches**:
   Modern Kubernetes networking with Cilium requires strict kernel eBPF capabilities, valid BTF (BPF Type Format) debug sections, and an early-boot shared mount of `/sys/fs/bpf`. Relying on post-boot scripts or in-cluster CNI daemonsets to mount and remount bpffs introduces startup races and daemon instability.

5. **Impure Storage & Mutating Upgrade Cycles**:
   Standard distributions conflate OS root binaries with mutable workload state (`/var/lib/containerd`, `/var/lib/kubelet`), encouraging dangerous in-place `apt upgrade` workflows that lead to configuration drift across control-plane and worker nodes.

---

## System Boundary & Separation of Concerns

SoftCloud Node Linux enforces a strict architectural boundary dividing the **Artifact Producer** from the **Laboratory Consumer**:

```text
+-------------------------------------------------------------------------------+
|                      PRODUCER: soft-cloud-dev/os-linux                        |
|                                                                               |
|  - Kernel LTS selection & configuration (linux-kubernetes-bhyve.config)       |
|  - Pinned BTF generation via pahole & bpftool verification                     |
|  - Deterministic userspace assembly via mmdebstrap & Debian snapshot          |
|  - Systemd, containerd, runc, and Kubernetes node binaries                    |
|  - CNI loopback binary & bpffs shared mount sequencing                        |
|  - Unified Kernel Image (BOOTX64.EFI) and EDK2 fallback boot contract          |
|  - First-boot softcloud-seed bootstrap agent & CIDATA device activation       |
|  - Deterministic raw disk image generation (softcloud-node-amd64.raw)         |
|  - SBOM generation (SPDX JSON), build provenance, and R4 verification         |
+-------------------------------------------------------------------------------+
                                        |
                          softcloud-node-amd64.raw
                                        v
+-------------------------------------------------------------------------------+
|                   CONSUMER: soft-cloud-dev/freebsd-laboratory                 |
|                                                                               |
|  - FreeBSD host configuration & kernel tuning                                 |
|  - bhyve virtual machine lifecycle management                                 |
|  - TAP interfaces, bridge construction, and VLAN routing                      |
|  - VM hardware identity assignment (MAC addresses, UUIDs, hostnames)          |
|  - CIDATA seed-image generation (network topology, SSH authorized keys)       |
|  - Kubernetes cluster bootstrap orchestration (kubeadm init / kubeadm join)   |
|  - Cilium CNI cluster-level deployment & network policies                     |
|  - Workload scheduling, runtime observations, and empirical experiments       |
+-------------------------------------------------------------------------------+
```

### Boundary Requirements

- **`ARCH-01`**: Kubernetes cluster state SHALL NOT be embedded in the SoftCloud Node Linux release artifact.
- **`ARCH-02`**: The same accepted OS image SHALL be usable as either a Kubernetes control-plane node or worker node.
- **`ARCH-03`**: Machine-specific identity SHALL be supplied or generated after the golden image has been instantiated.
- **`ARCH-04`**: Cluster-specific identity SHALL be established only by the cluster bootstrap process.

---

## Operational Scope

SoftCloud Node Linux implements this separation through five foundational architectural contracts:

1. **Specification by Formal Memorandum**:
   All architectural parameters, lockfile models, kernel options, and acceptance criteria are codified in [MEMORANDUM.md](memorandum.md) (`SOFTCLOUD-NODE-LINUX-1.0`).

2. **Immutable Artifact Replacement**:
   Nodes are treated as immutable appliances. Security patches, kernel updates, or Kubernetes releases result in a new golden OS artifact rather than mutable in-place package upgrades.

3. **Dynamic State Isolation**:
   The release image separates the OS root partition (`p2`) from the mutable node-state partition (`p3`). Workload paths (`/var/lib/containerd`, `/var/lib/kubelet`, `/var/lib/etcd`, `/var/log`) are dynamically grown via `systemd-repart` and projected via systemd bind mounts with explicit propagation.

4. **Deterministic Supply Chain**:
   All build inputs are pinned across five lockfiles (`sources.lock`, `debian.lock`, `kubernetes.lock`, `containerd.lock`, and `toolchain.lock`), guaranteeing that build artifacts can be independently verified.

5. **Phased Organizational Adoption**:
   Adoption is managed through a comprehensive, 8-phase implementation plan governed by 35 verifiable acceptance criteria (`SN-01` through `SN-35`), detailed in the [Adoption Plan](adoption-plan.md).
