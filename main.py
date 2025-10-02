import telebot
from telebot import types
import translate as tr
from CONFIG import TOKEN, config
import DDL as db
import DQL  # ✅ ایمپورت فایل DQL
import DML  # برای توابعی که در DML هستند

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
    try:
        bot.send_message(message.chat.id, tr.HELOO)
        show_main_menu(message.chat.id)
    except Exception as e:
        print(f"Error in start_command: {e}")

def show_main_menu(chat_id):
    try:
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🔑 ورود", callback_data="login"),
            types.InlineKeyboardButton("📝 ثبت‌نام", callback_data="register")
        )
        bot.send_message(chat_id, tr.CHOOSE_ACTION, reply_markup=markup)
    except Exception as e:
        print(f"Error in show_main_menu: {e}")

def show_student_menu(chat_id):
    try:
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(tr.STUDENT_TAKE_EXAM, callback_data="take_exam")
        )
        bot.send_message(chat_id, tr.STUDENT_MENU, reply_markup=markup)
    except Exception as e:
        print(f"Error in show_student_menu: {e}")

def show_teacher_menu(chat_id):
    try:
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(tr.NEW_EXAM_BTN, callback_data="teacher_new_exam"),
            types.InlineKeyboardButton(tr.QUESTION_BANK_BTN, callback_data="teacher_question_bank")
        )
        bot.send_message(chat_id, tr.TEACHER_MENU, reply_markup=markup)
    except Exception as e:
        print(f"Error in show_teacher_menu: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "register")
def start_register(call):
    try:
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
    except Exception as e:
        print(f"Error in start_register: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("role_"))
def choose_role(call):
    try:
        state = user_states.get(call.message.chat.id)
        if not state:
            return
        role = call.data.replace("role_", "")
        state["role"] = role
        state["step"] = "firstname"
        bot.edit_message_text(chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              text=tr.ASK_FIRSTNAME)
    except Exception as e:
        print(f"Error in choose_role: {e}")

@bot.message_handler(func=lambda m: m.chat.id in user_states and user_states[m.chat.id]["step"] not in ["login_id", "login_password"])
def handle_register(message):
    try:
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
    except Exception as e:
        print(f"Error in handle_register: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "login")
def start_login(call):
    try:
        user_states[call.message.chat.id] = {"step": "login_id"}
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=tr.ASK_LOGIN_ID
        )
    except Exception as e:
        print(f"Error in start_login: {e}")

@bot.message_handler(func=lambda m: m.chat.id in user_states and user_states[m.chat.id]["step"] in ["login_id", "login_password"])
def handle_login(message):
    try:
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
                bot.send_message(message.chat.id, tr.ENTER_ID_PASSWORD_WRONG)
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
                    "step": None,
                    "current_message_id": None,
                    "student_message_ids": []  # ✅ لیست message_idهای دانش‌آموز
                }
                show_student_menu(message.chat.id)

            else:
                bot.send_message(message.chat.id, tr.LOGIN_FAIL)
    except Exception as e:
        print(f"Error in handle_login: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "teacher_new_exam")
def teacher_new_exam(call):
    try:
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
    except Exception as e:
        print(f"Error in teacher_new_exam: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("q_"))
def choose_question_type(call):
    try:
        state = teacher_panels.get(call.message.chat.id)
        if not state:
            return
        qtype = call.data.replace("q_", "")
        state["type"] = qtype
        state["step"] = "ask_question"
        bot.edit_message_text(chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              text=tr.ASK_QUESTION_TEXT)
    except Exception as e:
        print(f"Error in choose_question_type: {e}")

@bot.message_handler(func=lambda m: m.chat.id in teacher_panels and teacher_panels[m.chat.id].get("step") in [
    "ask_question","opt1","opt2","opt3","opt4","correct_option","answer","difficulty","score"
])
def handle_teacher_exam(message):
    try:
        state = teacher_panels[message.chat.id]
        step = state["step"]

        if step == "ask_question":
            state["question"] = message.text
            if state["type"] == "testi":
                state["step"] = "opt1"
                bot.send_message(message.chat.id, tr.ASK_OPTION_1)
            elif state["type"] == "yesno":
                state["step"] = "answer"
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton(tr.YES, callback_data="yesno_answer_yes"),
                    types.InlineKeyboardButton(tr.NO, callback_data="yesno_answer_no")
                )
                bot.send_message(message.chat.id, tr.ASK_CORRECT_ANSWER, reply_markup=markup)
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
            # اگر نوع سوال yesno باشد، فقط بله یا خیر مجاز است
            if state.get("type") == "yesno":
                answer = message.text.strip()
                if answer not in ["بله", "خیر"]:
                    bot.send_message(message.chat.id, tr.CHOOSE_BITWEEN_YES_OR_NO)
                    return
                state["answer"] = answer
                state["step"] = "difficulty"
                markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
                markup.add(tr.DIFFICULTY_EASY, tr.DIFFICULTY_MEDIUM, tr.DIFFICULTY_HARD)
                bot.send_message(message.chat.id, tr.ASK_DIFFICULTY, reply_markup=markup)
            else:
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
    except Exception as e:
        print(f"Error in handle_teacher_exam: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "add_another")
def add_another_question(call):
    try:
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
    except Exception as e:
        print(f"Error in add_another_question: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "finish_exam")
def finish_exam(call):
    try:
        chat_id = call.message.chat.id
        message_id = call.message.message_id
        state = teacher_panels.get(chat_id)
        if not state:
            return
        teacher_panels[chat_id]["step"] = "duration"

        # حذف دکمه‌های قبلی
        bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=None)

        # ارسال پیام جدید بدون دکمه
        bot.send_message(chat_id, tr.ASK_DURATION)
    except Exception as e:
        print(f"Error in finish_exam: {e}")

@bot.message_handler(func=lambda m: m.chat.id in teacher_panels and teacher_panels[m.chat.id].get("step") == "duration")
def save_exam(message):
    try:
        state = teacher_panels[message.chat.id]
        try:
            duration = int(message.text.strip())
        except ValueError:
            bot.send_message(message.chat.id, tr.ASK_DURATION)
            return

        teacher_id = state["teacher_id"]
        
        # استفاده از تابع DML برای ایجاد آزمون
        exam_id, exam_code = DML.create_exam(teacher_id, duration)

        # تابع تبدیل فارسی به انگلیسی برای difficulty
        def fa_to_en_difficulty(fa_diff):
            mapping = {
                "آسان": "easy",
                "متوسط": "medium",
                "دشوار": "hard"
            }
            return mapping.get(fa_diff, "medium")

        # استفاده از تابع DML برای افزودن سوالات
        for q in state["questions"]:
            difficulty_en = fa_to_en_difficulty(q["difficulty"])
            DML.add_question(
                exam_id,
                q["text"],
                q["type"],
                q["options"],
                q["answer"],
                difficulty_en,  # ✅ اکنون مقدار انگلیسی است
                q["score"]
            )

        bot.send_message(message.chat.id, tr.EXAM_CREATED.format(exam_code=exam_code))

        # بازنشانی وضعیت معلم
        teacher_panels[message.chat.id] = {
            "teacher_id": teacher_id,
            "step": None,
            "questions": []
        }

        # نمایش منوی اصلی معلم
        show_teacher_menu(message.chat.id)
    except Exception as e:
        print(f"Error in save_exam: {e}")

@bot.message_handler(func=lambda m: m.chat.id in student_exam_states and student_exam_states[m.chat.id].get("step") in ["exam_code", "answer_question"])
def handle_student_exam(message):
    try:
        state = student_exam_states[message.chat.id]
        step = state["step"]

        if step == "exam_code":
            exam_code = message.text
            # چک کردن اینکه آیا دانش‌آموز قبلاً در این آزمون شرکت کرده است
            if DQL.has_student_taken_exam(state["student_id"], exam_code):
                bot.send_message(message.chat.id, tr.YOU_EXAMED_BEFOR)
                return
            # استفاده از تابع DQL برای دریافت سوالات آزمون
            questions = DQL.get_exam_questions(exam_code)
            if not questions:
                bot.send_message(message.chat.id, tr.EXAM_NOT_FOUND)
                return
            state.update({"exam_code": exam_code, "questions": questions, "current": 0, "score": 0, "step": "answer_question"})
            bot.send_message(message.chat.id, tr.EXAM_STARTED)
            # نمایش سوال اول با گزینه‌ها اگر تستی یا yesno باشد
            first_q = questions[0]
            msg = tr.ANSWER_PROMPT + "\n" + first_q["question_text"]
            markup = None
            if first_q["question_type"] == "testi":
                markup = types.InlineKeyboardMarkup()
                for i, opt in enumerate([first_q["option1"], first_q["option2"], first_q["option3"], first_q["option4"]], 1):
                    if opt:
                        markup.add(
                            types.InlineKeyboardButton(f"{i}. {opt}", callback_data=f"testi_opt_{i}")
                        )
                sent = bot.send_message(message.chat.id, msg, reply_markup=markup)
                state["current_message_id"] = sent.message_id
                return
            elif first_q["question_type"] == "yesno":
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton(tr.YES , callback_data="yesno_answer_yes"),
                    types.InlineKeyboardButton(tr.NO, callback_data="yesno_answer_no")
                )
                sent = bot.send_message(message.chat.id, msg, reply_markup=markup)
                state["current_message_id"] = sent.message_id
                return
            elif first_q["question_type"] == "blank":
                bot.send_message(message.chat.id, msg)
                return

            bot.send_message(message.chat.id, msg)

        elif step == "answer_question":
            question = state["questions"][state["current"]]
            student_answer = message.text.strip()
            correct = False

            if question["question_type"] == "testi":
                correct = (student_answer == question["correct_answer"])
                bot.send_message(message.chat.id, tr.CHOOSE_BITWEEN)
                return
            elif question["question_type"] == "yesno":
                correct = (student_answer == question["correct_answer"])
                bot.send_message(message.chat.id, tr.CHOOSE_BITWEEN)
                return
            else:
                correct = (student_answer == question["correct_answer"])

            # استفاده از تابع DML برای ذخیره پاسخ دانش‌آموز
            DML.save_student_answer(
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
                # استفاده از تابع DML برای ذخیره نتیجه
                DML.save_result(
                    exam_id=question["exam_id"],
                    student_id=state["student_id"],
                    score=state["score"]
                )
                # گرفتن رتبه
                rank = DQL.get_rank_in_exam(state["student_id"], question["exam_id"])
                # نمایش نمره و رتبه
                msg = tr.EXAM_FINISHED.format(score=state["score"]) + f"\n📊 رتبه شما: {rank}"
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton(tr.STUDENT_TAKE_ANOTHER_EXAM, callback_data="take_exam")
                )
                bot.send_message(message.chat.id, msg, reply_markup=markup)
                # ریست کردن وضعیت آزمون (اما نگه داشتن وضعیت کلی دانش‌آموز)
                state["step"] = None
            else:
                next_q = state["questions"][state["current"]]
                msg = tr.ANSWER_PROMPT + "\n" + next_q["question_text"]
                markup = None
                if next_q["question_type"] == "testi":
                    markup = types.InlineKeyboardMarkup()
                    for i, opt in enumerate([next_q["option1"], next_q["option2"], next_q["option3"], next_q["option4"]], 1):
                        if opt:
                            markup.add(
                                types.InlineKeyboardButton(f"{i}. {opt}", callback_data=f"testi_opt_{i}")
                            )
                    current_msg_id = state.get("current_message_id")
                    if current_msg_id:
                        bot.edit_message_text(chat_id=message.chat.id, message_id=current_msg_id, text=msg, reply_markup=markup)
                    else:
                        sent = bot.send_message(message.chat.id, msg, reply_markup=markup)
                        state["current_message_id"] = sent.message_id
                    return
                elif next_q["question_type"] == "yesno":
                    markup = types.InlineKeyboardMarkup()
                    markup.add(
                        types.InlineKeyboardButton(tr.YES, callback_data="yesno_answer_yes"),
                        types.InlineKeyboardButton(tr.NO, callback_data="yesno_answer_no")
                    )
                    current_msg_id = state.get("current_message_id")
                    if current_msg_id:
                        bot.edit_message_text(chat_id=message.chat.id, message_id=current_msg_id, text=msg, reply_markup=markup)
                    else:
                        sent = bot.send_message(message.chat.id, msg, reply_markup=markup)
                        state["current_message_id"] = sent.message_id
                    return
                elif next_q["question_type"] == "blank":
                    # ✅ ذخیره message_id پیام دانش‌آموز
                    if state.get("student_message_ids") is None:
                        state["student_message_ids"] = []
                    state["student_message_ids"].append(message.message_id)
                    
                    # ✅ حذف پیام دانش‌آموز بعد از پاسخ دادن
                    for msg_id in state.get("student_message_ids", []):
                        try:
                            bot.delete_message(chat_id=message.chat.id, message_id=msg_id)
                        except:
                            pass
                    state["student_message_ids"] = []
                    
                    bot.send_message(message.chat.id, msg)
                    return

                current_msg_id = state.get("current_message_id")
                if current_msg_id:
                    bot.edit_message_text(chat_id=message.chat.id, message_id=current_msg_id, text=msg)
                else:
                    sent = bot.send_message(message.chat.id, msg)
                    state["current_message_id"] = sent.message_id
    except Exception as e:
        print(f"Error in handle_student_exam: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("testi_opt_"))
def handle_testi_option(call):
    try:
        chat_id = call.message.chat.id
        state = student_exam_states.get(chat_id)
        if not state or state.get("step") != "answer_question":
            return

        option_number = int(call.data.split("_")[-1])
        question = state["questions"][state["current"]]
        correct = (str(option_number) == question["correct_answer"])

        # ذخیره پاسخ
        DML.save_student_answer(
            exam_id=question["exam_id"],
            student_id=state["student_id"],
            question_id=question["id"],
            student_answer=str(option_number),
            is_correct=correct
        )

        if correct:
            state["score"] += float(question["score"])

        state["current"] += 1
        if state["current"] >= len(state["questions"]):
            # ذخیره نتیجه نهایی
            DML.save_result(
                exam_id=question["exam_id"],
                student_id=state["student_id"],
                score=state["score"]
            )
            # گرفتن رتبه
            rank = DQL.get_rank_in_exam(state["student_id"], question["exam_id"])
            msg = tr.EXAM_FINISHED.format(score=state["score"]) + f"\n📊 رتبه شما: {rank}"
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton(tr.STUDENT_TAKE_ANOTHER_EXAM, callback_data="take_exam")
            )
            bot.send_message(chat_id, msg, reply_markup=markup)
            state["step"] = None
        else:
            next_q = state["questions"][state["current"]]
            msg = tr.ANSWER_PROMPT + "\n" + next_q["question_text"]
            markup = None
            if next_q["question_type"] == "testi":
                markup = types.InlineKeyboardMarkup()
                for i, opt in enumerate([next_q["option1"], next_q["option2"], next_q["option3"], next_q["option4"]], 1):
                    if opt:
                        markup.add(
                            types.InlineKeyboardButton(f"{i}. {opt}", callback_data=f"testi_opt_{i}")
                        )
                current_msg_id = state.get("current_message_id")
                if current_msg_id:
                    bot.edit_message_text(chat_id=chat_id, message_id=current_msg_id, text=msg, reply_markup=markup)
                else:
                    sent = bot.send_message(chat_id, msg, reply_markup=markup)
                    state["current_message_id"] = sent.message_id
                return
            elif next_q["question_type"] == "yesno":
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton(tr.YES, callback_data="yesno_answer_yes"),
                    types.InlineKeyboardButton(tr.NO , callback_data="yesno_answer_no")
                )
                current_msg_id = state.get("current_message_id")
                if current_msg_id:
                    bot.edit_message_text(chat_id=chat_id, message_id=current_msg_id, text=msg, reply_markup=markup)
                else:
                    sent = bot.send_message(chat_id, msg, reply_markup=markup)
                    state["current_message_id"] = sent.message_id
                return
            elif next_q["question_type"] == "blank":
                # ✅ ذخیره message_id پیام دانش‌آموز
                if state.get("student_message_ids") is None:
                    state["student_message_ids"] = []
                state["student_message_ids"].append(call.message.message_id)
                
                # ✅ حذف پیام دانش‌آموز بعد از پاسخ دادن
                for msg_id in state.get("student_message_ids", []):
                    try:
                        bot.delete_message(chat_id=chat_id, message_id=msg_id)
                    except:
                        pass
                state["student_message_ids"] = []
                
                bot.send_message(chat_id, msg)
                return

            current_msg_id = state.get("current_message_id")
            if current_msg_id:
                bot.edit_message_text(chat_id=chat_id, message_id=current_msg_id, text=msg)
            else:
                sent = bot.send_message(chat_id, msg)
                state["current_message_id"] = sent.message_id

        # حذف دکمه‌ها پس از انتخاب
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
    except Exception as e:
        print(f"Error in handle_testi_option: {e}")

@bot.callback_query_handler(func=lambda call: call.data in ["yesno_answer_yes", "yesno_answer_no"])
def handle_yesno_selection(call):
    try:
        chat_id = call.message.chat.id

        # چک کردن آیا کاربر معلم است
        if chat_id in teacher_panels:
            state = teacher_panels[chat_id]
            if state.get("step") == "answer" and state.get("type") == "yesno":
                answer = tr.YES if call.data == "yesno_answer_yes" else tr.NO
                state["answer"] = answer
                state["step"] = "difficulty"
                markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
                markup.add(tr.DIFFICULTY_EASY, tr.DIFFICULTY_MEDIUM, tr.DIFFICULTY_HARD)
                bot.send_message(chat_id, tr.ASK_DIFFICULTY, reply_markup=markup)
                bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
                return

        # چک کردن آیا کاربر دانش‌آموز است
        if chat_id in student_exam_states:
            state = student_exam_states[chat_id]
            if state.get("step") == "answer_question":
                answer = "بله" if call.data == "yesno_answer_yes" else "خیر"
                question = state["questions"][state["current"]]
                correct = (answer == question["correct_answer"])

                # ذخیره پاسخ
                DML.save_student_answer(
                    exam_id=question["exam_id"],
                    student_id=state["student_id"],
                    question_id=question["id"],
                    student_answer=answer,
                    is_correct=correct
                )

                if correct:
                    state["score"] += float(question["score"])

                state["current"] += 1
                if state["current"] >= len(state["questions"]):
                    # ذخیره نتیجه نهایی
                    DML.save_result(
                        exam_id=question["exam_id"],
                        student_id=state["student_id"],
                        score=state["score"]
                    )
                    # گرفتن رتبه
                    rank = DQL.get_rank_in_exam(state["student_id"], question["exam_id"])
                    msg = tr.EXAM_FINISHED.format(score=state["score"]) + f"\n📊 رتبه شما: {rank}"
                    markup = types.InlineKeyboardMarkup()
                    markup.add(
                        types.InlineKeyboardButton(tr.STUDENT_TAKE_ANOTHER_EXAM, callback_data="take_exam")
                    )
                    bot.send_message(chat_id, msg, reply_markup=markup)
                    state["step"] = None
                else:
                    next_q = state["questions"][state["current"]]
                    msg = tr.ANSWER_PROMPT + "\n" + next_q["question_text"]
                    markup = None
                    if next_q["question_type"] == "testi":
                        markup = types.InlineKeyboardMarkup()
                        for i, opt in enumerate([next_q["option1"], next_q["option2"], next_q["option3"], next_q["option4"]], 1):
                            if opt:
                                markup.add(
                                    types.InlineKeyboardButton(f"{i}. {opt}", callback_data=f"testi_opt_{i}")
                                )
                        current_msg_id = state.get("current_message_id")
                        if current_msg_id:
                            bot.edit_message_text(chat_id=chat_id, message_id=current_msg_id, text=msg, reply_markup=markup)
                        else:
                            sent = bot.send_message(chat_id, msg, reply_markup=markup)
                            state["current_message_id"] = sent.message_id
                        return
                    elif next_q["question_type"] == "yesno":
                        markup = types.InlineKeyboardMarkup()
                        markup.add(
                            types.InlineKeyboardButton(tr.YES , callback_data="yesno_answer_yes"),
                            types.InlineKeyboardButton(tr.NO, callback_data="yesno_answer_no")
                        )
                        current_msg_id = state.get("current_message_id")
                        if current_msg_id:
                            bot.edit_message_text(chat_id=chat_id, message_id=current_msg_id, text=msg, reply_markup=markup)
                        else:
                            sent = bot.send_message(chat_id, msg, reply_markup=markup)
                            state["current_message_id"] = sent.message_id
                        return
                    elif next_q["question_type"] == "blank":
                        # ✅ ذخیره message_id پیام دانش‌آموز
                        if state.get("student_message_ids") is None:
                            state["student_message_ids"] = []
                        state["student_message_ids"].append(call.message.message_id)
                        
                        # ✅ حذف پیام دانش‌آموز بعد از پاسخ دادن
                        for msg_id in state.get("student_message_ids", []):
                            try:
                                bot.delete_message(chat_id=chat_id, message_id=msg_id)
                            except:
                                pass
                        state["student_message_ids"] = []
                        
                        bot.send_message(chat_id, msg)
                        return

                    current_msg_id = state.get("current_message_id")
                    if current_msg_id:
                        bot.edit_message_text(chat_id=chat_id, message_id=current_msg_id, text=msg)
                    else:
                        sent = bot.send_message(chat_id, msg)
                        state["current_message_id"] = sent.message_id
                bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
                return

        # اگر کاربر معتبر نبود
        bot.send_message(chat_id, tr.DONT_FIGUR)
    except Exception as e:
        print(f"Error in handle_yesno_selection: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "teacher_question_bank")
def show_teacher_question_bank(call):
    try:
        chat_id = call.message.chat.id
        state = teacher_panels.get(chat_id)
        if not state:
            bot.send_message(chat_id, tr.ENTER_FIRST)
            return

        teacher_id = state.get("teacher_id")
        if not teacher_id:
            bot.send_message(chat_id, tr.CANT_FIND_TEACHER)
            return

        # گرفتن اطلاعات معلم از دیتابیس
        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT subject, grade FROM teachers WHERE teacher_id = %s", (teacher_id,))
        teacher_info = cursor.fetchone()
        conn.close()

        if not teacher_info:
            bot.send_message(chat_id, tr.CANT_FIND_INFO)
            return

        subject = teacher_info["subject"]
        grade = teacher_info["grade"]

        # گرفتن سوالات مربوط به درس و مقطع
        questions = DQL.get_questions_by_subject_grade(subject, grade)

        if not questions:
            bot.send_message(chat_id, tr.CANT_FIND_QUESTION)
            return

        for q in questions:
            msg = f"سؤال: {q['question_text']}\n"
            if q["question_type"] == "testi":
                msg += f"گزینه‌ها:\n"
                for i, opt in enumerate([q["option1"], q["option2"], q["option3"], q["option4"]], 1):
                    if opt:
                        msg += f"{i}. {opt}\n"
            else:
                msg += f"نوع: {q['question_type']}\n"
            msg += f"سختی: {q['difficulty']}\n"
            bot.send_message(chat_id, msg)
    except Exception as e:
        print(f"Error in show_teacher_question_bank: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "take_exam")
def take_exam(call):
    try:
        chat_id = call.message.chat.id
        # پیدا کردن شناسه دانش‌آموز از وضعیت فعلی
        student_state = student_exam_states.get(chat_id)
        if not student_state:
            bot.send_message(chat_id, tr.ENTER_FIRST)
            return

        student_id = student_state.get("student_id")
        if not student_id:
            bot.send_message(chat_id, tr.CANT_FIND_STUDENT)
            return

        # ریست وضعیت آزمون
        student_exam_states[chat_id] = {
            "student_id": student_id,
            "step": "exam_code",
            "current_message_id": None,
            "student_message_ids": []  # ✅ لیست message_idهای دانش‌آموز
        }
        bot.send_message(chat_id, tr.ASK_EXAM_CODE)
    except Exception as e:
        print(f"Error in take_exam: {e}")

print("🤖 ربات در حال اجراست ...")
bot.infinity_polling()