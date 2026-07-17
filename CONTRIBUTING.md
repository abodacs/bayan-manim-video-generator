# Contributing to زتونيات

Thanks for contributing to زتونيات! This repo uses documented decisions and requires lightweight decision records.

> **⚠️ Keep this document in sync with the codebase.** If you change development setup, add new coding standards, or modify the contribution workflow, update this document as part of the same change.

---

## Before You Start

### Required Reading

1. **Read `AGENTS.md`** - Agent participation protocol, ADR/AgDR process
2. **Read `ARCHITECTURE.md`** - System architecture, DDD layers, design constraints
3. **Read relevant ADRs** in `docs/adr/` for subsystems you'll touch

### Decision Records

- **New architecture or major change?** → Draft an ADR in `docs/adr/`
- **Technical choice (library/pattern)?** → Create an AgDR in `docs/agdr/`

See `AGENTS.md` for templates and trigger patterns.

---

## Development Setup

### Prerequisites

- Python 3.11+ (see `.python-version`)
- Git
- Code editor (VS Code recommended)

### Setup Steps

```bash
# 1. Clone the repository
git clone <repository-url>
cd learnyourway

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
uv sync

# 4. Copy environment file
cp .env.example .env
# Edit .env with your values

# 5. Run database setup (if applicable)
python -m backend.app.shared.infrastructure.database
```

---

## Development Commands

### Package Management

```bash
# Install dependencies
uv sync

# Add a new dependency
uv add <package-name>

# Add dev dependency
uv add --dev <package-name>

# Remove dependency
uv remove <package-name>
```

### Running the Application

```bash
# Development server (with auto-reload)
uv run uvicorn backend.app.main:app --reload

# Specific host/port
uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# With debug logging
uv run uvicorn backend.app.main:app --reload --log-level debug
```

### Testing

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_auth.py

# Run specific test
uv run pytest tests/test_auth.py::test_register

# Run with coverage
uv run pytest --cov=backend/app

# Run with verbose output
uv run pytest -v

# Stop at first failure
uv run pytest -x
```

### Database

```bash
# Run DDD validation (checks layer constraints)
python scripts/validate_ddd.py

# View database schema (SQLite)
sqlite3 database.db ".schema"
```

### Docker

```bash
# Build Docker image
docker build -t learnyourway .

# Run container
docker run -p 8000:8000 learnyourway
```

---

## Coding Standards

### Architecture: DDD Layers

Each module follows **vertical slicing** with **Onion-Clean** layers:

```
module/
├── domain/           # Business logic (NO framework deps)
│   ├── entities/     # @dataclasses inheriting Entity
│   ├── repositories/ # Abstract interfaces
│   ├── services/     # Domain services
│   └── exceptions.py # Domain exceptions
├── application/      # Use cases
│   ├── commands/     # Write operations
│   ├── queries/      # Read operations
│   └── dto/          # Pydantic models
├── infrastructure/   # External concerns
│   ├── persistence/  # SQLAlchemy implementations
│   └── external/     # AI providers, parsers
└── presentation/     # FastAPI routers
    └── router.py
```

**Layer dependency rules:**
- Domain → NO dependencies (pure Python)
- Application → Domain only
- Infrastructure → Domain + Application
- Presentation → Application + shared.exceptions

**Verify:** Run `python scripts/validate_ddd.py` before committing.

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Files | `snake_case.py` | `command_handlers.py` |
| Classes | `PascalCase` | `InitiateUploadHandler` |
| Functions/Methods | `snake_case` | `execute`, `find_by_id` |
| Constants | `UPPER_SNAKE_CASE` | `HTTPStatus`, `MAX_RETRIES` |
| Private | `_leading_underscore` | `_verify_magic_number` |

### HTTP Status Codes

**Always use `http.HTTPStatus` constants:**

```python
# ✅ GOOD
from http import HTTPStatus
assert response.status_code == HTTPStatus.NOT_FOUND

# ❌ BAD - Magic integers
assert response.status_code == 404
```

### Error Handling

**Domain exceptions** in `module/domain/exceptions.py`:

```python
# ✅ GOOD - Domain-specific exception
class UploadExpiredError(Exception):
    """Upload expired and can no longer be confirmed."""
    pass

