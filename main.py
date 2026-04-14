import os
import uuid
from multipart import parse_form_data

from db import (
    dismiss_match_notification,
    get_conn,
    get_matches,
    get_messages,
    get_next_profile,
    get_notifications,
    hash_password,
    init_db,
    mark_messages_read,
    record_swipe,
    delete_swipe,
    send_message,
    verify_password,
    update_user_settings,
    get_user_settings,
    get_user_testimonial,
    upsert_testimonial,
    delete_testimonial,
    save_course,
    get_schedule,
    remove_course,
    set_match_icebreaker,
    get_match_icebreaker,
    clear_match_icebreaker,
    get_match_user_ids,
    delete_match,
)
from db import (
    dismiss_match_notification,
    get_conn,
    get_matches,
    get_messages,
    get_next_profile,
    get_notifications,
    hash_password,
    init_db,
    mark_messages_read,
    record_swipe,
    send_message,
    verify_password,
    update_user_settings,
    get_user_settings,
    get_user_testimonial,
    upsert_testimonial,
    save_course,
    get_schedule,
    remove_course,
    set_match_icebreaker,
    get_match_icebreaker,
    hash_password,
    reset_password,
    delete_account,
)
from scraper import lookup_crns
from icebreaker import generate_icebreaker
import json
import queue

from kindling import Application
from kindling.reactive import on, signal
from kindling.streaming import StreamedHttpResponse
from urllib.parse import quote as _url_quote
from kindling.response import Response, redirect
from session import clear_session_header, get_session, set_session_header

_icebreaker_subscribers: list[queue.SimpleQueue] = []


def _broadcast_icebreaker(match_id: int, text: str) -> None:
    payload = json.dumps({"match_id": match_id, "text": text})
    for q in list(_icebreaker_subscribers):
        q.put_nowait(payload)

init_db()

app = Application(template_dir="templates")
app.config.max_request_body_bytes = 10 * 1024 * 1024
app.static("/static", "static")

PROFILE_IMAGES_DIR = os.path.join("static", "profile_images")
os.makedirs(PROFILE_IMAGES_DIR, exist_ok=True)


def _parse_form(req):
    import io

    environ = {
        "wsgi.input": io.BytesIO(req.body),
        "CONTENT_TYPE": req.header("content-type", "") or "",
        "CONTENT_LENGTH": str(len(req.body)),
        "REQUEST_METHOD": "POST",
    }
    return parse_form_data(environ)


def _nc(user_id):
    return len(get_notifications(user_id))


def _get_user(user_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT username, name, major, height, age, year, pronouns, gender, about, photo_path, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return dict(row) if row else {}


@app.get("/")
def landing(req):
    return app.render("landing.html")


with app.reactive("signup", path="/signup", template="signup.html") as _signup:
    _error = signal("")
    _success = signal(False)
    _signup.expose(error=_error, success=_success)

    @on("signup-form", "submit")
    def handle_signup(req):
        username = (req.form_value("username") or "").strip()
        password = req.form_value("password") or ""
        confirm = req.form_value("confirm_password") or ""
        _error.value = ""
        _success.value = False

        if not username or not password:
            _error.value = "Username and password are required."
            return
        if password != confirm:
            _error.value = "Passwords do not match."
            return
        if len(password) < 6:
            _error.value = "Password must be at least 6 characters."
            return

        with get_conn() as conn:
            if conn.execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            ).fetchone():
                _error.value = "Username already taken."
                return
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, hash_password(password)),
            )
            user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            print(user_id)
            conn.execute("INSERT INTO user_settings(user_id) VALUES (?)", (user_id,))

        _success.value = True


@app.get("/profile")
def profile_get(req):
    user_id = get_session(req)
    if not user_id:
        return redirect("/login")
    return app.render(
        "profile.html",
        user=_get_user(user_id),
        error=None,
        success=False,
        notif_count=_nc(user_id),
    )


