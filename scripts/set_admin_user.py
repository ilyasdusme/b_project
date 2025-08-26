import sqlite3
from werkzeug.security import generate_password_hash

USERNAME = "sugreks"
PASSWORD = "18631258.!#="
DB_PATH = "blog.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    pwd = generate_password_hash(PASSWORD)
    # Ensure table exists
    c.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Upsert user
    c.execute("SELECT id FROM admin_users WHERE username=?", (USERNAME,))
    row = c.fetchone()
    if row:
        c.execute("UPDATE admin_users SET password_hash=? WHERE id=?", (pwd, row[0]))
    else:
        c.execute("INSERT INTO admin_users (username, password_hash) VALUES (?, ?)", (USERNAME, pwd))
    # Remove default 'admin' user if exists
    c.execute("DELETE FROM admin_users WHERE username=?", ("admin",))
    conn.commit()
    conn.close()
    print(f"Admin user '{USERNAME}' set successfully.")

if __name__ == "__main__":
    main()
