import sqlite3
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor

# Bot tokeni va admin ID
TOKEN = "7434515708:AAHtUvtyoM-NGz0LqbAicZlDFzVh9sNqIPk"  # Bot tokenini shu yerga yozing
ADMINS = [6141812477]  # Admin ID (O'zingizning Telegram ID'ingizni qo'ying)

# Botni ishga tushirish
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Logger sozlamalari
logging.basicConfig(level=logging.INFO)

# Ma'lumotlar bazasi: SQLite
conn = sqlite3.connect("uzauto_bozor.db")
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS ads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    car TEXT,
    image TEXT,
    year INTEGER,
    mileage INTEGER,
    paint TEXT,
    fuel TEXT,
    region TEXT,
    price INTEGER,
    vip INTEGER DEFAULT 0
)''')
conn.commit()

# Asosiy menyu tugmalari
menu = ReplyKeyboardMarkup(resize_keyboard=True)
menu.add(KeyboardButton("🚗 E'lon joylash"), KeyboardButton("🔍 Mashina qidirish"))
menu.add(KeyboardButton("🌟 VIP e'lonlar"), KeyboardButton("👤 Shaxsiy kabinet"))
menu.add(KeyboardButton("📝 E'lonlarni boshqarish"))

# /start komandasi
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("Assalomu alaykum! UzAuto Bozor botiga xush kelibsiz!", reply_markup=menu)

# E'lon joylash uchun holatlar
class AdStates(StatesGroup):
    car = State()
    image = State()
    year = State()
    mileage = State()
    paint = State()
    fuel = State()
    region = State()
    price = State()

@dp.message_handler(lambda message: message.text == "🚗 E'lon joylash")
async def add_ad(message: types.Message):
    await message.answer("Mashina nomini kiriting:")
    await AdStates.car.set()

@dp.message_handler(state=AdStates.car)
async def process_car(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['car'] = message.text
    await message.answer("Iltimos, mashinaning rasmini yuboring:")
    await AdStates.image.set()

@dp.message_handler(content_types=['photo'], state=AdStates.image)
async def process_image(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['image'] = message.photo[-1].file_id
    await message.answer("Mashina yilini kiriting:")
    await AdStates.year.set()

@dp.message_handler(state=AdStates.year)
async def process_year(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        try:
            data['year'] = int(message.text)
        except ValueError:
            await message.answer("Iltimos, yili raqam orqali kiriting:")
            return
    await message.answer("Yurgan masofasini (km) kiriting:")
    await AdStates.mileage.set()

@dp.message_handler(state=AdStates.mileage)
async def process_mileage(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        try:
            data['mileage'] = int(message.text)
        except ValueError:
            await message.answer("Iltimos, masofani raqam orqali kiriting:")
            return
    await message.answer("Kraskasi haqida ma'lumot kiriting:")
    await AdStates.paint.set()

@dp.message_handler(state=AdStates.paint)
async def process_paint(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['paint'] = message.text
    await message.answer("Yoqilg'i turini kiriting:")
    await AdStates.fuel.set()

@dp.message_handler(state=AdStates.fuel)
async def process_fuel(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['fuel'] = message.text
    await message.answer("Viloyatni kiriting:")
    await AdStates.region.set()

@dp.message_handler(state=AdStates.region)
async def process_region(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['region'] = message.text
    await message.answer("Narxni kiriting:")
    await AdStates.price.set()

@dp.message_handler(state=AdStates.price)
async def process_price(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        try:
            data['price'] = int(message.text)
        except ValueError:
            await message.answer("Iltimos, narxni raqamlar orqali kiriting:")
            return
        cursor.execute(
            "INSERT INTO ads (user_id, car, image, year, mileage, paint, fuel, region, price) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (message.from_user.id, data['car'], data['image'], data['year'], data['mileage'], data['paint'], data['fuel'], data['region'], data['price'])
        )
        conn.commit()
    await message.answer("✅ E'loningiz muvaffaqiyatli qo'shildi!", reply_markup=menu)
    await state.finish()

# VIP e’lonlarni chiqarish
@dp.message_handler(lambda message: message.text == "🌟 VIP e'lonlar")
async def show_vip_ads(message: types.Message):
    cursor.execute("SELECT car, region, price FROM ads WHERE vip=1")
    ads = cursor.fetchall()
    if ads:
        for ad in ads:
            await message.answer(f"🌟 **VIP E’lon**\n🚗 {ad[0]} | 📍 {ad[1]} | 💰 {ad[2]} so'm")
    else:
        await message.answer("Hozircha VIP e’lonlar yo‘q.")

# Admin paneli: VIP e’lon qilish
@dp.message_handler(commands=["admin"], user_id=ADMINS)
async def admin_panel(message: types.Message):
    await message.answer("👮‍♂️ *Admin paneliga xush kelibsiz!*\n\n🔹 VIP e’lon qilish uchun e’lon ID-sini yuboring:")

@dp.message_handler(lambda message: message.text.isdigit(), user_id=ADMINS)
async def make_vip(message: types.Message):
    ad_id = int(message.text)
    cursor.execute("UPDATE ads SET vip=1 WHERE id=?", (ad_id,))
    conn.commit()
    await message.answer(f"✅ E’lon #{ad_id} VIP ga o‘zgartirildi!")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)