@app.post("/profile")
def profile_post(req):
    user_id = get_session(req)
    if not user_id:
        return redirect("/login")

    forms, files = _parse_form(req)

    username = forms.get("username", "").strip()
    name = forms.get("name", "").strip()
    major = forms.get("major", "").strip()
    height = forms.get("height", "").strip()
    year = forms.get("year", "").strip()
    pronouns = forms.get("pronouns", "").strip()
    gender = forms.get("gender", "").strip()
    about = forms.get("about", "").strip()
    age = forms.get("age", "").strip()

    if not name or not age:
        return app.render(
            "profile.html",
            user=_get_user(user_id),
            error="Name and age are required.",
            success=False,
            notif_count=_nc(user_id),
        )
    if not age.isdigit() or int(age) < 18:
        return app.render(
            "profile.html",
            user=_get_user(user_id),
            error="You must be at least 18 years old.",
            success=False,
            notif_count=_nc(user_id),
        )

    photo_path = None
    photo_file = files.get("photo")
    if photo_file and photo_file.filename:
        ext = os.path.splitext(photo_file.filename)[1].lower() or ".jpg"
        safe_image_name = f"{user_id}_{uuid.uuid4().hex}{ext}"
        with open(os.path.join(PROFILE_IMAGES_DIR, safe_image_name), "wb") as f:
            photo_file.file.seek(0)
            f.write(photo_file.file.read())
        photo_path = f"profile_images/{safe_image_name}"

    with get_conn() as conn:
        if photo_path:
            conn.execute(
                "UPDATE users SET username=?, name=?, major=?, height=?, age=?, year=?, pronouns=?, gender=?, about=?, photo_path=? WHERE id=?",
                (
                    username,
                    name,
                    major,
                    height,
                    int(age),
                    year,
                    pronouns,
                    gender,
                    about,
                    photo_path,
                    user_id,
                ),
            )
        else:
            conn.execute(
                "UPDATE users SET username=?, name=?, major=?, height=?, age=?, year=?, pronouns=?, gender=?, about=? WHERE id=?",
                (
                    username,
                    name,
                    major,
                    height,
                    int(age),
                    year,
                    pronouns,
                    gender,
                    about,
                    user_id,
                ),
            )

    return app.render(
        "profile.html",
        user=_get_user(user_id),
        error=None,
        success=True,
        notif_count=_nc(user_id),
    )


@app.get("/login")
def login_get(req):
    return app.render("login.html", error=None)


@app.post("/login")
def login_post(req):
    username = (req.form_value("username") or "").strip()
    password = req.form_value("password") or ""

    if not username or not password:
        return app.render(
            "login.html", error="Please enter your username and password."
        )

    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, password_hash FROM users WHERE username = ?", (username,)
        ).fetchone()

    if not row or not verify_password(password, row["password_hash"]):
        return app.render("login.html", error="Invalid username or password.")

    resp = redirect("/discover")
    return Response(
        status=resp.status,
        headers=resp.headers + (set_session_header(row["id"]),),
        body=resp.body,
    )


@app.get("/discover")
def discover_get(req):
    user_id = get_session(req)
    if not user_id:
        return redirect("/login")
    me = _get_user(user_id)
    if not me.get("name") or not me.get("age"):
        return redirect("/profile")
    settings = get_user_settings(user_id)
    profile = get_next_profile(user_id, settings)
    toast = req.query("toast") or ""
    undo_id = int(req.query("undo") or 0)
    return app.render(
        "discover.html", profile=profile, toast=toast, undo_id=undo_id, notif_count=_nc(user_id)
    )


def _make_icebreaker(match_id: int, user_a_id: int, user_b_id: int):
    import threading

    def _run():
        try:
            ua = _get_user(user_a_id)
            ub = _get_user(user_b_id)
            sa = get_schedule(user_a_id)
            sb = get_schedule(user_b_id)
            text = generate_icebreaker(ua, ub, sa, sb)
            if text:
                set_match_icebreaker(match_id, text)
                _broadcast_icebreaker(match_id, text)
        except Exception as exc:
            print(f"[icebreaker] error: {exc}")

    threading.Thread(target=_run, daemon=True).start()


