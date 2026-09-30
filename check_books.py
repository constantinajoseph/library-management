from functions import get_connection, find_book

# Add a test book
conn = get_connection()
cursor = conn.cursor()
cursor.execute("INSERT OR IGNORE INTO books (book_id, title, author, category, available_copies) VALUES (?, ?, ?, ?, ?)",
               (1, "Learning Python", "Mark Lutz", "Programming", 3))
conn.commit()
conn.close()

# Try the function
print("Search 'python':", find_book("python"))
print("Search 'cooking':", find_book("cooking"))