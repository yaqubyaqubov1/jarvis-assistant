from tools.registry import register
from ai.ollama import chat, answer_with_context

@register("local_answer", "Ask the local AI a question. arguments={question,context?}")
def local_answer(question, context=""):
    return answer_with_context(question, context) if context else chat(question)