@app.get("/_icebreaker/stream")
def icebreaker_stream(_req):
    def _generate():
        q: queue.SimpleQueue = queue.SimpleQueue()
        _icebreaker_subscribers.append(q)
        try:
            while True:
                try:
                    msg = q.get(timeout=20.0)
                    yield f"data: {msg}\n\n".encode()
                except queue.Empty:
                    yield b": ping\n\n"
        finally:
            _icebreaker_subscribers.remove(q)

    headers = (
        ("Content-Type", "text/event-stream; charset=utf-8"),
        ("Cache-Control", "no-cache"),
        ("Connection", "keep-alive"),
        ("X-Accel-Buffering", "no"),
    )
    return StreamedHttpResponse(200, headers, _generate())


@app.post("/discover")
def discover_post(req):
    user_id = get_session(req)
    if not user_id:
        return redirect("/login")
    action = req.form_value("action") or ""
    swiped_id = int(req.form_value("swiped_id") or 0)
    toast = ""
    if swiped_id and swiped_id != user_id:
        if action == "accept":
            match_id = record_swipe(user_id, swiped_id, "right")
            if match_id:
                toast = "It's a match!"
                _make_icebreaker(match_id, user_id, swiped_id)
        elif action == "reject":
            record_swipe(user_id, swiped_id, "left")
            return redirect("/discover?undo=" + str(swiped_id))
    dest = "/discover?toast=" + _url_quote(toast, safe="") if toast else "/discover"
    return redirect(dest)


@app.post("/discover/undo")
def discover_undo(req):
    user_id = get_session(req)
    if not user_id:
        return redirect("/login")
    swiped_id = int(req.form_value("swiped_id") or 0)
    if swiped_id:
        delete_swipe(user_id, swiped_id)
    return redirect("/discover")


@app.get("/chats")
def chats_get(req):
    user_id = get_session(req)
    if not user_id:
        return redirect("/login")
    matches = get_matches(user_id)
    match_id = int(req.query("match") or 0)
    active = next(
        (m for m in matches if m["id"] == match_id), matches[0] if matches else None
    )
    messages = get_messages(active["id"]) if active else []
    icebreaker = get_match_icebreaker(active["id"]) if active else ""
    if active:
        mark_messages_read(user_id, active["id"])
    return app.render(
        "chats.html",
        matches=matches,
        active=active,
        messages=messages,
        user_id=user_id,
        icebreaker=icebreaker,
        notif_count=_nc(user_id),
    )


@app.post("/chats/unmatch")
def chats_unmatch(req):
    user_id = get_session(req)
    if not user_id:
        return redirect("/login")
    match_id = int(req.form_value("match_id") or 0)
    if match_id:
        delete_match(match_id, user_id)
    return redirect("/chats")


@app.post("/chats/regenerate")
def chats_regenerate(req):
    user_id = get_session(req)
    if not user_id:
        return redirect("/login")
    match_id = int(req.form_value("match_id") or 0)
    if match_id:
        a_id, b_id = get_match_user_ids(match_id)
        if user_id in (a_id, b_id):
            other_id = b_id if user_id == a_id else a_id
            clear_match_icebreaker(match_id)
            _make_icebreaker(match_id, user_id, other_id)
    return redirect(f"/chats?match={match_id}")


@app.post("/chats")
def chats_post(req):
    user_id = get_session(req)
    if not user_id:
        return redirect("/login")
    match_id = int(req.form_value("match_id") or 0)
    body = (req.form_value("body") or "").strip()
    if match_id and body:
        send_message(match_id, user_id, body)
    return redirect(f"/chats?match={match_id}")


