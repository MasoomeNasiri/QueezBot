import mysql.connector
from CONFIG import config

def get_connection():
    """ایجاد اتصال به دیتابیس"""
    return mysql.connector.connect(**config)

def get_exam_questions(exam_code):
    """
    گرفتن تمام سوالات یک آزمون بر اساس کد آزمون
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT q.*, e.id as exam_id
        FROM questions q
        JOIN exams e ON q.exam_id = e.id
        WHERE e.exam_code = %s
        ORDER BY q.id
    """, (exam_code,))
    questions = cursor.fetchall()
    conn.close()
    return questions

def has_student_taken_exam(student_id, exam_code):
    """
    چک کردن اینکه دانش‌آموز قبلاً در آزمون شرکت کرده یا نه
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.id
        FROM results r
        JOIN exams e ON r.exam_id = e.id
        WHERE r.student_id = %s AND e.exam_code = %s
    """, (student_id, exam_code))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def get_rank_in_exam(student_id, exam_id):
    """
    گرفتن رتبه دانش‌آموز در یک آزمون
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT student_id, score
        FROM results
        WHERE exam_id = %s
        ORDER BY score DESC
    """, (exam_id,))
    all_results = cursor.fetchall()
    conn.close()

    rank = 1
    for res in all_results:
        if res["student_id"] == student_id:
            break
        rank += 1
    return rank

def get_questions_by_subject_grade(subject, grade):
    """
    گرفتن سوالات مربوط به یک درس و مقطع
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT q.*, t.subject, t.grade
        FROM questions q
        JOIN exams e ON q.exam_id = e.id
        JOIN teachers t ON e.teacher_id = t.teacher_id
        WHERE t.subject = %s AND t.grade = %s
    """, (subject, grade))
    questions = cursor.fetchall()
    conn.close()
    return questions