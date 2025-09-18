import mysql.connector
from mysql.connector import errorcode

DB_CONFIG = {
    "host": "localhost",
    "user": "root",           
    "password": "3381222384", 
    "database": "queez"
}

def get_server_connection():
    """اتصال به سرور MySQL بدون انتخاب دیتابیس (برای ایجاد دیتابیس اگر لازم باشد)"""
    cfg = DB_CONFIG.copy()
    cfg.pop("database", None)
    return mysql.connector.connect(**cfg)

def get_connection():
    """اتصال به دیتابیس مشخص (DB_CONFIG['database'])"""
    return mysql.connector.connect(**DB_CONFIG)

def init_db():
    """ایجاد دیتابیس و جداول (با حذف جداول قبلی ناسازگار)"""
    try:
        server_conn = get_server_connection()
        server_conn.autocommit = True
        cur = server_conn.cursor()
        cur.execute("CREATE DATABASE IF NOT EXISTS `{}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci".format(DB_CONFIG["database"]))
        server_conn.close()
    except mysql.connector.Error as e:
        print("خطا هنگام ایجاد دیتابیس:", e)
        raise

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        cursor.execute("DROP TABLE IF EXISTS student_answers")
        cursor.execute("DROP TABLE IF EXISTS results")
        cursor.execute("DROP TABLE IF EXISTS questions")
        cursor.execute("DROP TABLE IF EXISTS exams")
        cursor.execute("DROP TABLE IF EXISTS students")
        cursor.execute("DROP TABLE IF EXISTS teachers")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    except mysql.connector.Error as e:
        print("خطا هنگام پاک کردن جداول قدیمی:", e)
        conn.close()
        raise

    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            teacher_id INT NOT NULL UNIQUE,
            firstname VARCHAR(100) NOT NULL,
            lastname VARCHAR(100) NOT NULL,
            grade VARCHAR(50) NOT NULL,
            subject VARCHAR(50) NOT NULL,
            password VARCHAR(255) NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT NOT NULL UNIQUE,
            firstname VARCHAR(100) NOT NULL,
            lastname VARCHAR(100) NOT NULL,
            grade VARCHAR(50) NOT NULL,
            password VARCHAR(255) NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS exams (
            id INT AUTO_INCREMENT PRIMARY KEY,
            exam_code INT NOT NULL UNIQUE,
            teacher_id INT NOT NULL,
            duration INT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_exams_teacher_id (teacher_id),
            CONSTRAINT fk_exams_teacher FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            exam_id INT NOT NULL,
            question_text TEXT NOT NULL,
            question_type ENUM('testi','blank','yesno') NOT NULL,
            option1 TEXT,
            option2 TEXT,
            option3 TEXT,
            option4 TEXT,
            correct_answer TEXT NOT NULL,
            difficulty ENUM('easy','medium','hard') NOT NULL,
            score FLOAT NOT NULL,
            INDEX idx_questions_exam_id (exam_id),
            CONSTRAINT fk_questions_exam FOREIGN KEY (exam_id) REFERENCES exams(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_answers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            exam_id INT NOT NULL,
            student_id INT NOT NULL,
            question_id INT NOT NULL,
            student_answer TEXT,
            is_correct BOOLEAN,
            answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_sa_exam_id (exam_id),
            INDEX idx_sa_student_id (student_id),
            INDEX idx_sa_question_id (question_id),
            CONSTRAINT fk_sa_exam FOREIGN KEY (exam_id) REFERENCES exams(id) ON DELETE CASCADE,
            CONSTRAINT fk_sa_student FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
            CONSTRAINT fk_sa_question FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INT AUTO_INCREMENT PRIMARY KEY,
            exam_id INT NOT NULL,
            student_id INT NOT NULL,
            score FLOAT NOT NULL,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_results_exam_id (exam_id),
            INDEX idx_results_student_id (student_id),
            CONSTRAINT fk_results_exam FOREIGN KEY (exam_id) REFERENCES exams(id) ON DELETE CASCADE,
            CONSTRAINT fk_results_student FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        conn.commit()
    except mysql.connector.Error as e:
        conn.rollback()
        print("خطا هنگام ایجاد جداول:", e)
        raise
    finally:
        conn.close()

def get_next_exam_code():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(exam_code) FROM exams")
    r = cursor.fetchone()
    conn.close()
    max_val = r[0] if r else None
    return 100000 if max_val is None else max_val + 1

def create_exam(teacher_id, duration=30):
    exam_code = get_next_exam_code()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO exams (exam_code, teacher_id, duration) VALUES (%s, %s, %s)", (exam_code, teacher_id, duration))
    conn.commit()
    exam_id = cursor.lastrowid
    conn.close()
    return exam_id, exam_code

def add_question(exam_id, question_text, question_type, options, correct_answer, difficulty, score):
    conn = get_connection()
    cursor = conn.cursor()
    opt1 = opt2 = opt3 = opt4 = None
    if question_type == "testi" and options:

        opt1, opt2, opt3, opt4 = (options + [None, None, None, None])[:4]
    cursor.execute("""INSERT INTO questions 
                      (exam_id, question_text, question_type, option1, option2, option3, option4, correct_answer, difficulty, score)
                      VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                   (exam_id, question_text, question_type, opt1, opt2, opt3, opt4, correct_answer, difficulty, score))
    conn.commit()
    conn.close()

def save_student_answer(exam_id, student_id, question_id, student_answer, is_correct):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""INSERT INTO student_answers
                      (exam_id, student_id, question_id, student_answer, is_correct)
                      VALUES (%s,%s,%s,%s,%s)""",
                   (exam_id, student_id, question_id, student_answer, int(bool(is_correct))))
    conn.commit()
    conn.close()

def save_result(exam_id, student_id, score):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO results (exam_id, student_id, score) VALUES (%s,%s,%s)", (exam_id, student_id, score))
    conn.commit()
    conn.close()

def get_student_results(student_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT r.*, e.exam_code
        FROM results r
        JOIN exams e ON r.exam_id = e.id
        WHERE r.student_id = %s
        ORDER BY r.completed_at DESC
    """, (student_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_exam_questions(exam_code):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM exams WHERE exam_code = %s", (exam_code,))
    exam = cursor.fetchone()
    if not exam:
        conn.close()
        return []
    exam_id = exam["id"]
    cursor.execute("SELECT * FROM questions WHERE exam_id = %s ORDER BY id", (exam_id,))
    questions = cursor.fetchall()
    conn.close()
    return questions
