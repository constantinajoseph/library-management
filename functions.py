import sqlite3
import hashlib
from datetime import date, timedelta


def get_connection():
    return sqlite3.connect("library.db")


def register_member(reg_no, name, password):
    if not reg_no.strip() or not name.strip() or not password:
        return "Please fill in all fields"

    password_hash = hashlib.sha256(password.encode()).hexdigest()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM members WHERE reg_no = ?", (reg_no.strip(),))
    if cursor.fetchone() is not None:
        conn.close()
        return "This registration number is already registered"

    cursor.execute(
        "INSERT INTO members (reg_no, name, password_hash) VALUES (?, ?, ?)",
        (reg_no.strip(), name.strip(), password_hash))
    conn.commit()
    conn.close()
    return "Account created. You can log in now."


def member_exists(member_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE member_id = ?", (member_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def login_member(reg_no, password):
    password_hash = hashlib.sha256(password.encode()).hexdigest()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT member_id, name FROM members WHERE reg_no = ? AND password_hash = ?",
                   (reg_no, password_hash))
    row = cursor.fetchone()
    conn.close()
    return row


MAX_BOOKS = 3

def check_eligibility(member_id):
    today = date.today().isoformat()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM transactions WHERE member_id = ? AND return_date IS NULL",
                   (member_id,))
    borrowed = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM transactions WHERE member_id = ? AND return_date IS NULL AND due_date < ?",
                   (member_id, today))
    overdue = cursor.fetchone()[0]

    conn.close()

    if overdue > 0:
        return False, "You have overdue books. Please return them first."
    if borrowed >= MAX_BOOKS:
        return False, "You have reached the borrowing limit of 3 books."
    return True, "Eligible to borrow."


def search_books(keyword):
    conn = get_connection()
    cursor = conn.cursor()
    pattern = "%" + keyword + "%"
    cursor.execute(
        "SELECT book_id, title, author, category, available_copies FROM books "
        "WHERE title LIKE ? OR author LIKE ? OR category LIKE ?",
        (pattern, pattern, pattern))
    rows = cursor.fetchall()
    conn.close()
    return rows


LOAN_DAYS = 14

def issue_book(member_id, book_id):
    ok, message = check_eligibility(member_id)
    if not ok:
        return False, message

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT available_copies FROM books WHERE book_id = ?", (book_id,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        return False, "Book not found."
    if row[0] <= 0:
        conn.close()
        return False, "No copies available right now."

    issue = date.today()
    due = issue + timedelta(days=LOAN_DAYS)
    cursor.execute(
        "INSERT INTO transactions (member_id, book_id, issue_date, due_date) VALUES (?, ?, ?, ?)",
        (member_id, book_id, issue.isoformat(), due.isoformat()))
    cursor.execute("UPDATE books SET available_copies = available_copies - 1 WHERE book_id = ?",
                   (book_id,))
    conn.commit()
    conn.close()
    return True, "Book issued. Due on " + due.isoformat()


FINE_PER_DAY = 2

def return_book(member_id, book_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT transaction_id, due_date FROM transactions "
        "WHERE member_id = ? AND book_id = ? AND return_date IS NULL "
        "ORDER BY transaction_id LIMIT 1",
        (member_id, book_id))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        return False, "No active loan found for this book."

    transaction_id, due_date = row
    today = date.today()
    days_late = (today - date.fromisoformat(due_date)).days

    cursor.execute("UPDATE transactions SET return_date = ? WHERE transaction_id = ?",
                   (today.isoformat(), transaction_id))
    cursor.execute("UPDATE books SET available_copies = available_copies + 1 WHERE book_id = ?",
                   (book_id,))
    conn.commit()
    conn.close()

    if days_late > 0:
        fine = days_late * FINE_PER_DAY
        return True, f"Book returned. It was {days_late} day(s) late. Fine: Rs. {fine}"
    return True, "Book returned."


def get_borrowed_books(member_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT books.book_id, books.title, transactions.issue_date, transactions.due_date "
        "FROM transactions JOIN books ON books.book_id = transactions.book_id "
        "WHERE transactions.member_id = ? AND transactions.return_date IS NULL "
        "ORDER BY transactions.due_date",
        (member_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def is_admin(member_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_admin FROM members WHERE member_id = ?", (member_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None and row[0] == 1


def add_book(title, author, category, copies):
    if not title.strip() or not author.strip():
        return False, "Title and author are required."
    if copies < 1:
        return False, "Copies must be at least 1."

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO books (title, author, category, available_copies) VALUES (?, ?, ?, ?)",
        (title.strip(), author.strip(), category.strip(), copies))
    conn.commit()
    conn.close()
    return True, "Book added."
    def request_book(member_id, book_id):
    from datetime import date
    conn = sqlite3.connect("library.db")
    cur = conn.cursor()

    cur.execute(
        "SELECT 1 FROM requests WHERE member_id=? AND book_id=? AND status='Pending'",
        (member_id, book_id))
    if cur.fetchone():
        conn.close()
        return False, "You have already requested this book."

    cur.execute(
        "SELECT 1 FROM transactions WHERE member_id=? AND book_id=? AND return_date IS NULL",
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
    conn = sqlite3.connect("library.db")
    cur = conn.cursor()
    cur.execute("""
        SELECT r.request_id, b.title, r.status, r.requested_on, r.note
        FROM requests r JOIN books b ON b.book_id = r.book_id
        WHERE r.member_id = ?
        ORDER BY r.request_id DESC
    """, (member_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_pending_requests():
    conn = sqlite3.connect("library.db")
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
    conn = sqlite3.connect("library.db")
    cur = conn.cursor()
    cur.execute(
        "SELECT member_id, book_id FROM requests WHERE request_id=? AND status='Pending'",
        (request_id,))
    row = cur.fetchone()
    conn.close()
    if row is None:
        return False, "This request is no longer pending."

    member_id, book_id = row
    ok, message = issue_book(member_id, book_id)  # your existing function
    if not ok:
        return False, message

    conn = sqlite3.connect("library.db")
    conn.execute("UPDATE requests SET status='Approved' WHERE request_id=?", (request_id,))
    conn.commit()
    conn.close()
    return True, "Request approved and book issued."


def reject_request(request_id, note=""):
    conn = sqlite3.connect("library.db")
    conn.execute(
        "UPDATE requests SET status='Rejected', note=? WHERE request_id=? AND status='Pending'",
        (note, request_id))
    conn.commit()
    conn.close()
    return True, "Request rejected."
