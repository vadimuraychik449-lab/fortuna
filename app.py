import os
import random
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

TOKEN = "8867087367:AAE5o5px2UU56vDfPmxr-SmSNDzTZXTUODs"
GROUP_CHAT_ID = -1001728921242

user_sessions = {}
flask_app = Flask(__name__)

# ========== КЛАВИАТУРЫ ==========
def get_main_keyboard():
    keyboard = [[InlineKeyboardButton("🎲 Новый розыгрыш", callback_data="new_draw")]]
    return InlineKeyboardMarkup(keyboard)

def get_action_keyboard():
    keyboard = [[InlineKeyboardButton("🎡 Запустить колесо", callback_data="spin")]]
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
            "Розыгрыши создаются в [личных сообщениях](t.me/fortuna_ab_bot)\n\n"
            "Результат будет опубликован здесь автоматически.",
            parse_mode="Markdown"
        )
        return
    
    await update.message.reply_text(
        "🎡 *Колесо фортуны*\n\n"
        "Вы создаёте розыгрыш здесь, а результат увидят все в группе!\n\n"
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
        user_sessions[user_id] = {"step": "awaiting_title"}
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
                f"🏆 Победитель: {winner}\n\n"
                f"Проверьте ID группы ({GROUP_CHAT_ID}) и права бота.",
                parse_mode="Markdown"
            )
        
        user_sessions.pop(user_id, None)

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
        session["step"] = "awaiting_participants"
        user_sessions[user_id] = session
        await update.message.reply_text(
            f"✅ *Заявка:* {text}\n\n"
            f"🎲 *Шаг 2 из 2*\n\n"
            f"Введите список участников через запятую:\n"
            f"`Аня, Ваня, Маша, Ольга`",
            parse_mode="Markdown"
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
    # Запускаем Flask в отдельном потоке
    threading.Thread(target=run_flask, daemon=True).start()
    
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback, pattern="^(new_draw|spin)$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_private_text))
    
    print("🚀 Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()
