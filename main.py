import os
import uuid
from multipart import parse_form_data

from db import get_conn, get_next_profile, hash_password, init_db, record_swipe, verify_password
from kindling import Application
from kindling.reactive import on, signal
from urllib.parse import quote as _url_quote
from kindling.response import Response, redirect
from session import clear_session_header, get_session, set_session_header

init_db()

app = Application(template_dir="templates")
app.config.max_request_body_bytes = 10 * 1024 * 1024  # 10 MB
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


def _get_user(user_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT username, name, major, height, age, about, photo_path FROM users WHERE id = ?",
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
    return app.render("profile.html", user=_get_user(user_id), error=None, success=False)


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
    about    = forms.get("about", "").strip()
    age      = forms.get("age", "").strip()

    if not name or not age:
        return app.render("profile.html", user=_get_user(user_id), error="Name and age are required.", success=False)
    if not age.isdigit() or int(age) < 18:
        return app.render("profile.html", user=_get_user(user_id), error="You must be at least 18 years old.", success=False)

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
                "UPDATE users SET username=?, name=?, major=?, height=?, age=?, about=?, photo_path=? WHERE id=?",
                (username, name, major, height, int(age), about, photo_path, user_id),
            )
        else:
            conn.execute(
                "UPDATE users SET username=?, name=?, major=?, height=?, age=?, about=? WHERE id=?",
                (username, name, major, height, int(age), about, user_id),
            )

    return app.render("profile.html", user=_get_user(user_id), error=None, success=True)

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
    return app.render("discover.html", profile=profile, toast=toast)


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

@app.get("/settings")
def settings_get(req):
    user_id = get_session(req)
    if not user_id:
        return redirect("/login")
    return app.render("settings.html")

@app.post("/settings")


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
