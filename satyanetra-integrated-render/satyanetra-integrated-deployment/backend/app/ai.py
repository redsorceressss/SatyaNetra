import re
from app.config import settings

def answer(message: str, context: str | None = None) -> dict:
    # Deliberately transparent mock; no external model is called.
    text = message.lower()
    if settings.ai_provider != "mock":
        return {"provider": settings.ai_provider, "mode": "not_configured",
                "answer": "The configured AI provider adapter is not implemented/configured yet. No external model was called."}
    if re.search(r"anonymous|privacy|safe", text):
        reply = "Share only information you can safely provide. Anonymous reporting reduces account linkage but cannot guarantee anonymity: server, hosting, or network logs may still contain metadata."
    elif re.search(r"report|brib|corrupt|incident|complaint", text):
        reply = "Describe what you personally observed, when and where it happened, who or what was involved if known, and what supporting material exists. Separate direct observations from assumptions. An allegation is not a verified finding."
    elif re.search(r"evidence|document|file", text):
        reply = "Keep original evidence unchanged, record how and when it was obtained, and avoid sharing material you are not authorised to disclose. This prototype does not determine authenticity."
    else:
        reply = "I can help organise a report, explain the workflow, and distinguish observations from assumptions. I cannot determine guilt or verify allegations. Please avoid including unnecessary sensitive personal data."
    return {"provider":"mock","mode":"mock","answer":reply}
