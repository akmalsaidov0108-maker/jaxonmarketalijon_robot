import asyncio
import json
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

import database as db

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "0").split(",")))
WORK_START = 8
WORK_END = 21
MIN_ALIJON = 20000
MIN_BUSTON = 40000
DISTRICTS = {"Alijon MFY": MIN_ALIJON, "Buston hududi": MIN_BUSTON}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
router = Router()
class Reg(StatesGroup):
    lang = State()
    phone = State()
    district = State()

class Order(StatesGroup):
    browsing = State()
    delivery = State()
    address = State()
    confirm = State()

class AdminSt(StatesGroup):
    main = State()
    add_cat_uz = State()
    add_cat_ru = State()
    add_cat_emoji = State()
    del_cat = State()
    add_prod_cat = State()
    add_prod_name_uz = State()
    add_prod_name_ru = State()
    add_prod_price = State()
    add_prod_unit = State()
    del_prod = State()
    update_price_prod = State()
    update_price_val = State()
    broadcast = State()
    send_akciya = State()

class ReviewSt(StatesGroup):
    rating = State()
    text = State()

class SearchSt(StatesGroup):
    query = State()

def is_work_time():
    h = datetime.now().hour
    return WORK_START <= h < WORK_END

async def get_lang(user_id):
    user = await db.get_user(user_id)
    return user["lang"] if user else "uz"

def t(lang, key, **kwargs):
    text = T[lang].get(key, T["uz"].get(key, ""))
    return text.format(**kwargs) if kwargs else text
