import sqlite3
from werkzeug.security import generate_password_hash

def safe_update_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # === Schools table ===
    c.execute('''
        CREATE TABLE IF NOT EXISTS schools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            admin_username TEXT NOT NULL UNIQUE,
            admin_password TEXT NOT NULL
        )
    ''')

    # === Students table ===
    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            class_level TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            school_id INTEGER NOT NULL,
            FOREIGN KEY (school_id) REFERENCES schools(id)
        )
    ''')

    # === Questions table (Supports Multiple Sets) ===
    c.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_level TEXT NOT NULL,
            subject TEXT NOT NULL,
            topic TEXT NOT NULL,
            qna_2m TEXT NOT NULL,
            qna_5m TEXT NOT NULL,
            exam_mode TEXT DEFAULT 'topic',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # === Answers table ===
    c.execute('''
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            class_level TEXT NOT NULL,
            school_name TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            student_answer TEXT NOT NULL,
            evaluation TEXT,
            score INTEGER,
            school_id INTEGER NOT NULL,
            exam_mode TEXT DEFAULT 'topic',
            FOREIGN KEY (school_id) REFERENCES schools(id)
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ Database structure verified and updated safely.")

if __name__ == '__main__':
    safe_update_db()