def _get_testimonials():
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT t.body, u.name, u.username, u.photo_path
            FROM testimonials t
            JOIN users u ON u.id = t.user_id
            ORDER BY t.created_at DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/testimonials")
def testimonials_get(req):
    user_id = get_session(req)
    if not user_id:
        return redirect("/login")
    return app.render(
        "testimonials.html",
        testimonials=_get_testimonials(),
        my_testimonial=get_user_testimonial(user_id),
        error=None,
        notif_count=_nc(user_id),
    )


@app.post("/testimonials/delete")
def testimonials_delete(req):
    user_id = get_session(req)
    if not user_id:
        return redirect("/login")
    delete_testimonial(user_id)
    return redirect("/testimonials")


@app.post("/testimonials")
def testimonials_post(req):
    user_id = get_session(req)
    if not user_id:
        return redirect("/login")
    body = (req.form_value("body") or "").strip()
    error = None
    if not body:
        error = "Testimonial cannot be empty."
    elif len(body) > 300:
        error = "Keep it under 300 characters."
    else:
        upsert_testimonial(user_id, body)
        return redirect("/testimonials")
    return app.render(
        "testimonials.html",
        testimonials=_get_testimonials(),
        my_testimonial=get_user_testimonial(user_id),
        error=error,
        notif_count=_nc(user_id),
    )


@app.get("/settings")
def settings_get(req):
    user_id = get_session(req)
    if not user_id:
        return redirect("/login")
    settings = get_user_settings(user_id)
    user = _get_user(user_id)
    return app.render(
        "settings.html", notif_count=_nc(user_id), settings=settings, user=user
    )


@app.get("/notifications")
def notifications_get(req):
    user_id = get_session(req)
    if not user_id:
        return redirect("/login")
    notifs = get_notifications(user_id)
    return app.render("notifications.html", notifs=notifs, notif_count=len(notifs))


@app.post("/notifications/dismiss")
def notifications_dismiss(req):
    user_id = get_session(req)
    if not user_id:
        return redirect("/login")
    match_id = int(req.form_value("match_id") or 0)
    if match_id:
        dismiss_match_notification(user_id, match_id)
    return redirect("/notifications")


@app.post("/settings")
def settings_post(req):
    user_id = get_session(req)
    if not user_id:
        return redirect("/login")

    match_all_majors = 1 if req.form.get("majorsMatchSelection") == ["all"] else 0
    match_men = 1 if req.form.get("genderSelectMen") else 0
    match_women = 1 if req.form.get("genderSelectWomen") else 0
    match_nb = 1 if req.form.get("genderSelectNB") else 0
    match_other = 1 if req.form.get("genderSelectOther") else 0

    try:
        age_min = int(req.form_value("age_min") or 18)
        age_max = int(req.form_value("age_max") or 99)
    except ValueError:
        age_min, age_max = 18, 99

    age_min = max(18, min(age_min, 99))
    age_max = max(18, min(age_max, 99))
    if age_min > age_max:
        age_min, age_max = age_max, age_min

    if not (match_men or match_women or match_nb or match_other):
        settings = get_user_settings(user_id)
        user = _get_user(user_id)
        return app.render(
            "settings.html",
            notif_count=_nc(user_id),
            settings=settings,
            user=user,
            error="Select at least one gender to match with.",
        )

    update_user_settings(
        user_id, match_all_majors, match_men, match_women, match_nb, match_other,
        age_min, age_max,
    )
    settings = get_user_settings(user_id)
    user = _get_user(user_id)
    return app.render(
        "settings.html",
        notif_count=_nc(user_id),
        settings=settings,
        user=user,
        saved=True,
    )


@app.get("/schedule")
def schedule_get(req):
    user_id = get_session(req)
    if not user_id:
        return redirect("/login")
    removed_crn = req.query("removed_crn") or ""
    return app.render(
        "schedule.html",
        schedule=get_schedule(user_id),
        preview=None,
        error=None,
        crn_input="",
        removed_crn=removed_crn,
        notif_count=_nc(user_id),
    )


