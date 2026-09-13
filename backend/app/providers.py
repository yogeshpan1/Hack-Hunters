"""Optional external adapters. No database access or executable model output."""
import hashlib
import json
import os
import httpx


def provider_status():
    return {
        "ai_enabled": os.getenv("AI_PROVIDER", "structured") == "groq" and bool(os.getenv("GROQ_API_KEY")),
        "email_enabled": os.getenv("EMAIL_PROVIDER", "demo") == "resend" and bool(os.getenv("RESEND_API_KEY")) and bool(os.getenv("RESEND_FROM_EMAIL")),
    }


def normalize_question(query, history):
    """Translate conversational wording into a supported read-only question."""
    if not provider_status()["ai_enabled"]:
        return query, False
    try:
        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": "Bearer " + os.environ["GROQ_API_KEY"]},
            json={"model": os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"), "temperature": 0,
                  "response_format": {"type": "json_object"}, "max_completion_tokens": 300,
                  "messages": [
                      {"role": "system", "content": 'Rewrite the latest question as a standalone question for a college database assistant. Supported topics: faculty workload, faculty directory, room capacity/availability, session conflicts/alternatives, audit (who changed), optimization. Resolve references using earlier user questions only. Preserve all names, codes, numbers and times. Do not answer, invent facts, write SQL, or request mutations. If unsupported keep the question unchanged. Return JSON with one string field: query.'},
                      {"role": "user", "content": json.dumps({"earlier_questions": history[-6:], "question": query})}]},
            timeout=12,
        )
        response.raise_for_status()
        rewritten = json.loads(response.json()["choices"][0]["message"]["content"])["query"]
        if not isinstance(rewritten, str) or not 1 <= len(rewritten.strip()) <= 1000:
            raise ValueError("Invalid rewrite")
        return rewritten.strip(), True
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
        return query, False


def send_reviewed_email(email):
    if not provider_status()["email_enabled"]:
        raise ValueError("Live email is not configured. Configure Resend and a verified sender first.")
    payload = {"from": os.environ["RESEND_FROM_EMAIL"], "to": [email.recipient], "subject": email.subject, "text": email.body}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    try:
        response = httpx.post("https://api.resend.com/emails", headers={
            "Authorization": "Bearer " + os.environ["RESEND_API_KEY"],
            "Idempotency-Key": f"nexus-{email.id}-{digest}",
        }, json=payload, timeout=15)
        response.raise_for_status()
        ident = response.json()["id"]
        if not isinstance(ident, str) or not ident:
            raise ValueError("Missing receipt")
        return ident
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise ValueError("Delivery could not be confirmed. Check Resend before retrying; the draft is preserved.") from None
