import sqlite3

# Connect to the database (it is created if it doesn't exist)
conn = sqlite3.connect("library.db")
cursor = conn.cursor()

# Members table
cursor.execute("""
CREATE TABLE IF NOT EXISTS members (
    member_id INTEGER PRIMARY KEY AUTOINCREMENT,
    reg_no TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL
)
""")

# Books table

# Books table
cursor.execute("""
CREATE TABLE IF NOT EXISTS books (
    book_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    category TEXT,
    available_copies INTEGER NOT NULL DEFAULT 1
)
""")

# Transactions table (records every issue and return)
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

conn.commit()
conn.close()

print("Database and tables created successfully!")