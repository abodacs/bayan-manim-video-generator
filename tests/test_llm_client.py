import os
import pytest
from unittest.mock import MagicMock, patch
from bayan.generator.llm_client import LLMClient

# -------------------------------------------------------------------------
# 1. اختبارات دالة التنظيف (_clean_code)
# -------------------------------------------------------------------------

def test_clean_code_with_markdown_wrapper():
    """تأكيد أن الدالة تستخلص الكود الصافي بنجاح عند وجود علامات الاقتباس الثلاثية"""
    client = LLMClient(api_key="fake-api-key")
    raw_response = (
        "```python\n"
        "class GeneratedScene(Scene):\n"
        "    def construct(self):\n"
        "        pass\n"
        "```"
    )
    expected_clean_code = (
        "class GeneratedScene(Scene):\n"
        "    def construct(self):\n"
        "        pass"
    )
    assert client._clean_code(raw_response) == expected_clean_code


def test_clean_code_without_markdown_wrapper():
    """تأكيد أن الدالة ترجع الكود كما هو إذا لم يحتوي على علامات Markdown"""
    client = LLMClient(api_key="fake-api-key")
    raw_response = "class GeneratedScene(Scene):\n    pass"
    assert client._clean_code(raw_response) == raw_response.strip()


# -------------------------------------------------------------------------
# 2. اختبارات الوحدة مع محاكاة الـ API (Mocking)
# -------------------------------------------------------------------------

@patch("bayan.generator.llm_client.OpenAI")
def test_generate_manim_code_success(mock_openai_class):
    """تأكيد إرسال البارامترات الصحيحة للـ API واستلام الكود وتنظيفه بنجاح"""
    # تهيئة الـ Mock الخاص باستجابة الـ API
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    
    # محاكاة بنية الرد المرتجع من OpenAI (choices[0].message.content)
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="```python\n# Clean Code\n```"))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    # تشغيل الدالة
    client = LLMClient(api_key="fake-api-key")
    result = client.generate_manim_code("ارسم دائرة حمراء")

    # التحقق من أن الكود تم تنظيفه بنجاح
    assert result == "# Clean Code"

    # التحقق من تمرير البارامترات الصحيحة للـ API
    mock_client.chat.completions.create.assert_called_once()
    called_kwargs = mock_client.chat.completions.create.call_args[1]
    
    assert called_kwargs["model"] == "gpt-4o"
    assert called_kwargs["temperature"] == 0.2
    assert called_kwargs["messages"][0]["role"] == "system"
    assert "ارسم دائرة حمراء" in called_kwargs["messages"][1]["content"]


@patch("bayan.generator.llm_client.OpenAI")
def test_generate_manim_code_api_error_raises_runtime_error(mock_openai_class):
    """تأكيد أن أي خطأ اتصال أو صلاحيات يتحول إلى RuntimeError مفهوم"""
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    
    # محاكاة إثارة خطأ أثناء طلب الـ API
    mock_client.chat.completions.create.side_effect = Exception("Connection timeout")

    client = LLMClient(api_key="fake-api-key")
    
    with pytest.raises(RuntimeError) as exc_info:
        client.generate_manim_code("ارسم مربع")
        
    assert "Failed to communicate with LLM provider" in str(exc_info.value)


# =========================================================================
# 3. اختبار التكامل (Integration Test - يتخطى تلقائياً لو الحساب غير مشحون)
# =========================================================================

def has_active_openai_quota():
    if not os.getenv("OPENAI_API_KEY"):
        return False
    try:
        from openai import OpenAI
        client = OpenAI()
        # محاولة طلب توليد بسيط وسريع جداً للتحقق من الرصيد الفعلي
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1
        )
        return True
    except Exception as e:
        # إذا رجع أي خطأ يحتوي على كلمة quota، نرجع False لتخطي التست بأمان
        if "quota" in str(e).lower() or "insufficient_quota" in str(e).lower():
            return False
        # لأي خطأ شبكة أو خطأ آخر، برضه نرجع False للتخطي الآمن
        return False

@pytest.mark.skipif(
    not has_active_openai_quota(),
    reason="يتطلب هذا الاختبار وجود مفتاح فعال ورصيد كافٍ (Quota) في حساب OpenAI"
)
def test_integration_live_llm_call():
    """اختبار اتصال حقيقي بالـ API والتحقق من صحة سنتاكس كود Manim الناتج"""
    client = LLMClient()
    prompt = "Draw a blue circle that fades in"
    
    # استدعاء الـ API الحقيقي
    generated_code = client.generate_manim_code(prompt)
    
    # 1. التحقق من أن النتيجة نص غير فارغ
    assert isinstance(generated_code, str)
    assert len(generated_code) > 0
    
    # 2. التحقق من خلو النص تماماً من علامات الاقتباس التجميلية للـ Markdown
    assert "```python" not in generated_code
    assert "```" not in generated_code
    
    # 3. التحقق من صحة السنتاكس البرمجي للكود المرتجع (Python Syntax Compilation)
    try:
        compile(generated_code, "<string>", "exec")
    except SyntaxError as e:
        pytest.fail(f"الكود المولد يحتوي على أخطاء برمجية في السنتاكس: {e}")