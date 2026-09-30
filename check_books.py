
from functions import register_member, member_exists

print(register_member("145111999", "Anu", "mypassword"))
print(register_member("145111999", "Anu", "mypassword"))
print(register_member("", "Anu", "mypassword"))
print("145111999 exists:", member_exists("145111999"))