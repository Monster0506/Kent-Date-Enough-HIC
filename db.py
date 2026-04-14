import hashlib
import os
import sqlite3

DB_PATH = "kde.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT    NOT NULL UNIQUE,
                password_hash TEXT    NOT NULL,
                name          TEXT,
                major         TEXT,
                height        TEXT,
                age           INTEGER,
                year          TEXT,
                pronouns      TEXT,
                gender        TEXT,
                about         TEXT,
                photo_path    TEXT,
                created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
            );



            CREATE TABLE IF NOT EXISTS matches (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_a_id  INTEGER NOT NULL REFERENCES users(id),
                user_b_id  INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id   INTEGER NOT NULL REFERENCES matches(id),
                sender_id  INTEGER NOT NULL REFERENCES users(id),
                body       TEXT    NOT NULL,
                sent_at    DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS testimonials (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL REFERENCES users(id),
                body       TEXT    NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS swipes (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                swiper_id  INTEGER NOT NULL REFERENCES users(id),
                swiped_id  INTEGER NOT NULL REFERENCES users(id),
                direction  TEXT    NOT NULL CHECK(direction IN ('left','right')),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(swiper_id, swiped_id)
            );

            CREATE TABLE IF NOT EXISTS message_reads (
                user_id      INTEGER NOT NULL REFERENCES users(id),
                match_id     INTEGER NOT NULL REFERENCES matches(id),
                last_read_id INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, match_id)
            );

            CREATE TABLE IF NOT EXISTS dismissed_matches (
                user_id  INTEGER NOT NULL REFERENCES users(id),
                match_id INTEGER NOT NULL REFERENCES matches(id),
                PRIMARY KEY (user_id, match_id)
            );

            CREATE TABLE IF NOT EXISTS user_schedules (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                crn         TEXT    NOT NULL,
                subject     TEXT,
                course_num  TEXT,
                name        TEXT,
                days        TEXT,
                time        TEXT,
                location    TEXT,
                instructor  TEXT,
                term        TEXT,
                UNIQUE(user_id, crn)
            );

            CREATE TABLE IF NOT EXISTS reports (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_id  INTEGER NOT NULL REFERENCES users(id),
                reported_id  INTEGER NOT NULL REFERENCES users(id),
                reason       TEXT,
                created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(reporter_id, reported_id)
            );

            CREATE TABLE IF NOT EXISTS user_settings(
                id                  INTEGER     PRIMARY KEY AUTOINCREMENT,
                user_id             INTEGER     NOT NULL UNIQUE REFERENCES users(id),
                match_all_majors     INTEGER     DEFAULT 1,
                match_men           INTEGER     DEFAULT 1,
                match_women         INTEGER     DEFAULT 1,
                match_nb            INTEGER     DEFAULT 1,
                match_other         INTEGER     DEFAULT 1
            );
        """
        )
        cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        if "gender" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN gender TEXT")

        match_cols = [r[1] for r in conn.execute("PRAGMA table_info(matches)").fetchall()]
        if "icebreaker" not in match_cols:
            conn.execute("ALTER TABLE matches ADD COLUMN icebreaker TEXT")

        settings_cols = [r[1] for r in conn.execute("PRAGMA table_info(user_settings)").fetchall()]
        if "age_min" not in settings_cols:
            conn.execute("ALTER TABLE user_settings ADD COLUMN age_min INTEGER DEFAULT 18")
        if "age_max" not in settings_cols:
            conn.execute("ALTER TABLE user_settings ADD COLUMN age_max INTEGER DEFAULT 99")


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
    return salt.hex() + ":" + key.hex()


def get_next_profile(user_id: int, settings: dict | None = None) -> dict | None:
    with get_conn() as conn:
        me = conn.execute("SELECT major, year FROM users WHERE id = ?", (user_id,)).fetchone()
        my_major = me["major"] if me else None
        my_year = me["year"] if me else None

        clauses = [
            "id != ?",
            "id NOT IN (SELECT swiped_id FROM swipes WHERE swiper_id = ?)",
        ]
        params: list = [user_id, user_id]

        if settings:
            if not settings.get("match_all_majors", 1) and my_major:
                clauses.append("major = ?")
                params.append(my_major)

            gender_map = {
                "Men": settings.get("match_men", 1),
                "Women": settings.get("match_women", 1),
                "Nonbinary": settings.get("match_nb", 1),
                "Other": settings.get("match_other", 1),
            }
            allowed = [g for g, v in gender_map.items() if v]
            if allowed and len(allowed) < 4:
                placeholders = ",".join("?" * len(allowed))
                clauses.append(
                    f"(gender IN ({placeholders}) OR gender IS NULL OR gender = '')"
                )
                params.extend(allowed)

            age_min = settings.get("age_min", 18)
            age_max = settings.get("age_max", 99)
            clauses.append("(age IS NULL OR (age >= ? AND age <= ?))")
            params.extend([age_min, age_max])

        where = " AND ".join(clauses)

        # Scoring weights:
        # +3 per shared CRN (same class section)
        # +2 same major
        # +1 same year
        # +1 per overlapping free time block (same day letter + same hour window)
        # guys sql is so very awesome there's no logic to matching other than this sql that's pretty cool
        score_sql = f"""
            (
                SELECT COUNT(*) * 3
                FROM user_schedules s1
                JOIN user_schedules s2
                  ON s1.crn = s2.crn
                 AND s1.user_id = ?
                 AND s2.user_id = u.id
            )
            + (CASE WHEN u.major = ? AND u.major IS NOT NULL AND u.major != '' THEN 2 ELSE 0 END)
            + (CASE WHEN u.year  = ? AND u.year  IS NOT NULL AND u.year  != '' THEN 1 ELSE 0 END)

            + (
                SELECT COUNT(*) * 1
                FROM user_schedules s1
                JOIN user_schedules s2
                  ON s1.user_id = ?
                 AND s2.user_id = u.id
                 AND s1.days LIKE '%' || substr(s2.days, 1, 1) || '%'
                 AND substr(s1.time, 1, instr(s1.time || ':', ':') - 1)
                   = substr(s2.time, 1, instr(s2.time || ':', ':') - 1)
            )
        """
        score_params = [user_id, my_major or "", my_year or "", user_id]

        row = conn.execute(
            f"""
            SELECT id, username, name, major, height, age, year, pronouns, gender, about, photo_path,
                   ({score_sql}) AS compat_score
            FROM users u
            WHERE {where}
            ORDER BY ({score_sql}) DESC, created_at ASC
            LIMIT 1
            """,
            score_params + params + score_params,
        ).fetchone()
    return dict(row) if row else None


def record_swipe(swiper_id: int, swiped_id: int, direction: str) -> int:
    if swiper_id == swiped_id:
        return 0
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO swipes (swiper_id, swiped_id, direction) VALUES (?, ?, ?)",
            (swiper_id, swiped_id, direction),
        )
        if direction == "right":
            mutual = conn.execute(
                "SELECT 1 FROM swipes WHERE swiper_id = ? AND swiped_id = ? AND direction = 'right'",
                (swiped_id, swiper_id),
            ).fetchone()
            if mutual:
                conn.execute(
                    "INSERT INTO matches (user_a_id, user_b_id) VALUES (?, ?)",
                    (swiper_id, swiped_id),
                )
                return conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    return 0


def delete_swipe(swiper_id: int, swiped_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM swipes WHERE swiper_id = ? AND swiped_id = ?",
            (swiper_id, swiped_id),
        )


def set_match_icebreaker(match_id: int, text: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE matches SET icebreaker = ? WHERE id = ?",
            (text, match_id),
        )


def get_match_icebreaker(match_id: int) -> str:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT icebreaker FROM matches WHERE id = ?", (match_id,)
        ).fetchone()
    return row["icebreaker"] or "" if row else ""


def clear_match_icebreaker(match_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE matches SET icebreaker = NULL WHERE id = ?",
            (match_id,),
        )


def get_matches(user_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT m.id,
                   u.id AS other_user_id, u.name, u.username, u.photo_path
            FROM matches m
            JOIN users u ON u.id = CASE WHEN m.user_a_id = ? THEN m.user_b_id ELSE m.user_a_id END
            WHERE m.user_a_id = ? OR m.user_b_id = ?
            ORDER BY m.created_at DESC
            """,
            (user_id, user_id, user_id),
        ).fetchall()
    return [dict(r) for r in rows]


