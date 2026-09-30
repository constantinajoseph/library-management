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
        if has_loan:
            return False, "You have already borrowed this book."

        has_pending = conn.execute(
            "SELECT 1 FROM requests WHERE member_id = ? AND book_id = ? AND status = 'Pending'",
            (member_id, book_id)).fetchone()
        if has_pending:
            return False, "You have already requested this book. Please wait for approval."

        loan_count = conn.execute(
            "SELECT COUNT(*) FROM loans WHERE member_id = ? AND return_date IS NULL",
            (member_id,)).fetchone()[0]
        if loan_count >= MAX_BOOKS:
            return False, f"You already have {MAX_BOOKS} books. Return one first."

        book = conn.execute(
            "SELECT available_copies FROM books WHERE book_id = ?",
            (book_id,)).fetchone()
        if book is None:
            return False, "Book not found."
        if book[0] < 1:
            return False, "This book is not available right now."

        conn.execute(
            "INSERT INTO requests (member_id, book_id, status, requested_on) VALUES (?, ?, 'Pending', ?)",
            (member_id, book_id, date.today().isoformat()))
        conn.commit()
        return True, "Request sent. Wait for the librarian to approve."
    finally:
        conn.close()


def get_my_requests(member_id):
    conn = _connect()
    rows = conn.execute("""
        SELECT r.request_id, b.title, r.status, r.requested_on, r.note
        FROM requests r
        JOIN books b ON b.book_id = r.book_id
        WHERE r.member_id = ?
        ORDER BY r.request_id DESC
    """, (member_id,)).fetchall()
    conn.close()
    return rows


def get_my_loans(member_id):
    conn = _connect()
    rows = conn.execute("""
        SELECT l.loan_id, b.title, l.issue_date, l.due_date
        FROM loans l
        JOIN books b ON b.book_id = l.book_id
        WHERE l.member_id = ? AND l.return_date IS NULL
        ORDER BY l.due_date
    """, (member_id,)).fetchall()
    conn.close()
    return rows


# ---------- Admin side ----------
def get_pending_requests():
    conn = _connect()
    rows = conn.execute("""
        SELECT r.request_id, m.reg_no, m.name, b.title,
               b.available_copies, r.requested_on
        FROM requests r
        JOIN members m ON m.member_id = r.member_id
        JOIN books b ON b.book_id = r.book_id
        WHERE r.status = 'Pending'
        ORDER BY r.request_id
    """).fetchall()
    conn.close()
    return rows


def decide_request(request_id, approve, note=""):
    conn = _connect()
    try:
        req = conn.execute(
            "SELECT member_id, book_id, status FROM requests WHERE request_id = ?",
            (request_id,)).fetchone()
        if req is None or req[2] != "Pending":
            return False, "This request is no longer pending."
        member_id, book_id, _ = req

        if not approve:
            conn.execute(
                "UPDATE requests SET status = 'Rejected', note = ? WHERE request_id = ?",
                (note.strip(), request_id))
            conn.commit()
            return True, "Request rejected."

        copies = conn.execute(
            "SELECT available_copies FROM books WHERE book_id = ?",
            (book_id,)).fetchone()[0]
        if copies < 1:
            return False, "No copies left to issue."

        loan_count = conn.execute(
            "SELECT COUNT(*) FROM loans WHERE member_id = ? AND return_date IS NULL",
            (member_id,)).fetchone()[0]
        if loan_count >= MAX_BOOKS:
            return False, f"This student already has {MAX_BOOKS} books."

        today = date.today()
        due = today + timedelta(days=LOAN_DAYS)
        conn.execute(
            "INSERT INTO loans (member_id, book_id, issue_date, due_date) VALUES (?, ?, ?, ?)",
            (member_id, book_id, today.isoformat(), due.isoformat()))
        conn.execute(
            "UPDATE books SET available_copies = available_copies - 1 WHERE book_id = ?",
            (book_id,))
        conn.execute(
            "UPDATE requests SET status = 'Approved' WHERE request_id = ?",
            (request_id,))
        conn.commit()
        return True, f"Book issued. Due date: {due.isoformat()}"
    finally:
        conn.close()


def get_all_loans():
    conn = _connect()
    rows = conn.execute("""
        SELECT l.loan_id, m.reg_no, m.name, b.title, l.issue_date, l.due_date
        FROM loans l
        JOIN members m ON m.member_id = l.member_id
        JOIN books b ON b.book_id = l.book_id
        WHERE l.return_date IS NULL
        ORDER BY l.due_date
    """).fetchall()
    conn.close()
    return rows


def return_book(loan_id):
    conn = _connect()
    try:
        loan = conn.execute(
            "SELECT book_id, return_date FROM loans WHERE loan_id = ?",
            (loan_id,)).fetchone()
        if loan is None:
            return False, "Loan not found."
        if loan[1] is not None:
            return False, "This book was already returned."

        conn.execute(
            "UPDATE loans SET return_date = ? WHERE loan_id = ?",
            (date.today().isoformat(), loan_id))
        conn.execute(
            "UPDATE books SET available_copies = available_copies + 1 WHERE book_id = ?",
            (loan[0],))
        conn.commit()
        return True, "Book marked as returned."
    finally:
        conn.close()
