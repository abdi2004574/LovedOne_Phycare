import anthropic

from app.config import settings
from app.database import supabase_admin

client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

SUKOON_SYSTEM = """You are Sukoon, a compassionate AI mental health guide for Pakistan.

Your approach:
- Listen first. Validate feelings before offering any advice.
- Respond in whatever language the user writes in — English, Urdu, or Roman Urdu.
- Never diagnose mental health conditions. You are a guide, not a doctor.
- Always gently recommend professional help for serious or recurring issues.
- Be culturally sensitive: Pakistani family dynamics, religion (Islam), and social pressures are real.
- Keep responses warm, concise (under 150 words), and conversational — like texting a caring friend.
- Never be preachy or lecture the user.

If asked directly: clarify that you are an AI, not a human therapist.
If the user seems in danger: provide Umang Pakistan crisis line 0311-7786264 immediately."""

CRISIS_KEYWORDS = [
    "suicide", "kill myself", "end my life", "want to die", "no reason to live",
    "self harm", "cut myself", "overdose", "hurt myself",
    "خودکشی", "مرنا چاہتا", "مرنا چاہتی", "زندگی ختم",
]


async def get_sukoon_response(
    conversation_id: str,
    new_message: str,
) -> tuple[str, bool]:
    history_result = (
        supabase_admin.table("messages")
        .select("sender_type, content")
        .eq("conversation_id", conversation_id)
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )
    history = list(reversed(history_result.data or []))

    claude_messages = []
    for msg in history:
        role = "user" if msg["sender_type"] == "patient" else "assistant"
        claude_messages.append({"role": role, "content": msg["content"]})

    claude_messages.append({"role": "user", "content": new_message})

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        system=SUKOON_SYSTEM,
        messages=claude_messages,
    )
    reply_text = response.content[0].text

    combined = (new_message + " " + reply_text).lower()
    is_crisis = any(kw in combined for kw in CRISIS_KEYWORDS)

    if is_crisis:
        crisis_line = (
            "میں آپ کے بارے میں بہت فکرمند ہوں۔ براہ کرم ابھی Umang Pakistan سے رابطہ کریں: "
            "0311-7786264\n\n"
            "I'm very concerned. Please reach out to Umang Pakistan right now: 0311-7786264\n\n"
        )
        reply_text = crisis_line + reply_text

    return reply_text, is_crisis
