import os
import re
from typing import cast

from openai import OpenAI

# Import dotenv to load the .env file automatically
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except ImportError:
    pass

SYSTEM_PROMPT = (
    "You are an expert animator using Manim (Community Edition). Your task is "
    "to generate valid, clean, and executable Python code that defines a single "
    "Manim Scene class.\n\n"
    "Rules:\n"
    "1. ALWAYS start the code with `from manim import *`.\n"
    "2. ONLY return executable Python code. Do not write explanations. Do not "
    "include markdown blocks like ```python.\n"
    "3. If there is any Arabic text in the video, you MUST:\n"
    "   - Import ArabicText using: `from bayan.utils.arabic_helper import ArabicText`\n"
    "   - Use `ArabicText(\"your arabic text\")` instead of `Text(...)` or `Tex(...)`.\n"
    "4. ALL elements (both shapes like Circle and texts) MUST be explicitly "
    "animated using `self.play(...)` in sequence. Do NOT use `self.add()` or "
    "render static objects unless requested.\n"
    "5. Keep the scene name consistent, such as class GeneratedScene(Scene).\n"
    "6. ARABIC ANIMATION INSTRUCTIONS:\n"
    "   - NEVER add the ArabicText object to the scene before animating it.\n"
    "   - Set its position FIRST using `.next_to()`, `.to_edge()`, etc.\n"
    "   - Write Arabic smoothly from Right-to-Left using: "
    "`self.play(Write(arabic_text[::-1]))`.\n"
)


class LLMClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        # Configuration is loaded from the environment variables (populated via the .env file)
        self.api_key = (
            api_key or os.getenv("BAYAN_API_KEY") or os.getenv("OPENAI_API_KEY")
        )
        if not self.api_key:
            raise ValueError(
                "API Key must be provided via BAYAN_API_KEY or "
                "OPENAI_API_KEY environment variables."
            )

        # Cleaned default URL from any markdown link wrappers
        self.base_url = base_url or os.getenv(
            "BAYAN_BASE_URL", "https://api.z.ai/api/coding/paas/v4/"
        )
        
        # Ensure Mypy knows this is a clean string and not None to prevent arg-type mismatch
        chosen_model = model or os.getenv("BAYAN_LLM_MODEL", "glm-5.2")
        self.model: str = cast(str, chosen_model)

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def generate_manim_code(self, user_prompt: str) -> str:
        """
        Sends the user prompt to the LLM and returns the parsed Python script.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"Create a Manim scene for: {user_prompt}",
                    },
                ],
                temperature=0.2,
            )
            raw_content = response.choices[0].message.content or ""
            return self._clean_code(raw_content)
        except Exception as e:
            raise RuntimeError(
                f"Failed to communicate with LLM provider: {str(e)}"
            ) from e

    def _clean_code(self, raw_code: str) -> str:
        """
        Extracts raw python code out of LLM markdown wrappers if present.
        """
        pattern = r"```python(.*?)```"
        match = re.search(pattern, raw_code, re.DOTALL)
        if match:
            return match.group(1).strip()
        return raw_code.strip()