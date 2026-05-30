import random
import os
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

TOKEN = "8867087367:AAE5o5px2UU56vDfPmxr-SmSNDzTZXTUODs"
GROUP_CHAT_ID = -4161930401

user_sessions = {}
default_users = []  # Список участников по умолчанию

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
    keyboard.append([InlineKeyboardButton("✅ Готово", callback_data="select_done")])
    keyboard.append([InlineKeyboardButton("◀️ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(keyboard)

def get_users_list_keyboard(users):
    keyboard = []
    for user in users:
        keyboard.append([InlineKeyboardButton(f"📌 {user}", callback_data=f"use_user_{user}")])
    keyboard.append([InlineKeyboardButton("➕ Ввести вручную", callback_data="manual_input")])
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="new_draw")])
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

# ========== КОМАНДЫ ДЛЯ УПРАВЛЕНИЯ УЧАСТНИКАМИ ==========
async def set_users(update, context):
    """Устанавливает список участников по умолчанию"""
    if update.effective_chat.id > 0:
        if not context.args:
            await update.message.reply_text(
                "📝 *Установка списка участников*\n\n"
                "Напишите список через запятую:\n"
                "`/setusers Аня, Ваня, Маша, Ольга`\n\n"
                "Или через пробел:\n"
                "`/setusers Аня Ваня Маша Ольга`",
                parse_mode="Markdown"
            )
            return
        
        global default_users
        text = " ".join(context.args)
        default_users = parse_participants(text)
        await update.message.reply_text(
            f"✅ *Список участников сохранён!*\n\n"
            f"👥 Участников: {len(default_users)}\n"
            f"📋 {', '.join(default_users)}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Эта команда работает только в личных сообщениях.")

async def show_users(update, context):
    """Показывает текущий список участников"""
    if default_users:
        await update.message.reply_text(
            f"👥 *Текущий список участников:*\n\n"
            f"{chr(10).join([f'{i+1}. {u}' for i, u in enumerate(default_users)])}\n\n"
            f"Изменить: `/setusers Аня, Ваня`",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "📭 *Список участников пуст*\n\n"
            "Установите: `/setusers Аня, Ваня, Маша`",
            parse_mode="Markdown"
        )

# ========== ОБРАБОТЧИКИ ==========
async def start(update, context):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    is_group = chat_id < 0
    
    user_sessions.pop(user_id, None)
    
    if is_group:
        await update.message.reply_text(
            "🎡 *Колесо фортуны*\n\n"
            "Розыгрыши создаются в [личных сообщениях](t.me/fortuna_ab_bot)\n\n"
            "Результат будет опубликован здесь автоматически.",
            parse_mode="Markdown"
        )
        return
    
    await update.message.reply_text(
        "🎡 *Колесо фортуны*\n\n"
        "Вы создаёте розыгрыш здесь, а результат увидят все в группе!\n\n"
        "📌 Команды:\n"
        "/setusers — установить список участников\n"
        "/users — показать текущий список\n\n"
        "Нажмите «Новый розыгрыш», чтобы начать.",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def handle_callback(update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "new_draw":
        if default_users:
            # Показываем кнопку с выбором из списка
            keyboard = [
                [InlineKeyboardButton("📋 Выбрать из списка", callback_data="select_from_list")],
                [InlineKeyboardButton("✏️ Ввести вручную", callback_data="manual_input")]
            ]
            await query.edit_message_text(
                "🎲 *Новый розыгрыш*\n\n"
                "Выберите способ ввода участников:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            user_sessions[user_id] = {"step": "awaiting_title"}
            await query.edit_message_text(
                "🎲 *Шаг 1 из 2*\n\n"
                "Напишите, *кого разыгрываем?*\n"
                "Например: *ИП Иванов*",
                parse_mode="Markdown"
            )
    
    elif data == "select_from_list":
        user_sessions[user_id] = {"step": "awaiting_participants_select", "selected": []}
        await query.edit_message_text(
            "👥 *Выберите участников:*\n\n"
            "Нажимайте на имена, чтобы отметить. Когда закончите, нажмите «Готово».",
            parse_mode="Markdown",
            reply_markup=get_select_keyboard(default_users, [])
        )
    
    elif data == "manual_input":
        user_sessions[user_id] = {"step": "awaiting_title"}
        await query.edit_message_text(
            "🎲 *Шаг 1 из 2*\n\n"
            "Напишите, *кого разыгрываем?*\n"
            "Например: *ИП Иванов*",
            parse_mode="Markdown"
        )
    
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
        await query.edit_message_reply_markup(reply_markup=get_select_keyboard(default_users, selected))
    
    elif data == "select_done":
        session = user_sessions.get(user_id, {})
        selected = session.get("selected", [])
        if len(selected) < 2:
            await query.edit_message_text("❌ Нужно выбрать минимум 2 участника.")
            return
        # Сохраняем выбранных участников и переходим к вводу заявки
        session["participants"] = selected
        session["step"] = "awaiting_title"
        user_sessions[user_id] = session
        await query.edit_message_text(
            "🎲 *Шаг 1 из 2*\n\n"
            "Напишите, *кого разыгрываем?*\n"
            "Например: *ИП Иванов*",
            parse_mode="Markdown"
        )
    
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
                f"Результат отправлен в группу.",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                f"❌ Ошибка при отправке в группу.\n\n"
                f"📌 Заявка: {title}\n"
                f"👥 Участники: {', '.join(participants)}\n"
                f"🏆 Победитель: {winner}",
                parse_mode="Markdown"
            )
        user_sessions.pop(user_id, None)
    
    elif data == "cancel":
        user_sessions.pop(user_id, None)
        await query.edit_message_text("❌ Отменено.", reply_markup=get_main_keyboard())

async def handle_private_text(update, context):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if chat_id < 0:
        return
    
    session = user_sessions.get(user_id, {})
    step = session.get("step")
    
    if not step:
        await start(update, context)
        return
    
    text = update.message.text.strip()
    
    if step == "awaiting_title":
        session["title"] = text
        if "participants" not in session or not session["participants"]:
            session["step"] = "awaiting_participants"
        else:
            session["step"] = "ready"
        user_sessions[user_id] = session
        
        if session.get("step") == "awaiting_participants":
            await update.message.reply_text(
                f"✅ *Заявка:* {text}\n\n"
                f"🎲 *Шаг 2 из 2*\n\n"
                f"Введите список участников через запятую:\n"
                f"`Аня, Ваня, Маша, Ольга`\n\n"
                f"Или используйте /setusers для сохранения списка.",
                parse_mode="Markdown"
            )
        else:
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
    
    elif step == "awaiting_participants":
        participants = parse_participants(text)
        if len(participants) < 2:
            await update.message.reply_text("❌ Нужно минимум 2 участника. Повторите ввод через запятую:")
            return
        
        session["participants"] = participants
        session["step"] = "ready"
        user_sessions[user_id] = session
        
        title = session.get("title", "Розыгрыш")
        participants_list = "\n".join([f"{i+1}. {p}" for i, p in enumerate(participants)])
        await update.message.reply_text(
            f"✅ *Готово!*\n\n"
            f"📌 *Заявка:* {title}\n\n"
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
    application.add_handler(CommandHandler("setusers", set_users))
    application.add_handler(CommandHandler("users", show_users))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_private_text))
    
    print("🚀 Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()
