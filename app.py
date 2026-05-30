import random
import asyncio
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# ========== НАСТРОЙКИ ==========
TOKEN = "8867087367:AAE5o5px2UU56vDfPmxr-SmSNDzTZXTUODs"

# Хранилище сессий
user_sessions = {}

app = Flask(__name__)

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
    
    # Разбираем участников
    if ',' in participants_text:
        participants = [p.strip() for p in participants_text.split(',') if p.strip()]
    else:
        participants = [p.strip() for p in participants_text.split('\n') if p.strip()]
        if not participants and ' ' in participants_text:
            participants = [p.strip() for p in participants_text.split(' ') if p.strip()]
    
    # Убираем дубликаты
    seen = set()
    unique = []
    for p in participants:
        if p.lower() not in seen:
            seen.add(p.lower())
            unique.append(p)
    
    return title, unique

async def spin_wheel(chat_id, context, draw_data, message_id=None):
    """Анимация колеса фортуны"""
    participants = draw_data["participants"]
    winner_index = random.randrange(len(participants))
    winner = participants[winner_index]
    
    draw_data["winner"] = winner
    
    total_spins = random.randint(20, 35)
    
    # Отправляем начальное сообщение
    if message_id:
        await context.bot.edit_message_text(
            "🎡 *Вращаем колесо фортуны...*",
            chat_id=chat_id,
            message_id=message_id,
            parse_mode="Markdown"
        )
    else:
        sent_msg = await context.bot.send_message(
            chat_id=chat_id,
            text="🎡 *Вращаем колесо фортуны...*",
            parse_mode="Markdown"
        )
        message_id = sent_msg.message_id
    
    # Анимация
    for i in range(total_spins):
        current_index = (winner_index + total_spins - i) % len(participants)
        
        progress = int((i + 1) / total_spins * 20)
        bar = "█" * progress + "░" * (20 - progress)
        
        spin_text = f"🎡 *Колесо фортуны*\n\n"
        spin_text += f"`{bar}`\n\n"
        
        # Показываем текущего "лидера"
        spin_text += f"👉 *{participants[current_index]}* 👈"
        
        await context.bot.edit_message_text(
            spin_text,
            chat_id=chat_id,
            message_id=message_id,
            parse_mode="Markdown"
        )
        
        delay = 0.2 - (i / total_spins) * 0.15
        await asyncio.sleep(max(0.05, delay))
    
    # Финальный результат
    final_text = f"🎉 *РЕЗУЛЬТАТ РОЗЫГРЫША* 🎉\n\n"
    if draw_data.get("title") and draw_data["title"] != "Розыгрыш":
        final_text += f"📌 *Заявка:* {draw_data['title']}\n\n"
    final_text += f"👥 *Участников:* {len(participants)}\n\n"
    final_text += f"🏆 *ПОБЕДИТЕЛЬ:* **{winner}** 🏆\n\n"
    final_text += f"Поздравляем! 🎊🎉"
    
    await context.bot.edit_message_text(
        final_text,
        chat_id=chat_id,
        message_id=message_id,
        parse_mode="Markdown",
        reply_markup=get_result_keyboard()
    )

# ========== ОБРАБОТЧИКИ ==========
async def start(update, context):
    user_id = update.effective_user.id
    user_sessions.pop(user_id, None)
    
    welcome_text = """🎡 *Колесо фортуны АБ*

Я провожу розыгрыши с анимацией колеса!

*Как использовать:*
1️⃣ Нажмите «Новый розыгрыш»
2️⃣ Напишите список участников
   • Через запятую: `Аня, Ваня, Маша`
   • Через пробел: `Аня Ваня Маша`
   • Или построчно
3️⃣ Запустите колесо!

*Опционально:* можно указать заявку перед списком через вертикальную черту `|`

Пример: `Подарочный сертификат | Аня, Ваня, Маша`

Нажмите кнопку ниже 👇"""
    
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
            "Напишите список участников:\n\n"
            "• Через запятую: `Аня, Ваня, Маша`\n"
            "• Через пробел: `Аня Ваня Маша`\n"
            "• Или построчно:\n\n"
            "Чтобы указать заявку, напишите её перед списком через `|`:\n"
            "`Подарочный сертификат | Аня, Ваня, Маша`",
            parse_mode="Markdown"
        )
    
    elif data == "howto":
        howto_text = """ℹ️ *Как пользоваться ботом*

1. Нажмите «Новый розыгрыш»
2. Введите список участников (минимум 2)
3. Нажмите «Запустить колесо»
4. Наслаждайтесь анимацией!

*Форматы ввода участников:*
• `Аня, Ваня, Маша`
• `Аня Ваня Маша`
• Построчно

*С заявкой:* `Приз | Аня, Ваня, Маша`"""
        
        await query.edit_message_text(howto_text, parse_mode="Markdown", reply_markup=get_main_keyboard())
    
    elif data == "spin":
        session = user_sessions.get(user_id, {})
        participants = session.get("participants", [])
        
        if len(participants) < 2:
            await query.edit_message_text(
                "❌ Недостаточно участников (нужно минимум 2).\nНажмите «Новый розыгрыш».",
                reply_markup=get_main_keyboard()
            )
            return
        
        draw_data = {
            "title": session.get("title", "Розыгрыш"),
            "participants": participants
        }
        
        asyncio.create_task(spin_wheel(query.message.chat_id, context, draw_data, query.message.message_id))
    
    elif data == "edit":
        user_sessions[user_id] = {"step": "awaiting_participants", "title": user_sessions.get(user_id, {}).get("title", "Розыгрыш")}
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
            f"❌ Найдено всего {len(participants)} участник(ов). Нужно минимум 2.\n\n"
            f"Пожалуйста, введите список ещё раз:"
        )
        return
    
    session["title"] = title
    session["participants"] = participants
    session["step"] = "ready"
    user_sessions[user_id] = session
    
    participants_list = "\n".join([f"{i+1}. {p}" for i, p in enumerate(participants[:20])])
    if len(participants) > 20:
        participants_list += f"\n... и ещё {len(participants) - 20}"
    
    result_text = f"✅ *Участники ({len(participants)} чел.):*\n{participants_list}\n\n"
    if title != "Розыгрыш":
        result_text += f"📌 *Заявка:* {title}\n\n"
    result_text += f"Нажмите «Запустить колесо», чтобы провести розыгрыш."
    
    await update.message.reply_text(result_text, parse_mode="Markdown", reply_markup=get_action_keyboard())

# ========== ЗАПУСК ==========
def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("🚀 Бот Колесо фортуны АБ запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()
