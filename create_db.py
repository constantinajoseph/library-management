import sqlite3
import hashlib

# Demo "ERP" list: replace these with your friends' register numbers and names.
DEMO_STUDENTS = [
    ("145111268", "Constantina J"),
    ("145111292", "Oshika Arsha A"),
    ("145111270", "Devika V"),
    ("145111287", "Kavyasri R"),
    ("145111306","Rithikasri K"),
]


def init_db():
    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    # Only used for the admin (librarian) login
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

    # Demo student list (stands in for the college ERP)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        reg_no TEXT PRIMARY KEY,
        name TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS loans (
        loan_id INTEGER PRIMARY KEY AUTOINCREMENT,
        reg_no TEXT NOT NULL,
        book_id INTEGER NOT NULL,
        issue_date TEXT NOT NULL,
        due_date TEXT NOT NULL,
        return_date TEXT,
        FOREIGN KEY (reg_no) REFERENCES students (reg_no),
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

    # Demo students (added if not already there)
    for reg, student_name in DEMO_STUDENTS:
        cursor.execute(
            "INSERT OR IGNORE INTO students (reg_no, name) VALUES (?, ?)",
            (reg, student_name))

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database and tables ready!")