# ❌ BAD - Generic exception
raise Exception("Upload expired")
```

**Exception handling in handlers:**

```python
# ✅ GOOD - Explicit exception translation
try:
    pending = await self.uploads_repo.find_active_upload(cmd.upload_id, now)
    if not pending:
        raise NotFoundError(f"Upload {cmd.upload_id} not found")
except UnauthorizedError:
    logger.warning(f"Unauthorized access attempt by user {cmd.owner_id}")
    raise

# ❌ BAD - Bare except
try:
    # ... code ...
except:
    pass
```

### Logging

**Use structured logging with key-value context:**

```python
# ✅ GOOD - Structured with extra dict
logger.info(
    "upload_initiated",
    extra={
        "event": "upload_initiated",
        "upload_id": upload_id,
        "owner_id": owner_id,
        "request_id": request_id,
    }
)

# ✅ GOOD - For asyncio, use QueueHandler (non-blocking)
from logging.handlers import QueueHandler, QueueListener
queue = Queue()
logger.addHandler(QueueHandler(queue))
listener = QueueListener(queue, StreamHandler())
listener.start()

# ❌ BAD - String interpolation, no structured fields
logger.info(f"Upload initiated: upload_id={upload_id}")
```

**Required fields for EVERY log event:**
- `event` - snake_case machine-readable name
- `request_id` or `trace_id` - correlation ID
- `user_id` or `owner_id` - who is affected
- Domain IDs (upload_id, session_id, material_id)

### Type Hints

All public functions MUST have type hints:

```python
# ✅ GOOD - Full type hints
async def execute(self, cmd: InitiateUploadCommand) -> InitUploadResponse:
    ...

def is_ready_for_generation(self) -> bool:
    ...

# ❌ BAD - Missing types
async def execute(self, cmd):
    ...
```

### Imports

**All imports must be at the top of the file** (PEP 8). No mid-file imports.

Do not place imports inside functions, methods, classes, or `try/except` blocks.
If you think a "lazy import" is needed, surface it for review first — real cases
are rare (true circular-import breaks, optional heavy deps gated by a flag).

```python
# ✅ GOOD - module-level imports
from pathlib import Path
from ingest.exceptions import InvalidFilenameError

def execute(cmd):
    safe_name = Path(cmd.filename).name.strip()
    if not safe_name:
        raise InvalidFilenameError("Filename cannot be empty")

# ❌ BAD - import inside a function
def execute(cmd):
    from pathlib import Path  # don't do this
    ...
```

### Keyword-only Arguments

**Prefer keyword-only arguments in function and method signatures.** Use `*` to
force callers to pass by name. This prevents silent bugs when argument order
changes and makes call sites self-documenting.

```python
# ✅ GOOD - kw-only forces named arguments at the call site
async def execute(self, cmd: InitiateUpload, *, pipeline_fn=None) -> dict:
    ...

await handler.execute(cmd, pipeline_fn=my_fn)

# ❌ BAD - positional fn can be silently misaligned
async def execute(self, cmd, pipeline_fn=None) -> dict:
    ...

await handler.execute(cmd, my_fn)  # readers must check the signature
```

Exceptions: single-argument methods, dunder methods, and `self`/`cls` stay
positional. Dataclasses: use `@dataclass(kw_only=True)` (see
`docs/code-patterns.md`).

### Flatten Nested Conditionals

**Favor guard clauses and early returns over deep nesting**, especially for
"nothing to do" scenarios. Arrow-shaped code (`if ok: if ok: if ok: ...`) is a
smell — invert the condition and return early.

```python
# ✅ GOOD - guard clause, linear flow
async def execute(self, cmd):
    safe_name = Path(cmd.filename).name.strip()
    if not safe_name:
        raise InvalidFilenameError("Filename cannot be empty")

    ext = Path(safe_name).suffix.lstrip(".").lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise InvalidFileTypeError(...)

    # happy path continues at top indent level
    return await self._do_work(safe_name)

