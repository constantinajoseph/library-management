from functions import get_connection, member_exists

# Add a test member with a real-looking registration number
conn = get_connection()
cursor = conn.cursor()
cursor.execute("INSERT OR IGNORE INTO members (member_id, reg_no, name, password_hash) VALUES (?, ?, ?, ?)",
               (2, "145111268", "Ike", "test"))
conn.commit()
conn.close()

# Try the function
print("145111268 exists:", member_exists("145111268"))
print("999999999 exists:", member_exists("999999999"))