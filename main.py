import telebot
from telebot import types
import translate as tr
from Config import TOKEN
import DDL as db

import os
if os.environ.get("INIT_DB") == "1":
    db.init_db()

bot = telebot.TeleBot(TOKEN)

user_states = {}         
teacher_panels = {}     
student_exam_states = {} 

# -------------------- شروع ربات --------------------
@bot.message_handler(commands=['start'])
def start_command(message):
    bot.send_message(message.chat.id, "سلام 👋 خوش آمدید!")
    show_main_menu(message.chat.id)


def show_main_menu(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🔑 ورود", callback_data="login"),
        types.InlineKeyboardButton("📝 ثبت‌نام", callback_data="register")
    )
    bot.send_message(chat_id, tr.CHOOSE_ACTION, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "register")
def start_register(call):
    user_states[call.message.chat.id] = {"step": "choose_role"}
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(tr.ROLE_TEACHER, callback_data="role_teacher"),
        types.InlineKeyboardButton(tr.ROLE_STUDENT, callback_data="role_student")
    )
    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text=tr.ASK_ROLE,
                          reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("role_"))
def choose_role(call):
    state = user_states.get(call.message.chat.id)
    if not state:
        return
    role = call.data.replace("role_", "")
    state["role"] = role
    state["step"] = "firstname"
    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text=tr.ASK_FIRSTNAME)

@bot.message_handler(func=lambda m: m.chat.id in user_states and user_states[m.chat.id]["step"] not in ["login_id", "login_password"])
def handle_register(message):
    state = user_states[message.chat.id]
    step = state["step"]

    if step == "firstname":
        state["firstname"] = message.text
        state["step"] = "lastname"
        bot.send_message(message.chat.id, tr.ASK_LASTNAME)

    elif step == "lastname":
        state["lastname"] = message.text
        state["step"] = "grade"
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add(tr.GRADE_7, tr.GRADE_8, tr.GRADE_9)
        bot.send_message(message.chat.id, tr.ASK_GRADE, reply_markup=markup)

    elif step == "grade":
        state["grade"] = message.text
        if state["role"] == "teacher":
            state["step"] = "subject"
            markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            markup.add(tr.SUBJECT_MATH, tr.SUBJECT_SCIENCE, tr.SUBJECT_FARSI, tr.SUBJECT_HISTORY)
            bot.send_message(message.chat.id, tr.ASK_SUBJECT, reply_markup=markup)
        else:
            state["step"] = "password"
            bot.send_message(message.chat.id, tr.ASK_PASSWORD, reply_markup=types.ReplyKeyboardRemove())

    elif step == "subject":
        state["subject"] = message.text
        state["step"] = "password"
        bot.send_message(message.chat.id, tr.ASK_PASSWORD, reply_markup=types.ReplyKeyboardRemove())

    elif step == "password":
        state["password"] = message.text
        conn = db.get_connection()
        cursor = conn.cursor()

        if state["role"] == "teacher":
            cursor.execute("SELECT MAX(teacher_id) FROM teachers")
            max_id = cursor.fetchone()[0] or 999
            user_id = max_id + 1
            cursor.execute("""INSERT INTO teachers (teacher_id, firstname, lastname, grade, subject, password)
                              VALUES (%s,%s,%s,%s,%s,%s)""",
                           (user_id, state["firstname"], state["lastname"], state["grade"],
                            state["subject"], state["password"]))
        else:
            cursor.execute("SELECT MAX(student_id) FROM students")
            max_id = cursor.fetchone()[0] or 9999
            user_id = max_id + 1
            cursor.execute("""INSERT INTO students (student_id, firstname, lastname, grade, password)
                              VALUES (%s,%s,%s,%s,%s)""",
                           (user_id, state["firstname"], state["lastname"], state["grade"], state["password"]))

        conn.commit()
        conn.close()

        bot.send_message(message.chat.id, tr.REGISTRATION_SUCCESS.format(user_id=user_id))
        user_states.pop(message.chat.id)
        show_main_menu(message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == "login")
def start_login(call):
    user_states[call.message.chat.id] = {"step": "login_id"}
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=tr.ASK_LOGIN_ID
    )


@bot.message_handler(func=lambda m: m.chat.id in user_states and user_states[m.chat.id]["step"] in ["login_id", "login_password"])
def handle_login(message):
    state = user_states[message.chat.id]
    step = state["step"]

    if step == "login_id":
        state["login_id"] = message.text
        state["step"] = "login_password"
        bot.send_message(message.chat.id, tr.ASK_LOGIN_PASSWORD)

    elif step == "login_password":
        # تبدیل آیدی به عدد
        try:
            login_id = int(state["login_id"])
        except ValueError:
            bot.send_message(message.chat.id, "⚠️ لطفا نام کاربری یا رمز عبور را به درستی وارد کنید. برای اینکار از قسمت منو ربات را دوباره استارت کنید.")
            return

        password = message.text.strip()

        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)

        # چک کردن معلم
        cursor.execute("SELECT * FROM teachers WHERE teacher_id=%s AND password=%s", (login_id, password))
        teacher = cursor.fetchone()

        # چک کردن دانش‌آموز
        cursor.execute("SELECT * FROM students WHERE student_id=%s AND password=%s", (login_id, password))
        student = cursor.fetchone()
        conn.close()

        if teacher:
            bot.send_message(message.chat.id, tr.LOGIN_SUCCESS)
            user_states.pop(message.chat.id, None)
            teacher_panels[message.chat.id] = {
                "teacher_id": teacher["teacher_id"],
                "step": None,
                "questions": []
            }
            show_teacher_menu(message.chat.id)

        elif student:
            bot.send_message(message.chat.id, tr.LOGIN_SUCCESS)
            user_states.pop(message.chat.id, None)
            student_exam_states[message.chat.id] = {
                "student_id": student["student_id"],
                "step": None
            }
            show_student_menu(message.chat.id)

        else:
            bot.send_message(message.chat.id, tr.LOGIN_FAIL)



