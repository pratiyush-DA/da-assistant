from services.langchain.prompts import (
    DATA_DICTIONARY_SYSTEM_PROMPT,
    MIXED_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
)


def test_prompts_require_direct_answer_not_summary_section():
    for prompt in (SYSTEM_PROMPT, DATA_DICTIONARY_SYSTEM_PROMPT, MIXED_SYSTEM_PROMPT):
        assert "Direct answer" in prompt
        assert "Do NOT include a separate Summary section" in prompt
        assert "## Summary" not in prompt
