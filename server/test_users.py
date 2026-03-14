import database

conn = database.get_db_connection()
cursor = conn.cursor()
cursor.execute('SELECT username, role, created_at FROM users')
users = cursor.fetchall()
conn.close()

print(f'Users found: {len(users)}')
for u in users:
    print(f'  - Username: {u["username"]}, Role: {u["role"]}, Created: {u["created_at"]}')
