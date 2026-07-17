import os
import re
from openai import OpenAI

SYSTEM_PROMPT = """You are an expert animator using Manim (Community Edition). Your task is to generate valid, clean, and executable Python code that defines a single Manim Scene class.

Rules:
1. ALWAYS start the code with `from manim import *`.
2. ONLY return executable Python code. Do not write explanations. Do not include markdown blocks like ```python.
3. If there is any Arabic text in the video, you MUST:
   - Import ArabicText using: `from bayan.utils.arabic_helper import ArabicText`
   - Use `ArabicText("your arabic text")` instead of `Text(...)` or `Tex(...)`.
4. ALL elements (both shapes like Circle and texts) MUST be explicitly animated using `self.play(...)` in sequence. Do NOT use `self.add()` or render static objects unless requested.
5. Keep the scene name consistent, such as class GeneratedScene(Scene).
6. ARABIC ANIMATION INSTRUCTIONS:
   - NEVER add the ArabicText object to the scene before animating it.
   - Set its position FIRST using `.next_to()`, `.to_edge()`, etc.
   - Write Arabic smoothly from Right-to-Left using: `self.play(Write(arabic_text[::-1]))`.
"""
class LLMClient:
    def __init__(self, api_key: str | None = None):
        # Look for the API key in the passed argument or environment variables
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("API Key must be provided or set via OPENAI_API_KEY env variable.")
        
        # Initialize the OpenAI client
        self.client = OpenAI(api_key=self.api_key)

    def generate_manim_code(self, user_prompt: str) -> str:
        """
        Sends the user prompt to the LLM and returns the parsed Python script.
        """
        try:
            response = self.client.chat.completions.create(
    model="llama-3.3-70b-versatile",  # 👈 موديل مجاني وسريع من Groq
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Create a Manim scene for: {user_prompt}"}
    ],
    temperature=0.2,
)
            raw_content = response.choices[0].message.content or ""
            return self._clean_code(raw_content)
        except Exception as e:
            # Handle API communication or authentication errors gracefully
            raise RuntimeError(f"Failed to communicate with LLM provider: {str(e)}")    
        
    def _clean_code(self, raw_code: str) -> str:
        """
        Extracts raw python code out of LLM markdown wrappers if present.
        """
        # Use regex to extract code wrapped inside markdown code blocks
        pattern = r"```python(.*?)```"
        match = re.search(pattern, raw_code, re.DOTALL)
        if match:
            return match.group(1).strip()
        return raw_code.strip()