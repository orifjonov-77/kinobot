"""
Database module for SQLite operations.
Handles users, admins, and movies tables.
"""

import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from config import DATABASE_PATH, SUPER_ADMIN_ID


def get_connection() -> sqlite3.Connection:
    """Create and return a database connection with dict-like row access."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize database tables and create default indexes."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Movies table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                file_id TEXT NOT NULL,
                file_type TEXT NOT NULL,
                added_by INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Admins table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                added_by INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Users table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_movies_code ON movies(code)")
        conn.commit()


# ================= User functions ================= #

def add_or_update_user(user_id: int, username: Optional[str], first_name: Optional[str]) -> None:
    """Upsert user details into users table."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO users (user_id, username, first_name, joined_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name
            """,
            (user_id, username, first_name, datetime.utcnow()),
        )
        conn.commit()


def get_all_user_ids() -> List[int]:
    """Retrieve all user IDs for broadcasting."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        rows = cursor.fetchall()
        return [row["user_id"] for row in rows]


# ================= Admin functions ================= #

def is_admin(user_id: int) -> bool:
    """Check if the user is a super admin or an existing admin."""
    if SUPER_ADMIN_ID != 0 and user_id == SUPER_ADMIN_ID:
        return True
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
        return cursor.fetchone() is not None


def is_super_admin(user_id: int) -> bool:
    """Check if user matches SUPER_ADMIN_ID."""
    return SUPER_ADMIN_ID != 0 and user_id == SUPER_ADMIN_ID


def add_admin(user_id: int, added_by: int) -> bool:
    """
    Add a new admin.
    Returns True if added, False if already exists.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO admins (user_id, added_by, added_at) VALUES (?, ?, ?)",
                (user_id, added_by, datetime.utcnow()),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def remove_admin(user_id: int) -> bool:
    """
    Remove an admin.
    Returns True if removed, False if was not present.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0


def get_all_admins() -> List[Dict[str, Any]]:
    """Return all admins with metadata."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, added_by, added_at FROM admins ORDER BY added_at DESC")
        return [dict(row) for row in cursor.fetchall()]


# ================= Movie functions ================= #

def add_movie(
    code: str,
    title: str,
    file_id: str,
    file_type: str,
    added_by: int
) -> Tuple[bool, str]:
    """
    Save a movie into the database.
    Returns (success: bool, message: str).
    """
    clean_code = code.strip()
    clean_title = title.strip()

    if not clean_code or not clean_title:
        return False, "Kod yoki kino nomi bo'sh bo'lishi mumkin emas."

    if " " in clean_code or len(clean_code) > 20:
        return False, "Kodda bo'sh joy (probel) bo'lmasligi va uzunligi 20 belgidan oshmasligi kerak."

    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO movies (code, title, file_id, file_type, added_by, added_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (clean_code, clean_title, file_id, file_type, added_by, datetime.utcnow()),
            )
            conn.commit()
            return True, "Kino muvaffaqiyatli saqlandi!"
        except sqlite3.IntegrityError:
            return False, f"'{clean_code}' kodli kino allaqachon mavjud! Boshqa kod tanlang."


def get_movie_by_code(code: str) -> Optional[Dict[str, Any]]:
    """Retrieve a movie by its unique code."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, code, title, file_id, file_type, added_by, added_at
            FROM movies
            WHERE code = ?
            """,
            (code.strip(),),
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def delete_movie_by_code(code: str) -> bool:
    """Delete a movie by its code. Returns True if deleted."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM movies WHERE code = ?", (code.strip(),))
        conn.commit()
        return cursor.rowcount > 0


def get_recent_movies(limit: int = 20) -> List[Dict[str, Any]]:
    """Fetch the latest movies up to limit."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT code, title, added_at
            FROM movies
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]


# ================= Stats functions ================= #

def get_stats() -> Dict[str, int]:
    """Return count statistics for movies, users, and admins."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS count FROM movies")
        movies_count = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) AS count FROM users")
        users_count = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) AS count FROM admins")
        admins_count = cursor.fetchone()["count"]

        # If SUPER_ADMIN is defined, count it in admins total if not already in DB
        if SUPER_ADMIN_ID != 0:
            cursor.execute("SELECT 1 FROM admins WHERE user_id = ?", (SUPER_ADMIN_ID,))
            if not cursor.fetchone():
                admins_count += 1

        return {
            "movies": movies_count,
            "users": users_count,
            "admins": admins_count,
        }