T = {
    "uz": {
        "welcome": "🌟 <b>Jaxon Market</b>ga xush kelibsiz!",
        "choose_lang": "🌐 Tilni tanlang / Выберите язык:",
        "ask_phone": "📱 Telefon raqamingizni ulashing:",
        "ask_district": "🏘 Manzilingiz — qaysi hududda?",
        "registered": "✅ Ro'yxatdan o'tdingiz!\n\nHududingiz: <b>{district}</b>\nMinimal zakaz: <b>{min_sum:,} so'm</b>",
        "main_menu": "🏪 <b>Jaxon Market</b>\n\nNima qilmoqchisiz?",
        "catalog": "📦 Kategoriyani tanlang:",
        "products": "🛒 <b>{cat}</b> mahsulotlari:",
        "cart_empty": "🛒 Savat bo'sh.",
        "cart_title": "🛒 <b>Savatingiz:</b>\n\n{items}\n\n💰 Jami: <b>{total:,} so'm</b>",
        "cart_min_warn": "⚠️ {district} uchun minimal zakaz <b>{min:,} so'm</b>.\nYana <b>{diff:,} so'm</b>lik mahsulot qo'shing.",
        "added_to_cart": "✅ Savatga qo'shildi!",
        "choose_delivery": "🚚 Yetkazib berish turini tanlang:",
        "ask_address": "📍 Yetkazib berish manzilingizni yozing:",
        "order_confirm": "📋 <b>Zakaz tasdiqlash</b>\n\n{items}\n💰 Jami: <b>{total:,} so'm</b>\n🚚 Turi: <b>{dtype}</b>\n📍 Manzil: <b>{address}</b>\n📱 Telefon: <b>{phone}</b>\n\n✅ Tasdiqlaysizmi?",
        "order_placed": "🎉 Zakaz #{order_id} qabul qilindi!\n\nHolat: ⏳ Ko'rib chiqilmoqda",
        "order_cancelled": "❌ Zakaz bekor qilindi.",
        "closed": "🕐 Hozir ish vaqti emas.\n\nBiz <b>08:00–21:00</b> gacha ishlaymiz.",
        "about": "🏪 <b>Jaxon Market</b>\n\nAlijon mahallasi va Buston hududi uchun qulay onlayn oziq-ovqat do'koni.\n\n🕐 Ish vaqti: 08:00 – 21:00\n📦 Minimal zakaz:\n  • Alijon MFY: 20 000 so'm\n  • Buston hududi: 40 000 so'm\n\n⚠️ Yetkazilgan mahsulot qaytarib olinmaydi",
        "partnership": "🤝 <b>Hamkorlik</b>\n\nAdminimizga murojaat qiling.\n\n📩 Admin: @jaxon_market_admin",
        "aksiya": "🎁 <b>Aksiyalar</b>\n\nHozircha yangi aksiyalar yo'q.",
        "ask_review_rating": "⭐ Xizmatimizni baholang (1-5):",
        "ask_review_text": "✍️ Izohingizni yozing:",
        "review_sent": "✅ Izohingiz uchun rahmat!",
        "search_ask": "🔍 Mahsulot nomini yozing:",
        "search_empty": "❌ Hech narsa topilmadi.",
        "repeat_order": "🔁 Oldingi zakazingiz savatchaga solinmoqda...",
        "no_prev_order": "❌ Oldingi zakaz topilmadi.",
        "warning_return": "⚠️ <b>Diqqat!</b>\n\nYetkazib berilgan mahsulotlar qaytarib olinmaydi.",
    },
    "ru": {
        "welcome": "🌟 Добро пожаловать в <b>Jaxon Market</b>!",
        "choose_lang": "🌐 Tilni tanlang / Выберите язык:",
        "ask_phone": "📱 Поделитесь номером телефона:",
        "ask_district": "🏘 Укажите ваш район:",
        "registered": "✅ Вы зарегистрированы!\n\nРайон: <b>{district}</b>\nМинимальный заказ: <b>{min_sum:,} сум</b>",
        "main_menu": "🏪 <b>Jaxon Market</b>\n\nЧто хотите сделать?",
        "catalog": "📦 Выберите категорию:",
        "products": "🛒 Товары <b>{cat}</b>:",
        "cart_empty": "🛒 Корзина пуста.",
        "cart_title": "🛒 <b>Ваша корзина:</b>\n\n{items}\n\n💰 Итого: <b>{total:,} сум</b>",
        "cart_min_warn": "⚠️ Минимальный заказ для {district}: <b>{min:,} сум</b>.\nДобавьте ещё на <b>{diff:,} сум</b>.",
        "added_to_cart": "✅ Добавлено в корзину!",
        "choose_delivery": "🚚 Выберите тип доставки:",
        "ask_address": "📍 Напишите адрес доставки:",
        "order_confirm": "📋 <b>Подтверждение заказа</b>\n\n{items}\n💰 Итого: <b>{total:,} сум</b>\n🚚 Тип: <b>{dtype}</b>\n📍 Адрес: <b>{address}</b>\n📱 Телефон: <b>{phone}</b>\n\n✅ Подтвердить?",
        "order_placed": "🎉 Заказ #{order_id} принят!\n\nСтатус: ⏳ На рассмотрении",
        "order_cancelled": "❌ Заказ отменён.",
        "closed": "🕐 Сейчас не рабочее время.\n\nМы работаем с <b>08:00 до 21:00</b>.",
        "about": "🏪 <b>Jaxon Market</b>\n\nУдобный онлайн-магазин продуктов для Alijon MFY и Buston.\n\n🕐 Время работы: 08:00 – 21:00\n📦 Минимальный заказ:\n  • Alijon MFY: 20 000 сум\n  • Buston: 40 000 сум\n\n⚠️ Доставленный товар возврату не подлежит",
        "partnership": "🤝 <b>Сотрудничество</b>\n\nОбратитесь к нашему администратору.\n\n📩 Admin: @jaxon_market_admin",
        "aksiya": "🎁 <b>Акции</b>\n\nПока акций нет.",
        "ask_review_rating": "⭐ Оцените наш сервис (1-5):",
        "ask_review_text": "✍️ Напишите отзыв:",
        "review_sent": "✅ Спасибо за отзыв!",
        "search_ask": "🔍 Введите название товара:",
        "search_empty": "❌ Ничего не найдено.",
        "repeat_order": "🔁 Загружаю ваш предыдущий заказ...",
        "no_prev_order": "❌ Предыдущий заказ не найден.",
        "warning_return": "⚠️ <b>Внимание!</b>\n\nДоставленные товары возврату не подлежат.",
    }
}

