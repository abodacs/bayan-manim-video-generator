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
    يقوم بفحص مخرجات الأخطاء (stderr) الخاصة بـ Manim لاستخلاص
    ملخص نظيف ومقروء للـ Traceback بدلاً من طباعة شاشة الأخطاء بأكملها.
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
    يكتب كود المانيم في مجلد مؤقت، ويقوم بتشغيل الريندر عبر subprocess
    مع تمرير مسار المشروع لـ PYTHONPATH لضمان إمكانية استيراد موديولات المشروع (مثل العربي)،
    ثم ينقل الفيديو الناتج بأمان إلى مجلد media الرئيسي للمشروع وينظف الملفات المؤقتة.
    """
    # 1. إنشاء مجلد مؤقت آمن يضمن التنظيف التلقائي عند انتهاء العملية
    temp_dir = tempfile.TemporaryDirectory()
    temp_path = pathlib.Path(temp_dir.name)
    
    try:
        # كتابة كود السكريبت داخل المجلد المؤقت
        script_file = temp_path / "scene.py"
        script_file.write_text(code_content, encoding="utf-8")
        
        output_dir = temp_path / "output"
        
        # 2. بناء أمر التشغيل باستخدام uv run لضمان العمل على نفس الـ virtual environment
        cmd = [
            "uv", "run", "manim",
            str(script_file),
            scene_class_name,
            "-ql",
            "--media_dir", str(output_dir)
        ]
        
        # 3. إعداد متغيرات البيئة لربط الـ Subprocess بمسارات المشروع الحالي
        project_root = pathlib.Path.cwd()
        env = os.environ.copy()
        # نضع مسار المشروع الحالي في PYTHONPATH لكي تستطيع الأكواد المؤقتة استيراد موديول bayan بسهولة
        env["PYTHONPATH"] = str(project_root) + os.pathsep + env.get("PYTHONPATH", "")
        
        # حساب وقت بداية الريندر الفعلي
        start_time = time.perf_counter()
        
        # تشغيل الـ Subprocess
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            env=env
        )
        
        # حساب وقت نهاية الريندر
        duration = time.perf_counter() - start_time
        print(f"Manim render completed successfully in {duration:.2f} seconds.")
        
        # 4. البحث عن ملف الـ .mp4 الناتج داخل المجلد المؤقت
        video_paths = list(output_dir.glob("**/*.mp4"))
        if not video_paths:
            raise RenderError("Render completed, but no .mp4 output files were detected.")
            
        # 5. تحديد المسار النهائي للفيديو داخل المشروع الرئيسي ونقله بأمان
        destination = project_root / "media" / f"{scene_class_name}.mp4"
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        if destination.exists():
            destination.unlink()
            
        # استخدام shutil.copy2 لنقل آمن وسريع على مستوى نظام التشغيل دون مشاكل الـ File Locking على ويندوز
        shutil.copy2(video_paths[0], destination)
        return destination

    except subprocess.CalledProcessError as e:
        # استخلاص وتمرير تفاصيل الخطأ بشكل نظيف وسهل القراءة عند حدوث أي مشكلة في الريندر
        clean_error = _parse_manim_error(e.stderr)
        raise RenderError(f"Manim Render Failed!\n{clean_error}") from e
        
    finally:
        # 6. ضمان تنظيف وحذف المجلد المؤقت وملفاته بالكامل حتى في حال حدوث خطأ أثناء الريندر
        try:
            temp_dir.cleanup()
        except Exception:
            pass