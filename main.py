import os
import uuid
from multipart import parse_form_data

from db import dismiss_match_notification, get_conn, get_matches, get_messages, get_next_profile, get_notifications, hash_password, init_db, mark_messages_read, record_swipe, send_message, verify_password, update_user_settings, get_user_settings
from kindling import Application
from kindling.reactive import on, signal
from urllib.parse import quote as _url_quote
from kindling.response import Response, redirect
from session import clear_session_header, get_session, set_session_header

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
            "SELECT username, name, major, height, age, year, pronouns, about, photo_path FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return dict(row) if row else {}


@app.get("/")
def landing(req):
    return app.render("landing.html")


with app.reactive("signup", path="/signup", template="signup.html") as _signup:
    _error   = signal("")
    _success = signal(False)
    _signup.expose(error=_error, success=_success)

    @on("signup-form", "submit")
    def handle_signup(req):
        username = (req.form_value("username") or "").strip()
        password = req.form_value("password") or ""
        confirm  = req.form_value("confirm_password") or ""
        _error.value   = ""
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
            if conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone():
                _error.value = "Username already taken."
                return
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, hash_password(password)),
            )

        _success.value = True

@app.get("/profile")
def profile_get(req):
    user_id = get_session(req)
    if not user_id:
        return redirect("/login")
    return app.render("profile.html", user=_get_user(user_id), error=None, success=False, notif_count=_nc(user_id))


@app.post("/profile")
def profile_post(req):
    user_id = get_session(req)
    if not user_id:
        return redirect("/login")

    forms, files = _parse_form(req)

    username = forms.get("username", "").strip()
    name     = forms.get("name", "").strip()
    major    = forms.get("major", "").strip()
    height   = forms.get("height", "").strip()
    year     = forms.get("year", "").strip()
    pronouns = forms.get("pronouns", "").strip()
    about    = forms.get("about", "").strip()
    age      = forms.get("age", "").strip()

    if not name or not age:
        return app.render("profile.html", user=_get_user(user_id), error="Name and age are required.", success=False, notif_count=_nc(user_id))
    if not age.isdigit() or int(age) < 18:
        return app.render("profile.html", user=_get_user(user_id), error="You must be at least 18 years old.", success=False, notif_count=_nc(user_id))

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
                "UPDATE users SET username=?, name=?, major=?, height=?, age=?, year=?, pronouns=?, about=?, photo_path=? WHERE id=?",
                (username, name, major, height, int(age), year, pronouns, about, photo_path, user_id),
            )
        else:
            conn.execute(
                "UPDATE users SET username=?, name=?, major=?, height=?, age=?, year=?, pronouns=?, about=? WHERE id=?",
                (username, name, major, height, int(age), year, pronouns, about, user_id),
            )

    return app.render("profile.html", user=_get_user(user_id), error=None, success=True, notif_count=_nc(user_id))

@app.get("/login")
def login_get(req):
    return app.render("login.html", error=None)


@app.post("/login")
def login_post(req):
    username = (req.form_value("username") or "").strip()
    password = req.form_value("password") or ""

    if not username or not password:
        return app.render("login.html", error="Please enter your username and password.")

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
    profile = get_next_profile(user_id)
    toast   = req.query("toast") or ""
    return app.render("discover.html", profile=profile, toast=toast, notif_count=_nc(user_id))


@app.post("/discover")
def discover_post(req):
    user_id = get_session(req)
    if not user_id:
        return redirect("/login")
    action    = req.form_value("action") or ""
    swiped_id = int(req.form_value("swiped_id") or 0)
    toast = ""
    if swiped_id:
        if action == "accept":
            matched = record_swipe(user_id, swiped_id, "right")
            if matched:
                toast = "It's a match!"
        elif action == "reject":
            record_swipe(user_id, swiped_id, "left")
    dest = "/discover?toast=" + _url_quote(toast, safe="") if toast else "/discover"
    return redirect(dest)


@app.get("/chats")
def chats_get(req):
    user_id = get_session(req)
    if not user_id:
        return redirect("/login")
    matches = get_matches(user_id)
    match_id = int(req.query("match") or 0)
    active = next((m for m in matches if m["id"] == match_id), matches[0] if matches else None)
    messages = get_messages(active["id"]) if active else []
    if active:
        mark_messages_read(user_id, active["id"])
    return app.render("chats.html", matches=matches, active=active, messages=messages, user_id=user_id, notif_count=_nc(user_id))


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


@app.get("/testimonials")
def testimonials_get(req):
    user_id = get_session(req)
    if not user_id:
        return redirect("/login")
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT t.body, u.name, u.username, u.photo_path
            FROM testimonials t
            JOIN users u ON u.id = t.user_id
            ORDER BY t.created_at DESC
            """
        ).fetchall()
    return app.render("testimonials.html", testimonials=[dict(r) for r in rows], notif_count=_nc(user_id))


@app.get("/settings")
def settings_get(req):
    user_id = get_session(req)
    if not user_id:
        return redirect("/login")
    return app.render("settings.html", notif_count=_nc(user_id))


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
    settings = get_user_settings(user_id)
    return app.render("settings.html", settings=settings)
    


@app.post("/settings")
def settings_post(req):
    user_id = get_session(req)
    if not user_id:
        return redirect("/login")
    
    #defaults to 0 since unselected check is not passed
    match_all_majors = 1 if req.form.get("majorsMatchSelection") == "all" else 0
    match_men    = 1 if req.form.get("genderSelectMen")   else 0
    match_women  = 1 if req.form.get("genderSelectWomen") else 0
    match_nb     = 1 if req.form.get("genderSelectNB")    else 0
    match_other  = 1 if req.form.get("genderSelectOther") else 0

    update_user_settings(user_id, match_all_majors, match_men, match_women, match_nb, match_other)
    return redirect("/settings")



@app.get("/logout")
def logout(req):
    resp = redirect("/")
    return Response(
        status=resp.status,
        headers=resp.headers + (clear_session_header(),),
        body=resp.body,
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
