import subprocess
import tempfile
import pathlib
import time
import shutil
import os
import re

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
        r"(ImportError: .*?)(?:\n|$)"
    ]
    if "Traceback (most recent call last):" in stderr_text:
        lines = stderr_text.splitlines()
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i]
            if any(re.search(pat, line) for pat in error_patterns):
                start_context = max(0, i - 2)
                return "\n".join(lines[start_context:i + 1])
    return "\n".join(stderr_text.strip().splitlines()[-8:])


def execute_manim_script(code_content: str, scene_class_name: str = "GeneratedScene") -> pathlib.Path:
    """
    Writes the Manim script to a temporary directory and executes rendering via subprocess.
    Injects the project path into PYTHONPATH to allow importing internal modules (e.g., Arabic handlers),
    then safely transfers the output video to the project's media directory and cleans up temp files.
    """
    # 1. Create a secure temporary directory that auto-cleans up after completion
    temp_dir = tempfile.TemporaryDirectory()
    temp_path = pathlib.Path(temp_dir.name)
    
    try:
        # Write the generated script code into the temporary directory
        script_file = temp_path / "scene.py"
        script_file.write_text(code_content, encoding="utf-8")
        
        output_dir = temp_path / "output"
        
        # 2. Build execution command using `uv run` to guarantee virtual environment consistency
        cmd = [
            "uv", "run", "manim",
            str(script_file),
            scene_class_name,
            "-ql",
            "--media_dir", str(output_dir)
        ]
        
        # 3. Configure environment variables to attach the subprocess to current project paths
        project_root = pathlib.Path.cwd()
        env = os.environ.copy()
        # Add current project root to PYTHONPATH so temporary scripts can import the `bayan` module easily
        env["PYTHONPATH"] = str(project_root) + os.pathsep + env.get("PYTHONPATH", "")
        
        # Track render start execution time
        start_time = time.perf_counter()
        
        # Run the rendering subprocess
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            env=env
        )
        
        # Calculate render completion time
        duration = time.perf_counter() - start_time
        print(f"Manim render completed successfully in {duration:.2f} seconds.")
        
        # 4. Search for the generated .mp4 video file inside the temporary output directory
        video_paths = list(output_dir.glob("**/*.mp4"))
        if not video_paths:
            raise RenderError("Render completed, but no .mp4 output files were detected.")
            
        # 5. Determine final destination path inside the main project directory and safely move the file
        destination = project_root / "media" / f"{scene_class_name}.mp4"
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        if destination.exists():
            destination.unlink()
            
        # Use shutil.copy2 for safe, fast cross-platform transfer avoiding Windows file locking issues
        shutil.copy2(video_paths[0], destination)
        return destination

    except subprocess.CalledProcessError as e:
        # Extract and format clean error details when rendering fails
        clean_error = _parse_manim_error(e.stderr)
        raise RenderError(f"Manim Render Failed!\n{clean_error}") from e
        
    finally:
        # 6. Guarantee complete cleanup of the temporary directory, even if rendering fails
        try:
            temp_dir.cleanup()
        except Exception:
            pass