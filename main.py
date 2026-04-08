from db import get_conn, hash_password, init_db, verify_password
from kindling import Application
from kindling.response import Response, redirect
from session import get_session, set_session_header

init_db()

app = Application(template_dir="templates")
app.static("/static", "static")


@app.get("/")
def landing(req):
    return app.render("landing.html")


@app.get("/signup")
def signup_get(req):
    return app.render("signup.html", error=None)


@app.post("/signup")
def signup_post(req):
    username = (req.form_value("username") or "").strip()
    password = req.form_value("password") or ""
    confirm  = req.form_value("confirm_password") or ""

    if not username or not password:
        return app.render("signup.html", error="Username and password are required.")
    if password != confirm:
        return app.render("signup.html", error="Passwords do not match.")
    if len(password) < 6:
        return app.render("signup.html", error="Password must be at least 6 characters.")

    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()
        if existing:
            return app.render("signup.html", error="Username already taken.")
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, hash_password(password)),
        )

    return redirect("/login")


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


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
