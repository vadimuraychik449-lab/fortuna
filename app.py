import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

TOKEN = "8867087367:AAE5o5px2UU56vDfPmxr-SmSNDzTZXTUODs"
GROUP_CHAT_ID = 4161930401  # ⚠️ ЗАМЕНИТЕ НА РЕАЛЬНЫЙ ID ГРУППЫ

user_sessions = {}

# ========== КЛАВИАТУРЫ ==========
def get_main_keyboard():
    keyboard = [[InlineKeyboardButton("🎲 Новый розыгрыш", callback_data="new_draw")]]
    return InlineKeyboardMarkup(keyboard)

def get_action_keyboard():
    keyboard = [[InlineKeyboardButton("🎡 Запустить колесо", callback_data="spin")]]
    return InlineKeyboardMarkup(keyboard)

def parse_participants(text):
    if ',' in text:
        participants = [p.strip() for p in text.split(',') if p.strip()]
    else:
        participants = [p.strip() for p in text.split() if p.strip()]
    return participants

# ========== ОТПРАВКА РЕЗУЛЬТАТА В ГРУППУ ==========
async def send_result_to_group(context, title, participants, winner):
    participants_list = "\n".join([f"• {p}" for p in participants])
    
    message = f"🎉 *РЕЗУЛЬТАТ РОЗЫГРЫША* 🎉\n\n"
    message += f"📌 *Заявка:* {title}\n\n"
    message += f"👥 *Участники:*\n{participants_list}\n\n"
    message += f"🏆 *ПОБЕДИТЕЛЬ:* **{winner}** 🏆\n\n"
    message += f"Поздравляем! 🎊🎉"
    
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
        
        # Отправляем результат в группу
        success = await send_result_to_group(context, title, participants, winner)
        
        if success:
            # Подтверждение админу
            await query.edit_message_text(
                f"✅ *Розыгрыш проведён!*\n\n"
                f"📌 Заявка: {title}\n"
                f"🏆 Победитель: **{winner}**\n\n"
                f"Результат отправлен в группу.",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                "❌ Ошибка при отправке результата в группу.\n"
                "Проверьте ID группы и права бота.",
                parse_mode="Markdown"
            )
        
        user_sessions.pop(user_id, None)

# ========== ОБРАБОТЧИК ТОЛЬКО ДЛЯ ЛИЧНЫХ СООБЩЕНИЙ ==========
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
        result_text += f"Нажмите «Запустить колесо», чтобы провести розыгрыш.\n\n"
        result_text += f"Результат автоматически отправится в группу."
        
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
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_private_text))
    
    print("🚀 Бот Колесо фортуны запущен...")
    print(f"📢 Результаты будут отправляться в группу с ID: {GROUP_CHAT_ID}")
    application.run_polling()

if __name__ == "__main__":
    main()
