# Render generated Manim code in an isolated worker

**Status:** Proposed

Bayan will execute generated Manim scene code outside the application host, in
an isolated worker with no network access by default, no application secrets,
an explicit temporary workspace, bounded resources, and a controlled artifact
output. The host will exchange serialized requests and results with the worker
instead of importing or executing generated code directly.

## Context

The North Star includes model-assisted scene generation. Manim scenes are
executable Python, so model output must be treated as untrusted even when it
was produced by a trusted provider or passed an initial validation step. A
render can also fail through ordinary bugs, resource exhaustion, or native
dependency problems.

## Decision

Use a separate worker boundary for rendering. The first implementation may use
a constrained subprocess if that is the smallest reliable vertical slice; a
container or stronger sandbox can replace the worker mechanism without changing
the application-facing contract.

The worker receives only the scene source or approved scene representation,
declared assets, and render configuration. It returns structured status,
diagnostics, and artifacts from an allowlisted output location. Network access,
ambient credentials, and access to the host filesystem are denied by default.

## Options considered

| Option | Decision | Reason |
| --- | --- | --- |
| Execute in the application process | Rejected | A scene failure or malicious operation can compromise orchestration and secrets. |
| Unconstrained child process | Rejected | It separates crashes but does not provide a sufficient security or resource boundary. |
| Constrained subprocess | First-slice option | Small operational footprint while preserving a process boundary; requires careful OS-level limits. |
| Container or dedicated sandbox worker | Long-term option | Stronger isolation and repeatability at the cost of operational complexity. |

## Consequences

- The renderer must define a serialized request/result contract.
- Render jobs need timeouts, resource limits, cancellation, and failure-stage
  reporting.
- Assets and output paths must be explicit; the worker must not inherit the
  host’s environment or working directory by accident.
- Security policy becomes part of renderer design and deployment, not a prompt
  instruction.
- A stronger sandbox can be introduced later without coupling the content
  domain to a particular runtime.

## Not decided yet

This record does not choose a container runtime, queue, deployment platform, or
exact Linux sandbox mechanism. Those choices should be recorded only when the
first render worker has concrete operational requirements.
