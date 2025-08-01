import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "7690610155:AAFiZwYYZpTXg-UbNTldLQZuKbG4q7DlyOc"
bot = telebot.TeleBot(TOKEN)

user_data = {}
registered_users = {}

exams_database = {
    "متوسطه اول": {
        "ریاضی": ["آزمون ریاضی نوبت اول", "آزمون ریاضی نوبت دوم"],
        "علوم": ["آزمون علوم فصل 1", "آزمون علوم فصل 2"]
    },
    "متوسطه دوم": {
        "ریاضی": ["آزمون ریاضی پایه دهم", "آزمون ریاضی پایه یازدهم"],
        "فیزیک": ["آزمون فیزیک 1", "آزمون فیزیک 2"]
    }
}

(
    STATE_START,
    STATE_CHOOSE_ACTION,
    STATE_CHOOSE_ROLE,
    STATE_GET_NAME,
    STATE_GET_LESSONS,
    STATE_ADD_MORE_LESSONS,
    STATE_LOGIN,
    STATE_STUDENT_DASHBOARD,
    STATE_CHOOSE_EXAM_TYPE,
    STATE_CHOOSE_EDUCATION_LEVEL,
    STATE_ENTER_SUBJECT,
    STATE_CHOOSE_EXAM
) = range(12)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user = message.from_user

    welcome_message = f"""
سلام {user.first_name} عزیز! 👋
به ربات آموزشی خوش آمدید.

لطفا یکی از گزینه‌های زیر را انتخاب کنید:
    """

    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("ثبت‌نام 📝", callback_data='action_register'),
        InlineKeyboardButton("ورود 🔑", callback_data='action_login')
    )

    bot.send_message(chat_id, welcome_message, reply_markup=keyboard)

    # ذخیره وضعیت کاربر
    user_data[chat_id] = {'state': STATE_CHOOSE_ACTION}


@bot.callback_query_handler(func=lambda call: call.data.startswith('action_'))
def process_action_selection(call):
    chat_id = call.message.chat.id
    action = call.data.split('_')[1]

    if action == 'register':

        ask_for_role(call)
    elif action == 'login':

        user_data[chat_id]['state'] = STATE_LOGIN
        ask_for_login_role(call)


def ask_for_role(call):
    chat_id = call.message.chat.id

    message = "لطفا نقش خود را انتخاب کنید:"

    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("👨‍🏫 معلم", callback_data='role_teacher'),
        InlineKeyboardButton("👨‍🎓 شاگرد", callback_data='role_student')
    )

    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text=message,
        reply_markup=keyboard
    )

    user_data[chat_id]['state'] = STATE_CHOOSE_ROLE
    bot.answer_callback_query(call.id)


def ask_for_login_role(call):
    chat_id = call.message.chat.id

    message = "لطفا نقش خود را برای ورود انتخاب کنید:"

    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("👨‍🏫 معلم", callback_data='login_teacher'),
        InlineKeyboardButton("👨‍🎓 شاگرد", callback_data='login_student')
    )

    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text=message,
        reply_markup=keyboard
    )

    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('role_'))
def process_role_selection(call):
    chat_id = call.message.chat.id
    role = call.data.split('_')[1]


    user_data[chat_id]['role'] = role

    if role == 'teacher':
        role_text = "معلم"
    else:
        role_text = "شاگرد"


    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text=f"شما نقش {role_text} را برای ثبت‌نام انتخاب کردید.\n\nلطفا نام و نام خانوادگی خود را وارد کنید:"
    )


    user_data[chat_id]['state'] = STATE_GET_NAME
    bot.answer_callback_query(call.id)



@bot.callback_query_handler(func=lambda call: call.data.startswith('login_'))
def process_login_role_selection(call):
    chat_id = call.message.chat.id
    role = call.data.split('_')[1]


    if chat_id in registered_users:
        user_info = registered_users[chat_id]
        if user_info['role'] == role:
            # نقش مطابقت دارد
            if role == 'teacher':
                lessons = "\n".join([f"• {lesson}" for lesson in user_info.get('lessons', [])])
                message = f"""
✅ ورود با موفقیت انجام شد
نقش: معلم 👨‍🏫
نام: {user_info['name']}
دروس تدریس:
{lessons}
                """

                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=call.message.message_id,
                    text=message
                )


                show_restart_button(chat_id, call.message.message_id)
            else:

                welcome_msg = f"""
سلام {user_info['name']} عزیز! 👋
به پنل دانش‌آموزی خوش آمدید.

چه کاری می‌خواهید انجام دهید؟
                """

                keyboard = InlineKeyboardMarkup()
                keyboard.add(InlineKeyboardButton("شرکت در آزمون �", callback_data='take_exam'))

                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=call.message.message_id,
                    text=welcome_msg,
                    reply_markup=keyboard
                )

                user_data[chat_id]['state'] = STATE_STUDENT_DASHBOARD
        else:

            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=f"⚠️ شما به عنوان {role} ثبت‌نام نکرده‌اید."
            )
            show_restart_button(chat_id, call.message.message_id)
    else:

        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="⚠️ شما هنوز ثبت‌نام نکرده‌اید. لطفا ابتدا ثبت‌نام کنید."
        )
        show_restart_button(chat_id, call.message.message_id)

    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message:
