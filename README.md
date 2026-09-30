# SoftCloud Node Linux

Welcome to **SoftCloud Node Linux**, a dedicated, reproducible Linux distribution engineered specifically for Kubernetes nodes executed as FreeBSD `bhyve` virtual machines, published at [linux.softcloud.dev](https://linux.softcloud.dev/).

SoftCloud Node Linux is neither a customized Ubuntu installation nor a generic Debian server image. It is a purpose-built, deterministic operating system artifact produced by [`soft-cloud-dev/os-linux`](https://github.com/soft-cloud-dev/os-linux) and consumed directly by [`soft-cloud-dev/freebsd-laboratory`](https://github.com/soft-cloud-dev/freebsd-laboratory).

---

## Architectural Principles & Organizational Pillars

In alignment with the core engineering standards of the Software Cloud organization, SoftCloud Node Linux is governed by four primary pillars:

1. **Cryptographic Reproducibility**:
   All dependencies and build inputs resolve to immutable, cryptographic SHA-256 digests (`--require-hashes`, `--only-binary=:all:`). The release pipeline targets level **R4** reproducibility, requiring two independent clean builds to yield bit-identical raw disk images (`softcloud-node-amd64.raw`).

2. **Hermetic & Isolated Execution**:
   Build processes strictly isolate the network fetch-and-verify phase from the canonical builder. Canonical kernel, userspace (`mmdebstrap`), and UKI compilation execute with external network access completely disabled (`BUILD-01` through `BUILD-05`).

3. **Strict Profile Conformance**:
   Every release artifact and build pipeline adheres to formal JSON schemas (`softcloud.os/v1`, `softcloud.node/v1`, and `softcloud.artifact/v1`). Standalone preflight validators enforce structural integrity, kernelspec compliance, and schema validity before artifact promotion.

4. **Continuous Delivery & Formal Provenance**:
   Every commit and release is built, validated, and signed through automated CI/CD. Releases generate comprehensive software supply chain artifacts, including SPDX SBOMs, SLSA-grade provenance manifests, and cryptographic checksum manifests (`SHA256SUMS`).

---

## Core System Architecture

```text
                     +-----------------------------------+
                     |      soft-cloud-dev/os-linux      |
                     +-----------------------------------+
                                       |
                       (Hermetic Build & Verification)
                                       v
                          softcloud-node-amd64.raw
                                       |
                   +-------------------+-------------------+
                   |                   |                   |
                   v                   v                   v
              k8s-cp1 (bhyve)     k8s-w1 (bhyve)      k8s-w2 (bhyve)
                   |                   |                   |
              CIDATA Seed A       CIDATA Seed B       CIDATA Seed C
                   |                   |                   |
                   +-------------------+-------------------+
                                       |
                     +-----------------------------------+
                     |    freebsd-laboratory Cluster     |
                     |         Kubernetes + Cilium       |
                     +-----------------------------------+
```

- **Boot Pipeline**: Direct UEFI boot via EDK2 loading a self-contained Unified Kernel Image (UKI) at `/EFI/BOOT/BOOTX64.EFI`. Does not depend on persistent NVRAM variables.
- **Kernel Configuration**: Tailored Linux 6.18 LTS profile (`kernel/config/linux-kubernetes-bhyve.config`) featuring built-in VirtIO block/PCI/net drivers, ext4 root, cgroup v2, and verified eBPF BTF (`CONFIG_DEBUG_INFO_BTF=y`).
- **Disk Layout & State Separation**: Three-partition GPT containing:
  - `p1` (ESP, FAT32): Self-contained UKI.
  - `p2` (OS root, ext4): Deterministic release filesystem.
  - `p3` (node-state, dynamic ext4): Provisioned and auto-expanded via `systemd-repart`, projecting state into `/var/lib/containerd`, `/var/lib/kubelet`, `/var/lib/etcd`, and `/var/log` using systemd bind mounts.
- **Machine Bootstrap (`softcloud.node/v1`)**: Clean `cloud-init` replacement utilizing systemd device activation (`dev-disk-by\x2dlabel-CIDATA.device`) and a persistent one-shot initialization marker preventing accidental reconfiguration.
- **Runtime Stack**: Native `containerd` and `kubelet` under the `systemd` cgroup driver, with early shared `/sys/fs/bpf` mount propagation (`rshared`) satisfying Cilium CNI prerequisites before container daemon activation.

---

## Documentation Roadmap

- **[Introduction](introduction.md)**: Background, operational scope, and the system boundary dividing artifact producer (`os-linux`) and consumer (`freebsd-laboratory`).
- **[SoftCloud Node Linux Memorandum](memorandum.md)**: The normative specification baseline (`SOFTCLOUD-NODE-LINUX-1.0`) establishing all 32 architectural sections and 35 acceptance criteria (`SN-01` through `SN-35`).
- **[Adoption Plan](adoption-plan.md)**: Comprehensive, phased operational adoption roadmap based on organizational rules, covering implementation milestones, verification gates, supply chain conformance, and rollout runbooks.
- **[Computational Verification](notebooks/experiment.ipynb)**: Executable runtime validation notebook executed during the build pipeline under the canonical `jb2-python` kernel.