# ❌ BAD - nested, hard to follow
async def execute(self, cmd):
    safe_name = Path(cmd.filename).name.strip()
    if safe_name:
        ext = Path(safe_name).suffix.lstrip(".").lower()
        if ext in SUPPORTED_EXTENSIONS:
            return await self._do_work(safe_name)
        else:
            raise InvalidFileTypeError(...)
    else:
        raise InvalidFilenameError(...)
```

### Async/Await

- Always `await` async calls
- Use `async def` for I/O operations (DB, external APIs)

```python
# ✅ GOOD
result = await self.uploads_repo.find_by_id(upload_id)

# ❌ BAD - Missing await
result = self.uploads_repo.find_by_id(upload_id)  # Returns coroutine!
```

### Testing

**Write tests that verify valuable business behavior.**

#### What Makes a Test Valuable?

✅ **Valuable tests** protect business rules and invariants:
- **Expiry invariant**: Upload expires after 1 hour → prevents stale data
- **Rate limit invariant**: 5 uploads/day max → protects resources
- **Security invariant**: Malware must be CLEAN before generation
- **Authorization invariant**: Only owner can confirm their upload

❌ **Low-value tests** (avoid these):
- Testing property getters/setters
- Testing `assert entity.id == entity.id`
- Testing framework code (SQLAlchemy, FastAPI internals)
- Tests that pass even when behavior changes

**Principle:** Tests fail when **valuable behavior breaks**, not when you refactor internals.

#### Test Structure

- **Fixture**: Create test data fixtures in `conftest.py` or test file
- **Arrange-Act-Assert**: Clear test phases
- **One assertion per test**: Prefer multiple tests over one multi-assert test
- **Parametrize**: Use `@pytest.mark.parametrize` for similar test cases

```python
# ✅ GOOD - Clear test with fixture and single assertion
def test_fresh_upload_not_expired(self, fresh_upload):
    assert not fresh_upload.is_expired()

# ✅ GOOD - Parametrized edge cases
@pytest.mark.parametrize("scan_status", [MalwareScanStatus.INFECTED, MalwareScanStatus.PENDING])
def test_not_ready_if_not_clean(self, ready_material, scan_status):
    ready_material.malware_scan_status = scan_status
    assert not ready_material.is_ready_for_generation()

# ❌ BAD - Multiple assertions, unclear phases
def test_upload(self):
    upload = PendingUpload(...)
    assert upload.is_expired() == False
    assert upload.is_confirmed() == False
    assert upload.public_id == upload.upload_id
```

### Ubiquitous Language

**Always use terms from `docs/ubiquitous-language.md`** in code, comments, and documentation:

- **Study Material** (not "Document", "File", "Upload")
- **Learning Session** (not "Session", "Course")
- **Card** (not "Flashcard", "Item")
- **Vibe Check** (not "Quiz", "Test")
- **Interest Lens** (not "Interest", "Category")

---

## Git Workflow & Versioning

Optimized for a **solo developer + AI agents today**, and designed to hold up
unchanged when **2–3 more devs** join. Rule of thumb: enforce with tooling, not memory.

```
main is always deployable ──► short-lived branch ──► PR ──► green CI ──► squash-merge ──► delete branch
        ▲                                                                                      │
        └──────────────── release-please opens a Release PR; merge it to cut a version ◄───────┘
