
import sqlite3
from datetime import date, timedelta
from create_db import get_connection

MAX_BOOKS = 3
LOAN_DAYS = 14


def login_admin(username, password):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, username
        FROM admins
        WHERE username = ? AND password = ?
    """, (username, password))

    admin = cur.fetchone()
    conn.close()
    return admin


def search_books(keyword=""):
    conn = get_connection()
    cur = conn.cursor()

    search = f"%{keyword.strip()}%"

    cur.execute("""
        SELECT
            id, title, author, category, available_copies
        FROM books
        WHERE title LIKE ?
           OR author LIKE ?
           OR category LIKE ?
        ORDER BY title
    """, (search, search, search))

    books = cur.fetchall()
    conn.close()
    return books


def add_book(title, author, category, copies):
    title = title.strip()
    author = author.strip()
    category = category.strip()

    if not title or not author or not category:
        return False, "Please fill in all book details."

    if copies < 1:
        return False, "Copies must be at least 1."

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id FROM books
        WHERE LOWER(title) = LOWER(?)
          AND LOWER(author) = LOWER(?)
    """, (title, author))

    if cur.fetchone():
        conn.close()
        return False, "This book already exists."

    cur.execute("""
        INSERT INTO books
        (title, author, category, total_copies, available_copies)
        VALUES (?, ?, ?, ?, ?)
    """, (title, author, category, copies, copies))

    conn.commit()
    conn.close()
    return True, "Book added successfully."


def get_student(reg_no):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT reg_no, name
        FROM students
        WHERE reg_no = ?
    """, (reg_no.strip(),))

    student = cur.fetchone()
    conn.close()
    return student


def add_student(reg_no, name):
    reg_no = reg_no.strip()
    name = name.strip()

    if not reg_no or not name:
        return False, "Please enter both register number and name."

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO students (reg_no, name)
            VALUES (?, ?)
        """, (reg_no, name))

        conn.commit()
        return True, "Student added successfully."

    except sqlite3.IntegrityError:
        return False, "This register number already exists."

    finally:
        conn.close()


def count_active_loans(reg_no):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM loans
        WHERE reg_no = ? AND return_date IS NULL
    """, (reg_no,))

    count = cur.fetchone()[0]
    conn.close()
    return count


def issue_book(reg_no, book_id):
    conn = get_connection()
    cur = conn.cursor()

    try:
        # Check student
        cur.execute("""
            SELECT name FROM students
            WHERE reg_no = ?
        """, (reg_no,))

        student = cur.fetchone()

        if student is None:
            return False, "Student verification failed."

        # Check book
        cur.execute("""
            SELECT title, available_copies
            FROM books
            WHERE id = ?
        """, (book_id,))

        book = cur.fetchone()

        if book is None:
            return False, "Book not found."

        if book[1] <= 0:
            return False, "This book is currently unavailable."

        # Check borrowing limit
        cur.execute("""
            SELECT COUNT(*)
            FROM loans
            WHERE reg_no = ? AND return_date IS NULL
        """, (reg_no,))

        active_count = cur.fetchone()[0]

        if active_count >= MAX_BOOKS:
            return False, (
                f"Issue rejected! {student[0]} has already "
                f"borrowed {MAX_BOOKS} books."
            )

        # Prevent duplicate active loan of same book
        cur.execute("""
            SELECT id FROM loans
            WHERE reg_no = ?
              AND book_id = ?
              AND return_date IS NULL
        """, (reg_no, book_id))

        if cur.fetchone():
            return False, "This student has already borrowed this book."

        # Issue book
        issue_date = date.today()
        due_date = issue_date + timedelta(days=LOAN_DAYS)

        cur.execute("""
            INSERT INTO loans
            (reg_no, book_id, issue_date, due_date)
            VALUES (?, ?, ?, ?)
        """, (
            reg_no,
            book_id,
            issue_date.isoformat(),
            due_date.isoformat()
        ))

        cur.execute("""
            UPDATE books
            SET available_copies = available_copies - 1
            WHERE id = ? AND available_copies > 0
        """, (book_id,))

        if cur.rowcount != 1:
            conn.rollback()
            return False, "Book is no longer available."

        conn.commit()

        return True, (
            f"'{book[0]}' issued successfully to {student[0]}. "
            f"Due date: {due_date.isoformat()}."
        )

    except sqlite3.Error as e:
        conn.rollback()
        return False, f"Database error: {e}"

    finally:
        conn.close()


def get_student_loans(reg_no):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            loans.id,
            books.title,
            loans.issue_date,
            loans.due_date
        FROM loans
        JOIN books ON loans.book_id = books.id
        WHERE loans.reg_no = ?
          AND loans.return_date IS NULL
        ORDER BY loans.due_date
    """, (reg_no,))

    loans = cur.fetchall()
    conn.close()
    return loans


def get_all_loans():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            loans.reg_no,
            students.name,
            books.title,
            loans.issue_date,
            loans.due_date
        FROM loans
        JOIN students ON loans.reg_no = students.reg_no
        JOIN books ON loans.book_id = books.id
        WHERE loans.return_date IS NULL
        ORDER BY loans.due_date
    """)

    loans = cur.fetchall()
    conn.close()
    return loans


def return_book(reg_no, loan_id):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT book_id
            FROM loans
            WHERE id = ?
              AND reg_no = ?
              AND return_date IS NULL
        """, (loan_id, reg_no))

        loan = cur.fetchone()

        if loan is None:
            return False, "Active loan not found."

        cur.execute("""
            UPDATE loans
            SET return_date = ?
            WHERE id = ?
              AND return_date IS NULL
        """, (date.today().isoformat(), loan_id))

        if cur.rowcount != 1:
            conn.rollback()
            return False, "Book has already been returned."

        cur.execute("""
            UPDATE books
            SET available_copies = available_copies + 1
            WHERE id = ?
        """, (loan[0],))

        conn.commit()
        return True, "Book returned successfully."

    except sqlite3.Error as e:
        conn.rollback()
        return False, f"Database error: {e}"

    finally:
        conn.close()
