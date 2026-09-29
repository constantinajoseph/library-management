import sqlite3
import hashlib
from datetime import date, timedelta

DB = "library.db"
LOAN_DAYS = 14


def _hash(password):
    return hashlib.sha256(password.encode()).hexdigest()


# ---------- Accounts ----------
def register_member(reg_no, name, password):
    reg_no = reg_no.strip()
    name = name.strip()
    if not reg_no or not name or not password:
        return False, "Please fill in all the fields."

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM members WHERE reg_no = ?", (reg_no,))
    if cur.fetchone():
        conn.close()
        return False, "This registration number already has an account."

    cur.execute(
        "INSERT INTO members (reg_no, name, password_hash, is_admin) VALUES (?, ?, ?, 0)",
        (reg_no, name, _hash(password)))
    conn.commit()
    conn.close()
    return True, "Account created. You can log in now."


def login_member(reg_no, password):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        "SELECT member_id, name FROM members WHERE reg_no = ? AND password_hash = ?",
        (reg_no.strip(), _hash(password)))
    row = cur.fetchone()
    conn.close()
    return row  # (member_id, name) or None


def is_admin(member_id):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT is_admin FROM members WHERE member_id = ?", (member_id,))
    row = cur.fetchone()
    conn.close()
    return bool(row and row[0] == 1)


# ---------- Books ----------
def search_books(keyword):
    like = f"%{keyword.strip()}%"
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT book_id, title, author, category, available_copies
        FROM books
        WHERE title LIKE ? OR author LIKE ? OR IFNULL(category, '') LIKE ?
        ORDER BY title
    """, (like, like, like))
    rows = cur.fetchall()
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

    conn = sqlite3.connect(DB)
    conn.execute(
        "INSERT INTO books (title, author, category, available_copies) VALUES (?, ?, ?, ?)",
        (title, author, category, copies))
    conn.commit()
    conn.close()
    return True, "Book added."


# ---------- Issue / Return ----------
def issue_book(member_id, book_id):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("SELECT available_copies FROM books WHERE book_id = ?", (book_id,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        return False, "Book not found."
    if row[0] < 1:
        conn.close()
        return False, "No copies available."

    cur.execute(
        "SELECT 1 FROM transactions WHERE member_id = ? AND book_id = ? AND return_date IS NULL",
        (member_id, book_id))
    if cur.fetchone():
        conn.close()
        return False, "This member already has this book."

    today = date.today()
    due = today + timedelta(days=LOAN_DAYS)
    cur.execute(
        "INSERT INTO transactions (member_id, book_id, issue_date, due_date) VALUES (?, ?, ?, ?)",
        (member_id, book_id, today.isoformat(), due.isoformat()))
    cur.execute(
        "UPDATE books SET available_copies = available_copies - 1 WHERE book_id = ?",
        (book_id,))
    conn.commit()
    conn.close()
    return True, f"Book issued. Due date: {due.isoformat()}"


def return_book(member_id, book_id):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        "SELECT transaction_id FROM transactions "
        "WHERE member_id = ? AND book_id = ? AND return_date IS NULL",
        (member_id, book_id))
    row = cur.fetchone()
    if row is None:
        conn.close()
        return False, "No active loan found for this book."

    cur.execute(
        "UPDATE transactions SET return_date = ? WHERE transaction_id = ?",
        (date.today().isoformat(), row[0]))
    cur.execute(
        "UPDATE books SET available_copies = available_copies + 1 WHERE book_id = ?",
        (book_id,))
    conn.commit()
    conn.close()
    return True, "Book returned."


def get_borrowed_books(member_id):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT b.book_id, b.title, t.issue_date, t.due_date
        FROM transactions t
        JOIN books b ON b.book_id = t.book_id
        WHERE t.member_id = ? AND t.return_date IS NULL
        ORDER BY t.due_date
    """, (member_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


# ---------- Requests (student asks, admin approves) ----------
def request_book(member_id, book_id):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute(
        "SELECT 1 FROM requests WHERE member_id = ? AND book_id = ? AND status = 'Pending'",
        (member_id, book_id))
    if cur.fetchone():
        conn.close()
        return False, "You have already requested this book."

    cur.execute(
        "SELECT 1 FROM transactions WHERE member_id = ? AND book_id = ? AND return_date IS NULL",
        (member_id, book_id))
    if cur.fetchone():
        conn.close()
        return False, "You already have this book."

    cur.execute(
        "INSERT INTO requests (member_id, book_id, status, requested_on) VALUES (?, ?, 'Pending', ?)",
        (member_id, book_id, date.today().isoformat()))
    conn.commit()
    conn.close()
    return True, "Request sent. Wait for the admin to approve it."


def get_member_requests(member_id):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT r.request_id, b.title, r.status, r.requested_on, r.note
        FROM requests r
        JOIN books b ON b.book_id = r.book_id
        WHERE r.member_id = ?
        ORDER BY r.request_id DESC
    """, (member_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_pending_requests():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT r.request_id, m.reg_no, m.name, b.title, b.available_copies, r.requested_on
        FROM requests r
        JOIN members m ON m.member_id = r.member_id
        JOIN books b ON b.book_id = r.book_id
        WHERE r.status = 'Pending'
        ORDER BY r.request_id
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def approve_request(request_id):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        "SELECT member_id, book_id FROM requests WHERE request_id = ? AND status = 'Pending'",
        (request_id,))
    row = cur.fetchone()
    conn.close()
    if row is None:
        return False, "This request is no longer pending."

    member_id, book_id = row
    ok, message = issue_book(member_id, book_id)
    if not ok:
        return False, message

    conn = sqlite3.connect(DB)
    conn.execute("UPDATE requests SET status = 'Approved' WHERE request_id = ?", (request_id,))
    conn.commit()
    conn.close()
    return True, "Request approved and book issued."


def reject_request(request_id, note=""):
    conn = sqlite3.connect(DB)
    conn.execute(
        "UPDATE requests SET status = 'Rejected', note = ? "
        "WHERE request_id = ? AND status = 'Pending'",
        (note, request_id))
    conn.commit()
    conn.close()
    return True, "Request rejected."