def show_teacher_menu(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(tr.NEW_EXAM_BTN, callback_data="teacher_new_exam"),
        types.InlineKeyboardButton(tr.QUESTION_BANK_BTN, callback_data="teacher_question_bank")
    )
    bot.send_message(chat_id, tr.TEACHER_MENU, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "teacher_new_exam")
def teacher_new_exam(call):
    teacher_panels[call.message.chat.id].update({"step": "choose_type", "questions": []})
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(tr.QUESTION_TYPE_TESTI, callback_data="q_testi"),
        types.InlineKeyboardButton(tr.QUESTION_TYPE_BLANK, callback_data="q_blank"),
        types.InlineKeyboardButton(tr.QUESTION_TYPE_YESNO, callback_data="q_yesno")
    )
    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text=tr.CHOOSE_QUESTION_TYPE,
                          reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("q_"))
def choose_question_type(call):
    state = teacher_panels.get(call.message.chat.id)
    if not state:
        return
    qtype = call.data.replace("q_", "")
    state["type"] = qtype
    state["step"] = "ask_question"
    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text=tr.ASK_QUESTION_TEXT)

@bot.message_handler(func=lambda m: m.chat.id in teacher_panels and teacher_panels[m.chat.id].get("step") in [
    "ask_question","opt1","opt2","opt3","opt4","correct_option","answer","difficulty","score"
])
def handle_teacher_exam(message):
    state = teacher_panels[message.chat.id]
    step = state["step"]

    if step == "ask_question":
        state["question"] = message.text
        if state["type"] == "testi":
            state["step"] = "opt1"
            bot.send_message(message.chat.id, tr.ASK_OPTION_1)
        else:
            state["step"] = "answer"
            bot.send_message(message.chat.id, tr.ASK_CORRECT_ANSWER)

    elif step == "opt1":
        state["opt1"] = message.text
        state["step"] = "opt2"
        bot.send_message(message.chat.id, tr.ASK_OPTION_2)

    elif step == "opt2":
        state["opt2"] = message.text
        state["step"] = "opt3"
        bot.send_message(message.chat.id, tr.ASK_OPTION_3)

    elif step == "opt3":
        state["opt3"] = message.text
        state["step"] = "opt4"
        bot.send_message(message.chat.id, tr.ASK_OPTION_4)

    elif step == "opt4":
        state["opt4"] = message.text
        state["step"] = "correct_option"
        bot.send_message(message.chat.id, tr.ASK_CORRECT_OPTION)

    elif step == "correct_option":
        if message.text not in ["1", "2", "3", "4"]:
            bot.send_message(message.chat.id, tr.ASK_CORRECT_OPTION)
            return
        state["answer"] = message.text
        state["step"] = "difficulty"
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add(tr.DIFFICULTY_EASY, tr.DIFFICULTY_MEDIUM, tr.DIFFICULTY_HARD)
        bot.send_message(message.chat.id, tr.ASK_DIFFICULTY, reply_markup=markup)

    elif step == "answer":
        state["answer"] = message.text
        state["step"] = "difficulty"
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add(tr.DIFFICULTY_EASY, tr.DIFFICULTY_MEDIUM, tr.DIFFICULTY_HARD)
        bot.send_message(message.chat.id, tr.ASK_DIFFICULTY, reply_markup=markup)

    elif step == "difficulty":
        state["difficulty"] = message.text
        state["step"] = "score"
        bot.send_message(message.chat.id, tr.ASK_SCORE, reply_markup=types.ReplyKeyboardRemove())

    elif step == "score":
        try:
            score = float(message.text)
        except:
            bot.send_message(message.chat.id, tr.ASK_SCORE)
            return
        state["score"] = score

        q = {
            "type": state["type"],
            "text": state["question"],
            "options": [state.get("opt1"), state.get("opt2"), state.get("opt3"), state.get("opt4")],
            "answer": state["answer"],
            "difficulty": state["difficulty"],
            "score": state["score"]
        }
        state["questions"].append(q)
        state["step"] = "next_question"

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(tr.ADD_ANOTHER_BTN, callback_data="add_another"),
            types.InlineKeyboardButton(tr.FINISH_EXAM_BTN, callback_data="finish_exam")
        )
        bot.send_message(message.chat.id, tr.QUESTION_ADDED)
        bot.send_message(message.chat.id, tr.ANOTHER_OR_END, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "add_another")
