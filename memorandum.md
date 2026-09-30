# SoftCloud Node Linux Memorandum

**Document:** `MEMORANDUM.md`  
**Specification:** `SOFTCLOUD-NODE-LINUX-1.0`  
**Status:** Normative Implementation Baseline  
**Owner:** `soft-cloud-dev/os-linux`  
**Primary Consumer:** `soft-cloud-dev/freebsd-laboratory`  
**Target Hypervisor:** FreeBSD `bhyve`  
**Target Architecture:** `amd64`

---

## 1. Purpose

This memorandum defines the normative architecture, build process, boot contract, runtime environment, artifact format, provisioning interface, reproducibility requirements, and acceptance criteria for **SoftCloud Node Linux**.

SoftCloud Node Linux is a dedicated Linux distribution for Kubernetes nodes executed as `bhyve` virtual machines.

It is not a customized Ubuntu installation, a generic Debian server image, or an interactive operating-system installation.

The distribution SHALL be produced as a deterministic artifact by `soft-cloud-dev/os-linux` and consumed by `freebsd-laboratory`.

---

## 2. Normative Language

The key words **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are normative.

For this memorandum:

- **SHALL** means the requirement is mandatory.
- **SHALL NOT** means the behavior is prohibited.
- **SHOULD** means the requirement is expected unless a documented technical reason justifies deviation.
- **SHOULD NOT** means the behavior is discouraged unless a documented technical reason justifies it.
- **MAY** means the behavior is optional.

A deployment SHALL NOT claim conformance with this memorandum until all applicable acceptance criteria in Section 24 pass.

---

# 3. System Boundary

## 3.1 Artifact Producer

`os-linux` SHALL own:

1. Linux kernel selection and configuration.
2. Userspace construction.
3. `systemd`.
4. `containerd`.
5. `runc`.
6. Kubernetes node binaries.
7. CNI prerequisite binaries.
8. The bhyve boot contract.
9. The machine bootstrap mechanism.
10. Disk-image construction.
11. Build provenance.
12. SBOM generation.
13. Artifact verification.
14. Reproducibility validation.

`os-linux` SHALL produce a machine-independent node artifact.

The primary artifact SHALL be:

```text
softcloud-node-amd64.raw
```

## 3.2 Laboratory Consumer

`freebsd-laboratory` SHALL own:

1. FreeBSD host configuration.
2. `bhyve` lifecycle.
3. TAP and bridge construction.
4. VM MAC addresses.
5. VM UUIDs.
6. VM hostnames.
7. VM IP addresses.
8. seed-image generation.
9. Kubernetes cluster topology.
10. `kubeadm init`.
11. `kubeadm join`.
12. cluster-level Cilium deployment.
13. experiments.
14. runtime observations.
15. verification evidence.

## 3.3 Boundary Requirements

**ARCH-01:** Kubernetes cluster state SHALL NOT be embedded in the SoftCloud Node Linux release artifact.

**ARCH-02:** The same accepted OS image SHALL be usable as either a Kubernetes control-plane node or worker node.

**ARCH-03:** Machine-specific identity SHALL be supplied or generated after the golden image has been instantiated.

**ARCH-04:** Cluster-specific identity SHALL be established only by the cluster bootstrap process.

---

# 4. Target Platform

The initial conforming profile SHALL have the following characteristics:

```text
Architecture       amd64
Hypervisor         FreeBSD bhyve
Firmware           EDK2
Boot format        Unified Kernel Image
Kernel             Linux LTS
libc               glibc
Init               systemd
Cgroup hierarchy   cgroup v2
Container runtime  containerd
OCI runtime        runc
Orchestrator       Kubernetes
CNI target         Cilium
Root filesystem    ext4
State filesystem   ext4
Network manager    systemd-networkd
Console            ttyS0
Provisioning       softcloud.node/v1
```

**PLAT-01:** The initial implementation SHALL support `amd64`.

**PLAT-02:** The initial implementation SHALL support execution under FreeBSD `bhyve`.

**PLAT-03:** Other architectures and hypervisors MAY be added through separate profiles.

**PLAT-04:** Additional targets SHALL NOT alter the behavior of the `kubernetes-node` bhyve profile without a memorandum revision.

---

# 5. Input and Dependency Model

## 5.1 General Rule

Every build input SHALL resolve to an immutable identity before the canonical build begins.

Moving references such as:

```text
latest
stable
current
main
master
6.18.x
1.36.x
```

SHALL NOT constitute accepted build inputs.

## 5.2 Lockfiles

The repository SHALL maintain at least:

```text
locks/
├── sources.lock
├── debian.lock
├── kubernetes.lock
├── containerd.lock
└── toolchain.lock
```

**SRC-01:** `sources.lock` SHALL identify Linux and other source archives by exact version and cryptographic digest.

**SRC-02:** `debian.lock` SHALL identify the complete Debian package closure used by the root filesystem.

**SRC-03:** `kubernetes.lock` SHALL identify exact versions and digests for Kubernetes node binaries and Kubernetes-specific utilities.

**SRC-04:** `containerd.lock` SHALL identify exact versions and digests for `containerd`, `runc`, and related runtime inputs.

**SRC-05:** `toolchain.lock` SHALL identify the canonical compiler, linker, `pahole`, filesystem tooling, UKI tooling, and other build-critical utilities.

**SRC-06:** Lockfile changes SHALL be reviewable independently from build logic changes.

