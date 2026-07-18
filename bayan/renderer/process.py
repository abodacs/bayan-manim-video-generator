"""Bounded subprocess execution used by the Docker render boundary."""

from __future__ import annotations

import os
import selectors
import shlex
import signal
import subprocess
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from bayan.renderer.models import PhaseRecord, PhaseStatus


@dataclass(frozen=True)
class CommandResult:
    """The bounded result of one external command."""

    command: tuple[str, ...]
    returncode: int | None
    output_tail: str = ""
    timed_out: bool = False
    output_limited: bool = False
    error: str | None = None
    cleanup_error: str | None = None

    @property
    def succeeded(self) -> bool:
        """Return whether the command completed successfully."""
        return (
            self.returncode == 0
            and not self.timed_out
            and not self.output_limited
            and self.error is None
            and self.cleanup_error is None
        )

    @property
    def phase_status(self) -> PhaseStatus:
        """Map process state to the manifest's small status vocabulary."""
        if self.timed_out:
            return "timed_out"
        if self.output_limited:
            return "output_limited"
        return "passed" if self.succeeded else "failed"

    def as_phase_record(self, name: str, log_path: Path, run_directory: Path) -> PhaseRecord:
        """Convert the execution result into a portable manifest record."""
        errors = [message for message in (self.error, self.cleanup_error) if message]
        return PhaseRecord(
            name=name,
            status=self.phase_status,
            command=self.command,
            returncode=self.returncode,
            log=str(log_path.relative_to(run_directory)),
            output_limited=self.output_limited,
            error="; ".join(errors) if errors else None,
        )


@dataclass(frozen=True)
class CaptureResult:
    """Short output captured from Docker control-plane commands."""

    returncode: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False


class BoundedProcessRunner:
    """Run commands with bounded output and an explicit timeout."""

    def __init__(self, environment: dict[str, str], max_output_bytes: int) -> None:
        self.environment = environment
        self.max_output_bytes = max_output_bytes

    def capture(self, command: Sequence[str], timeout_seconds: int) -> CaptureResult:
        """Capture a small Docker control-plane response."""
        try:
            completed = subprocess.run(
                tuple(str(part) for part in command),
                capture_output=True,
                check=False,
                encoding="utf-8",
                errors="replace",
                env=self.environment,
                timeout=timeout_seconds,
            )
        except FileNotFoundError as error:
            return CaptureResult(127, stderr=str(error))
        except subprocess.TimeoutExpired as error:
            stdout = error.stdout if isinstance(error.stdout, str) else ""
            stderr = error.stderr if isinstance(error.stderr, str) else ""
            return CaptureResult(124, stdout=stdout, stderr=stderr, timed_out=True)
        except OSError as error:
            return CaptureResult(127, stderr=str(error))
        return CaptureResult(completed.returncode, completed.stdout, completed.stderr)

    def stream(
        self,
        command: Sequence[str],
        phase: str,
        log_path: Path,
        timeout_seconds: int,
    ) -> CommandResult:
        """Stream command output to disk without exceeding the byte limit."""
        normalized = tuple(str(part) for part in command)
        self.append_log(log_path, f"## {phase}\n$ {_format_command(normalized)}\n")
        try:
            process = subprocess.Popen(
                normalized,
                env=self.environment,
                start_new_session=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
        except FileNotFoundError as error:
            return CommandResult(normalized, 127, error=str(error))
        except OSError as error:
            return CommandResult(normalized, 127, error=str(error))

        assert process.stdout is not None
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        output_tail = bytearray()
        output_bytes = 0
        stream_open = True
        timed_out = False
        output_limited = False
        deadline = time.monotonic() + timeout_seconds

        with log_path.open("ab") as log:
            while stream_open:
                remaining_time = deadline - time.monotonic()
                if remaining_time <= 0:
                    timed_out = True
                    break
                events = selector.select(min(0.1, remaining_time))
                for key, _ in events:
                    try:
                        chunk = os.read(key.fd, 65_536)
                    except BlockingIOError:
                        continue
                    if not chunk:
                        selector.unregister(key.fileobj)
                        stream_open = False
                        break

                    remaining_bytes = self.max_output_bytes - output_bytes
                    if remaining_bytes <= 0:
                        output_limited = True
                        break
                    accepted = chunk[:remaining_bytes]
                    log.write(accepted)
                    output_tail.extend(accepted)
                    output_bytes += len(accepted)
                    if len(accepted) != len(chunk):
                        output_limited = True
                        break

                if timed_out or output_limited:
                    break
                if process.poll() is not None and not stream_open:
                    break

        if timed_out or output_limited:
            self.terminate(process)
        else:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                timed_out = True
                self.terminate(process)
        selector.close()
        if process.stdout is not None:
            process.stdout.close()

        result = CommandResult(
            command=normalized,
            returncode=process.returncode,
            output_tail=bytes(output_tail[-4096:]).decode("utf-8", errors="replace"),
            timed_out=timed_out,
            output_limited=output_limited,
        )
        self.append_log(
            log_path,
            f"exit_code={result.returncode} "
            f"timed_out={result.timed_out} "
            f"output_limited={result.output_limited}\n",
        )
        return result

    @staticmethod
    def terminate(process: subprocess.Popen[bytes]) -> None:
        """Stop a CLI process promptly before its container is removed."""
        try:
            process.send_signal(signal.SIGTERM)
            process.wait(timeout=2)
        except ProcessLookupError:
            return
        except subprocess.TimeoutExpired:
            try:
                process.kill()
                process.wait(timeout=2)
            except ProcessLookupError:
                return
        except OSError:
            try:
                process.kill()
                process.wait(timeout=2)
            except ProcessLookupError:
                return

    @staticmethod
    def append_log(log_path: Path, content: str) -> None:
        """Append UTF-8 diagnostics to the run log."""
        with log_path.open("ab") as log:
            log.write(content.encode("utf-8", errors="replace"))

    @staticmethod
    def append_capture(
        log_path: Path,
        phase: str,
        command: Sequence[str],
        result: CaptureResult,
    ) -> None:
        """Append bounded output from a Docker control-plane command."""
        details = [
            f"## {phase}",
            f"$ {_format_command(command)}",
            f"exit_code={result.returncode} timed_out={result.timed_out}",
        ]
        if result.stdout:
            details.extend(("stdout:", _tail_text(result.stdout)))
        if result.stderr:
            details.extend(("stderr:", _tail_text(result.stderr)))
        BoundedProcessRunner.append_log(log_path, "\n".join(details) + "\n")


def _tail_text(value: bytes | str, limit: int = 4096) -> str:
    """Return only the final bounded portion of a diagnostic value."""
    if isinstance(value, bytes):
        return value[-limit:].decode("utf-8", errors="replace")
    return value[-limit:]


def _format_command(command: Sequence[str]) -> str:
    """Format a command for a diagnostic log without invoking a shell."""
    return " ".join(shlex.quote(str(part)) for part in command)
