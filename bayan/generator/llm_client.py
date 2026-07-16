import os
import re
from openai import OpenAI

SYSTEM_PROMPT = """You are an expert animator using Manim (Community Edition). Your task is to generate valid, clean, and executable Python code that defines a single Manim Scene class.

Rules:
1. ONLY return executable Python code. Do not write explanations. Do not include markdown blocks like ```python.
2. If there is any Arabic text in the video, you MUST:
   - Import ArabicText using: `from bayan.utils.arabic_helper import ArabicText`
   - Use `ArabicText("your arabic text")` instead of `Text(...)` or `Tex(...)`.
3. Use simple, visually pleasing animations (Write, Create, FadeIn, Transform).
4. Keep the scene name consistent, such as class GeneratedScene(Scene).
"""

class LLMClient:
    def __init__(self, api_key: str | None = None):
        # البحث عن الـ API Key في الممرر للكلاس أو في متغيرات البيئة
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("API Key must be provided or set via OPENAI_API_KEY env variable.")
        
        # تهيئة الكلاينت الخاص بـ OpenAI
        self.client = OpenAI(api_key=self.api_key)

    def generate_manim_code(self, user_prompt: str) -> str:
        """
        Sends the user prompt to the LLM and returns the parsed Python script.
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Create a Manim scene for: {user_prompt}"}
                ],
                temperature=0.2,  # درجة حرارة منخفضة لضمان كود مستقر ومنظم
            )
            raw_content = response.choices[0].message.content or ""
            return self._clean_code(raw_content)
        except Exception as e:
            # معالجة أي أخطاء اتصال أو صلاحيات بشكل نظيف ومفهوم
            raise RuntimeError(f"Failed to communicate with LLM provider: {str(e)}")    
        
    def _clean_code(self, raw_code: str) -> str:
        """
        Extracts raw python code out of LLM markdown wrappers if present.
        """
        # استخدام الـ Regex لاستخراج الكود من بين علامات الاقتباس الثلاثية
        pattern = r"```python(.*?)```"
        match = re.search(pattern, raw_code, re.DOTALL)
        if match:
            return match.group(1).strip()
        return raw_code.strip()    