---

# 6. Fetch and Build Separation

The build process SHALL contain an explicit trust boundary:

```text
FETCH
  ↓
VERIFY
  ↓
VERIFIED LOCAL INPUT SET
  ↓
DISABLE NETWORK
  ↓
BUILD
  ↓
VERIFY OUTPUT
```

**BUILD-01:** All network-dependent inputs SHALL be retrieved before the canonical build phase.

**BUILD-02:** Every retrieved input SHALL be cryptographically verified before entering the build input set.

**BUILD-03:** The canonical image build SHALL succeed with network access disabled.

**BUILD-04:** The build SHALL fail when a required undeclared input is unavailable locally.

**BUILD-05:** The build SHALL NOT silently retrieve dependencies during compilation, package assembly, UKI creation, filesystem construction, or image generation.

---

# 7. Canonical Builder

Linux kernel and Linux userspace construction SHALL occur in a versioned canonical Linux build environment.

FreeBSD SHALL remain responsible for final `bhyve` execution validation.

```text
verified inputs
       |
       v
canonical Linux builder
       |
       +--> kernel
       +--> rootfs
       +--> UKI
       +--> disk image
       |
       v
digested artifacts
       |
       v
FreeBSD bhyve verification
```

**BLD-01:** The canonical builder definition SHALL be version controlled.

**BLD-02:** The canonical builder SHALL have a deterministic dependency set.

**BLD-03:** Compiler and linker versions SHALL be recorded in provenance.

**BLD-04:** The `pahole` version SHALL be recorded in provenance.

**BLD-05:** Filesystem-generation tools SHALL be recorded in provenance.

**BLD-06:** UKI-generation tooling SHALL be recorded in provenance.

---

# 8. Linux Kernel

A dedicated Kubernetes/bhyve configuration SHALL exist at:

```text
kernel/config/linux-kubernetes-bhyve.config
```

The generic bhyve kernel configuration SHALL NOT silently become the Kubernetes profile.

## 8.1 Root Boot Requirements

The following capabilities SHALL be built directly into the kernel:

```ini
CONFIG_VIRTIO=y
CONFIG_VIRTIO_PCI=y
CONFIG_VIRTIO_BLK=y
CONFIG_EXT4_FS=y
```

These requirements SHALL NOT be satisfied by modules.

## 8.2 Namespaces and Cgroups

The Kubernetes profile SHALL provide at least:

```ini
CONFIG_NAMESPACES=y
CONFIG_UTS_NS=y
CONFIG_IPC_NS=y
CONFIG_USER_NS=y
CONFIG_PID_NS=y
CONFIG_NET_NS=y

CONFIG_CGROUPS=y
CONFIG_MEMCG=y
CONFIG_BLK_CGROUP=y
CONFIG_CGROUP_SCHED=y
CONFIG_FAIR_GROUP_SCHED=y
CONFIG_CFS_BANDWIDTH=y
CONFIG_CGROUP_BPF=y
```

## 8.3 eBPF and Cilium

The profile SHALL provide at least:

```ini
CONFIG_BPF=y
CONFIG_BPF_SYSCALL=y
CONFIG_BPF_JIT=y
CONFIG_BPF_EVENTS=y

CONFIG_NET_CLS_ACT=y
CONFIG_NET_SCH_INGRESS=y
CONFIG_NET_SCH_FQ=y
CONFIG_NET_ACT_BPF=y

CONFIG_LWTUNNEL=y
CONFIG_LWTUNNEL_BPF=y

CONFIG_VXLAN=y
CONFIG_GENEVE=y
```

## 8.4 Networking

The profile SHALL provide bridge, routing, conntrack, Netfilter, nftables, TPROXY, VETH, and policy-routing facilities required by Kubernetes and the selected Cilium configuration.

At minimum:

```ini
CONFIG_NETFILTER=y
CONFIG_NF_CONNTRACK=y
CONFIG_NF_TABLES=y
CONFIG_NETFILTER_XT_TARGET_TPROXY=y
CONFIG_NETFILTER_XT_MATCH_SOCKET=y

CONFIG_VETH=y
CONFIG_BRIDGE=y
CONFIG_BRIDGE_NETFILTER=y
```

## 8.5 Storage and Security

The profile SHALL provide at least:

```ini
CONFIG_OVERLAY_FS=y
CONFIG_EXT4_FS=y
CONFIG_EXT4_FS_POSIX_ACL=y
CONFIG_EXT4_FS_SECURITY=y

CONFIG_SECCOMP=y
CONFIG_SECCOMP_FILTER=y
```

## 8.6 Swap

The dedicated Kubernetes-node profile SHOULD compile with:

```ini
CONFIG_SWAP=n
```

If swap support is retained for another reason, swap SHALL remain disabled for the complete lifetime of a conforming Kubernetes node unless a future Kubernetes profile explicitly defines otherwise.

## 8.7 Security Mitigations

CPU security mitigations SHALL remain enabled by default.

A laboratory-specific profile MAY disable individual mitigations only when:

1. the behavior under study requires it;
2. the change is explicit;
3. the change is documented;
4. the resulting artifact is distinguishable from the normal Kubernetes-node artifact.

---

# 9. BTF Contract

The kernel SHALL provide valid BTF suitable for the selected Cilium release.

Configuration alone SHALL NOT satisfy this requirement.

