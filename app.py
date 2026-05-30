import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

TOKEN = "8867087367:AAE5o5px2UU56vDfPmxr-SmSNDzTZXTUODs"

user_sessions = {}

# ========== КЛАВИАТУРЫ ==========
def get_main_keyboard():
    keyboard = [[InlineKeyboardButton("🎲 Новый розыгрыш", callback_data="new_draw")]]
    return InlineKeyboardMarkup(keyboard)

def get_action_keyboard():
    keyboard = [[InlineKeyboardButton("🎡 Запустить колесо", callback_data="spin")]]
    return InlineKeyboardMarkup(keyboard)

def parse_participants(text):
    """Превращает текст в список участников"""
    if ',' in text:
        participants = [p.strip() for p in text.split(',') if p.strip()]
    else:
        participants = [p.strip() for p in text.split() if p.strip()]
    return participants

# ========== ОБРАБОТЧИКИ ==========
async def start(update, context):
    user_id = update.effective_user.id
    user_sessions.pop(user_id, None)
    await update.message.reply_text(
        "🎡 *Колесо фортуны*\n\nНажмите «Новый розыгрыш», чтобы начать.",
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
        
        # Формируем список участников
        participants_list = "\n".join([f"• {p}" for p in participants])
        
        text = f"🎉 *РЕЗУЛЬТАТ РОЗЫГРЫША* 🎉\n\n"
        text += f"📌 *Заявка:* {title}\n\n"
        text += f"👥 *Участники:*\n{participants_list}\n\n"
        text += f"🏆 *ПОБЕДИТЕЛЬ:* **{winner}** 🏆\n\n"
        text += f"Поздравляем! 🎊🎉"
        
        await query.edit_message_text(text, parse_mode="Markdown")
        user_sessions.pop(user_id, None)

async def handle_text(update, context):
    user_id = update.effective_user.id
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
            f"`Аня, Ваня, Маша, Ольга`\n\n"
            f"Имена могут быть любыми — имена, никнеймы, ID.",
            parse_mode="Markdown"
        )
    
    elif step == "awaiting_participants":
        participants = parse_participants(text)
        
        if len(participants) < 2:
            await update.message.reply_text(
                f"❌ Найдено {len(participants)} участников. Нужно минимум 2.\n"
                f"Повторите ввод через запятую:"
            )
            return
        
        session["participants"] = participants
        session["step"] = "ready"
        user_sessions[user_id] = session
        
        title = session.get("title", "Розыгрыш")
        participants_list = "\n".join([f"{i+1}. {p}" for i, p in enumerate(participants)])
        
        result_text = f"✅ *Готово!*\n\n"
        result_text += f"📌 *Заявка:* {title}\n\n"
        result_text += f"👥 *Участники ({len(participants)}):*\n{participants_list}\n\n"
        result_text += f"Нажмите «Запустить колесо», чтобы провести розыгрыш."
        
        await update.message.reply_text(
            result_text,
            parse_mode="Markdown",
            reply_markup=get_action_keyboard()
        )

# ========== ЗАПУСК ==========
def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback, pattern="^(new_draw|spin)$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("🚀 Бот Колесо фортуны запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()