```

### Trunk-based branching

`main` is the single source of truth and is always deployable. Cut short-lived
branches from the latest `main` and merge them back within **1–3 days** — long-lived
branches accumulate merge risk. Prefer **feature flags** over long branches for
incomplete work.

| Prefix       | For                     | Example                     |
|--------------|-------------------------|-----------------------------|
| `feature/`   | new capability          | `feature/quiz-scoring`      |
| `fix/`       | bug fix                 | `fix/upload-expiry-race`    |
| `chore/`     | tooling / deps / config | `chore/bump-ruff`           |
| `refactor/`  | no behavior change      | `refactor/error-mapping`    |
| `docs/`      | docs only               | `docs/release-runbook`      |

**One concern per branch** — don't mix a refactor with a feature, or formatting with
behavior. **Delete the branch after merge.**

Parallel agent work uses git worktrees (`.claude/worktrees/`, sibling `learnyourway-*`
dirs):

```bash
git worktree add ../learnyourway-quiz feature/quiz-scoring
git worktree remove ../learnyourway-quiz    # when merged; frees the branch for deletion
```

### Conventional Commits (mandatory)

Format: `<type>(<scope>): <subject>` — e.g. `feat(generation): add quiz scoring handler`.

Allowed types: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `chore`, `ci`,
`build`, `style`, `revert`. Mark breaking changes with `!` (`feat!:`) or a
`BREAKING CHANGE:` footer.

This isn't cosmetic: release-please reads commit types to compute the next version and
write the release notes. `feat` → minor, `fix` → patch, `!`/`BREAKING CHANGE` →
breaking. Other types are non-releasable. Keep commits **atomic** and explain the
*why*, not the *what*.

### Local quality gates (run once per clone)

```bash
uv run pre-commit install --hook-type pre-commit --hook-type commit-msg --hook-type pre-push
```

| Stage         | What runs                                                              |
|---------------|------------------------------------------------------------------------|
| `commit-msg`  | Conventional Commit format check                                       |
| `pre-commit`  | ruff lint+format, pyright, DDD validation, file/secret/size checks     |
| `pre-push`    | **backend test suite** (`pytest`) — blocks pushing red code            |
| `post-commit` | ruff/pyright re-check (catches amends, rebases, cherry-picks)          |

Run manually: `uv run pre-commit run --all-files`. `--no-verify` is for genuine
emergencies only — CI is the backstop and will fail the PR anyway.

### Merge & CI

Every change reaches `main` through a PR (**including solo work**) with green CI
(`ci.yml`, `frontend-ci.yml`). **Squash-merge** so one PR = one atomic
Conventional-Commit on `main` — this keeps history linear and the changelog clean.

### Versioning & release notes (automated)

One **repo-wide** version (`vX.Y.Z`, [SemVer](https://semver.org/)). The **git tag is
the version of record** — nothing is published to a registry. Driven by
**release-please** (`release-please-config.json` + `.release-please-manifest.json`,
run by `.github/workflows/release.yml`):

1. Merge Conventional-Commit PRs into `main`.
2. release-please opens/updates a **"chore: release X.Y.Z" PR** that bumps `version.txt`
   + `.release-please-manifest.json` and writes categorized **release notes** into
   [`CHANGELOG.md`](CHANGELOG.md) (Features / Bug Fixes / Performance / Reverts; chores,
   docs, tests, etc. are hidden from public notes).
3. **To cut a release, merge that PR.** It tags `vX.Y.Z` (`v`-prefixed) and publishes
   the GitHub Release with the same notes. No manual tagging, no hand-edited versions.

You never edit versions or released changelog sections by hand — **edit commit messages
instead**, since they *are* the release notes. Pre-1.0, `feat`/breaking bump the minor;
`fix` bumps the patch.

### First release (bootstrap)

The baseline is pre-seeded: `.release-please-manifest.json` pins `0.1.0`, `version.txt`
holds `0.1.0`, and [`CHANGELOG.md`](CHANGELOG.md) ships a hand-written `0.1.0` section.
release-please always bumps *past* the manifest version, so the first automated Release
PR proposes the **next** version (e.g. `0.1.1` / `0.2.0`) and appends its notes **above**
the seeded `0.1.0` — it does not re-release `0.1.0`. The first tag is therefore `v0.1.x`.

If the first Release PR ever tries to re-release `0.1.0`, anchor the baseline by tagging
the merge commit once: `git tag v0.1.0 <commit> && git push origin v0.1.0`.

### Branch hygiene

```bash
git fetch --prune                         # drop refs deleted on the remote
git branch --merged main | grep -v main   # candidates to delete
git branch -d <branch>                    # delete a merged branch (remove its worktree first if any)
```

### Scaling solo → small team

The flow above already assumes more than one contributor. When devs join, turn on
**server-side enforcement**: GitHub branch protection / rulesets aren't available on
this repo's plan yet (private + free), so today the PR-only + local-hooks discipline
*is* the enforcement. On upgrade (or going public), protect `main` — require PRs, passing
CI, 1 approval, and linear history — to make these conventions non-bypassable. Keep PRs
small (~100 lines; split anything >~1000). Nothing else changes.

---

## Pull Request Guidelines

### Before Submitting

1. **Run tests**: `uv run pytest`
2. **Run DDD validation**: `python scripts/validate_ddd.py`
3. **Update documentation**: If behavior changed
4. **Check ADRs**: Ensure code aligns with accepted ADRs

### PR Checklist

- [ ] Tests pass locally
- [ ] DDD validation passes
- [ ] Code follows standards in this document
- [ ] Used ubiquitous language correctly
- [ ] Updated relevant documentation
- [ ] Created AgDR for technical choices
- [ ] Drafted ADR for architectural changes

### PR Description Template — "Context Is The Work"

Code is cheap; context is scarce. The diff already shows *what* changed — the
description must carry *what we meant*, *what constrained us*, and *how we know it's
correct*. Agents make implementation fast, so the engineering shifts into the PR body:
turning tribal knowledge into written constraints, making trade-offs explicit, and
making verification legible. This is the apprenticeship surface for the next dev (and
for future-you on call).

Optimize for three reader modes:

| Layer | Reader time | Answers |
|-------|-------------|---------|
| **Executive intent** | 30s | What changed, why now, what's the visible outcome |
| **Reviewer guidance** | 3–7 min | Where to look, what invariants matter, what you deliberately *didn't* change |
| **Provenance / replay** | only if needed | What context/decisions/tools produced this (collapsed `<details>`) |

Don't paste the agent transcript — it's high-volume and mixes signal with false
starts. Serialize the **plot points** instead. See CLAUDE.md →
"PR Philosophy: Context Is The Work".

```markdown
## Goal
<The outcome we're producing — not the mechanism. Why now?>