**BTF-01:** `CONFIG_DEBUG_INFO_BTF=y` SHALL be enabled.

**BTF-02:** The canonical builder SHALL contain a pinned compatible `pahole`.

**BTF-03:** The resulting `vmlinux` SHALL contain a valid `.BTF` section.

**BTF-04:** BTF data SHALL be parsed during validation.

A validation equivalent to:

```sh
bpftool btf dump file build/vmlinux format raw >/dev/null
```

SHALL succeed.

**BTF-05:** Failure to generate or parse BTF SHALL reject the kernel before disk-image construction.

---

# 10. Boot Contract

## 10.1 Unified Kernel Image

A Unified Kernel Image is mandatory in the initial implementation.

The canonical boot path SHALL be:

```text
bhyve
  ↓
EDK2
  ↓
EFI System Partition
  ↓
/EFI/BOOT/BOOTX64.EFI
  ↓
UKI
  ↓
Linux
  ↓
systemd
```

**BOOT-01:** `/EFI/BOOT/BOOTX64.EFI` SHALL be a self-contained accepted boot artifact.

**BOOT-02:** Normal boot SHALL NOT require persistent UEFI NVRAM variables.

**BOOT-03:** The system SHALL boot with a fresh or stateless EDK2 variable store.

## 10.2 Kernel Command Line

The UKI SHALL contain the required kernel command line.

At minimum it SHALL encode equivalent semantics to:

```text
root=PARTUUID=<ROOT_PARTUUID>
rootfstype=ext4
rootwait
console=ttyS0,115200
cgroup_no_v1=all
```

Additional options MAY be included when defined by the profile.

**BOOT-04:** `rootwait` SHALL be present.

**BOOT-05:** The root filesystem SHALL be identified deterministically.

**BOOT-06:** The root device SHALL NOT depend on incidental `/dev/vdX` enumeration.

## 10.3 Deterministic UKI

**BOOT-07:** The UKI binary SHALL be generated deterministically.

All PE/COFF fields whose values may depend on wall-clock build time, including the PE/COFF header timestamp, SHALL be derived from or normalized against `SOURCE_DATE_EPOCH`.

Two otherwise identical builds SHALL NOT produce different UKI binaries solely because they were executed at different wall-clock times.

UKI reproducibility SHALL be verified by digest comparison as part of R2 and higher reproducibility testing.

## 10.4 Initramfs

The image MAY include a minimal initramfs.

The initramfs SHALL NOT be required to provide basic VirtIO block or ext4 support.

---

# 11. Userspace

SoftCloud Node Linux SHALL use a `glibc` userspace.

Debian packages MAY serve as upstream userspace inputs.

The resulting OS identity SHALL remain SoftCloud Node Linux.

## 11.1 Debian Snapshot

**USR-01:** Debian packages SHALL come from a timestamped archive or equivalent immutable source.

**USR-02:** The build SHALL NOT consume a moving Debian `stable` mirror as an accepted source.

**USR-03:** The exact snapshot identity SHALL be recorded in the artifact manifest.

## 11.2 Rootfs Assembly

`mmdebstrap` SHOULD be used as the rootfs construction mechanism in the canonical builder.

The rootfs pipeline SHALL be equivalent to:

```text
locked snapshot
      ↓
locked package closure
      ↓
rootfs staging tree
      ↓
SoftCloud overlay
      ↓
ldconfig
      ↓
normalization
      ↓
filesystem generation
```

**USR-04:** Package maintainer scripts SHALL be controlled to prevent host-dependent or nondeterministic artifact mutations.

**USR-05:** Dynamic user/group allocation during the canonical build SHALL be deterministic.

**USR-06:** The rootfs build SHALL execute:

```sh
ldconfig -r <target-root>
```

or an equivalent deterministic operation before final filesystem generation.

**USR-07:** First boot SHALL NOT be required merely to make normal dynamically linked utilities executable.

---

# 12. Operating-System Identity

The release artifact SHALL identify itself as SoftCloud Node Linux.

At minimum:

```text
/etc/os-release
```

SHALL provide the distribution identity.

The image SHOULD also provide:

```text
/etc/issue
```

for human-readable console identification.

**ID-01:** The artifact SHALL NOT identify itself primarily as Ubuntu or Debian.

**ID-02:** Upstream origin metadata MAY identify Debian as a userspace source.

---

# 13. Container and Kubernetes Runtime

The accepted image SHALL contain:

```text
containerd
runc
kubelet
kubeadm
kubectl
cri-tools
```

The image SHALL also contain required reference CNI lifecycle binaries, including:

```text
/opt/cni/bin/loopback
```

## 13.1 Runtime Rules

**RUN-01:** `containerd` SHALL expose a functioning CRI endpoint.

**RUN-02:** `containerd` SHALL use the `systemd` cgroup driver.

**RUN-03:** `kubelet` SHALL use the `systemd` cgroup driver.

**RUN-04:** The node SHALL use cgroup v2.

**RUN-05:** cgroup v1 controllers SHALL NOT be required for the Kubernetes-node profile.

**RUN-06:** `/opt/cni/bin/loopback` SHALL exist before Kubernetes bootstrap.

**RUN-07:** The Kubernetes node BPF filesystem SHALL be mounted at:

```text
/sys/fs/bpf
```

in the node's host mount namespace and SHALL have shared mount-propagation semantics before `containerd` and `kubelet` start.

