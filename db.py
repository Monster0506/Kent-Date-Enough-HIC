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
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT    NOT NULL UNIQUE,
                password_hash TEXT    NOT NULL,
                name          TEXT,
                major         TEXT,
                height        TEXT,
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
        """)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
    return salt.hex() + ":" + key.hex()


def get_next_profile(user_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, username, name, major, height, about, photo_path
            FROM users
            WHERE id != ?
              AND id NOT IN (
                  SELECT swiped_id FROM swipes WHERE swiper_id = ?
              )
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (user_id, user_id),
        ).fetchone()
    return dict(row) if row else None


def record_swipe(swiper_id: int, swiped_id: int, direction: str) -> bool:
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
                return True
    return False


def verify_password(password: str, stored: str) -> bool:
    salt_hex, key_hex = stored.split(":", 1)
    salt = bytes.fromhex(salt_hex)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
    return key.hex() == key_hex
