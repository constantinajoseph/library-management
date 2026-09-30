import sqlite3
import hashlib
import hmac
import os
from datetime import date, timedelta

DB = "library.db"
LOAN_DAYS = 14
MAX_BOOKS = 3


def _connect():
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ---------- Passwords (never stored as plain text) ----------
def hash_password(password, salt=None):
    salt = salt or os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), 100000).hex()
    return f"{salt}${digest}"


def check_password(password, stored):
    salt = stored.split("$")[0]
    return hmac.compare_digest(hash_password(password, salt), stored)


# ---------- Accounts ----------
def register_student(reg_no, name, password):
    reg_no = reg_no.strip()
    name = name.strip()
    if not reg_no or not name or not password:
        return False, "Please fill in all the boxes."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO members (reg_no, name, password_hash, is_admin) VALUES (?, ?, ?, 0)",
            (reg_no, name, hash_password(password)))
        conn.commit()
    except sqlite3.IntegrityError:
        return False, "An account with this register number already exists."
    finally:
        conn.close()
    return True, "Account created. You can log in now."


def login(reg_no, password):
    conn = _connect()
    row = conn.execute(
        "SELECT member_id, name, password_hash, is_admin FROM members WHERE reg_no = ?",
        (reg_no.strip(),)).fetchone()
    conn.close()
    if row and check_password(password, row[2]):
        return {"member_id": row[0], "name": row[1], "is_admin": bool(row[3])}
    return None


# ---------- Books ----------
def search_books(keyword):
    like = f"%{keyword.strip()}%"
    conn = _connect()
    rows = conn.execute("""
        SELECT book_id, title, author, category, available_copies
        FROM books
        WHERE title LIKE ? OR author LIKE ? OR IFNULL(category, '') LIKE ?
        ORDER BY title
    """, (like, like, like)).fetchall()
    conn.close()
    return rows


def add_book(title, author, category, copies):
    title = title.strip()
    author = author.strip()
    category = category.strip()
    if not title or not author:
        return False, "Title and author are required."
    if copies < 1:
        return False, "Copies must be at least 1."

    conn = _connect()
    conn.execute(
        "INSERT INTO books (title, author, category, available_copies) VALUES (?, ?, ?, ?)",
        (title, author, category, copies))
    conn.commit()
    conn.close()
    return True, "Book added."


# ---------- Student side: requests ----------
def request_book(member_id, book_id):
    conn = _connect()
    try:
        has_loan = conn.execute(
            "SELECT 1 FROM loans WHERE member_id = ? AND book_id = ? AND return_date IS NULL",
            (member_id, book_id)).fetchone()
