import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import re

TOKEN = "8559347659:AAFnsr-pzRMzReHyt44ysrMjjnIwy4b4gDg"  # вставь свой токен
ADMIN_ID = 8221472317

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ===================== ДАННЫЕ =====================
SECOND_ADMIN = None
ORDERS = []
PRODUCTS = {
    "shishka05": {"name": "💎 Шишка 0.5гр", "price": 250},
    "shishka1": {"name": "💎 Шишка 1гр", "price": 400},
    "shishka2": {"name": "💎 Шишка 2гр", "price": 600},
    "shishka3": {"name": "💎 Шишка 3гр", "price": 800},
    "shishka5": {"name": "💎 Шишка 5гр", "price": 1200},
}
AREAS = ["✨ ПОСКОТ (ПЕРЕСИПСКИЙ) ✨"]
PAYMENT_INFO = {"crypto": "0x1234567890ABCDEF1234567890ABCDEF12345678",
                "card": "4081781009999999"}
ORDER_ID_COUNTER = 1

# ===================== ФУНКЦИИ =====================
def check_admin(user_id):
    return user_id == ADMIN_ID or user_id == SECOND_ADMIN

def get_order_by_id(order_id):
    for o in ORDERS:
        if o["id"] == order_id:
            return o
    return None

async def auto_reject_orders():
    while True:
        now = datetime.now()
        for order in ORDERS:
            if order["status"] == "waiting" and now > order["deadline"]:
                order["status"] = "rejected"
                await bot.send_message(order["user_id"],
                                       f"❌ Время на оплату заказа #{order['id']} истекло. Заказ отклонен.")
                await bot.send_message(ADMIN_ID,
                                       f"❌ Заказ #{order['id']} автоматически отклонен (не подтвержден).")
        await asyncio.sleep(30)

# ===================== ПОЛЬЗОВАТЕЛЬ =====================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🛍 Каталог", "📍 Доступные районы", "👑 Админ")
    await message.answer("✨ Добро пожаловать в премиальный магазин 🛒", reply_markup=kb)

@dp.message_handler(text="📍 Доступные районы")
async def areas(message: types.Message):
    text = "📍 Доступные районы доставки:\n\n" + "\n".join([f"• {a}" for a in AREAS])
    await message.answer(text)

