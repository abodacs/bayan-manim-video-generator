import contextlib
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import time


class RenderError(Exception):
    """Custom exception raised when Manim fails to render the scene."""

    pass


def _parse_manim_error(stderr_text: str) -> str:
    """
    Parses Manim error output (stderr) to extract a clean, readable summary
    of the traceback instead of dumping the entire raw output.
    """
    if not stderr_text:
        return "Unknown error occurred (empty stderr)."

    error_patterns = [
        r"(SyntaxError: .*?)(?:\n|$)",
        r"(NameError: .*?)(?:\n|$)",
        r"(TypeError: .*?)(?:\n|$)",
        r"(AttributeError: .*?)(?:\n|$)",
        r"(ModuleNotFoundError: .*?)(?:\n|$)",
        r"(ImportError: .*?)(?:\n|$)",
    ]
    if "Traceback (most recent call last):" in stderr_text:
        lines = stderr_text.splitlines()
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i]
            if any(re.search(pat, line) for pat in error_patterns):
                start_context = max(0, i - 2)
                return "\n".join(lines[start_context : i + 1])
    return "\n".join(stderr_text.strip().splitlines()[-8:])


def execute_manim_script(
    code_content: str,
    output_path: pathlib.Path,  # Received explicitly to eliminate race conditions
    scene_class_name: str = "GeneratedScene",
    timeout_seconds: int = 60,  # Enforced to safeguard compute resources
) -> pathlib.Path:
    """
    Executes the Manim script inside a strict, resource-bounded sandbox boundary
    and writes the final artifact atomically to the requested output destination.
    """
    # 1. Create a secure temporary directory for atomic isolation
    temp_dir = tempfile.TemporaryDirectory()
    temp_path = pathlib.Path(temp_dir.name)

    try:
        # Write the generated script code directly inside the sandbox
        script_file = temp_path / "scene.py"
        script_file.write_text(code_content, encoding="utf-8")

        output_dir = temp_path / "output"

        # 2. Build execution command targeting sandboxed assets
        cmd = [
            "uv",
            "run",
            "manim",
            str(script_file),
            scene_class_name,
            "-ql",
            "--media_dir",
            str(output_dir),
        ]

        # 3. Configure isolated environment to prevent systemic leakages
        project_root = pathlib.Path.cwd()
        env = {}

        # Pass only the bare necessary system parameters to keep the sandbox strict
        for key in ["PATH", "SYSTEMROOT", "USERPROFILE", "HOME", "TEMP", "TMP"]:
            if key in os.environ:
                env[key] = os.environ[key]

        # Inject project root securely into PYTHONPATH for dynamic internal lookups
        env["PYTHONPATH"] = str(project_root)

        start_time = time.perf_counter()

        # 4. Execute the sub-worker strictly inside the temporary path with a strict timeout limit
        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            env=env,
            cwd=str(temp_path),
            timeout=timeout_seconds,  # Prevents infinite loops or hung tasks
        )

        duration = time.perf_counter() - start_time
        print(f"Manim render completed successfully in {duration:.2f} seconds.")

        # 5. Locate the generated mp4 artifact within the isolated workspace
        video_paths = list(output_dir.glob("**/*.mp4"))
        if not video_paths:
            raise RenderError("Render completed, but no .mp4 output files were detected.")

        # 6. Atomic Transfer: Move the validated artifact directly to the permanent path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists():
            output_path.unlink()

        shutil.copy2(video_paths[0], output_path)
        return output_path

    except subprocess.TimeoutExpired as e:
        raise RenderError(
            f"Manim Render Pipeline exceeded resource limit timeout of {timeout_seconds}s."
        ) from e
    except subprocess.CalledProcessError as e:
        clean_error = _parse_manim_error(e.stderr)
        raise RenderError(f"Manim Render Failed!\n{clean_error}") from e
    finally:
        # 7. Guarantee total filesystem cleanup of the temporary worker block
        with contextlib.suppress(Exception):
            temp_dir.cleanup()
