"""
🐺 БурЛинго Telegram-бот
Напоминания, слово дня, мини-тесты и ссылка на сайт
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, JobQueue
)
from telegram.constants import ParseMode
import random
import json
import os
from datetime import time

# ============================================
# 🔑 НАСТРОЙКИ
# ============================================
TOKEN = "9107764668:AAFBCTLLUncRawAXgB7TvIEV13KWK8jorVU"  # ← Замените на ваш токен от BotFather
SITE_URL = "https://localhost:5500/burlingo.html.netlify.app"  # ← Замените на адрес вашего сайта

# Словарь бурятских слов (можно расширять)
WORDS = [
    {"buryat": "Сайн", "russian": "Привет / Хороший"},
    {"buryat": "Баяр", "russian": "До свидания"},
    {"buryat": "Баярлаа", "russian": "Спасибо"},
    {"buryat": "Энэ юэн бэ?", "russian": "Что это?"},
    {"buryat": "Аба", "russian": "Отец"},
    {"buryat": "Эжы", "russian": "Мать"},
    {"buryat": "Аха", "russian": "Старший брат"},
    {"buryat": "Дүү", "russian": "Младший брат"},
    {"buryat": "Нюрга", "russian": "Лошадь"},
    {"buryat": "Модон", "russian": "Дерево"},
    {"buryat": "Наран", "russian": "Солнце"},
    {"buryat": "Һара", "russian": "Луна / Месяц"},
    {"buryat": "Уһан", "russian": "Вода"},
    {"buryat": "Гал", "russian": "Огонь"},
    {"buryat": "Газар", "russian": "Земля"},
]

# Файл для хранения пользователей
USERS_FILE = "users.json"

# ============================================
# 💾 ХРАНИЛИЩЕ ПОЛЬЗОВАТЕЛЕЙ
# ============================================
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

users = load_users()

# ============================================
# 🚀 КОМАНДА /start
# ============================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    name = update.effective_user.first_name or "Друг"
    
    # Сохраняем пользователя
    if user_id not in users:
        users[user_id] = {
            "name": name,
            "username": update.effective_user.username or "",
            "words_learned": 0,
            "reminders_enabled": True,
        }
        save_users(users)
        
        # Настраиваем ежедневное напоминание
        if context.job_queue:
            context.job_queue.run_daily(
                send_daily_reminder,
                time=time(hour=10, minute=0),  # Каждый день в 10:00
                data={"user_id": user_id},
                name=f"reminder_{user_id}"
            )
    
    # Главное меню
    keyboard = [
        [InlineKeyboardButton("🎮 Начать обучение на сайте", url=SITE_URL)],
        [
            InlineKeyboardButton("📚 Слово дня", callback_data="word_of_day"),
            InlineKeyboardButton("🎯 Мини-тест", callback_data="quiz_start"),
        ],
        [
            InlineKeyboardButton("🔔 Напоминания", callback_data="toggle_reminder"),
            InlineKeyboardButton("📊 Мой прогресс", callback_data="stats"),
        ],
        [InlineKeyboardButton("📤 Пригласить друга", callback_data="invite")],
    ]
    
    await update.message.reply_text(
        f"🐺 <b>Сайн байна, {name}!</b>\n\n"
        f"Добро пожаловать в <b>БурЛинго</b> — приложение для изучения бурятского языка!\n\n"
        f"Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

# ============================================
# 📚 СЛОВО ДНЯ
# ============================================
async def word_of_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    word = random.choice(WORDS)
    
    keyboard = [
        [InlineKeyboardButton("🔊 Прослушать", callback_data=f"speak_{word['buryat']}")],
        [InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")],
    ]
    
    await query.message.reply_text(
        f"📚 <b>Слово дня:</b>\n\n"
        f"🇧🇺 <b>{word['buryat']}</b>\n"
        f"🇷🇺 <i>{word['russian']}</i>\n\n"
        f"Попробуйте использовать это слово сегодня!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

# ============================================
# 🎯 МИНИ-ТЕСТ
# ============================================
async def quiz_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Выбираем правильное слово и 3 неправильных варианта
    correct = random.choice(WORDS)
    distractors = [w for w in WORDS if w["russian"] != correct["russian"]]
    options = random.sample(distractors, min(3, len(distractors)))
    options.append(correct)
    random.shuffle(options)
    
    # Сохраняем правильный ответ
    context.user_data["quiz_answer"] = correct["russian"]
    
    keyboard = [[InlineKeyboardButton(opt["russian"], callback_data=f"quiz_{opt['russian']}")] 
                for opt in options]
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
    
    await query.message.reply_text(
        f"🎯 <b>Мини-тест!</b>\n\n"
        f"Как переводится слово:\n\n"
        f"🇧🇺 <b>{correct['buryat']}</b>?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    selected = query.data.replace("quiz_", "")
    correct = context.user_data.get("quiz_answer", "")
    
    user_id = str(query.from_user.id)
    
    if selected == correct:
        # Начисляем прогресс
        if user_id in users:
            users[user_id]["words_learned"] = users[user_id].get("words_learned", 0) + 1
            save_users(users)
        
        keyboard = [
            [InlineKeyboardButton("🎯 Ещё вопрос", callback_data="quiz_start")],
            [InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")],
        ]
        await query.message.reply_text(
            f"✅ <b>Правильно!</b> 🎉\n\n"
            f"+1 слово в вашу копилку!",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    else:
        keyboard = [
            [InlineKeyboardButton("🎯 Попробовать снова", callback_data="quiz_start")],
            [InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")],
        ]
        await query.message.reply_text(
            f"❌ Не совсем...\n\n"
            f"Правильный ответ: <b>{correct}</b>\n\n"
            f"Не расстраивайтесь, попробуйте ещё!",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )

# ============================================
# 🔔 НАПОМИНАНИЯ
# ============================================
async def toggle_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    if user_id in users:
        users[user_id]["reminders_enabled"] = not users[user_id].get("reminders_enabled", True)
        save_users(users)
        
        status = "включены ✅" if users[user_id]["reminders_enabled"] else "выключены ❌"
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")],
        ]
        await query.message.reply_text(
            f"🔔 Напоминания {status}\n\n"
            f"Вы будете получать ежедневное слово в 10:00.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def send_daily_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Ежедневная рассылка слова дня"""
    job_data = context.job.data
    user_id = job_data["user_id"]
    
    if user_id not in users:
        return
    if not users[user_id].get("reminders_enabled", True):
        return
    
    word = random.choice(WORDS)
    
    keyboard = [
        [InlineKeyboardButton("🎮 Перейти к урокам", url=SITE_URL)],
    ]
    
    try:
        await context.bot.send_message(
            chat_id=int(user_id),
            text=f"🌅 <b>Доброе утро!</b>\n\n"
                 f"📚 Слово на сегодня:\n"
                 f"🇧🇺 <b>{word['buryat']}</b>\n"
                 f"🇷🇺 <i>{word['russian']}</i>\n\n"
                 f"Не забудьте позаниматься! 🔥",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        print(f"Ошибка отправки {user_id}: {e}")

# ============================================
# 📊 СТАТИСТИКА
# ============================================
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    user_data = users.get(user_id, {})
    
    words = user_data.get("words_learned", 0)
    name = user_data.get("name", "Друг")
    
    # Вычисляем уровень
    level = words // 10 + 1
    xp_to_next = 10 - (words % 10)
    
    keyboard = [
        [InlineKeyboardButton("🎮 Продолжить обучение", url=SITE_URL)],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")],
    ]
    
    await query.message.reply_text(
        f"📊 <b>Ваш прогресс, {name}!</b>\n\n"
        f"📚 Слов изучено в боте: <b>{words}</b>\n"
        f"⭐ Уровень: <b>{level}</b>\n"
        f"⚡ До следующего: <b>{xp_to_next}</b> слов\n\n"
        f"Продолжайте в этом духе! 🚀",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

# ============================================
# 📤 ПРИГЛАШЕНИЕ ДРУЗЕЙ
# ============================================
async def invite_friend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    bot_username = (await context.bot.get_me()).username
    bot_link = f"https://t.me/{bot_username}"
    
    text = (
        f"📤 <b>Пригласи друзей!</b>\n\n"
        f"Отправь им ссылку на бота:\n"
        f"👉 {bot_link}\n\n"
        f"Или на сайт:\n"
        f"👉 {SITE_URL}\n\n"
        f"Учите бурятский вместе! 🐺"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")],
    ]
    
    await query.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

# ============================================
# 🔙 ВОЗВРАТ В МЕНЮ
# ============================================
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Имитируем команду /start
    fake_update = update
    await start(fake_update, context)

# ============================================
# 🔊 ОЗВУЧКА (имитация)
# ============================================
async def speak_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    word = query.data.replace("speak_", "")
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")],
    ]
    
    await query.message.reply_text(
        f"🔊 Произнесите вслух: <b>{word}</b>\n\n"
        f"(В будущих версиях будет аудио!)",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

# ============================================
# 🚀 ЗАПУСК БОТА
# ============================================
def main():
    print("🐺 БурЛинго-бот запускается...")
    
    app = Application.builder().token(TOKEN).build()
    
    # Команды
    app.add_handler(CommandHandler("start", start))
    
    # Callback-кнопки
    app.add_handler(CallbackQueryHandler(word_of_day, pattern="word_of_day"))
    app.add_handler(CallbackQueryHandler(quiz_start, pattern="quiz_start"))
    app.add_handler(CallbackQueryHandler(quiz_answer, pattern="quiz_.*"))
    app.add_handler(CallbackQueryHandler(toggle_reminder, pattern="toggle_reminder"))
    app.add_handler(CallbackQueryHandler(show_stats, pattern="stats"))
    app.add_handler(CallbackQueryHandler(invite_friend, pattern="invite"))
    app.add_handler(CallbackQueryHandler(speak_word, pattern="speak_.*"))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="back_to_menu"))
    
    print("✅ Бот запущен! Нажмите Ctrl+C для остановки.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()