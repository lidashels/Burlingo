import asyncio
import logging
import aiosqlite
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ВСТАВЬТЕ СЮДА ТОКЕН ОТ @BotFather
BOT_TOKEN = "9107764668:AAFBCTLLUncRawAXgB7TvIEV13KWK8jorVU"
# URL, где будет размещен ваш HTML-файл (например, через GitHub Pages или Vercel)
WEBAPP_URL = "https://lidashels.github.io/Burlingo/burlingo.html" 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

# ===== БАЗА ДАННЫХ (SQLite) =====
async def init_db():
    async with aiosqlite.connect("burlingo.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                chat_id INTEGER PRIMARY KEY,
                username TEXT,
                xp INTEGER DEFAULT 0,
                streak INTEGER DEFAULT 0,
                last_lesson_date TEXT,
                notifications_enabled INTEGER DEFAULT 1
            )
        """)
        await db.commit()

async def get_user(chat_id):
    async with aiosqlite.connect("burlingo.db") as db:
        cursor = await db.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
        return await cursor.fetchone()

async def update_user_streak(chat_id):
    today = datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect("burlingo.db") as db:
        user = await get_user(chat_id)
        if user:
            last_date = user[4]
            streak = user[3]
            if last_date != today:
                yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
                new_streak = streak + 1 if last_date == yesterday else 1
                await db.execute("UPDATE users SET streak = ?, last_lesson_date = ? WHERE chat_id = ?", 
                                 (new_streak, today, chat_id))
        else:
            await db.execute("INSERT INTO users (chat_id, last_lesson_date, streak) VALUES (?, ?, ?)",
                             (chat_id, today, 1))
        await db.commit()

# ===== ОБРАБОТЧИКИ БОТА =====
@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🐺 Начать обучение", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])
    await message.answer(
        f"Сайн байна, {message.from_user.first_name}! 👋\n\n"
        "Нажми кнопку ниже, чтобы открыть БурЛинго и начать учить бурятский язык!",
        reply_markup=kb
    )
    # Добавляем пользователя в БД, если его нет
    async with aiosqlite.connect("burlingo.db") as db:
        await db.execute("INSERT OR IGNORE INTO users (chat_id, username) VALUES (?, ?)", 
                         (message.chat.id, message.from_user.first_name))
        await db.commit()

@dp.message(F.text == "/stats")
async def cmd_stats(message: Message):
    user = await get_user(message.chat.id)
    if user:
        await message.answer(f"📊 Твоя статистика:\n⚡ XP: {user[2]}\n🔥 Серия дней: {user[3]}")
    else:
        await message.answer("Сначала нажми /start")

# Обработка данных, пришедших из Web App (когда пользователь закрыл окно)
@dp.message(F.web_app_data)
async def process_webapp_data(message: Message):
    import json
    try:
        data = json.loads(message.web_app_data.data)
        if data.get("action") == "lesson_completed":
            await update_user_streak(message.chat.id)
            await message.answer(f"🎉 Отлично! Урок пройден!\n+{data['xp_earned']} XP. Так держать!")
    except json.JSONDecodeError:
        pass

# ===== СИСТЕМА УВЕДОМЛЕНИЙ (DUOLINGO STYLE) =====
async def send_duolingo_notifications():
    """Проверяет пользователей и шлет напоминания"""
    today = datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect("burlingo.db") as db:
        # Находим тех, у кого включены уведомления и кто не занимался сегодня
        async with db.execute("""
            SELECT chat_id, username, streak FROM users 
            WHERE notifications_enabled = 1 AND (last_lesson_date IS NULL OR last_lesson_date != ?)
        """, (today,)) as cursor:
            users = await cursor.fetchall()
            
            for chat_id, username, streak in users:
                if streak >= 3:
                    text = f"🔥 {username}, твоя серия {streak} дней под угрозой! Зайди в БурЛинго и не потеряй прогресс!"
                else:
                    text = f"🐺 Сайн байна, {username}! Время выучить 5 новых бурятских слов. Это займет всего 2 минуты!"
                
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📚 Открыть урок", web_app=WebAppInfo(url=WEBAPP_URL))]
                ])
                try:
                    await bot.send_message(chat_id, text, reply_markup=kb)
                except Exception as e:
                    print(f"Не удалось отправить сообщение {chat_id}: {e}")

# ===== ЗАПУСК =====
async def main():
    await init_db()
    
    # Настраиваем расписание: проверка каждый день в 18:00
    scheduler.add_job(send_duolingo_notifications, 'cron', hour=18, minute=0)
    scheduler.start()
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())