The distribution SHOULD provide an explicit systemd-managed boot unit sequence equivalent to:

```text
mount bpffs at /sys/fs/bpf
        ↓
make /sys/fs/bpf shared
        ↓
containerd
        ↓
kubelet
```

The implementation SHALL NOT depend on Cilium performing the first persistent bpffs mount after Kubernetes startup.

The runtime verifier SHALL confirm both:

```text
filesystem type = bpf
mount propagation = shared
```

before the node is accepted.

## 13.2 Cluster-State Boundary

The image SHALL NOT contain:

```text
kubeadm join tokens
cluster CA private keys
node certificates
etcd data
preconfigured cluster membership
Cilium cluster identity
```

Cluster state SHALL be created by `freebsd-laboratory` or the cluster bootstrap workflow.

---

# 14. Disk Layout

The image SHALL use GPT.

The logical layout SHALL be:

```text
+---------------------------------------------------------+
| GPT                                                     |
+---------------+----------------------+------------------+
| p1 ESP        | p2 OS root           | p3 node-state    |
| FAT32         | ext4                 | dynamic ext4     |
+---------------+----------------------+------------------+
```

## 14.1 EFI System Partition

`p1` SHALL contain the UKI.

The standard fallback boot path SHALL be:

```text
/EFI/BOOT/BOOTX64.EFI
```

## 14.2 Root Partition

`p2` SHALL contain the distribution root filesystem.

Its partition identity SHALL be deterministic.

Its filesystem UUID SHALL be deterministic.

**LAYOUT-01:** For SoftCloud Node Linux v1, `p2` SHALL be mounted read-write during normal operation.

Runtime mutability of `p2` SHALL NOT redefine the release artifact.

Workload and node-state directories identified by this memorandum SHALL be delegated to `p3`.

A future read-only or verified-root profile MAY supersede this behavior only through an explicit profile or memorandum revision.

## 14.3 State Partition

`p3` SHALL represent mutable node state.

The release process SHALL NOT assume a fixed final bhyve disk size.

The state filesystem SHALL be initialized or expanded according to the actual VM disk size.

Mutable state SHALL include at least:

```text
/var/lib/containerd
/var/lib/kubelet
/var/lib/etcd
/var/log
```

**LAYOUT-02:** Projection of mutable state from `p3` into standard filesystem locations SHALL use systemd-managed bind mounts.

Symbolic links SHALL NOT be used as the state-projection mechanism.

The bind-mount definition and its required propagation semantics SHALL be explicit and version controlled.

Where recursive propagation is required by a consumer, the implementation SHALL apply `rshared` semantics; where non-recursive propagation is sufficient, the implementation SHALL explicitly declare the selected shared propagation mode.

A conforming implementation SHALL establish the bind mount before services consuming the corresponding state path start.

Conceptually:

```text
p3: node-state
│
├── containerd/
├── kubelet/
├── etcd/
└── log/
       │
       ├── bind → /var/lib/containerd
       ├── bind → /var/lib/kubelet
       ├── bind → /var/lib/etcd
       └── bind → /var/log
```

---

# 15. First-Boot State Provisioning

`systemd-repart` SHOULD provide first-boot partition-growth and filesystem-initialization behavior.

A configuration equivalent to:

```ini
[Partition]
Type=linux-generic
Label=node-state
Format=ext4
MountPoint=/var/mnt/state
GrowFileSystem=yes
```

SHALL be maintained.

**STATE-01:** A cloned release image SHALL support different final virtual-disk capacities.

**STATE-02:** Node state SHALL expand without requiring bespoke interactive partitioning.

**STATE-03:** Node state SHALL remain logically separate from the replaceable OS partition.

**STATE-04:** The mechanism SHALL work for both control-plane and worker nodes.

**STATE-05:** The state filesystem SHALL be mounted before state bind mounts are activated.

**STATE-06:** Services consuming `/var/lib/containerd`, `/var/lib/kubelet`, `/var/lib/etcd`, or `/var/log` SHALL be ordered after their corresponding state mounts.

---

# 16. Machine Bootstrap Contract

The distribution SHALL implement:

```text
softcloud.node/v1
```

This contract replaces `cloud-init` for the dedicated bhyve profile.

A seed MAY contain information equivalent to:

```yaml
schema: softcloud.node/v1

identity:
  hostname: k8s-w1

network:
  interface: eth0
  address: 192.168.70.12/24
  gateway: 192.168.70.1
  dns:
    - 192.168.70.1

ssh:
  authorized_keys:
    - ssh-ed25519 ...

class:
  name: kubernetes-node
```

## 16.1 Allowed Responsibilities

`softcloud-seed` SHALL be permitted to configure:

1. hostname;
2. network configuration;
3. SSH authorized keys;
4. machine-local identity;
5. profile-approved machine-local configuration.

## 16.2 Forbidden Responsibilities

The seed SHALL NOT contain or directly establish:

1. Kubernetes cluster membership;
2. reusable `kubeadm` tokens;
3. Kubernetes private CA keys;
4. etcd state;
5. container runtime workload state;
6. a shared static machine ID.

---

# 17. Seed Service Ordering

`softcloud-seed` SHALL use systemd device activation rather than `systemd-udev-settle.service`.

The dependency graph SHALL include:

```ini
[Unit]
Description=SoftCloud Seed Initializer
DefaultDependencies=no

Requires=dev-disk-by\x2dlabel-CIDATA.device
After=dev-disk-by\x2dlabel-CIDATA.device local-fs.target
Before=sysinit.target systemd-networkd.service sshd.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/lib/softcloud/softcloud-seed --mount /dev/disk/by-label/CIDATA
StandardOutput=journal+console

[Install]
WantedBy=sysinit.target
```

Where required to write the persistent initialization marker, the implementation SHALL additionally establish an explicit dependency on the mounted node-state filesystem.

The exact dependency graph MAY contain additional required units, but SHALL preserve the following invariants.

**SEED-01:** Seed schema validation SHALL finish before seed data is applied.

**SEED-02:** Network configuration SHALL be written before `systemd-networkd` configures the node interface.

**SEED-03:** SSH authorized keys SHALL be installed before the SSH daemon accepts connections.

**SEED-04:** Invalid seed data SHALL fail closed.

**SEED-05:** Seed processing SHALL emit diagnostic information to the journal and serial console.

**SEED-06:** Seed processing SHALL be safe against unintended repeated application.

**SEED-07:** Upon successful first-time configuration, `softcloud-seed` SHALL create a persistent initialization marker on the `node-state` filesystem.

The marker SHALL prevent normal seed initialization from executing again on subsequent boots when the original `CIDATA` volume remains attached.

The marker SHOULD contain at least:

```text
softcloud.node schema version
seed digest
initialization completion state
```

A suitable location is:

```text
/var/mnt/state/.softcloud/seed-initialized
```

or an equivalent path owned by the SoftCloud bootstrap subsystem.

If an attached seed differs from the seed digest recorded by the initialization marker, the bootstrap implementation SHALL NOT silently reconfigure the machine.

It SHALL either:

1. fail with a diagnostic indicating seed identity mismatch; or
2. require an explicit reset/reprovisioning operation defined by the implementation.

`CIDATA` presence alone SHALL NOT cause repeated initialization.

---

# 18. Machine Identity

The golden image SHALL contain no shared active machine identity.

**MID-01:** `/etc/machine-id` SHALL be empty or in a documented systemd uninitialized state in the release artifact.

**MID-02:** First boot SHALL generate or establish a unique machine ID.

**MID-03:** VM clones SHALL receive different machine IDs.

**MID-04:** Persistent SSH host identity SHALL NOT be duplicated across cloned machines.

**MID-05:** VM-specific UUIDs SHALL be supplied by the virtualization environment.

For a three-node laboratory:

```text
machine-id(cp1) != machine-id(w1)
machine-id(cp1) != machine-id(w2)
machine-id(w1)  != machine-id(w2)
```

SHALL hold.

---

# 19. Deterministic Filesystem Construction

## 19.1 Root Tree Normalization

Before filesystem generation:

**DET-01:** File ownership SHALL be normalized.

**DET-02:** File and directory ordering SHALL be deterministic.

**DET-03:** Relevant timestamps SHALL be clamped to `SOURCE_DATE_EPOCH`.

A normalization mechanism equivalent to:

```sh
find rootfs \
    -exec touch --no-dereference \
    --date="@${SOURCE_DATE_EPOCH}" {} +
```

MAY be used.

## 19.2 ext4

Filesystem generation SHALL control nondeterministic values.

An operation equivalent to:

```sh
mke2fs \
    -d rootfs/ \
    -t ext4 \
    -O ^has_journal,dir_index \
    -U "${ROOT_UUID}" \
    -E nodiscard,lazy_itable_init=0,lazy_journal_init=0 \
    root.img
```

MAY be used.

**DET-04:** Root filesystem UUIDs SHALL NOT come from runtime randomness.

**DET-05:** Lazy inode-table initialization SHALL NOT introduce post-build differences into an artifact declared reproducible.

**DET-06:** Filesystem creation parameters SHALL be recorded or derivable from version-controlled configuration.

## 19.3 GPT

The image builder SHALL explicitly control:

```text
disk GUID
partition GUIDs
partition type GUIDs
partition start LBAs
partition sizes
alignment
```

**DET-07:** Partition GUIDs SHALL NOT be generated randomly during an accepted build.

**DET-08:** Partition placement SHALL use explicit deterministic alignment.

The default SHOULD use 1 MiB alignment.

---

# 20. Reproducibility Levels

The project SHALL classify reproducibility using:

```text
R0  identical resolved dependency closure
R1  identical normalized rootfs manifest
R2  identical kernel and UKI digests
R3  identical filesystem images
R4  identical complete raw disk image
```

**REP-01:** Every release SHALL declare its achieved reproducibility level.

**REP-02:** R4 SHALL be the target for a fully accepted SoftCloud Node Linux release.

**REP-03:** An R4 claim SHALL require two independent clean builds producing identical cryptographic digests for the complete raw image.

**REP-04:** R2 and higher SHALL require bit-identical UKI output, including deterministic PE/COFF metadata required by BOOT-07.

Conceptually:

```text
clean build environment A
          ↓
       image A
          ↓
        SHA-A

clean build environment B
          ↓
       image B
          ↓
        SHA-B

SHA-A == SHA-B
```

---

# 21. Release Artifacts

A release SHALL produce at least:

```text
artifacts/<release>/
├── softcloud-node-amd64.raw
├── BOOTX64.EFI
├── kernel.config
├── artifact-manifest.json
├── sbom.spdx.json
├── provenance.json
└── SHA256SUMS
```