def get_match_user_ids(match_id: int) -> tuple[int, int]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT user_a_id, user_b_id FROM matches WHERE id = ?", (match_id,)
        ).fetchone()
    return (row["user_a_id"], row["user_b_id"]) if row else (0, 0)


def get_messages(match_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT sender_id, body, sent_at FROM messages WHERE match_id = ? ORDER BY sent_at ASC",
            (match_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def send_message(match_id: int, sender_id: int, body: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (match_id, sender_id, body) VALUES (?, ?, ?)",
            (match_id, sender_id, body),
        )


def mark_messages_read(user_id: int, match_id: int) -> None:
    with get_conn() as conn:
        last = conn.execute(
            "SELECT MAX(id) FROM messages WHERE match_id = ?", (match_id,)
        ).fetchone()[0]
        if last:
            conn.execute(
                """INSERT INTO message_reads (user_id, match_id, last_read_id)
                   VALUES (?, ?, ?)
                   ON CONFLICT(user_id, match_id) DO UPDATE SET last_read_id = excluded.last_read_id""",
                (user_id, match_id, last),
            )


def dismiss_match_notification(user_id: int, match_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO dismissed_matches (user_id, match_id) VALUES (?, ?)",
            (user_id, match_id),
        )


def get_notifications(user_id: int) -> list[dict]:
    notifs = []
    with get_conn() as conn:
        matches = conn.execute(
            """SELECT m.id, u.name, u.username
               FROM matches m
               JOIN users u ON u.id = CASE WHEN m.user_a_id = ? THEN m.user_b_id ELSE m.user_a_id END
               WHERE (m.user_a_id = ? OR m.user_b_id = ?)
                 AND m.id NOT IN (
                     SELECT match_id FROM dismissed_matches WHERE user_id = ?
                 )
               ORDER BY m.created_at DESC""",
            (user_id, user_id, user_id, user_id),
        ).fetchall()
        for m in matches:
            notifs.append(
                {
                    "type": "match",
                    "match_id": m["id"],
                    "name": m["name"] or m["username"],
                }
            )

        unread_by_match = conn.execute(
            """SELECT m.id AS match_id,
                      u.name, u.username,
                      COUNT(msg.id) AS unread_count
               FROM messages msg
               JOIN matches m ON m.id = msg.match_id
               JOIN users u ON u.id = CASE WHEN m.user_a_id = ? THEN m.user_b_id ELSE m.user_a_id END
               LEFT JOIN message_reads mr ON mr.user_id = ? AND mr.match_id = msg.match_id
               WHERE (m.user_a_id = ? OR m.user_b_id = ?)
                 AND msg.sender_id != ?
                 AND msg.id > COALESCE(mr.last_read_id, 0)
               GROUP BY m.id""",
            (user_id, user_id, user_id, user_id, user_id),
        ).fetchall()
        for row in unread_by_match:
            notifs.append(
                {
                    "type": "message",
                    "match_id": row["match_id"],
                    "name": row["name"] or row["username"],
                    "count": row["unread_count"],
                }
            )

        row = conn.execute(
            "SELECT name, age, photo_path FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not row["name"] or not row["age"] or not row["photo_path"]:
            notifs.append({"type": "profile"})

    return notifs


def save_course(user_id: int, course: dict) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO user_schedules
               (user_id, crn, subject, course_num, name, days, time, location, instructor, term)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id, crn) DO UPDATE SET
               subject=excluded.subject, course_num=excluded.course_num, name=excluded.name,
               days=excluded.days, time=excluded.time, location=excluded.location,
               instructor=excluded.instructor, term=excluded.term""",
            (
                user_id, course["crn"], course["subject"], course["course_num"],
                course["name"], course["days"], course["time"],
                course["location"], course["instructor"], course["term"],
            ),
        )


def get_schedule(user_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT crn, subject, course_num, name, days, time, location, instructor, term
               FROM user_schedules WHERE user_id = ? ORDER BY days, time""",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def remove_course(user_id: int, crn: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM user_schedules WHERE user_id = ? AND crn = ?",
            (user_id, crn),
        )


def get_user_testimonial(user_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, body FROM testimonials WHERE user_id = ?", (user_id,)
        ).fetchone()
    return dict(row) if row else None


def upsert_testimonial(user_id: int, body: str) -> None:
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM testimonials WHERE user_id = ?", (user_id,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE testimonials SET body = ? WHERE user_id = ?", (body, user_id)
            )
        else:
            conn.execute(
                "INSERT INTO testimonials (user_id, body) VALUES (?, ?)",
                (user_id, body),
            )


def report_user(reporter_id: int, reported_id: int, reason: str = "") -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO reports (reporter_id, reported_id, reason) VALUES (?, ?, ?)",
            (reporter_id, reported_id, reason),
        )
        conn.execute(
            "INSERT OR IGNORE INTO swipes (swiper_id, swiped_id, direction) VALUES (?, ?, 'left')",
            (reporter_id, reported_id),
        )


