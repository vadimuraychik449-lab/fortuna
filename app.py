import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# Токен бота
TOKEN = "8867087367:AAE5o5px2UU56vDfPmxr-SmSNDzTZXTUODs"

# Хранилище сессий пользователей
user_sessions = {}

# ========== КЛАВИАТУРЫ ==========
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎲 Новый розыгрыш", callback_data="new_draw")],
        [InlineKeyboardButton("ℹ️ Как это работает", callback_data="howto")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_action_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎡 Запустить колесо", callback_data="spin")],
        [InlineKeyboardButton("✏️ Изменить участников", callback_data="edit")],
        [InlineKeyboardButton("◀️ Отмена", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_result_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎲 Новый розыгрыш", callback_data="new_draw")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ========== ФУНКЦИИ ==========
def parse_participants(text):
    """Превращает текст в список участников"""
    title = "Розыгрыш"
    participants_text = text
    
    if '|' in text:
        parts = text.split('|', 1)
        title = parts[0].strip()
        participants_text = parts[1].strip()
    
    if ',' in participants_text:
        participants = [p.strip() for p in participants_text.split(',') if p.strip()]
    else:
        participants = [p.strip() for p in participants_text.split() if p.strip()]
    
    # Убираем дубликаты
    seen = set()
    unique = []
    for p in participants:
        if p.lower() not in seen:
            seen.add(p.lower())
            unique.append(p)
    
    return title, unique

async def spin_wheel(update, context, draw_data):
    """Анимация колеса фортуны (упрощённая)"""
    query = update.callback_query
    participants = draw_data["participants"]
    winner_index = random.randrange(len(participants))
    winner = participants[winner_index]
    total_spins = random.randint(15, 25)
    
    # Анимация
    for i in range(total_spins):
        current_index = (winner_index + total_spins - i) % len(participants)
        spin_text = f"🎡 *Колесо фортуны*\n\n👉 *{participants[current_index]}* 👈"
        await query.edit_message_text(spin_text, parse_mode="Markdown")
        await asyncio.sleep(0.1)
    
    # Финальный результат
    final_text = f"🎉 *РЕЗУЛЬТАТ РОЗЫГРЫША* 🎉\n\n"
    if draw_data.get("title") and draw_data["title"] != "Розыгрыш":
        final_text += f"📌 *Заявка:* {draw_data['title']}\n\n"
    final_text += f"👥 *Участников:* {len(participants)}\n\n"
    final_text += f"🏆 *ПОБЕДИТЕЛЬ:* **{winner}** 🏆\n\n"
    final_text += f"Поздравляем! 🎊🎉"
    
    await query.edit_message_text(final_text, parse_mode="Markdown", reply_markup=get_result_keyboard())

# ========== ОБРАБОТЧИКИ ==========
async def start(update, context):
    user_id = update.effective_user.id
    user_sessions.pop(user_id, None)
    
    welcome_text = """🎡 *Колесо фортуны*

Я провожу розыгрыши с анимацией!

*Как использовать:*
1️⃣ Нажмите «Новый розыгрыш»
2️⃣ Напишите список участников
3️⃣ Запустите колесо!

*Пример:* `Аня, Ваня, Маша`
*С заявкой:* `Приз | Аня, Ваня, Маша`"""
    
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

async def handle_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "new_draw":
        user_sessions[user_id] = {"step": "awaiting_participants"}
        await query.edit_message_text(
            "🎲 *Новый розыгрыш*\n\n"
            "Напишите список участников:\n"
            "• Через запятую: `Аня, Ваня, Маша`\n\n"
            "С заявкой: `Приз | Аня, Ваня, Маша`",
            parse_mode="Markdown"
        )
    
    elif data == "howto":
        await query.edit_message_text(
            "ℹ️ *Как пользоваться*\n\n"
            "1. Нажмите «Новый розыгрыш»\n"
            "2. Введите список участников\n"
            "3. Запустите колесо",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    
    elif data == "spin":
        session = user_sessions.get(user_id, {})
        participants = session.get("participants", [])
        
        if len(participants) < 2:
            await query.edit_message_text(
                "❌ Нужно минимум 2 участника.\nНажмите «Новый розыгрыш».",
                reply_markup=get_main_keyboard()
            )
            return
        
        draw_data = {
            "title": session.get("title", "Розыгрыш"),
            "participants": participants
        }
        
        await spin_wheel(update, context, draw_data)
    
    elif data == "edit":
        user_sessions[user_id] = {"step": "awaiting_participants"}
        await query.edit_message_text(
            "✏️ *Редактирование участников*\n\n"
            "Напишите новый список участников:",
            parse_mode="Markdown"
        )
    
    elif data == "cancel":
        user_sessions.pop(user_id, None)
        await query.edit_message_text("❌ Розыгрыш отменён.", reply_markup=get_main_keyboard())

async def handle_text(update, context):
    user_id = update.effective_user.id
    session = user_sessions.get(user_id, {})
    
    if session.get("step") != "awaiting_participants":
        await start(update, context)
        return
    
    text = update.message.text.strip()
    title, participants = parse_participants(text)
    
    if len(participants) < 2:
        await update.message.reply_text(
            f"❌ Найдено {len(participants)} участников. Нужно минимум 2.\nПовторите ввод:"
        )
        return
    
    session["title"] = title
    session["participants"] = participants
    session["step"] = "ready"
    user_sessions[user_id] = session
    
    participants_list = "\n".join([f"{i+1}. {p}" for i, p in enumerate(participants)])
    
    result_text = f"✅ *Участники ({len(participants)} чел.):*\n{participants_list}\n\n"
    if title != "Розыгрыш":
        result_text += f"📌 *Заявка:* {title}\n\n"
    result_text += f"Нажмите «Запустить колесо»."
    
    await update.message.reply_text(result_text, parse_mode="Markdown", reply_markup=get_action_keyboard())

# ========== ЗАПУСК ==========
def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("🚀 Бот Колесо фортуны запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()
