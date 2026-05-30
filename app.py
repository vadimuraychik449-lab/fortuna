import random
import os
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

TOKEN = "8867087367:AAE5o5px2UU56vDfPmxr-SmSNDzTZXTUODs"
GROUP_CHAT_ID = -4161930401

# ОБЩИЙ СПИСОК УЧАСТНИКОВ
ALL_USERS = [
    "Расоян", "Шайкин", "Терехов", "Купаев", "Макаров", "Иевский",
    "Борисов", "Марасанов", "Самигулин", "Гранаткин", "Рыжков"
]

user_sessions = {}
flask_app = Flask(__name__)

# ========== КЛАВИАТУРЫ ==========
def get_main_keyboard():
    keyboard = [[InlineKeyboardButton("🎲 Новый розыгрыш", callback_data="new_draw")]]
    return InlineKeyboardMarkup(keyboard)

def get_action_keyboard():
    keyboard = [[InlineKeyboardButton("🎡 Запустить колесо", callback_data="spin")]]
    return InlineKeyboardMarkup(keyboard)

def get_select_keyboard(users, selected):
    """Клавиатура для выбора участников с галочками"""
    keyboard = []
    for user in users:
        status = "✅ " if user in selected else "☑️ "
        keyboard.append([InlineKeyboardButton(f"{status}{user}", callback_data=f"toggle_{user}")])
    keyboard.append([InlineKeyboardButton("➕ Добавить участника", callback_data="add_user")])
    keyboard.append([InlineKeyboardButton("✅ Готово", callback_data="selection_done")])
    keyboard.append([InlineKeyboardButton("◀️ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(keyboard)

def parse_participants(text):
    if ',' in text:
        return [p.strip() for p in text.split(',') if p.strip()]
    return [p.strip() for p in text.split() if p.strip()]

# ========== ОТПРАВКА В ГРУППУ ==========
async def send_to_group(context, title, participants, winner):
    participants_list = "\n".join([f"• {p}" for p in participants])
    message = (
        f"🎉 *РЕЗУЛЬТАТ РОЗЫГРЫША* 🎉\n\n"
        f"📌 *Заявка:* {title}\n\n"
        f"👥 *Участники:*\n{participants_list}\n\n"
        f"🏆 *ПОБЕДИТЕЛЬ:* **{winner}** 🏆\n\n"
        f"Поздравляем! 🎊🎉"
    )
    try:
        await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=message, parse_mode="Markdown")
        return True
    except Exception as e:
        print(f"Ошибка отправки в группу: {e}")
        return False

# ========== ОБРАБОТЧИКИ ==========
async def start(update, context):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    is_group = chat_id < 0
    
    user_sessions.pop(user_id, None)
    
    if is_group:
        await update.message.reply_text(
            "🎡 *Колесо фортуны*\n\n"
            "Розыгрыши создаются в [личные сообщения](t.me/fortuna_ab_bot)\n\n"
            "Результат будет опубликован здесь автоматически.",
            parse_mode="Markdown"
        )
        return
    
    await update.message.reply_text(
        "🎡 *Колесо фортуны*\n\n"
        "Нажмите «Новый розыгрыш», чтобы начать.\n\n"
        "Результат автоматически отправится в группу.",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def handle_callback(update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    # НОВЫЙ РОЗЫГРЫШ — показываем список участников
    if data == "new_draw":
        user_sessions[user_id] = {"selected": []}
        await query.edit_message_text(
            "👥 *Выберите участников розыгрыша:*\n\n"
            "Нажимайте на имена, чтобы отметить галочкой.\n"
            "Можно добавить участника вручную.\n\n"
            "Когда закончите, нажмите «Готово».",
            parse_mode="Markdown",
            reply_markup=get_select_keyboard(ALL_USERS, [])
        )
    
    elif data == "cancel":
        user_sessions.pop(user_id, None)
        await query.edit_message_text(
            "🎡 *Колесо фортуны*\n\n"
            "Нажмите «Новый розыгрыш», чтобы начать.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    
    # ДОБАВИТЬ УЧАСТНИКА ВРУЧНУЮ
    elif data == "add_user":
        session = user_sessions.get(user_id, {})
        session["adding_user"] = True
        user_sessions[user_id] = session
        await query.edit_message_text(
            "✏️ *Добавление участника*\n\n"
            "Напишите имя участника, которого хотите добавить.\n\n"
            "Можно добавить нескольких через запятую:\n"
            "`Иванов, Петров, Сидоров`\n\n"
            "После добавления вернётесь к выбору.",
            parse_mode="Markdown"
        )
    
    # ПЕРЕКЛЮЧЕНИЕ ГАЛОЧКИ (выбрать/убрать участника)
    elif data.startswith("toggle_"):
        user_name = data.replace("toggle_", "")
        session = user_sessions.get(user_id, {})
        selected = session.get("selected", [])
        
        if user_name in selected:
            selected.remove(user_name)
        else:
            selected.append(user_name)
        
        session["selected"] = selected
        user_sessions[user_id] = session
        await query.edit_message_reply_markup(reply_markup=get_select_keyboard(ALL_USERS, selected))
    
    # ВЫБОР ЗАВЕРШЁН — переходим к вводу заявки
    elif data == "selection_done":
        session = user_sessions.get(user_id, {})
        selected = session.get("selected", [])
        
        if len(selected) < 2:
            await query.edit_message_text("❌ Нужно выбрать минимум 2 участника.")
            return
        
        session["participants"] = selected
        session["step"] = "awaiting_title"
        user_sessions[user_id] = session
        
        selected_list = "\n".join([f"• {p}" for p in selected])
        await query.edit_message_text(
            f"✅ *Выбрано участников: {len(selected)}*\n\n"
            f"{selected_list}\n\n"
            f"🎲 *Шаг 1 из 2*\n\n"
            f"Напишите, *кого разыгрываем?*\n"
            f"Например: *ИП Иванов*",
            parse_mode="Markdown"
        )
    
    # ЗАПУСК КОЛЕСА
    elif data == "spin":
        session = user_sessions.get(user_id, {})
        participants = session.get("participants", [])
        title = session.get("title", "Розыгрыш")
        
        if len(participants) < 2:
            await query.edit_message_text("❌ Нужно минимум 2 участника. Начните новый розыгрыш.")
            return
        
        winner = random.choice(participants)
        success = await send_to_group(context, title, participants, winner)
        
        if success:
            await query.edit_message_text(
                f"✅ *Розыгрыш проведён!*\n\n"
                f"📌 Заявка: {title}\n"
                f"🏆 Победитель: **{winner}**\n\n"
                f"Результат отправлен в группу.\n\n"
                f"🎲 Нажмите «Новый розыгрыш», чтобы продолжить.",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
        else:
            await query.edit_message_text(
                f"❌ Ошибка при отправке в группу.\n\n"
                f"📌 Заявка: {title}\n"
                f"👥 Участники: {', '.join(participants)}\n"
                f"🏆 Победитель: {winner}\n\n"
                f"Проверьте ID группы и права бота.",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
        user_sessions.pop(user_id, None)

# ========== ОБРАБОТКА ТЕКСТА (добавление участника + ручной ввод заявки) ==========
async def handle_private_text(update, context):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if chat_id < 0:
        return
    
    session = user_sessions.get(user_id, {})
    
    # Режим добавления участника
    if session.get("adding_user"):
        text = update.message.text.strip()
        new_users = parse_participants(text)
        
        if not new_users:
            await update.message.reply_text("❌ Не удалось распознать имя. Попробуйте ещё раз.")
            return
        
        session["adding_user"] = False
        selected = session.get("selected", [])
        
        for u in new_users:
            if u not in selected and u not in ALL_USERS:
                selected.append(u)
            elif u in ALL_USERS and u not in selected:
                selected.append(u)
        
        session["selected"] = selected
        user_sessions[user_id] = session
        
        await update.message.reply_text(
            f"✅ Добавлено: {', '.join(new_users)}\n\n"
            f"Продолжите выбор участников.",
            parse_mode="Markdown",
            reply_markup=get_select_keyboard(ALL_USERS, selected)
        )
        return
    
    step = session.get("step")
    
    if not step:
        await start(update, context)
        return
    
    text = update.message.text.strip()
    
    # Шаг 1: ввод заявки
    if step == "awaiting_title":
        session["title"] = text
        session["step"] = "ready"
        user_sessions[user_id] = session
        
        participants = session.get("participants", [])
        participants_list = "\n".join([f"{i+1}. {p}" for i, p in enumerate(participants)])
        await update.message.reply_text(
            f"✅ *Готово!*\n\n"
            f"📌 *Заявка:* {text}\n\n"
            f"👥 *Участники ({len(participants)}):*\n{participants_list}\n\n"
            f"Нажмите «Запустить колесо», чтобы провести розыгрыш.\n\n"
            f"Результат автоматически отправится в группу.",
            parse_mode="Markdown",
            reply_markup=get_action_keyboard()
        )

# ========== FLASK ДЛЯ RENDER ==========
@flask_app.route("/")
def index():
    return "🎡 Колесо фортуны работает!"

@flask_app.route("/health")
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)

# ========== ЗАПУСК ==========
def main():
    threading.Thread(target=run_flask, daemon=True).start()
    
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_private_text))
    
    print("🚀 Бот Колесо фортуны запущен...")
    print(f"📢 Общий список участников: {len(ALL_USERS)} человек")
    application.run_polling()

if __name__ == "__main__":
    main()
