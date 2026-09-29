import sqlite3
import hashlib


def init_db():
    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS members (
        member_id INTEGER PRIMARY KEY AUTOINCREMENT,
        reg_no TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        is_admin INTEGER NOT NULL DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS books (
        book_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        category TEXT,
        available_copies INTEGER NOT NULL DEFAULT 1
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER NOT NULL,
        book_id INTEGER NOT NULL,
        issue_date TEXT NOT NULL,
        due_date TEXT NOT NULL,
        return_date TEXT,
        FOREIGN KEY (member_id) REFERENCES members (member_id),
        FOREIGN KEY (book_id) REFERENCES books (book_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER NOT NULL,
        book_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending',
        requested_on TEXT NOT NULL,
        note TEXT,
        FOREIGN KEY (member_id) REFERENCES members (member_id),
        FOREIGN KEY (book_id) REFERENCES books (book_id)
    )
    """)

    # Starter admin (only when there are no members yet)
    cursor.execute("SELECT COUNT(*) FROM members")
    if cursor.fetchone()[0] == 0:
        admin_hash = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute(
            "INSERT INTO members (reg_no, name, password_hash, is_admin) VALUES (?, ?, ?, 1)",
            ("admin", "Admin", admin_hash))

    # Sample books (only when there are no books yet)
    cursor.execute("SELECT COUNT(*) FROM books")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO books (title, author, category, available_copies) VALUES (?, ?, ?, ?)",
            [
                ("Learning Python", "Mark Lutz", "Programming", 3),
                ("Clean Code", "Robert C. Martin", "Programming", 2),
                ("Theory of Computation", "Michael Sipser", "Computer Science", 2),
            ])

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database and tables ready!")
