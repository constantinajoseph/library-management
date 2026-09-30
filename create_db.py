
import sqlite3

DB_NAME = "library.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Admin table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # Books table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            category TEXT NOT NULL,
            total_copies INTEGER NOT NULL,
            available_copies INTEGER NOT NULL
        )
    """)

    # Students table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            reg_no TEXT PRIMARY KEY,
            name TEXT NOT NULL
        )
    """)

    # Book loans table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reg_no TEXT NOT NULL,
            book_id INTEGER NOT NULL,
            issue_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            return_date TEXT,
            FOREIGN KEY (reg_no) REFERENCES students(reg_no),
            FOREIGN KEY (book_id) REFERENCES books(id)
        )
    """)

    # Create default admin only if it does not exist
    cur.execute("""
        INSERT OR IGNORE INTO admins (username, password)
        VALUES (?, ?)
    """, ("admin", "admin123"))

    # Sample books
    sample_books = [
        ("Python Programming", "Reema Thareja", "Programming", 5, 5),
        ("Java: The Complete Reference", "Herbert Schildt", "Programming", 5, 5),
        ("Data Structures", "Seymour Lipschutz", "Computer Science", 4, 4),
        ("Theory of Computation", "Mishra and Chandrasekaran", "TOC", 3, 3),
        ("Database Management Systems", "Raghu Ramakrishnan", "DBMS", 4, 4)
    ]

    cur.executemany("""
        INSERT INTO books
        (title, author, category, total_copies, available_copies)
        SELECT ?, ?, ?, ?, ?
        WHERE NOT EXISTS (
            SELECT 1 FROM books WHERE title = ?
        )
    """, [(*book, book[0]) for book in sample_books])

    # Demo students: replace these with your friends' demo details
    sample_students = [
        ("145111268", "Constantina J"),
        ("145111270", "Devika V"),
        ("145111287", "Kavyasri R"),
        ("145111292", "Oshika Arsha A"),
        ("145111306", "Rithikasri K")
    ]

    cur.executemany("""
        INSERT OR IGNORE INTO students (reg_no, name)
        VALUES (?, ?)
    """, sample_students)

    conn.commit()
    conn.close()