## Non-goals
<What we're explicitly NOT doing — data model? partner/API contract? refactors?>

## Constraints / invariants
<What would make this change wrong even if tests pass? Latency budgets, security
rules (e.g. no PII logging), DDD-layer rules, ubiquitous language, idempotency, ...>

## Approach
<The shape of the solution, in 2–4 lines.>

## What changed (walkthrough)
<Where should a reviewer look first? The plot points, in order.>

## Verification
<How do we KNOW this works? Commands run + outcomes:
- uv run pytest
- python scripts/validate_ddd.py
- <integration / manual checks, benchmarks>>

## Risks & rollback
<How does this fail in prod, and how do we undo it? Feature flag %? Migration? DLQ?>

<details>
<summary>Context manifest (audit / archaeology)</summary>

- **Prompt summary (not transcript):** the intent + constraints we gave the agent.
- **Repo anchors used:** the handful of files / docs / ADRs that defined "truth".
- **Decision points:** the 2–4 moments where options existed — what we chose, and why.
- **Tools invoked:** tests, linters, benchmarks — and their outcomes.
</details>

## Checklist
**General**
- [ ] I read `AGENTS.md` and relevant ADRs
- [ ] Ubiquitous language used correctly
- [ ] ADR drafted / AgDR created for architectural or technical choices
- [ ] Documentation updated

**Backend** (if `backend/**` touched)
- [ ] Tests pass (`uv run pytest`)
- [ ] DDD validation passes (`python scripts/validate_ddd.py`)

**Frontend** (if `frontend/**` touched — run from `frontend/`)
- [ ] Tests pass (`pnpm test`)
- [ ] Lint + types pass (`pnpm lint && pnpm type-check`)
```

---

## Getting Help

| Resource | Purpose |
|----------|---------|
| `ARCHITECTURE.md` | System architecture, DDD layers |
| `AGENTS.md` | ADR/AgDR process, agent protocol |
| `docs/ubiquitous-language.md` | Domain terminology |
| `docs/code-patterns.md` | Gold standard code examples |
| `docs/adr/` | Architecture Decision Records |

---

## Code Review

All contributions require code review. When reviewing:

1. **Check architecture compliance** - Does it follow DDD layering?
2. **Verify ubiquitous language** - Are domain terms used correctly?
3. **Review error handling** - Are domain exceptions used?
4. **Check logging** - Is logging structured with context?
5. **Verify tests** - Are tests focused on behavior?

---

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
