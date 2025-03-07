import sqlite3

# Baza bilan ulanish
connect = sqlite3.connect("bot_database.db")
cursor = connect.cursor()

# Guruhlarni saqlash uchun jadval
cursor.execute("""
CREATE TABLE IF NOT EXISTS active_groups (
    group_id TEXT PRIMARY KEY,
    group_name TEXT,
    joined_date TEXT
)
""")

# Rejalashtirilgan postlar uchun jadval
cursor.execute("""
CREATE TABLE IF NOT EXISTS active_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    photo TEXT,
    caption TEXT,
    post_time TEXT,
    status TEXT DEFAULT 'active'
)
""")



connect.commit()

def get_post(post_id):
    return cursor.execute("""
    SELECT * FROM active_posts WHERE id = ?
    """, (post_id,)).fetchone()

def get_post_times(post_id):
    result = cursor.execute("""
        SELECT post_time FROM active_posts WHERE id = ?
    """, (post_id,)).fetchone()
    
    if result and result[0]:
        # Tuple ning birinchi elementini olib, list ga aylantiramiz
        return result[0].split(",")
    else:
        # Agar post_time bo'sh bo'lsa, bo'sh list qaytadi
        return []

def updateting_post_time(post_id, post_time):
    cursor.execute("""
    UPDATE active_posts SET post_time = ? WHERE id = ?
    """, (post_time, post_id))
    connect.commit()

# Post qo‘shish funksiyasi
def add_post(photo, caption, post_time):
    cursor.execute("""
    INSERT INTO active_posts (photo, caption, post_time) 
    VALUES (?, ?, ?)
    """, (photo, caption, post_time))
    
    connect.commit()

# Barcha aktiv postlarni olish
def get_active_posts():
    return cursor.execute("""
    SELECT * FROM active_posts WHERE status = 'active'
    """).fetchall()

# Postni statusini "sent" qilish
def mark_post_as_sent(post_id):
    cursor.execute("""
    UPDATE active_posts SET status = 'sent' WHERE id = ?
    """, (post_id,))
    connect.commit()