user_data.get(message.chat.id, {}).get('state') == STATE_GET_NAME)
def process_name(message):
    chat_id = message.chat.id
    name = message.text


    user_data[chat_id]['name'] = name

    if user_data[chat_id]['role'] == 'teacher':
        bot.send_message(chat_id, "لطفا نام اولین درس خود را وارد کنید:")
        user_data[chat_id]['state'] = STATE_GET_LESSONS
        user_data[chat_id]['lessons'] = []
    else:
        complete_registration(chat_id)



@bot.message_handler(func=lambda message:
user_data.get(message.chat.id, {}).get('state') in [STATE_GET_LESSONS, STATE_ADD_MORE_LESSONS])
def process_lessons(message):
    chat_id = message.chat.id
    lesson = message.text
    state = user_data[chat_id]['state']


    user_data[chat_id]['lessons'].append(lesson)

    if state == STATE_GET_LESSONS:

        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton("بله، اضافه کردن درس دیگر", callback_data='add_more_lessons'),
            InlineKeyboardButton("خیر، ثبت‌نام کامل شد", callback_data='finish_registration')
        )

        bot.send_message(
            chat_id,
            f"درس '{lesson}' با موفقیت اضافه شد.\nآیا می‌خواهید درس دیگری اضافه کنید؟",
            reply_markup=keyboard
        )

        user_data[chat_id]['state'] = STATE_ADD_MORE_LESSONS
    else:

        bot.send_message(
            chat_id,
            f"درس '{lesson}' با موفقیت اضافه شد.\nلطفا نام درس بعدی را وارد کنید یا از دکمه‌های زیر استفاده کنید:",
            reply_markup=get_lessons_keyboard()
        )


def get_lessons_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("اتمام ثبت دروس", callback_data='finish_registration'),
        InlineKeyboardButton("انصراف و شروع مجدد", callback_data='restart')
    )
    return keyboard



@bot.callback_query_handler(func=lambda call: call.data in ['add_more_lessons', 'finish_registration'])
def process_lessons_decision(call):
    chat_id = call.message.chat.id

    if call.data == 'add_more_lessons':
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="لطفا نام درس بعدی را وارد کنید:"
        )
        user_data[chat_id]['state'] = STATE_GET_LESSONS
    else:

        complete_registration(chat_id)

    bot.answer_callback_query(call.id)


def complete_registration(chat_id):
    data = user_data[chat_id]
    name = data['name']
    role = data['role']


    registered_users[chat_id] = {
        'name': name,
        'role': role
    }

    if role == 'teacher':
        registered_users[chat_id]['lessons'] = data.get('lessons', [])
        lessons = "\n".join([f"• {lesson}" for lesson in data.get('lessons', [])])
        message = f"""
✅ ثبت‌نام با موفقیت انجام شد
نقش: معلم 👨‍🏫
نام: {name}
دروس تدریس:
{lessons}
        """
    else:
        message = f"""
✅ ثبت‌نام با موفقیت انجام شد
نقش: شاگرد 👨‍🎓
نام: {name}
        """

    # ارسال پیام تأیید
    msg = bot.send_message(chat_id, message)

    # نمایش دکمه شروع مجدد
    show_restart_button(chat_id, msg.message_id)

    # پاک کردن وضعیت کاربر
    user_data[chat_id]['state'] = STATE_START



def show_restart_button(chat_id, message_id):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("شروع مجدد 🔄", callback_data='restart'))

    bot.edit_message_reply_markup(
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=keyboard
    )



