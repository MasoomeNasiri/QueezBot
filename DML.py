import mysql.connector
from CONFIG import config  # ✅ اینجا باید config باشد

def get_connection():
    """ایجاد اتصال به پایگاه داده"""
    return mysql.connector.connect(**config)  # ✅ استفاده از config

def create_exam(teacher_id, duration):
    """
    ایجاد یک آزمون جدید و بازگرداندن exam_id و exam_code
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # تولید exam_code تصادفی ۶ رقمی
    import random
    exam_code = str(random.randint(100000, 999999))
    
    cursor.execute(
        "INSERT INTO exams (teacher_id, exam_code, duration) VALUES (%s, %s, %s)",  # تغییر: duration_minutes -> duration
        (teacher_id, exam_code, duration)
    )
    exam_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return exam_id, exam_code

def add_question(exam_id, question_text, question_type, options, correct_answer, difficulty, score):
    """
    افزودن سؤال به یک آزمون
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # تبدیل لیست options به چهار فیلد
    opt1 = opt2 = opt3 = opt4 = None
    if question_type == "testi" and options:
        opt1, opt2, opt3, opt4 = (options + [None, None, None, None])[:4]
    
    cursor.execute(
        """INSERT INTO questions 
        (exam_id, question_text, question_type, option1, option2, option3, option4, correct_answer, difficulty, score) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (exam_id, question_text, question_type, opt1, opt2, opt3, opt4, correct_answer, difficulty, score)
    )
    
    conn.commit()
    conn.close()

def get_exam_questions(exam_code):
    """
    دریافت تمام سؤالات یک آزمون بر اساس exam_code
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute(
        """SELECT q.*, e.id as exam_id 
        FROM questions q 
        JOIN exams e ON q.exam_id = e.id 
        WHERE e.exam_code = %s""",
        (exam_code,)
    )
    questions = cursor.fetchall()
    
    # تبدیل option1...4 به یک لیست
    for q in questions:
        q["options"] = [q["option1"], q["option2"], q["option3"], q["option4"]]
    
    conn.close()
    return questions

def save_student_answer(exam_id, student_id, question_id, student_answer, is_correct):
    """
    ذخیره پاسخ دانش‌آموز به یک سؤال
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """INSERT INTO student_answers 
        (exam_id, student_id, question_id, student_answer, is_correct) 
        VALUES (%s, %s, %s, %s, %s)""",
        (exam_id, student_id, question_id, student_answer, is_correct)
    )
    
    conn.commit()
    conn.close()

def save_result(exam_id, student_id, score):
    """
    ذخیره نمره نهایی دانش‌آموز در یک آزمون
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # بررسی وجود رکورد قبلی
    cursor.execute(
        "SELECT id FROM results WHERE exam_id = %s AND student_id = %s",
        (exam_id, student_id)
    )
    existing = cursor.fetchone()
    
    if existing:
        # به‌روزرسانی نمره موجود
        cursor.execute(
            "UPDATE results SET score = %s WHERE id = %s",
            (score, existing[0])
        )
    else:
        # درج رکورد جدید
        cursor.execute(
            "INSERT INTO results (exam_id, student_id, score) VALUES (%s, %s, %s)",
            (exam_id, student_id, score)
        )
    
    conn.commit()
    conn.close()

def get_student_results(student_id):
    """
    دریافت نتایج تمام آزمون‌های یک دانش‌آموز به همراه کد آزمون
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute(
        """SELECT r.*, e.exam_code 
        FROM results r 
        JOIN exams e ON r.exam_id = e.id 
        WHERE r.student_id = %s""",
        (student_id,)
    )
    results = cursor.fetchall()
    
    conn.close()
    return results

def get_question_bank(teacher_id):
    """
    دریافت بانک سؤالات یک معلم
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute(
        """SELECT q.*, e.exam_code 
        FROM questions q 
        JOIN exams e ON q.exam_id = e.id 
        WHERE e.teacher_id = %s""",
        (teacher_id,)
    )
    questions = cursor.fetchall()
    
    # تبدیل option1...4 به یک لیست
    for q in questions:
        q["options"] = [q["option1"], q["option2"], q["option3"], q["option4"]]
    
    conn.close()
    return questions

def delete_question(question_id):
    """
    حذف یک سؤال از پایگاه داده
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM questions WHERE id = %s", (question_id,))
    
    conn.commit()
    conn.close()

def get_all_questions():
    """
    گرفتن تمام سوالات از دیتابیس
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM questions")
    questions = cursor.fetchall()
    conn.close()
    return questions

def get_questions_by_subject_grade(subject, grade):
    """
    گرفتن تمام سوالات مربوط به یک درس و مقطع
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT q.*, t.subject, t.grade
    FROM questions q
    JOIN exams e ON q.exam_id = e.id
    JOIN teachers t ON e.teacher_id = t.teacher_id
    WHERE t.subject = %s AND t.grade = %s
    """
    cursor.execute(query, (subject, grade))
    questions = cursor.fetchall()
    conn.close()
    return questions
def has_student_taken_exam(student_id, exam_code):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM results WHERE student_id = %s AND exam_id = (SELECT id FROM exams WHERE exam_code = %s)", (student_id, exam_code))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def get_rank_in_exam(student_id, exam_id):
    """
    گرفتن رتبه یک دانش‌آموز در یک آزمون خاص
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # گرفتن تمام نمرات آزمون
    cursor.execute(
        "SELECT student_id, score FROM results WHERE exam_id = %s ORDER BY score DESC",
        (exam_id,)
    )
    all_results = cursor.fetchall()
    conn.close()

    # پیدا کردن رتبه
    rank = 1
    for res in all_results:
        if res["student_id"] == student_id:
            break
        rank += 1

    return rank

def update_question(question_id, question_text, question_type, options, correct_answer, difficulty, score):
    """
    به‌روزرسانی اطلاعات یک سؤال
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # تبدیل لیست options به چهار فیلد
    opt1 = opt2 = opt3 = opt4 = None
    if question_type == "testi" and options:
        opt1, opt2, opt3, opt4 = (options + [None, None, None, None])[:4]

    cursor.execute(
        """UPDATE questions 
        SET question_text = %s, question_type = %s, option1 = %s, option2 = %s, option3 = %s, option4 = %s, 
            correct_answer = %s, difficulty = %s, score = %s 
        WHERE id = %s""",
        (question_text, question_type, opt1, opt2, opt3, opt4, correct_answer, difficulty, score, question_id)
    )
     
    conn.commit()
    conn.close()