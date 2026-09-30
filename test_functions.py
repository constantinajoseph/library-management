from functions import get_connection, member_exists

# Add a test member
conn = get_connection()
cursor = conn.cursor()
cursor.execute("INSERT OR IGNORE INTO members (member_id, reg_no, name, password_hash) VALUES (?, ?, ?, ?)",
               (1, "REG001", "Test Member", "test"))
conn.commit()
conn.close()

# Try the function
print("Member 1 exists:", member_exists(1))
print("Member 99 exists:", member_exists(99))