def delete_match(match_id: int, user_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM matches WHERE id = ? AND (user_a_id = ? OR user_b_id = ?)",
            (match_id, user_id, user_id),
        ).fetchone()
        if not row:
            return False
        conn.execute("DELETE FROM message_reads WHERE match_id = ?", (match_id,))
        conn.execute("DELETE FROM dismissed_matches WHERE match_id = ?", (match_id,))
        conn.execute("DELETE FROM messages WHERE match_id = ?", (match_id,))
        conn.execute("DELETE FROM matches WHERE id = ?", (match_id,))
    return True


def delete_testimonial(user_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM testimonials WHERE user_id = ?", (user_id,))


def verify_password(password: str, stored: str) -> bool:
    salt_hex, key_hex = stored.split(":", 1)
    salt = bytes.fromhex(salt_hex)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
    return key.hex() == key_hex


def update_user_settings(
    userID: int,
    majorSetting: int,
    matchMen: int,
    matchWomen: int,
    matchNB: int,
    matchOther: int,
    age_min: int = 18,
    age_max: int = 99,
):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO user_settings(user_id, match_all_majors, match_men, match_women, match_nb, match_other, age_min, age_max) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET "
            "match_all_majors=excluded.match_all_majors, "
            "match_men=excluded.match_men, "
            "match_women=excluded.match_women, "
            "match_nb=excluded.match_nb, "
            "match_other=excluded.match_other, "
            "age_min=excluded.age_min, "
            "age_max=excluded.age_max",
            (userID, majorSetting, matchMen, matchWomen, matchNB, matchOther, age_min, age_max),
        )


