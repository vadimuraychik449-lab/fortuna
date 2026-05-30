import os
import random
import json
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Dispatcher, CommandHandler, CallbackQueryHandler, MessageHandler, filters

TOKEN = "8867087367:AAE5o5px2UU56vDfPmxr-SmSNDzTZXTUODs"
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, None, use_context=True)

app = Flask(__name__)

user_sessions = {}

# ========== КЛАВИАТУРЫ И ФУНКЦИИ ==========
def get_main_keyboard():
    keyboard = [[InlineKeyboardButton("🎲 Новый розыгрыш", callback_data="new_draw")]]
    return InlineKeyboardMarkup(keyboard)

def get_action_keyboard():
    keyboard = [[InlineKeyboardButton("🎡 Запустить колесо", callback_data="spin")]]
    return InlineKeyboardMarkup(keyboard)

def parse_participants(text):
    title = "Розыгрыш"
    if '|' in text:
        parts = text.split('|', 1)
        title = parts[0].strip()
        text = parts[1].strip()
    if ',' in text:
        participants = [p.strip() for p in text.split(',') if p.strip()]
    else:
        participants = [p.strip() for p in text.split() if p.strip()]
    return title, participants

# ========== ОБРАБОТЧИКИ ==========
async def start(update, context):
    user_id = update.effective_user.id
    user_sessions.pop(user_id, None)
    await update.message.reply_text(
        "🎡 *Колесо фортуны*\n\nВведите участников через запятую:\n`Аня, Ваня, Маша`\n\nС заявкой: `Приз | Аня, Ваня, Маша`",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def handle_callback(update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "new_draw":
        user_sessions[user_id] = {"step": "awaiting_participants"}
        await query.edit_message_text("Введите список участников через запятую:", parse_mode="Markdown")

    elif data == "spin":
        session = user_sessions.get(user_id, {})
        participants = session.get("participants", [])
        if len(participants) < 2:
            await query.edit_message_text("❌ Нужно минимум 2 участника.")
            return
        winner = random.choice(participants)
        title = session.get("title", "Розыгрыш")
        text = f"🎉 *РЕЗУЛЬТАТ* 🎉\n\n📌 {title}\n👥 {len(participants)} участников\n\n🏆 *ПОБЕДИТЕЛЬ:* {winner}"
        await query.edit_message_text(text, parse_mode="Markdown")
        user_sessions.pop(user_id, None)

async def handle_text(update, context):
    user_id = update.effective_user.id
    session = user_sessions.get(user_id, {})
    if session.get("step") != "awaiting_participants":
        await start(update, context)
        return
    text = update.message.text.strip()
    title, participants = parse_participants(text)
    if len(participants) < 2:
        await update.message.reply_text("❌ Нужно минимум 2 участника. Повторите:")
        return
    user_sessions[user_id] = {"title": title, "participants": participants}
    participants_list = "\n".join([f"{i+1}. {p}" for i, p in enumerate(participants)])
    await update.message.reply_text(
        f"✅ *Участники ({len(participants)}):*\n{participants_list}\n\nНажмите «Запустить колесо».",
        parse_mode="Markdown",
        reply_markup=get_action_keyboard()
    )

# ========== НАСТРОЙКА ОБРАБОТЧИКОВ ==========
dp.add_handler(CommandHandler("start", start))
dp.add_handler(CallbackQueryHandler(handle_callback, pattern="^(new_draw|spin)$"))
dp.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

# ========== ВЕБХУК ==========
@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        dp.process_update(update)
        return "ok", 200
    except Exception as e:
        return "error", 500

@app.route("/health")
def health():
    return "OK", 200

@app.route("/")
def index():
    return "🎡 Колесо фортуны работает!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