A normalized rootfs archive MAY additionally be published:

```text
rootfs.tar.zst
```

## 21.1 Artifact Manifest

`artifact-manifest.json` SHALL contain or reference:

1. schema version;
2. distribution identity;
3. release identity;
4. architecture;
5. profile;
6. Linux version;
7. Linux source digest;
8. kernel configuration digest;
9. `vmlinux` digest;
10. UKI digest;
11. root filesystem digest;
12. disk image digest;
13. Debian snapshot identity;
14. Debian package-lock digest;
15. Kubernetes version;
16. containerd version;
17. runc version;
18. toolchain-lock digest;
19. builder identity;
20. `SOURCE_DATE_EPOCH`;
21. source repository revision;
22. acceptance-test results;
23. achieved reproducibility level.

The manifest SHALL validate against:

```text
softcloud.artifact/v1
```

or its explicitly versioned successor.

---

# 22. SBOM and Provenance

**SUP-01:** Every accepted release SHALL contain an SBOM.

**SUP-02:** SPDX JSON SHOULD be the canonical initial SBOM representation.

**SUP-03:** Every accepted release SHALL contain build provenance.

**SUP-04:** Provenance SHALL identify the repository revision used to build the artifact.

**SUP-05:** Provenance SHALL identify the canonical builder.

**SUP-06:** Provenance SHALL identify all lockfile digests.

**SUP-07:** An artifact whose provenance cannot be associated with its source inputs SHALL NOT be accepted.

---

# 23. Repository Layout

The repository SHOULD converge on:

```text
os-linux/
├── MEMORANDUM.md
├── README.md
├── os.yaml
│
├── schemas/
│   ├── softcloud.os.v1.schema.json
│   ├── softcloud.artifact.v1.schema.json
│   └── softcloud.node.v1.schema.json
│
├── locks/
│   ├── sources.lock
│   ├── debian.lock
│   ├── kubernetes.lock
│   ├── containerd.lock
│   └── toolchain.lock
│
├── builder/
│   └── profile.yaml
│
├── kernel/
│   ├── config/
│   │   ├── linux-bhyve.config
│   │   └── linux-kubernetes-bhyve.config
│   ├── patches/
│   └── build.sh
│
├── userspace/
│   ├── debian/
│   │   ├── packages.in
│   │   ├── packages.lock
│   │   └── build-rootfs.sh
│   └── overlay/
│
├── boot/
│   ├── cmdline.txt
│   ├── build-uki.sh
│   └── os-release
│
├── profiles/
│   └── kubernetes-node/
│       ├── profile.yaml
│       ├── sysctl.conf
│       ├── containerd.toml
│       ├── repart.d/
│       └── systemd/
│
├── seed/
│   ├── softcloud-seed
│   ├── softcloud-seed.service
│   └── schema/
│
├── runtime/
│   └── bhyve/
│       ├── build-image.sh
│       ├── make-seed.sh
│       └── boot-test.sh
│
├── tools/
│   ├── resolve-sources.py
│   ├── validate-locks.py
│   ├── normalize-rootfs.py
│   ├── make-manifest.py
│   └── make-sbom.py
│
├── tests/
│   ├── kernel/
│   ├── rootfs/
│   ├── boot/
│   ├── seed/
│   ├── kubernetes/
│   └── reproducibility/
│
└── artifacts/
```

Equivalent organization MAY be used where repository evolution requires it, provided the ownership boundaries defined by this memorandum remain explicit.

---

# 24. Acceptance Criteria

## SN-01 — Verified Inputs
Every network-retrieved build input SHALL have a cryptographic identity and SHALL be verified before use.

## SN-02 — No Moving Inputs
No moving `latest`, `stable`, `current`, branch-tip, or equivalent reference SHALL participate in an accepted build without first resolving to an immutable locked identity.

## SN-03 — Kernel Source
The kernel source SHALL match `sources.lock`.

## SN-04 — Boot Configuration
The kernel and UKI SHALL satisfy the bhyve boot contract. The machine SHALL boot without unmanaged persistent UEFI NVRAM kernel arguments.

## SN-05 — Cilium/BTF
The kernel SHALL satisfy the selected Kubernetes/Cilium requirements. Generated BTF SHALL successfully parse with `bpftool` or an equivalent validator.

## SN-06 — CPU Mitigations
CPU security mitigations SHALL remain enabled for the normal profile unless explicitly waived by a distinct experimental profile.

## SN-07 — Package Closure
Every package contained in the root filesystem SHALL be represented by an accepted package or artifact lock.

## SN-08 — OS Identity
`/etc/os-release` SHALL identify the system as SoftCloud Node Linux.

## SN-09 — Init
PID 1 SHALL be `systemd`.

## SN-10 — cgroup v2
The running node SHALL use the cgroup v2 hierarchy required by the profile.

## SN-11 — CRI
The `containerd` CRI endpoint SHALL respond successfully.

## SN-12 — systemd Cgroups
`containerd` and `kubelet` SHALL use compatible `systemd` cgroup management.

## SN-13 — Swap
Swap SHALL be unavailable or disabled according to the Kubernetes-node profile.

## SN-14 — IP Forwarding
Required Linux forwarding settings SHALL be active.

## SN-15 — Machine Identity
The release artifact SHALL contain no shared active machine identity. Three independently instantiated laboratory nodes SHALL have distinct machine IDs.