@dp.message_handler(text="🛍 Каталог")
async def catalog(message: types.Message):
    # Отправляем каждый товар как отдельную "карточку"
    for key, p in PRODUCTS.items():
        text = (
            f"✨ <b>{p['name']}</b>\n"
            f"💎 Цена: <b>{p['price']} ГРН </b>\n"
            f"🌟 Топ-продукт магазина!"
        )
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🛒 Выбрать", callback_data=f"select_{key}"))
        await message.answer(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query_handler(lambda c: c.data.startswith("select_"))
async def select_product(callback: types.CallbackQuery):
    global ORDER_ID_COUNTER
    product_key = callback.data.split("_")[1]
    product = PRODUCTS[product_key]

    order_id = ORDER_ID_COUNTER
    ORDER_ID_COUNTER += 1
    deadline = datetime.now() + timedelta(minutes=30)

    ORDERS.append({
        "id": order_id,
        "user_id": callback.from_user.id,
        "user": f"@{callback.from_user.username}",
        "product": product["name"],
        "price": product["price"],
        "payment": None,
        "status": "waiting",
        "deadline": deadline,
        "photo": None
    })

    # Кнопки оплаты с эмодзи
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💳 Оплатить картой", callback_data=f"pay_card_{order_id}"),
        InlineKeyboardButton("₿ Оплатить криптой", callback_data=f"pay_crypto_{order_id}")
    )

    text = (
        f"🎁 Вы выбрали: <b>{product['name']}</b>\n"
        f"💰 Сумма: <b>{product['price']} ГРН</b>\n\n"
        f"Выберите способ оплаты ниже ⬇️"
    )
    await bot.send_message(callback.from_user.id, text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query_handler(lambda c: c.data.startswith("pay_"))
async def payment_info(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    method = parts[1]
    order_id = int(parts[2])

    order = get_order_by_id(order_id)
    if not order:
        await bot.send_message(callback.from_user.id, "❌ Ошибка: заказ не найден.")
        return

    order["payment"] = "Карта" if method == "card" else "Крипта"
    payment_address = PAYMENT_INFO["card"] if method == "card" else PAYMENT_INFO["crypto"]

    text = (f"💰 Оплата заказа #{order_id}\n"
            f"🎁 Товар: <b>{order['product']}</b>\n"
            f"💵 Сумма: <b>{order['price']} ГРН</b>\n"
            f"💳 Метод оплаты: <b>{order['payment']}</b>\n"
            f"🔗 Реквизиты: <code>{payment_address}</code>\n\n"
            f"📝 В комментарии к платежу укажите номер заказа: <b>{order_id}</b>\n"
            f"⏰ У вас есть 30 минут на оплату.\n"
            f"⚠️ Если админ не подтвердит — заказ будет отклонен.")
    await bot.send_message(callback.from_user.id, text, parse_mode="HTML")
    await bot.send_message(ADMIN_ID,
                           f"🛒 Новый заказ #{order_id}\nПользователь: {order['user']}\n"
                           f"Товар: {order['product']} — {order['price']}₽\nОплата: {order['payment']} — Статус: waiting")

# ===================== АДМИН-ПАНЕЛЬ =====================
@dp.message_handler(text="👑 Админ")
async def admin_panel(message: types.Message):
    if not check_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа!")
        return
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📦 Просмотр заказов", callback_data="adm_orders"),
        InlineKeyboardButton("📸 Добавить фото посылки", callback_data="adm_add_photo")
    )
    await message.answer("👑 <b>Админ-панель</b>:", reply_markup=kb, parse_mode="HTML")

@dp.callback_query_handler(lambda c: c.data == "adm_orders")
async def view_orders(callback: types.CallbackQuery):
    text = "📋 <b>Заказы:</b>\n"
    for order in ORDERS:
        text += (f"#{order['id']} {order['user']} — {order['product']} — {order['price']}₽ — "
                 f"{order['payment']} — {order['status']}\n")
        if order["status"] == "waiting":
            text += f"/confirm_{order['id']} ✅ /reject_{order['id']} ❌\n"
    await bot.send_message(callback.from_user.id, text, parse_mode="HTML")

@dp.message_handler(lambda m: m.text.startswith("/confirm_") or m.text.startswith("/reject_"))
async def admin_confirm_reject(message: types.Message):
    if not check_admin(message.from_user.id):
        await message.reply("❌ У вас нет доступа!")
        return
    cmd, order_id_str = message.text.split("_")
    order_id = int(order_id_str)
    order = get_order_by_id(order_id)
    if not order:
        await message.reply("❌ Заказ не найден!")
        return
    if cmd == "/confirm":
        order["status"] = "confirmed"
        await message.reply(f"✅ Заказ #{order_id} подтвержден")
        await bot.send_message(order["user_id"], f"✅ Ваш заказ #{order_id} подтвержден администратором.")
        if order["photo"]:
            await bot.send_photo(order["user_id"], order["photo"], caption=f"Ваш заказ #{order_id}")
    else:
        order["status"] = "rejected"
        await message.reply(f"❌ Заказ #{order_id} отклонен")
        await bot.send_message(order["user_id"], f"❌ Ваш заказ #{order_id} отклонен администратором.")

@dp.callback_query_handler(lambda c: c.data == "adm_add_photo")
async def add_photo_start(callback: types.CallbackQuery):
    await bot.send_message(callback.from_user.id, "📸 Отправьте фото посылки с подписью #НомерЗаказа")

@dp.message_handler(content_types=['photo'])
async def save_photo(message: types.Message):
    if not check_admin(message.from_user.id):
        return
    caption = message.caption or ""
    m = re.search(r"#(\d+)", caption)
    if not m:
        await message.reply("❌ Укажите номер заказа в подписи, например: #1")
        return
    order_id = int(m.group(1))
    order = get_order_by_id(order_id)
    if not order:
        await message.reply("❌ Заказ не найден")
        return
    order["photo"] = message.photo[-1].file_id
    await message.reply(f"✅ Фото добавлено к заказу #{order_id}")

# ===================== Фоновая проверка =====================
async def on_startup(_):
    asyncio.create_task(auto_reject_orders())

# ===================== ЗАПУСК =====================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
