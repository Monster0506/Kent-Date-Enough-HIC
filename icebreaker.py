import os
import pathlib
from google import genai


def _load_env():
    env_path = pathlib.Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def generate_icebreaker(
    user_a: dict,
    user_b: dict,
    schedule_a: list[dict],
    schedule_b: list[dict],
) -> str:
    _load_env()
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key or api_key == "your_key_here":
        return ""

    crns_b = {c["crn"] for c in schedule_b}
    shared = [c for c in schedule_a if c["crn"] in crns_b]

    def _fmt_user(u: dict, sched: list[dict]) -> str:
        parts = [f"Name: {u.get('name') or 'Unknown'}"]
        if u.get("major"):
            parts.append(f"Major: {u['major']}")
        if u.get("year"):
            parts.append(f"Year: {u['year']}")
        if u.get("about"):
            parts.append(f"Bio: {u['about']}")
        if sched:
            courses = ", ".join(
                f"{c['subject']} {c['course_num']} – {c['name']}" for c in sched
            )
            parts.append(f"Classes: {courses}")
        return "\n".join(parts)

    shared_line = ""
    if shared:
        shared_line = "\nClasses they share: " + ", ".join(
            f"{c['subject']} {c['course_num']} – {c['name']} ({c['days']} {c['time']})"
            for c in shared
        )

    prompt = f"""Two students just matched on a college dating app called Kent Date Enough (at Kent State University).
Write a single short icebreaker message (2-3 sentences max) that kicks off their conversation.
Be warm, playful, and specific — reference shared classes, overlapping interests from their bios, or their majors.
End with one concrete conversation-starting question. Address both people by first name. No excessive emojis.

Person A:
{_fmt_user(user_a, schedule_a)}

Person B:
{_fmt_user(user_b, schedule_b)}
{shared_line}

Icebreaker:"""

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )
    return (response.text or "").strip()