def add_another_question(call):
    state = teacher_panels.get(call.message.chat.id)
    if not state:
        return
    state["step"] = "choose_type"
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(tr.QUESTION_TYPE_TESTI, callback_data="q_testi"),
        types.InlineKeyboardButton(tr.QUESTION_TYPE_BLANK, callback_data="q_blank"),
        types.InlineKeyboardButton(tr.QUESTION_TYPE_YESNO, callback_data="q_yesno")
    )
    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text=tr.CHOOSE_QUESTION_TYPE,
                          reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "finish_exam")
def finish_exam(call):
    state = teacher_panels.get(call.message.chat.id)
    if not state:
        return
    teacher_panels[call.message.chat.id]["step"] = "duration"

    bot.send_message(call.message.chat.id, tr.ASK_DURATION, reply_markup=types.ReplyKeyboardRemove())


@bot.message_handler(func=lambda m: m.chat.id in teacher_panels and teacher_panels[m.chat.id].get("step") == "duration")
def save_exam(message):
    state = teacher_panels[message.chat.id]
    try:
        duration = int(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, tr.ASK_DURATION)
        return

    teacher_id = state["teacher_id"]
    exam_id, exam_code = db.create_exam(teacher_id, duration)

    for q in state["questions"]:
        db.add_question(
            exam_id,
            q["text"],
            q["type"],
            q["options"],
            q["answer"],
            q["difficulty"],
            q["score"]
        )

    bot.send_message(message.chat.id, tr.EXAM_CREATED.format(exam_code=exam_code))

  
    teacher_panels[message.chat.id] = {
        "teacher_id": teacher_id,
        "step": None,
        "questions": []
    }


def show_student_menu(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(tr.STUDENT_TAKE_EXAM, callback_data="take_exam"),
        types.InlineKeyboardButton(tr.STUDENT_RESULTS, callback_data="student_results")
    )
    bot.send_message(chat_id, tr.STUDENT_MENU, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "take_exam")
def take_exam(call):
    state = student_exam_states.get(call.message.chat.id)
    if not state:
        return
    state["step"] = "exam_code"
    bot.send_message(call.message.chat.id, tr.ASK_EXAM_CODE)

@bot.message_handler(func=lambda m: m.chat.id in student_exam_states and student_exam_states[m.chat.id].get("step") in ["exam_code", "answer_question"])
def handle_student_exam(message):
    state = student_exam_states[message.chat.id]
    step = state["step"]

    if step == "exam_code":
        exam_code = message.text
        questions = db.get_exam_questions(exam_code)
        if not questions:
            bot.send_message(message.chat.id, tr.EXAM_NOT_FOUND)
            return
        state.update({"exam_code": exam_code, "questions": questions, "current": 0, "score": 0, "step": "answer_question"})
        bot.send_message(message.chat.id, tr.EXAM_STARTED)
        bot.send_message(message.chat.id, tr.ANSWER_PROMPT + "\n" + questions[0]["question_text"])

    elif step == "answer_question":
        question = state["questions"][state["current"]]
        student_answer = message.text.strip()
        correct = False

        if question["question_type"] == "testi":
            correct = (student_answer == question["correct_answer"])
        else:
            correct = (student_answer == question["correct_answer"])

        db.save_student_answer(
            exam_id=question["exam_id"],
            student_id=state["student_id"],
            question_id=question["id"],
            student_answer=student_answer,
            is_correct=correct
        )

        if correct:
            state["score"] += float(question["score"])

        state["current"] += 1
        if state["current"] >= len(state["questions"]):
            db.save_result(
                exam_id=question["exam_id"],
                student_id=state["student_id"],
                score=state["score"]
            )
            bot.send_message(message.chat.id, tr.EXAM_FINISHED.format(score=state["score"]))
            student_exam_states.pop(message.chat.id, None)
        else:
            next_q = state["questions"][state["current"]]
            bot.send_message(message.chat.id, tr.ANSWER_PROMPT + "\n" + next_q["question_text"])

@bot.callback_query_handler(func=lambda call: call.data == "student_results")
def show_results(call):
    state = student_exam_states.get(call.message.chat.id)
    if not state:
        return
    student_id = state["student_id"]
    results = db.get_student_results(student_id)
    if not results:
        bot.send_message(call.message.chat.id, "⚠️ نتیجه‌ای برای شما یافت نشد.")
        return

    msg_lines = [tr.RESULTS_HEADER]
    for r in results:
        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT student_id, score FROM results WHERE exam_id=%s ORDER BY score DESC",
            (r["exam_id"],)
        )
        all_results = cursor.fetchall()
        conn.close()

        rank = 1
        for res in all_results:
            if res["student_id"] == student_id:
                break
            rank += 1

        msg_lines.append(
            tr.RESULT_LINE.format(exam_code=r["exam_code"], score=r["score"], rank=rank)
        )

    bot.send_message(call.message.chat.id, "\n".join(msg_lines))

print("🤖 ربات در حال اجراست ...")
bot.infinity_polling()

