# Rust MicroVM Sandbox for AI Agents — Design Plan

A plan for building an E2B‑style sandbox runtime in Rust. Target: per‑agent, hardware‑isolated micro‑sandboxes that cold‑start in **<100 ms**, run anywhere (laptop, bare metal, cloud), and scale to **hundreds of concurrent instances per host**.

---

## 1. What E2B actually is (baseline to beat)

From research ([E2B](https://e2b.dev/), [Firecracker vs QEMU](https://e2b.dev/blog/firecracker-vs-qemu), [Dwarves breakdown](https://memo.d.foundation/breakdown/e2b), [microVM 2026 survey](https://emirb.github.io/blog/microvm-2026/)):

- Each sandbox = a **Firecracker microVM** (AWS's Rust VMM) with its own kernel + network namespace. Not a container — true hardware isolation via KVM.
- Cold boot ≈ 125 ms; **snapshot restore ≈ 28–200 ms** ([28ms demo](https://dev.to/adwitiya/how-i-built-sandboxes-that-boot-in-28ms-using-firecracker-snapshots-i0k)).
- Templates built from Dockerfiles → baked into rootfs + memory snapshot. A pool of pre‑warmed snapshots is kept hot.
- Orchestrator exposes an SDK (Py/JS). Inside the guest, a long‑running agent process handles code exec, filesystem, process, pip, network.
- Runs only in E2B cloud by default (self‑host is possible but heavy).

**Gaps we target**: runs locally on a laptop (macOS dev loop), OSS first, Rust end‑to‑end, faster pool churn, sub‑100 ms p50 acquire, no cloud dep.

---

## 2. Non‑goals

- Not a general VM platform. No GPU passthrough, no live migration, no Windows guests.
- Not a container runtime. We are **not** competing with runc/containerd on Linux‑namespace isolation.
- Not a K8s scheduler. Single‑host orchestrator first; multi‑host is a later concern.

---

## 3. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Client SDK (Rust, Py, TS)  ── gRPC/HTTP ──► Orchestrator    │
└──────────────────────────────────────────────────────────────┘
                                                │
                                ┌───────────────┼────────────────┐
                                ▼               ▼                ▼
                          Pool Manager    Template Store   Metrics/Logs
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
                 VMM #1       VMM #2      VMM #N     (one per sandbox)
                 (KVM)        (KVM)       (KVM)
                    │           │           │
                 guest-agent  guest-agent  guest-agent  (vsock RPC)
```

### 3.1 Hypervisor layer (`zed-vmm`)

- **Fork/vendor Firecracker or Cloud Hypervisor** rather than write a VMM from scratch. Both are Rust, KVM‑based, audited. Firecracker is leaner (125 ms boot, fewer devices); Cloud Hypervisor has better snapshot tooling. **Decision: start with Firecracker** for boot speed, keep the VMM pluggable behind a trait.
- On macOS dev loops, fall back to **Hypervisor.framework** via `hvf` (no KVM on Darwin). This is the "runs locally" story. Accept 200–400 ms boots on macOS; treat Linux/KVM as prod target.
- Jailer equivalent: drop caps, chroot, seccomp‑bpf, cgroup v2 (cpu, memory, pids, io).

### 3.2 Guest image (`zed-rootfs`)

- Minimal kernel (custom `.config`, ~5–8 MB bzImage, virtio only, no modules).
- Rootfs = Alpine or distroless + `zed-guest-agent` as PID 1 (or init → agent).
- Templates defined via **OCI images** (Dockerfile compatible). Builder converts OCI layers → ext4 rootfs + optional overlay.

### 3.3 Guest agent (`zed-guest-agent`)

- Static Rust binary, PID 1 inside guest.
- Transport: **vsock** (no guest networking required for control plane).
- Exposes: exec(argv, env, stdin stream), fs read/write/watch, port forward, tty attach, process signal, snapshot‑checkpoint hook.
- Code execution: subprocess model, not an in‑process interpreter. Python/Node/Bash kernels are just long‑lived child processes; we stream stdout/stderr frames back over vsock. (Same mental model as E2B's code‑interpreter SDK.)

### 3.4 Orchestrator (`zed-orchestrator`)

Single‑host Rust daemon. Responsibilities:
1. **Pool manager** — keep N warm snapshots per template ready to restore. Refill on drain.
2. **Acquire/release API** — gRPC + HTTP. `acquire(template, ttl) → sandbox_id, vsock_addr`.
3. **Lifecycle** — enforce TTL, idle timeout, resource caps; clean teardown (unmap memfd, remove tap, rm cgroup).
4. **Template registry** — content‑addressed store of `{kernel, rootfs, memfile}` tuples.
5. **Networking** — per‑VM tap + Linux bridge + nftables egress policy (default‑deny with allowlist).

### 3.5 SDK

- Rust core crate `zed-sdk` (the source of truth).
- Py/TS bindings via **PyO3** and **napi-rs**. Keep API surface tiny: `Sandbox::new`, `.exec`, `.fs`, `.close`.

---

## 4. The <100 ms boot story

Cold boot a kernel is ~1 s. You don't cold boot — you **restore**.

1. **Build time**: for each template, boot once, run init to a known idle state, capture memory snapshot + CoW‑friendly memfile + device state.
2. **Serve time**: `MAP_PRIVATE` memfile (kernel demand‑pages pages as guest touches them), load CPU/device state, `KVM_RUN`. Measured 28 ms in public demos — plausible budget: **15 ms VMM setup + 20 ms restore + 10 ms agent ready = ~45 ms p50, <100 ms p99**.
3. **Pool**: keep k warm *restored* VMs idle per template, so acquire is queue pop + TTL stamp → ~1 ms. Snapshot restore is for refill and for cold templates.
4. **Uniqueness**: restored VMs share entropy/MAC/hostname. Inject randomness on resume (see [Restoring Uniqueness in MicroVM Snapshots](https://ar5iv.labs.arxiv.org/html/2102.12892)) — reseed `/dev/urandom`, regen machine‑id, re‑assign MAC from orchestrator.

---

## 5. Scale: hundreds per host

- Firecracker reports ~150 microVMs/sec create rate on one host; 100s concurrent is well within envelope.
- Memory is the real cap. With 128 MB guests and CoW memfile sharing, 256 sandboxes ≈ 32 GB worst case but far less in practice because most guest pages are read‑only kernel/rootfs pages shared across VMs (`MAP_PRIVATE` on the same backing file).
- CPU: pin VMMs to shared pool, rely on KVM overcommit. Use cgroup `cpu.weight` not hard pinning.
- I/O: virtio‑blk on a single ext4 image per template, overlay for writes (virtio‑fs overlay or block‑level overlay via dm‑snapshot).

---

## 6. Security model

- **Hardware isolation** via KVM — guest kernel compromise ≠ host compromise.
- **Jailer**: seccomp‑bpf filter on the VMM process (Firecracker ships one, we extend), chroot, non‑root uid, no ambient caps.
- **Network**: per‑VM tap in its own netns; default‑deny egress; allowlist by orchestrator policy (e.g. pip index, npm registry).
- **Resource caps**: cgroup v2 per VMM — cpu quota, memory.max, pids.max, io.max.
- **No host FS access** from guest. File exchange via agent RPC only.
- **Attestation** (later): sign template hashes, verify at restore.

Threat model matches E2B's. Explicit non‑defense: side‑channel attacks between co‑tenant VMs (Spectre class) — mitigated by KVM settings, not by us.

---

## 7. Milestones

**M0 — Spike (1 week)**
Fork Firecracker, boot Alpine rootfs, run `echo hi` via vsock. Measure baseline cold boot and snapshot restore on a Linux box. Prove <50 ms restore.

**M1 — Guest agent + exec (2 weeks)**
`zed-guest-agent` as PID 1. gRPC‑over‑vsock. `exec` with streaming stdout/stderr. Rust SDK can run `python -c "print(1)"` end‑to‑end.

**M2 — Orchestrator + pool (2 weeks)**
Single‑host daemon. Template registry (content‑addressed). Warm pool with refill. `acquire/release` HTTP API. p50 acquire <20 ms with warm pool.

**M3 — Template builder (2 weeks)**
OCI image → rootfs + kernel + snapshot pipeline. CLI: `zed build -f Dockerfile -t my-template`. Uniqueness injection on resume.

**M4 — Networking + security hardening (2 weeks)**
Per‑VM tap, netns, nftables egress policy. Seccomp profile. Cgroup caps. Jailer equivalent.

**M5 — SDK polish + macOS HVF backend (2 weeks)**
Py/TS bindings. `hvf` backend for local dev on Apple Silicon. Docs, examples, code‑interpreter‑style quickstart.

**M6 — Load test + public beta (1 week)**
300 concurrent sandboxes on a 32‑core / 128 GB box. Publish numbers.

Total: ~10 weeks to credible beta.

---

## 8. Key risks

| Risk | Mitigation |
|---|---|
| macOS HVF backend is a different VMM than KVM — double maintenance | Keep VMM behind a trait; macOS is dev‑only, not a perf target |
| Snapshot restore breaks with kernel upgrades | Pin kernel per template; rebuild templates on kernel bump |
| Egress policy vs. agent usability (agents want arbitrary HTTP) | Default‑deny + per‑sandbox allowlist token, not global off |
| Memory ballooning / overcommit under load | virtio‑balloon driver in guest, enforce cgroup memory.max |
| Firecracker upstream divergence if we fork | Vendor, don't fork hard; upstream non‑proprietary fixes |

---

## 9. Open questions (need user input before M1)

1. **Primary target host OS** — Linux‑only prod + macOS dev, or also Windows (WSL2 only)?
2. **Licensing** — Apache‑2.0 like Firecracker, or source‑available?
3. **Control plane protocol** — gRPC (ergonomic, streaming) vs plain HTTP+SSE (simpler SDKs)?
4. **Integration with ceo‑agent** — is this meant to replace current agent execution env, or a standalone product?
5. **GPU passthrough** — hard no, or "later" (pushes us toward Cloud Hypervisor over Firecracker)?

---

## Sources

- [E2B — Enterprise AI Agent Cloud](https://e2b.dev/)
- [E2B GitHub](https://github.com/e2b-dev/E2B)
- [E2B code-interpreter](https://github.com/e2b-dev/code-interpreter)
- [Firecracker](https://firecracker-microvm.github.io/)
- [Firecracker vs QEMU — E2B Blog](https://e2b.dev/blog/firecracker-vs-qemu)
- [Firecracker snapshot docs](https://github.com/firecracker-microvm/firecracker/blob/main/docs/snapshotting/snapshot-support.md)
- [28ms sandbox boot via snapshots](https://dev.to/adwitiya/how-i-built-sandboxes-that-boot-in-28ms-using-firecracker-snapshots-i0k)
- [MicroVM Isolation in 2026](https://emirb.github.io/blog/microvm-2026/)
- [Cloud Hypervisor guide](https://northflank.com/blog/guide-to-cloud-hypervisor)
- [Restoring Uniqueness in MicroVM Snapshots (paper)](https://ar5iv.labs.arxiv.org/html/2102.12892)
- [E2B breakdown — Dwarves](https://memo.d.foundation/breakdown/e2b)