STATUS_LABELS = {
    "new": {"uz": "⏳ Ko'rib chiqilmoqda", "ru": "⏳ На рассмотрении"},
    "accepted": {"uz": "✅ Qabul qilindi", "ru": "✅ Принят"},
    "packing": {"uz": "📦 Yig'ilmoqda", "ru": "📦 Комплектуется"},
    "delivery": {"uz": "🚴 Yo'lda", "ru": "🚴 В пути"},
    "done": {"uz": "✅ Yetkazildi", "ru": "✅ Доставлен"},
    "cancelled": {"uz": "❌ Bekor qilindi", "ru": "❌ Отменён"},
}
def main_menu_kb(lang):
    if lang == "uz":
        keys = [
            ["🛒 Katalog", "🔍 Qidirish"],
            ["🛒 Savat", "🔁 Oxirgi zakaz"],
            ["🎁 Aksiyalar", "⭐ Izoh qoldirish"],
            ["ℹ️ Biz haqimizda", "🤝 Hamkorlik"],
        ]
    else:
        keys = [
            ["🛒 Каталог", "🔍 Поиск"],
            ["🛒 Корзина", "🔁 Повторить заказ"],
            ["🎁 Акции", "⭐ Оставить отзыв"],
            ["ℹ️ О нас", "🤝 Сотрудничество"],
        ]
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=k) for k in row] for row in keys],
        resize_keyboard=True
    )

def lang_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz"),
         InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")]
    ])

def district_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏘 Alijon MFY", callback_data="district_Alijon MFY")],
        [InlineKeyboardButton(text="🏙 Buston hududi", callback_data="district_Buston hududi")],
    ])

def phone_kb(lang):
    label = "📱 Raqamni ulashish" if lang == "uz" else "📱 Поделиться номером"
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=label, request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )

def cart_kb(lang):
    if lang == "uz":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Zakaz berish", callback_data="checkout")],
            [InlineKeyboardButton(text="🗑 Savatni tozalash", callback_data="clear_cart")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")],
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Оформить заказ", callback_data="checkout")],
            [InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="clear_cart")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")],
        ])

def delivery_kb(lang):
    if lang == "uz":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚚 Yetkazib berish", callback_data="del_delivery")],
            [InlineKeyboardButton(text="🏪 O'zim olib ketaman", callback_data="del_pickup")],
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚚 Доставка", callback_data="del_delivery")],
            [InlineKeyboardButton(text="🏪 Самовывоз", callback_data="del_pickup")],
        ])

def confirm_kb(lang):
    if lang == "uz":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="order_confirm")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="order_cancel")],
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="order_confirm")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="order_cancel")],
        ])

def rating_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{'⭐'*i}", callback_data=f"rating_{i}") for i in range(1, 6)]
    ])

def cart_total(cart: dict) -> int:
    return sum(v["price"] * v["qty"] for v in cart.values())

