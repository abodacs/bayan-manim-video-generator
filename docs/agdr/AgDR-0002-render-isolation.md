# Render generated Manim code in an isolated worker

**Status:** Accepted for the first render-worker slice

Bayan executes generated Manim scene code outside the application host, in an
isolated worker with no network access by default, no application secrets, an
explicit temporary workspace, bounded resources, and controlled artifact
outputs. The host exchanges serialized requests and results with the worker
instead of importing or executing generated code directly.

## Context

Manim scenes are executable Python, so model output must be treated as
untrusted even when it was produced by a trusted provider or passed an initial
validation step. A render can also fail through ordinary bugs, resource
exhaustion, or native dependency problems.

## Decision

The first worker implementation uses a Docker-compatible OCI container. The
container image is built from digest-pinned Python and uv images and a dated
Debian package snapshot. Its final stage contains only the runtime libraries,
FFmpeg, Arabic fonts, and the locked Python environment; build compilers and
development headers stay in the builder stage.

Each smoke or render phase follows an explicit lifecycle:

1. Create a named container with the security policy.
2. Start it with an explicit command and stream bounded output to the run log.
3. Remove it with `docker rm --force` in a `finally` path, including timeout
   and process-failure paths.

The worker receives only the read-only scene mount and the declared output
mount. It runs as a non-root UID, has no network, a read-only root filesystem,
all Linux capabilities dropped, `no-new-privileges`, bounded PIDs/CPU/memory,
and a writable no-exec temporary filesystem. The Docker CLI receives an
allowlisted environment instead of the host environment. Render results are
represented by a typed manifest with phase status, bounded diagnostics,
source hashes, image metadata, and relative artifact paths.

## Options considered

| Option | Decision | Reason |
| --- | --- | --- |
| Execute in the application process | Rejected | A scene failure or malicious operation can compromise orchestration and secrets. |
| Unconstrained child process | Rejected | It separates crashes but does not provide a sufficient security or resource boundary. |
| Constrained subprocess | Rejected for the first slice | It would require platform-specific limits before the renderer contract is proven. |
| Docker-compatible OCI worker | Accepted | It gives this repository a repeatable, testable boundary with explicit mounts and limits. |
| Dedicated stronger sandbox | Deferred | It may be needed for hostile multi-tenant deployment after operational requirements are known. |

## Consequences

- The renderer has a serialized request/result contract instead of importing
  generated scene code into the host.
- Render jobs have timeouts, output limits, cancellation-by-cleanup, and
  failure-stage reporting.
- Assets and output paths are explicit; the worker does not inherit the host
  environment or working directory by accident.
- The container image and source hashes make a local result reproducible and
  diagnosable.
- CI must build the image and perform the Arabic smoke render, not only run
  Python unit tests.
- Docker is a runtime prerequisite for this first slice. A queue, remote
  worker protocol, rootless deployment policy, and stronger sandbox remain
  separate decisions.

## Not decided yet

This record does not choose a job queue, deployment platform, remote artifact
store, or production multi-tenant sandbox. Those choices should be recorded
when the render-job lifecycle and hosting requirements are implemented.