@app.post("/schedule")
def schedule_post(req):
    user_id = get_session(req)
    if not user_id:
        return redirect("/login")

    action = req.form_value("action") or ""

    if action == "remove":
        crn = (req.form_value("crn") or "").strip()
        if crn:
            remove_course(user_id, crn)
        return redirect("/schedule?removed_crn=" + _url_quote(crn, safe=""))

    if action == "undo_remove":
        import re as _re
        crn = (req.form_value("crn") or "").strip()
        if crn and crn.isdigit():
            restored = lookup_crns([crn])
            for course in restored:
                save_course(user_id, course)
        return redirect("/schedule")

    if action == "save":
        import json
        raw = req.form_value("courses_json") or "[]"
        try:
            courses = json.loads(raw)
        except Exception:
            courses = []
        for course in courses:
            save_course(user_id, course)
        return redirect("/schedule")

    raw_input = req.form_value("crns") or ""
    import re
    crns = re.split(r"[\s,;]+", raw_input.strip())
    crns = [c.strip() for c in crns if c.strip().isdigit()]

    if not crns:
        return app.render(
            "schedule.html",
            schedule=get_schedule(user_id),
            preview=None,
            error="Enter at least one CRN.",
            crn_input=raw_input,
            removed_crn="",
            notif_count=_nc(user_id),
        )

    preview = lookup_crns(crns)
    not_found = [c for c in crns if not any(p["crn"] == c for p in preview)]

    return app.render(
        "schedule.html",
        schedule=get_schedule(user_id),
        preview=preview,
        not_found=not_found,
        error=None,
        crn_input=raw_input,
        removed_crn="",
        notif_count=_nc(user_id),
    )


@app.get("/profile/{profile_id}")
def profile_view(req):
    user_id = get_session(req)
    if not user_id:
        return redirect("/login")
    profile_id = int(req.route_params.get("profile_id") or 0)
    if not profile_id:
        return redirect("/chats")
    if profile_id == user_id:
        return redirect("/profile")
    with get_conn() as conn:
        has_match = conn.execute(
            "SELECT 1 FROM matches WHERE (user_a_id=? AND user_b_id=?) OR (user_a_id=? AND user_b_id=?)",
            (user_id, profile_id, profile_id, user_id),
        ).fetchone()
    if not has_match:
        return redirect("/chats")
    person = _get_user(profile_id)
    if not person:
        return redirect("/chats")
    back_url = req.query("from") or "/chats"
    return app.render("profile_view.html", person=person, back_url=back_url, notif_count=_nc(user_id))


@app.get("/logout")
def logout(req):
    resp = redirect("/")
    return Response(
        status=resp.status,
        headers=resp.headers + (clear_session_header(),),
        body=resp.body,
    )
    
@app.get("/reset-password")
def reset_password_get(req):
    user_id = get_session(req)
    if not user_id:
        return redirect("/login")
    return app.render("reset_password.html", error=None, success=False)


@app.post("/reset-password")
def reset_password_post(req):
    user_id = get_session(req)
    if not user_id:
        return redirect("/login")

    new_pass = req.form_value("new_password") or ""
    confirm  = req.form_value("confirm_password") or ""

    if new_pass != confirm:
        return app.render("reset_password.html", error="Passwords do not match.", success=False)
    if len(new_pass) < 6:
        return app.render("reset_password.html", error="Password must be at least 6 characters.", success=False)

    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(new_pass), user_id),
        )

    return app.render("reset_password.html", error=None, success=True)

@app.post("/delete-account")
def delete_account_post(req):
    user_id = get_session(req)
    if not user_id:
        return redirect("/login")

    delete_account(user_id)

    resp = redirect("/signup")
    return Response(
        status=resp.status,
        headers=resp.headers + (clear_session_header(),),
        body=resp.body,
    )

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