def get_user_settings(userID: int):
    with get_conn() as conn:
        settings = conn.execute(
            """
            SELECT match_all_majors, match_men, match_women, match_nb, match_other
            FROM user_settings
            WHERE user_id = ?
            """,
            (userID,),
        ).fetchone()
    if not settings:
        return {
            "match_all_majors": 1,
            "match_men": 1,
            "match_women": 1,
            "match_nb": 1,
            "match_other": 1,
            "age_min": 18,
            "age_max": 99,
        }
    result = dict(settings)
    if result.get("age_min") is None:
        result["age_min"] = 18
    if result.get("age_max") is None:
        result["age_max"] = 99
    return result

def reset_password(username: str, new_password: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()
        if not row:
            return False
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(new_password), row["id"]),
        )
    return True

def delete_account(user_id: int) -> None:
    with get_conn() as conn:
        conn.executescript(f"""
            DELETE FROM message_reads     WHERE user_id   = {user_id};
            DELETE FROM dismissed_matches WHERE user_id   = {user_id};
            DELETE FROM user_schedules    WHERE user_id   = {user_id};
            DELETE FROM user_settings     WHERE user_id   = {user_id};
            DELETE FROM testimonials      WHERE user_id   = {user_id};
            DELETE FROM swipes            WHERE swiper_id = {user_id} OR swiped_id = {user_id};
            DELETE FROM messages          WHERE sender_id = {user_id};
            DELETE FROM matches           WHERE user_a_id = {user_id} OR user_b_id = {user_id};
            DELETE FROM users             WHERE id        = {user_id};
        """)