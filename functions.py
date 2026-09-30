import sqlite3

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