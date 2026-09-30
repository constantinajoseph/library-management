import sqlite3
from datetime import date, timedelta


def get_connection():
    return sqlite3.connect("library.db")


def member_exists(reg_no):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE reg_no = ?", (reg_no,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def find_book(search_text):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books WHERE title LIKE ?", ("%" + search_text + "%",))
    results = cursor.fetchall()
    conn.close()
    return results


def is_available(book_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT available_copies FROM books WHERE book_id = ?", (book_id,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return False
    return row[0] > 0


def issue_book(reg_no, book_id):
    if not member_exists(reg_no):
        return "Rejected: invalid library ID"
    if not is_available(book_id):
        return "Book not available"

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT member_id FROM members WHERE reg_no = ?", (reg_no,))
    member_id = cursor.fetchone()[0]

    today = date.today()
    due = today + timedelta(days=14)

    cursor.execute(
        "INSERT INTO transactions (member_id, book_id, issue_date, due_date) VALUES (?, ?, ?, ?)",
        (member_id, book_id, str(today), str(due)))
    cursor.execute(
        "UPDATE books SET available_copies = available_copies - 1 WHERE book_id = ?",
        (book_id,))

    conn.commit()
    conn.close()
    return "Book issued successfully"


def return_book(transaction_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT book_id, return_date FROM transactions WHERE transaction_id = ?", (transaction_id,))
    row = cursor.fetchone()

    if row is None:
        conn.close()
        return "Transaction not found"

    book_id, return_date = row
    if return_date is not None:
        conn.close()
        return "Book already returned"

    cursor.execute("UPDATE transactions SET return_date = ? WHERE transaction_id = ?",
                   (str(date.today()), transaction_id))
    cursor.execute("UPDATE books SET available_copies = available_copies + 1 WHERE book_id = ?",
                   (book_id,))

    conn.commit()
    conn.close()
    return "Return recorded"