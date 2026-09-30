import sqlite3
import hashlib
from datetime import date, timedelta

DB = "library.db"
LOAN_DAYS = 14
MAX_BOOKS = 3


def _hash(password):
    return hashlib.sha256(password.encode()).hexdigest()


# ---------- Admin login ----------
def login_admin(username, password):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        "SELECT member_id, name FROM members "
        "WHERE reg_no = ? AND password_hash = ? AND is_admin = 1",
        (username.strip(), _hash(password)))
    row = cur.fetchone()
    conn.close()
    return row  # (member_id, name) or None


# ---------- Students (demo ERP list) ----------
def get_student(reg_no):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        "SELECT reg_no, name FROM students WHERE reg_no = ? COLLATE NOCASE",
        (reg_no.strip(),))
    row = cur.fetchone()
    conn.close()
    return row  # (reg_no, name) or None


def add_student(reg_no, name):
    reg_no = reg_no.strip()
    name = name.strip()
    if not reg_no or not name:
        return False, "Please enter both register number and name."
    if get_student(reg_no):
        return False, "This register number is already in the list."

    conn = sqlite3.connect(DB)
    conn.execute("INSERT INTO students (reg_no, name) VALUES (?, ?)", (reg_no, name))
    conn.commit()
    conn.close()
    return True, "Student added."


def count_active_loans(reg_no):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM loans WHERE reg_no = ? AND return_date IS NULL",
        (reg_no,))
    count = cur.fetchone()[0]
    conn.close()
    return count


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
def issue_book(reg_no, book_id):
    student = get_student(reg_no)
    if student is None:
        return False, "Student ID not found."
    reg_no, student_name = student

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute(
        "SELECT COUNT(*) FROM loans WHERE reg_no = ? AND return_date IS NULL",
        (reg_no,))
    active = cur.fetchone()[0]
    if active >= MAX_BOOKS:
        conn.close()
        return False, (f"Limit reached: {student_name} already has {active} books "
                       f"(maximum {MAX_BOOKS}). A book must be returned first.")

    cur.execute("SELECT title, available_copies FROM books WHERE book_id = ?", (book_id,))
    book = cur.fetchone()
    if book is None:
        conn.close()
        return False, "Book not found."
    if book[1] < 1:
        conn.close()
        return False, "No copies available."

    cur.execute(
        "SELECT 1 FROM loans WHERE reg_no = ? AND book_id = ? AND return_date IS NULL",
        (reg_no, book_id))
    if cur.fetchone():
        conn.close()
        return False, f"{student_name} already has this book."

    today = date.today()
    due = today + timedelta(days=LOAN_DAYS)
    cur.execute(
        "INSERT INTO loans (reg_no, book_id, issue_date, due_date) VALUES (?, ?, ?, ?)",
        (reg_no, book_id, today.isoformat(), due.isoformat()))
    cur.execute(
        "UPDATE books SET available_copies = available_copies - 1 WHERE book_id = ?",
        (book_id,))
    conn.commit()
    conn.close()
    return True, (f"ID verified: {student_name}. '{book[0]}' issued. "
                  f"Due date: {due.isoformat()}")


def return_book(reg_no, book_id):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        "SELECT loan_id FROM loans "
        "WHERE reg_no = ? AND book_id = ? AND return_date IS NULL",
        (reg_no, book_id))
    row = cur.fetchone()
    if row is None:
        conn.close()
        return False, "No active loan found for this book."

    cur.execute(
        "UPDATE loans SET return_date = ? WHERE loan_id = ?",
        (date.today().isoformat(), row[0]))
    cur.execute(
        "UPDATE books SET available_copies = available_copies + 1 WHERE book_id = ?",
        (book_id,))
    conn.commit()
    conn.close()
    return True, "Book returned."


def get_student_loans(reg_no):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT b.book_id, b.title, l.issue_date, l.due_date
        FROM loans l
        JOIN books b ON b.book_id = l.book_id
        WHERE l.reg_no = ? AND l.return_date IS NULL
        ORDER BY l.due_date
    """, (reg_no,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_all_loans():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT s.reg_no, s.name, b.title, l.issue_date, l.due_date
        FROM loans l
        JOIN students s ON s.reg_no = l.reg_no
        JOIN books b ON b.book_id = l.book_id
        WHERE l.return_date IS NULL
        ORDER BY l.due_date
    """)
    rows = cur.fetchall()
    conn.close()
    return rows