def cart_text(cart: dict, lang: str) -> str:
    lines = []
    for i, (pid, v) in enumerate(cart.items(), 1):
        name = v["name_uz"] if lang == "uz" else v["name_ru"]
        lines.append(f"{i}. {name} x{v['qty']} = {v['price']*v['qty']:,} so'm")
    return "\n".join(lines)
    async def categories_kb(lang):
    cats = await db.get_categories()
    buttons = []
    for c in cats:
        name = c["name_uz"] if lang == "uz" else c["name_ru"]
        buttons.append([InlineKeyboardButton(
            text=f"{c['emoji']} {name}",
            callback_data=f"cat_{c['id']}"
        )])
    back = "🔙 Orqaga" if lang == "uz" else "🔙 Назад"
    buttons.append([InlineKeyboardButton(text=back, callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def products_kb(cat_id, lang, cart: dict):
    prods = await db.get_products(cat_id)
    buttons = []
    for p in prods:
        name = p["name_uz"] if lang == "uz" else p["name_ru"]
        unit = p["unit_uz"] if lang == "uz" else p["unit_ru"]
        qty = cart.get(str(p["id"]), {}).get("qty", 0)
        qty_text = f" ({qty} {unit})" if qty > 0 else ""
        buttons.append([InlineKeyboardButton(
            text=f"{name} — {p['price']:,} so'm{qty_text}",
            callback_data=f"prod_info_{p['id']}"
        )])
    back = "🔙 Kategoriyalar" if lang == "uz" else "🔙 Категории"
    buttons.append([InlineKeyboardButton(text=back, callback_data="back_cats")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def product_detail_kb(prod_id, lang, qty):
    row1 = [
        InlineKeyboardButton(text="➖", callback_data=f"qty_minus_{prod_id}"),
        InlineKeyboardButton(text=str(qty), callback_data="qty_noop"),
        InlineKeyboardButton(text="➕", callback_data=f"qty_plus_{prod_id}"),
    ]
    row2 = [InlineKeyboardButton(text="🛒 Savatga" if lang == "uz" else "🛒 В корзину", callback_data=f"add_cart_{prod_id}")]
    row3 = [InlineKeyboardButton(text="🔙 Orqaga" if lang == "uz" else "🔙 Назад", callback_data=f"back_prod_{prod_id}")]
    return InlineKeyboardMarkup(inline_keyboard=[row1, row2, row3])

def order_status_kb(order_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Qabul", callback_data=f"status_{order_id}_accepted"),
         InlineKeyboardButton(text="📦 Yig'ilmoqda", callback_data=f"status_{order_id}_packing")],
        [InlineKeyboardButton(text="🚴 Yo'lda", callback_data=f"status_{order_id}_delivery"),
         InlineKeyboardButton(text="✅ Yetkazildi", callback_data=f"status_{order_id}_done")],
        [InlineKeyboardButton(text="❌ Bekor", callback_data=f"status_{order_id}_cancelled")],
    ])

def admin_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Mijozlar soni", callback_data="admin_users"),
         InlineKeyboardButton(text="📊 Haftalik savdo", callback_data="admin_weekly")],
        [InlineKeyboardButton(text="🏆 TOP xaridorlar", callback_data="admin_top"),
         InlineKeyboardButton(text="📋 Zakazlar", callback_data="admin_orders")],
        [InlineKeyboardButton(text="📦 Mahsulotlar", callback_data="admin_products"),
         InlineKeyboardButton(text="💬 Izohlar", callback_data="admin_reviews")],
        [InlineKeyboardButton(text="📢 Aksiya yuborish", callback_data="admin_send_akciya"),
         InlineKeyboardButton(text="📣 Xabar yuborish", callback_data="admin_broadcast")],
    ])

def admin_products_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Kategoriya qo'shish", callback_data="admin_add_cat")],
        [InlineKeyboardButton(text="🗑 Kategoriya o'chirish", callback_data="admin_del_cat")],
        [InlineKeyboardButton(text="➕ Mahsulot qo'shish", callback_data="admin_add_prod")],
        [InlineKeyboardButton(text="🗑 Mahsulot o'chirish", callback_data="admin_del_prod")],
        [InlineKeyboardButton(text="💰 Narx o'zgartirish", callback_data="admin_update_price")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")],
    ])

def format_order_for_admin(order, user) -> str:
    items = json.loads(order["items"])
    items_text = ""
    for i, item in enumerate(items, 1):
        items_text += f"{i}. {item['name_uz']} x{item['qty']} = {item['price']*item['qty']:,} so'm\n"
    dtype = "🚚 Yetkazib berish" if order["delivery_type"] == "delivery" else "🏪 O'zim oladi"
    return (
        f"🆕 <b>Yangi zakaz #{order['id']}</b>\n\n"
        f"👤 Mijoz: {user['name'] if user else 'Noma\\'lum'}\n"
        f"📱 Telefon: <code>{order['phone']}</code>\n"
        f"🏘 Hudud: {order['district']}\n"
        f"🚚 Turi: {dtype}\n"
        f"📍 Manzil: {order['address']}\n\n"
        f"🛒 <b>Mahsulotlar:</b>\n{items_text}\n"
        f"💰 Jami: <b>{order['total']:,} so'm</b>\n"
        f"⚠️ Yetkazilgan mahsulot qaytarib olinmaydi!"
    )
