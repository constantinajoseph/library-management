from functions import get_connection, return_book

print(return_book(1))
print(return_book(1))
print(return_book(99))

conn = get_connection()
cursor = conn.cursor()
cursor.execute("SELECT * FROM transactions")
print("Transactions:", cursor.fetchall())
cursor.execute("SELECT title, available_copies FROM books WHERE book_id = 1")
print("Book 1:", cursor.fetchone())
conn.close()