@bot.callback_query_handler(func=lambda call: call.data == 'restart')
def process_restart(call):
    chat_id = call.message.chat.id
    if chat_id in user_data:
        del user_data[chat_id]
    send_welcome(call.message)
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == 'take_exam')
def process_take_exam(call):
    chat_id = call.message.chat.id

    message = "لطفا نوع آزمون مورد نظر خود را انتخاب کنید:"

    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("1. آزمون‌های آزمایشی", callback_data='exam_type_mock'),
        InlineKeyboardButton("2. آزمون‌های دبیر", callback_data='exam_type_teacher')
    )

    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text=message,
        reply_markup=keyboard
    )

    user_data[chat_id]['state'] = STATE_CHOOSE_EXAM_TYPE
    bot.answer_callback_query(call.id)


# پردازش انتخاب نوع آزمون
@bot.callback_query_handler(func=lambda call: call.data.startswith('exam_type_'))
def process_exam_type_selection(call):
    chat_id = call.message.chat.id
    exam_type = call.data.split('_')[2]

    if exam_type == 'mock':
        # آزمون‌های آزمایشی
        message = "لطفا مقطع مورد نظر خود را انتخاب کنید:"

        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton("متوسطه اول", callback_data='level_junior'),
            InlineKeyboardButton("متوسطه دوم", callback_data='level_senior')
        )
        keyboard.add(InlineKeyboardButton("بازگشت ↩️", callback_data='back_to_exam_type'))

        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=message,
            reply_markup=keyboard
        )

        user_data[chat_id]['state'] = STATE_CHOOSE_EDUCATION_LEVEL
        user_data[chat_id]['exam_type'] = exam_type
    else:

        message = "شما آزمون‌های دبیر را انتخاب کردید.\n"

        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=message
        )

        show_restart_button(chat_id, call.message.message_id)

    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('level_'))
def process_education_level(call):
    chat_id = call.message.chat.id
    level = call.data.split('_')[1]

    if level == 'junior':
        level_text = "متوسطه اول"
    else:
        level_text = "متوسطه دوم"

    user_data[chat_id]['education_level'] = level_text

    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text=f"مقطع {level_text} انتخاب شد.\n\nلطفا نام درس مورد نظر خود را تایپ کنید:"
    )

    user_data[chat_id]['state'] = STATE_ENTER_SUBJECT
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == 'back_to_exam_type')
def process_back_to_exam_type(call):
    chat_id = call.message.chat.id
    process_take_exam(call)
    bot.answer_callback_query(call.id)


@bot.message_handler(func=lambda message:
user_data.get(message.chat.id, {}).get('state') == STATE_ENTER_SUBJECT)
def process_subject(message):
    chat_id = message.chat.id
    subject = message.text
    level = user_data[chat_id]['education_level']

    if level in exams_database and subject in exams_database[level]:
        exams = exams_database[level][subject]
        message_text = f"آزمون‌های موجود برای درس {subject}:\n\n"

        keyboard = InlineKeyboardMarkup()
        for i, exam in enumerate(exams, 1):
            message_text += f"{i}. {exam}\n"
            keyboard.add(InlineKeyboardButton(f"{i}. {exam}", callback_data=f'exam_{i}'))

        message_text += "\nلطفا آزمون مورد نظر خود را انتخاب کنید:"

        bot.send_message(chat_id, message_text, reply_markup=keyboard)

        user_data[chat_id]['state'] = STATE_CHOOSE_EXAM
        user_data[chat_id]['available_exams'] = exams
        user_data[chat_id]['subject'] = subject
    else:
        bot.send_message(chat_id,
                         f"⚠️ هیچ آزمونی برای درس {subject} در مقطع {level} یافت نشد. لطفا درس دیگری وارد کنید.")


@bot.callback_query_handler(func=lambda call: call.data.startswith('exam_'))
def process_exam_selection(call):
    chat_id = call.message.chat.id
    exam_index = int(call.data.split('_')[1]) - 1
    exams = user_data[chat_id]['available_exams']
    subject = user_data[chat_id]['subject']

    if 0 <= exam_index < len(exams):
        selected_exam = exams[exam_index]

        # در اینجا می‌توانید کد آزمون را تولید یا از پایگاه داده دریافت کنید
        exam_code = f"EXAM-{subject[:3].upper()}-{exam_index + 1:03d}"

        message = f"""
✅ آزمون شما انتخاب شد:
درس: {subject}
آزمون: {selected_exam}
کد آزمون: {exam_code}

برای شروع آزمون روی /start_exam کلیک کنید.
        """

        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=message
        )

        user_data[chat_id]['selected_exam'] = selected_exam
        user_data[chat_id]['exam_code'] = exam_code

        show_restart_button(chat_id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "⚠️ آزمون انتخاب شده معتبر نیست!")

    bot.answer_callback_query(call.id)


if __name__ == '__main__':
    print("ربات در حال اجراست...")
    bot.infinity_polling()