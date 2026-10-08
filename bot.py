import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.utils import executor

# ============ НАСТРОЙКИ ============
BOT_TOKEN = "8725957123:AAHbgkZXmAoMMPd1tzxgTSF0ZNEc4X7YYpQ"
CHANNEL_ID = "@h0ll0w2010"
CHANNEL_LINK = "https://t.me/h0ll0w2010"

# ============ ФАЙЛЫ ============
FILES = {
    "file_1": ("Видео с собакой", "VID_20260829_231210_311.mp4", "Вот ваш файл!"),
    "file_2": ("Толстушка на соли", "VID_20260921_153349_985.mp4", "Вот ваш файл!"),
}
# =================================

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    subscribed INTEGER DEFAULT 0
)''')
conn.commit()

def is_subscribed_in_db(user_id):
    cursor.execute("SELECT subscribed FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return bool(row and row[0] == 1)

def set_subscribed(user_id, value):
    cursor.execute("INSERT OR REPLACE INTO users (user_id, subscribed) VALUES (?, ?)", (user_id, value))
    conn.commit()

async def check_subscription(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["creator", "administrator", "member"]
    except Exception as e:
        print(f"Ошибка проверки: {e}")
        return False

def files_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    for key, (title, _, _) in FILES.items():
        markup.add(types.InlineKeyboardButton(title, callback_data=key))
    return markup

def subscribe_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("📢 Подписаться на канал", url=CHANNEL_LINK))
    markup.add(types.InlineKeyboardButton("✅ Я подписался", callback_data="check_sub"))
    return markup

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("👋 Привет! Выбери файл:", reply_markup=files_keyboard())

@dp.callback_query_handler(lambda c: c.data in FILES)
async def choose_file(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    file_key = callback.data
    await state.update_data(chosen_file=file_key)

    if is_subscribed_in_db(user_id):
        if await check_subscription(user_id):
            await send_chosen_file(callback, file_key)
            return
        else:
            set_subscribed(user_id, 0)

    await callback.message.edit_text(
        f"🔒 Чтобы получить файл, подпишись на канал:\n\n"
        f"👉 {CHANNEL_LINK}\n\n"
        f"После подписки нажми «✅ Я подписался».",
        reply_markup=subscribe_keyboard()
    )
    await callback.answer()

@dp.callback_query_handler(text="check_sub")
async def check_sub(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if await check_subscription(user_id):
        set_subscribed(user_id, 1)
        data = await state.get_data()
        file_key = data.get("chosen_file")
        if not file_key or file_key not in FILES:
            await callback.message.edit_text("✅ Подписка подтверждена! Выбери файл:", reply_markup=files_keyboard())
        else:
            await send_chosen_file(callback, file_key)
    else:
        await callback.answer("❌ Вы ещё не подписаны!", show_alert=True)

async def send_chosen_file(callback: types.CallbackQuery, file_key: str):
    title, path, caption = FILES[file_key]
    try:
        with open(path, "rb") as f:
            await bot.send_document(chat_id=callback.from_user.id, document=f, caption=caption)
        await callback.message.answer("📂 Хочешь посмотреть что-то ещё?", reply_markup=files_keyboard())
        await callback.message.delete()
    except FileNotFoundError:
        await callback.message.answer("⚠️ Файл не найден. Сообщите администратору.")
    except Exception as e:
        await callback.message.answer(f"⚠️ Ошибка: {e}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