## SN-16 — bhyve Boot
The UKI SHALL boot directly under bhyve/EDK2 without requiring persistent boot-entry configuration.

## SN-17 — VirtIO Block
The root disk SHALL operate through the selected bhyve VirtIO block interface.

## SN-18 — VirtIO Network
The network interface SHALL operate through the selected bhyve VirtIO network interface.

## SN-19 — Serial Console
The kernel and userspace SHALL expose a functioning serial console through `ttyS0`.

## SN-20 — Seed Validation
Seed data SHALL validate against `softcloud.node/v1` before configuration is applied. Invalid input SHALL fail closed.

## SN-21 — SSH Authentication
A fresh node SHALL accept SSH only according to the profile's approved authentication policy. Seed-provided public keys SHALL be supported. Password-based remote root authentication SHALL NOT be enabled by default.

## SN-22 — kubeadm Preflight
`kubeadm` preflight SHALL succeed on a clean node. `/opt/cni/bin/loopback` SHALL exist.

## SN-23 — Kubernetes Join
A worker instantiated from the accepted image SHALL successfully join the target Kubernetes cluster.

## SN-24 — Cilium Health
Cilium SHALL report healthy after deployment.

## SN-25 — Pod Connectivity
Cross-node Pod communication SHALL pass the laboratory connectivity test.

## SN-26 — Service Connectivity
ClusterIP Service routing SHALL function.

## SN-27 — DNS
CoreDNS resolution SHALL function for Kubernetes service names.

## SN-28 — SBOM
The accepted release SHALL include an SBOM.

## SN-29 — Artifact Contract
`artifact-manifest.json` SHALL validate against the selected `softcloud.artifact` schema.

## SN-30 — Reproducibility
An independent clean rebuild SHALL meet the release's declared reproducibility level.

## SN-31 — Build Self-Containment
After the fetch-and-verify phase, the canonical builder SHALL successfully build with external network access disabled.

## SN-32 — Deterministic UKI
Two clean builds with identical locked inputs and identical `SOURCE_DATE_EPOCH` SHALL produce identical `BOOTX64.EFI` digests. PE/COFF build timestamps SHALL NOT vary with wall-clock build time.

## SN-33 — bpffs Propagation
Before `containerd` and `kubelet` start:
1. `/sys/fs/bpf` SHALL be mounted as `bpf`;
2. the mount SHALL have shared propagation semantics.

## SN-34 — State Projection
A booted node SHALL demonstrate that mutable node-state paths are bind-mounted from `p3`. The verifier SHALL confirm that these paths are mount points rather than symbolic links. At minimum: `/var/lib/containerd`, `/var/lib/kubelet`, `/var/lib/etcd`, and `/var/log` SHALL comply.

## SN-35 — Seed One-Shot Semantics
After first successful initialization:
1. an initialization marker SHALL exist on `p3`;
2. rebooting with the same `CIDATA` attached SHALL NOT reapply seed configuration;
3. a changed seed SHALL NOT be silently applied over an existing initialization marker.

---

# 25. Integration Test Topology

The primary laboratory acceptance topology SHALL use three machines instantiated from the same OS artifact:

```text
                     softcloud-node-amd64.raw
                               |
                    identical artifact digest
                               |
                 +-------------+-------------+
                 |             |             |
                 v             v             v
             k8s-cp1        k8s-w1        k8s-w2
                 |             |             |
              seed A         seed B         seed C
                 |             |             |
                 +-------------+-------------+
                               |
                          Kubernetes
                               |
                            Cilium
```

The OS artifact digest SHALL be identical for all three nodes before machine-local state is initialized.

---

# 26. Initial Network Contract

The first `freebsd-laboratory` integration MAY use:

```text
Node network:     192.168.70.0/24
Pod network:      10.244.0.0/16
Service network:  10.96.0.0/12
Cluster domain:   cluster.local
```

These values belong to laboratory topology and cluster configuration.

They SHALL NOT become hard dependencies of the generic SoftCloud Node Linux artifact.

---

# 27. Initial Implementation Baseline

The first implementation is intended to use:

```text
Linux family:       6.18 LTS
Userspace source:   Debian 13
Init:               systemd
Runtime:            containerd + runc
Kubernetes family:  1.36
CNI:                Cilium
Filesystem:         ext4
Firmware:           EDK2
```

Exact patch versions and source identities SHALL reside in lockfiles.

If a value in this section conflicts with a lockfile used for an accepted build, one of the following SHALL occur before release:

1. this memorandum is revised; or
2. the implementation is brought back into conformity.

Unreviewed divergence SHALL NOT be accepted.

---

# 28. Implementation Sequence

Implementation SHOULD proceed in the following dependency order.

## Phase 1 — Specification and Builder
1. Freeze this memorandum.
2. Define `softcloud.node/v1`.
3. Define the canonical Linux builder.
4. Create `toolchain.lock`.
5. Remove existing source/version inconsistencies.

## Phase 2 — Kernel and UKI
1. Lock Linux source.
2. Create `linux-kubernetes-bhyve.config`.
3. Integrate BTF generation.
4. Verify BTF using `bpftool`.
5. Create the UKI.
6. Embed the deterministic root reference.
7. Verify `rootwait`.
8. Normalize PE/COFF timestamps from `SOURCE_DATE_EPOCH`.
9. Demonstrate stateless EDK2 boot.
10. Demonstrate bit-identical UKI rebuild.

## Phase 3 — Root Filesystem
1. Lock the Debian snapshot.
2. Resolve the complete package closure.
3. Build with `mmdebstrap`.
4. Apply the SoftCloud overlay.
5. Execute `ldconfig`.
6. Install locked runtime binaries.
7. Install locked Kubernetes binaries.
8. Install CNI loopback.
9. Configure bpffs boot mounting.
10. Configure shared bpffs propagation.
11. Normalize the filesystem tree.

## Phase 4 — Deterministic Image
1. Generate deterministic GPT.
2. Generate deterministic ESP.
3. Generate deterministic root ext4.
4. Define expandable state storage.
5. Integrate `systemd-repart`.
6. Create systemd bind mount units.
7. Define mount propagation semantics.
8. Generate the artifact manifest.

## Phase 5 — Machine Bootstrap
1. Implement `softcloud-seed`.
2. Implement schema validation.
3. Implement direct CIDATA device-unit activation.
4. Initialize machine identity.
5. Configure networking.
6. Configure hostname.
7. Configure SSH authorization.
8. Write persistent first-boot marker.
9. Verify changed-seed rejection semantics.

## Phase 6 — bhyve Verification
1. Boot from the UKI.
2. Verify serial console.
3. Verify VirtIO block.
4. Verify VirtIO networking.
5. Verify systemd.
6. Verify cgroup v2.
7. Verify state expansion.
8. Verify state bind mounts.
9. Verify bpffs and mount propagation.
10. Verify seed one-shot behavior.

## Phase 7 — Kubernetes Verification
1. Verify CRI.
2. Run `kubeadm` preflight.
3. Initialize `k8s-cp1`.
4. Join `k8s-w1`.
5. Join `k8s-w2`.
6. Deploy Cilium.
7. Verify Pod networking.
8. Verify Services.
9. Verify DNS.

## Phase 8 — Supply Chain and Release
1. Perform network-disabled build.
2. Generate SBOM.
3. Generate provenance.
4. Generate artifact manifest.
5. Perform an independent clean rebuild.
6. Determine R0-R4 reproducibility level.
7. Publish only after all applicable SN acceptance gates pass.

---

# 29. Upgrade Model

SoftCloud Node Linux SHALL prefer artifact replacement over in-place mutation.

The intended lifecycle is:

```text
lock update
    ↓
new build
    ↓
verification
    ↓
new artifact
    ↓
node replacement or controlled reprovisioning
```

Routine administration SHOULD NOT use:

```text
SSH
  ↓
apt upgrade
  ↓
manual package replacement
  ↓
continued use of mutated node
```

**UPG-01:** Security or Kubernetes updates SHOULD result in a new OS artifact.

**UPG-02:** Manual modification of an instantiated node SHALL NOT alter the definition of the accepted release artifact.

**UPG-03:** Nodes modified interactively MAY be used for experiments but SHALL NOT be treated as pristine conformance instances.

**UPG-04:** The fact that `p2` is mounted read-write in v1 SHALL NOT authorize routine in-place OS package upgrades as the normal lifecycle mechanism.

---

# 30. Non-Goals

The initial release SHALL NOT attempt to provide:

1. a general-purpose desktop environment;
2. a conventional interactive OS installer;
3. arbitrary package-management workflows on production nodes;
4. automatic Kubernetes cluster creation inside the image;
5. cloud-provider-specific initialization;
6. multi-distribution compatibility;
7. arbitrary hypervisor compatibility;
8. persistent machine identity in the golden image;
9. general-purpose `cloud-init` compatibility;
10. in-place mutable release upgrades.

Such capabilities MAY be introduced by future profiles or memorandum revisions.

---

# 31. Change Control

Changes are divided into three classes.

## 31.1 Architectural Changes
An architectural change modifies one or more of:
- artifact ownership
- trust boundaries
- boot model
- identity model
- storage model
- provisioning contract
- cluster/OS boundary
- reproducibility model
- supported execution model

Architectural changes SHALL require revision of this memorandum.

## 31.2 Baseline Changes
A baseline change includes:
- Linux patch version
- Kubernetes patch version
- containerd version
- runc version
- Debian snapshot timestamp
- toolchain version
- package closure

Baseline changes SHALL update the relevant lockfiles and SHALL rerun all applicable acceptance criteria. A memorandum revision is required when the new baseline invalidates a normative architectural requirement.

## 31.3 Implementation Changes
Implementation-only changes MAY occur without a memorandum revision when they preserve all normative behavior and contracts. Examples include internal script refactoring, test implementation improvements, build performance improvements, error message improvements, and non-semantic repository reorganization.

---

# 32. Completion Condition

SoftCloud Node Linux 1.0 SHALL be considered implemented when:

```text
one locked OS definition
        ↓
one network-isolated canonical build
        ↓
one deterministic UKI
        ↓
one reproducible bhyve raw image
        ↓
three independently instantiated machines
        ↓
three unique machine identities
        ↓
persistent node-state bind mounts
        ↓
shared node bpffs
        ↓
one-shot seed initialization
        ↓
one kubeadm Kubernetes cluster
        ↓
healthy Cilium
        ↓
successful Pod / Service / DNS tests
        ↓
SBOM + provenance + artifact manifest
        ↓
all applicable SN-01 through SN-35 PASS
```

The architectural invariant is:

> **The machine changes; the operating-system artifact does not.**
