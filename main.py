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

# ══════════════════════════════════════════
# STATES
# ══════════════════════════════════════════
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

# ══════════════════════════════════════════
# TEXTS
# ══════════════════════════════════════════
T = {
    "uz": {
        "welcome": "🌟 <b>Jaxon Market</b>ga xush kelibsiz!\n\nMahalla va telefon raqamingizni kiritib, xarid qilishni boshlang.",
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
        "order_confirm": (
            "📋 <b>Zakaz tasdiqlash</b>\n\n"
            "{items}\n"
            "💰 Jami: <b>{total:,} so'm</b>\n"
            "🚚 Turi: <b>{dtype}</b>\n"
            "📍 Manzil: <b>{address}</b>\n"
            "📱 Telefon: <b>{phone}</b>\n\n"
            "✅ Tasdiqlaysizmi?"
        ),
        "order_placed": "🎉 Zakaz #{order_id} qabul qilindi!\n\nHolat: ⏳ Ko'rib chiqilmoqda\nXabar bering, tez yetkazamiz!",
        "order_cancelled": "❌ Zakaz bekor qilindi.",
        "closed": "🕐 Hozir ish vaqti emas.\n\nBiz <b>08:00–21:00</b> gacha ishlaymiz.\nErtaga keling! 😊",
        "about": (
            "🏪 <b>Jaxon Market</b>\n\n"
            "Alijon mahallasi va Buston hududi uchun\n"
            "qulay onlayn oziq-ovqat do'koni.\n\n"
            "🕐 Ish vaqti: 08:00 – 21:00\n"
            "📦 Minimal zakaz:\n"
            "  • Alijon MFY: 20 000 so'm\n"
            "  • Buston hududi: 40 000 so'm\n\n"
            "⚠️ Yetkazilgan mahsulot qaytarib olinmaydi\n"
            "(buzilmagan, achimaganligini tekshiring)\n\n"
            "📞 Aloqa uchun admin bilan bog'laning."
        ),
        "partnership": (
            "🤝 <b>Hamkorlik</b>\n\n"
            "Jaxon Market bilan hamkorlik qilmoqchimisiz?\n\n"
            "Mahsulotlaringizni bizda sotishni xohlasangiz\n"
            "yoki boshqa takliflaringiz bo'lsa,\n"
            "adminimizga murojaat qiling.\n\n"
            "📩 Admin: @jaxon_market_admin"
        ),
        "aksiya": "🎁 <b>Aksiyalar</b>\n\nHozircha yangi aksiyalar yo'q.\nKuzatib boring — tez orada bo'ladi! 🔥",
        "ask_review_rating": "⭐ Xizmatimizni baholang (1-5):",
        "ask_review_text": "✍️ Izohingizni yozing:",
        "review_sent": "✅ Izohingiz uchun rahmat!",
        "search_ask": "🔍 Mahsulot nomini yozing:",
        "search_empty": "❌ Hech narsa topilmadi.",
        "repeat_order": "🔁 Oldingi zakazingiz savatchaga solinmoqda...",
        "no_prev_order": "❌ Oldingi zakaz topilmadi.",
        "status_new": "⏳ Ko'rib chiqilmoqda",
        "status_accepted": "✅ Qabul qilindi",
        "status_packing": "📦 Yig'ilmoqda",
        "status_delivery": "🚴 Yo'lda",
        "status_done": "✅ Yetkazildi",
        "status_cancelled": "❌ Bekor qilindi",
        "warning_return": (
            "⚠️ <b>Diqqat!</b>\n\n"
            "Yetkazib berilgan mahsulotlar qaytarib olinmaydi.\n"
            "Zakaz berishdan oldin mahsulot tarkibini diqqat bilan ko'rib chiqing."
        ),
    },
    "ru": {
        "welcome": "🌟 Добро пожаловать в <b>Jaxon Market</b>!\n\nВведите адрес и номер телефона, чтобы начать покупки.",
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
        "order_confirm": (
            "📋 <b>Подтверждение заказа</b>\n\n"
            "{items}\n"
            "💰 Итого: <b>{total:,} сум</b>\n"
            "🚚 Тип: <b>{dtype}</b>\n"
            "📍 Адрес: <b>{address}</b>\n"
            "📱 Телефон: <b>{phone}</b>\n\n"
            "✅ Подтвердить?"
        ),
        "order_placed": "🎉 Заказ #{order_id} принят!\n\nСтатус: ⏳ На рассмотрении\nСкоро доставим!",
        "order_cancelled": "❌ Заказ отменён.",
        "closed": "🕐 Сейчас не рабочее время.\n\nМы работаем с <b>08:00 до 21:00</b>.\nПриходите завтра! 😊",
        "about": (
            "🏪 <b>Jaxon Market</b>\n\n"
            "Удобный онлайн-магазин продуктов\n"
            "для Alijon MFY и Buston.\n\n"
            "🕐 Время работы: 08:00 – 21:00\n"
            "📦 Минимальный заказ:\n"
            "  • Alijon MFY: 20 000 сум\n"
            "  • Buston: 40 000 сум\n\n"
            "⚠️ Доставленный товар возврату не подлежит\n"
            "(проверяйте при получении)\n\n"
            "📞 По вопросам — обратитесь к администратору."
        ),
        "partnership": (
            "🤝 <b>Сотрудничество</b>\n\n"
            "Хотите сотрудничать с Jaxon Market?\n\n"
            "Если хотите продавать свои товары у нас\n"
            "или есть другие предложения,\n"
            "обратитесь к нашему администратору.\n\n"
            "📩 Admin: @jaxon_market_admin"
        ),
        "aksiya": "🎁 <b>Акции</b>\n\nПока акций нет.\nСледите — скоро будет! 🔥",
        "ask_review_rating": "⭐ Оцените наш сервис (1-5):",
        "ask_review_text": "✍️ Напишите отзыв:",
        "review_sent": "✅ Спасибо за отзыв!",
        "search_ask": "🔍 Введите название товара:",
        "search_empty": "❌ Ничего не найдено.",
        "repeat_order": "🔁 Загружаю ваш предыдущий заказ...",
        "no_prev_order": "❌ Предыдущий заказ не найден.",
        "status_new": "⏳ На рассмотрении",
        "status_accepted": "✅ Принят",
        "status_packing": "📦 Комплектуется",
        "status_delivery": "🚴 В пути",
        "status_done": "✅ Доставлен",
        "status_cancelled": "❌ Отменён",
        "warning_return": (
            "⚠️ <b>Внимание!</b>\n\n"
            "Доставленные товары возврату не подлежат.\n"
            "Внимательно ознакомьтесь с составом заказа перед оформлением."
        ),
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

# ══════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════
def is_work_time():
    h = datetime.now().hour
    return WORK_START <= h < WORK_END

async def get_lang(user_id):
    user = await db.get_user(user_id)
    return user["lang"] if user else "uz"

def t(lang, key, **kwargs):
    text = T[lang].get(key, T["uz"].get(key, ""))
    return text.format(**kwargs) if kwargs else text

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
    minus = "➖"
    plus = "➕"
    cart_label = "🛒 Savatga" if lang == "uz" else "🛒 В корзину"
    back = "🔙 Orqaga" if lang == "uz" else "🔙 Назад"
    row1 = [
        InlineKeyboardButton(text=minus, callback_data=f"qty_minus_{prod_id}"),
        InlineKeyboardButton(text=str(qty), callback_data="qty_noop"),
        InlineKeyboardButton(text=plus, callback_data=f"qty_plus_{prod_id}"),
    ]
    row2 = [InlineKeyboardButton(text=cart_label, callback_data=f"add_cart_{prod_id}")]
    row3 = [InlineKeyboardButton(text=back, callback_data=f"back_prod_{prod_id}")]
    return InlineKeyboardMarkup(inline_keyboard=[row1, row2, row3])

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

def order_status_kb(order_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Qabul", callback_data=f"status_{order_id}_accepted"),
         InlineKeyboardButton(text="📦 Yig'ilmoqda", callback_data=f"status_{order_id}_packing")],
        [InlineKeyboardButton(text="🚴 Yo'lda", callback_data=f"status_{order_id}_delivery"),
         InlineKeyboardButton(text="✅ Yetkazildi", callback_data=f"status_{order_id}_done")],
        [InlineKeyboardButton(text="❌ Bekor", callback_data=f"status_{order_id}_cancelled")],
    ])

def rating_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{'⭐'*i}", callback_data=f"rating_{i}") for i in range(1, 6)]
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

def cart_total(cart: dict) -> int:
    return sum(v["price"] * v["qty"] for v in cart.values())

def cart_text(cart: dict, lang: str) -> str:
    lines = []
    for i, (pid, v) in enumerate(cart.items(), 1):
        name = v["name_uz"] if lang == "uz" else v["name_ru"]
        lines.append(f"{i}. {name} x{v['qty']} = {v['price']*v['qty']:,} so'm")
    return "\n".join(lines)

def format_order_for_admin(order, user) -> str:
    items = json.loads(order["items"])
    items_text = ""
    for i, item in enumerate(items, 1):
        items_text += f"{i}. {item['name_uz']} x{item['qty']} = {item['price']*item['qty']:,} so'm\n"
    dtype = "🚚 Yetkazib berish" if order["delivery_type"] == "delivery" else "🏪 O'zim oladi"
    return (
        f"🆕 <b>Yangi zakaz #{order['id']}</b>\n\n"
        f"👤 Mijoz: {user['name'] if user else 'Noma'lum'}\n"
        f"📱 Telefon: <code>{order['phone']}</code>\n"
        f"🏘 Hudud: {order['district']}\n"
        f"🚚 Turi: {dtype}\n"
        f"📍 Manzil: {order['address']}\n\n"
        f"🛒 <b>Mahsulotlar:</b>\n{items_text}\n"
        f"💰 Jami: <b>{order['total']:,} so'm</b>\n"
        f"⚠️ Yetkazilgan mahsulot qaytarib olinmaydi!"
    )

# ══════════════════════════════════════════
# REGISTRATION
# ══════════════════════════════════════════
@router.message(Command("start"))
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    user = await db.get_user(msg.from_user.id)
    if user:
        lang = user["lang"]
        await msg.answer(t(lang, "main_menu"), reply_markup=main_menu_kb(lang), parse_mode="HTML")
        return
    await msg.answer(t("uz", "choose_lang"), reply_markup=lang_kb(), parse_mode="HTML")
    await state.set_state(Reg.lang)

@router.callback_query(Reg.lang, F.data.startswith("lang_"))
async def reg_lang(cb: CallbackQuery, state: FSMContext):
    lang = cb.data.split("_")[1]
    await state.update_data(lang=lang)
    await cb.message.edit_text(t(lang, "ask_phone"), parse_mode="HTML")
    await cb.message.answer("👇", reply_markup=phone_kb(lang))
    await state.set_state(Reg.phone)

@router.message(Reg.phone, F.contact)
async def reg_phone(msg: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    phone = msg.contact.phone_number
    await state.update_data(phone=phone)
    await msg.answer(t(lang, "ask_district"),
                     reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
    await msg.answer("👇", reply_markup=district_kb())
    await state.set_state(Reg.district)

@router.callback_query(Reg.district, F.data.startswith("district_"))
async def reg_district(cb: CallbackQuery, state: FSMContext):
    district = cb.data[len("district_"):]
    data = await state.get_data()
    lang = data.get("lang", "uz")
    phone = data.get("phone", "")
    name = cb.from_user.full_name
    await db.save_user(cb.from_user.id, name, phone, district, lang)
    min_sum = DISTRICTS.get(district, 20000)
    await cb.message.edit_text(
        t(lang, "registered", district=district, min_sum=min_sum), parse_mode="HTML"
    )
    await cb.message.answer(t(lang, "warning_return"), parse_mode="HTML")
    await asyncio.sleep(1)
    await state.clear()
    await cb.message.answer(t(lang, "main_menu"), reply_markup=main_menu_kb(lang), parse_mode="HTML")

# ══════════════════════════════════════════
# MAIN MENU HANDLERS
# ══════════════════════════════════════════
@router.message(F.text.in_(["🛒 Katalog", "🛒 Каталог"]))
async def show_catalog(msg: Message, state: FSMContext):
    if not is_work_time():
        lang = await get_lang(msg.from_user.id)
        await msg.answer(t(lang, "closed"), parse_mode="HTML")
        return
    lang = await get_lang(msg.from_user.id)
    await state.set_state(Order.browsing)
    await msg.answer(t(lang, "catalog"), reply_markup=await categories_kb(lang), parse_mode="HTML")

@router.message(F.text.in_(["🔍 Qidirish", "🔍 Поиск"]))
async def search_start(msg: Message, state: FSMContext):
    lang = await get_lang(msg.from_user.id)
    await state.set_state(SearchSt.query)
    await msg.answer(t(lang, "search_ask"), parse_mode="HTML")

@router.message(SearchSt.query)
async def search_results(msg: Message, state: FSMContext):
    lang = await get_lang(msg.from_user.id)
    results = await db.search_products(msg.text)
    await state.clear()
    if not results:
        await msg.answer(t(lang, "search_empty"), parse_mode="HTML")
        return
    data = await state.get_data()
    cart = data.get("cart", {})
    buttons = []
    for p in results:
        name = p["name_uz"] if lang == "uz" else p["name_ru"]
        buttons.append([InlineKeyboardButton(
            text=f"{name} — {p['price']:,} so'm",
            callback_data=f"prod_info_{p['id']}"
        )])
    await msg.answer(
        f"🔍 {len(results)} ta natija:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )

@router.message(F.text.in_(["🛒 Savat", "🛒 Корзина"]))
async def show_cart(msg: Message, state: FSMContext):
    lang = await get_lang(msg.from_user.id)
    data = await state.get_data()
    cart = data.get("cart", {})
    if not cart:
        await msg.answer(t(lang, "cart_empty"), parse_mode="HTML")
        return
    total = cart_total(cart)
    items_text = cart_text(cart, lang)
    await msg.answer(
        t(lang, "cart_title", items=items_text, total=total),
        reply_markup=cart_kb(lang),
        parse_mode="HTML"
    )

@router.message(F.text.in_(["🎁 Aksiyalar", "🎁 Акции"]))
async def show_aksiya(msg: Message):
    lang = await get_lang(msg.from_user.id)
    await msg.answer(t(lang, "aksiya"), parse_mode="HTML")

@router.message(F.text.in_(["ℹ️ Biz haqimizda", "ℹ️ О нас"]))
async def show_about(msg: Message):
    lang = await get_lang(msg.from_user.id)
    await msg.answer(t(lang, "about"), parse_mode="HTML")

@router.message(F.text.in_(["🤝 Hamkorlik", "🤝 Сотрудничество"]))
async def show_partnership(msg: Message):
    lang = await get_lang(msg.from_user.id)
    await msg.answer(t(lang, "partnership"), parse_mode="HTML")

@router.message(F.text.in_(["⭐ Izoh qoldirish", "⭐ Оставить отзыв"]))
async def review_start(msg: Message, state: FSMContext):
    lang = await get_lang(msg.from_user.id)
    await state.set_state(ReviewSt.rating)
    await msg.answer(t(lang, "ask_review_rating"), reply_markup=rating_kb(), parse_mode="HTML")

@router.callback_query(ReviewSt.rating, F.data.startswith("rating_"))
async def review_rating(cb: CallbackQuery, state: FSMContext):
    rating = int(cb.data.split("_")[1])
    await state.update_data(rating=rating)
    lang = await get_lang(cb.from_user.id)
    await cb.message.edit_text(t(lang, "ask_review_text"), parse_mode="HTML")
    await state.set_state(ReviewSt.text)

@router.message(ReviewSt.text)
async def review_text(msg: Message, state: FSMContext):
    data = await state.get_data()
    rating = data.get("rating", 5)
    lang = await get_lang(msg.from_user.id)
    await db.add_review(msg.from_user.id, msg.from_user.full_name, msg.text, rating)
    await state.clear()
    await msg.answer(t(lang, "review_sent"), parse_mode="HTML")

@router.message(F.text.in_(["🔁 Oxirgi zakaz", "🔁 Повторить заказ"]))
async def repeat_order(msg: Message, state: FSMContext):
    lang = await get_lang(msg.from_user.id)
    last_order = await db.get_user_last_order(msg.from_user.id)
    if not last_order:
        await msg.answer(t(lang, "no_prev_order"), parse_mode="HTML")
        return
    items = json.loads(last_order["items"])
    cart = {}
    for item in items:
        cart[str(item["id"])] = item
    await state.update_data(cart=cart)
    await msg.answer(t(lang, "repeat_order"), parse_mode="HTML")
    total = cart_total(cart)
    items_text = cart_text(cart, lang)
    await msg.answer(
        t(lang, "cart_title", items=items_text, total=total),
        reply_markup=cart_kb(lang),
        parse_mode="HTML"
    )

# ══════════════════════════════════════════
# CATALOG CALLBACKS
# ══════════════════════════════════════════
@router.callback_query(F.data.startswith("cat_"))
async def show_products(cb: CallbackQuery, state: FSMContext):
    cat_id = int(cb.data.split("_")[1])
    lang = await get_lang(cb.from_user.id)
    data = await state.get_data()
    cart = data.get("cart", {})
    await state.update_data(current_cat=cat_id)
    cats = await db.get_categories()
    cat_name = next((c["name_uz"] if lang == "uz" else c["name_ru"] for c in cats if c["id"] == cat_id), "")
    await cb.message.edit_text(
        t(lang, "products", cat=cat_name),
        reply_markup=await products_kb(cat_id, lang, cart),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("prod_info_"))
async def show_product_detail(cb: CallbackQuery, state: FSMContext):
    prod_id = int(cb.data.split("_")[2])
    lang = await get_lang(cb.from_user.id)
    data = await state.get_data()
    cart = data.get("cart", {})
    qty = cart.get(str(prod_id), {}).get("qty", 1)
    prod = await db.get_product(prod_id)
    if not prod:
        await cb.answer("Mahsulot topilmadi")
        return
    name = prod["name_uz"] if lang == "uz" else prod["name_ru"]
    unit = prod["unit_uz"] if lang == "uz" else prod["unit_ru"]
    text = f"<b>{name}</b>\n💰 {prod['price']:,} so'm / {unit}"
    await cb.message.edit_text(
        text,
        reply_markup=product_detail_kb(prod_id, lang, qty),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("qty_plus_"))
async def qty_plus(cb: CallbackQuery, state: FSMContext):
    prod_id = int(cb.data.split("_")[2])
    data = await state.get_data()
    cart = data.get("cart", {})
    qty = cart.get(str(prod_id), {}).get("qty", 0) + 1
    lang = await get_lang(cb.from_user.id)
    prod = await db.get_product(prod_id)
    if prod:
        cart[str(prod_id)] = {
            "id": prod_id,
            "name_uz": prod["name_uz"],
            "name_ru": prod["name_ru"],
            "price": prod["price"],
            "qty": qty
        }
    await state.update_data(cart=cart)
    await cb.message.edit_reply_markup(reply_markup=product_detail_kb(prod_id, lang, qty))

@router.callback_query(F.data.startswith("qty_minus_"))
async def qty_minus(cb: CallbackQuery, state: FSMContext):
    prod_id = int(cb.data.split("_")[2])
    data = await state.get_data()
    cart = data.get("cart", {})
    qty = max(1, cart.get(str(prod_id), {}).get("qty", 1) - 1)
    lang = await get_lang(cb.from_user.id)
    if str(prod_id) in cart:
        cart[str(prod_id)]["qty"] = qty
    await state.update_data(cart=cart)
    await cb.message.edit_reply_markup(reply_markup=product_detail_kb(prod_id, lang, qty))

@router.callback_query(F.data == "qty_noop")
async def qty_noop(cb: CallbackQuery):
    await cb.answer()

@router.callback_query(F.data.startswith("add_cart_"))
async def add_to_cart(cb: CallbackQuery, state: FSMContext):
    prod_id = int(cb.data.split("_")[2])
    lang = await get_lang(cb.from_user.id)
    data = await state.get_data()
    cart = data.get("cart", {})
    prod = await db.get_product(prod_id)
    if prod:
        qty = cart.get(str(prod_id), {}).get("qty", 1)
        cart[str(prod_id)] = {
            "id": prod_id,
            "name_uz": prod["name_uz"],
            "name_ru": prod["name_ru"],
            "price": prod["price"],
            "qty": qty
        }
    await state.update_data(cart=cart)
    await cb.answer(t(lang, "added_to_cart"))

@router.callback_query(F.data.startswith("back_prod_"))
async def back_to_products(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(cb.from_user.id)
    data = await state.get_data()
    cart = data.get("cart", {})
    cat_id = data.get("current_cat")
    if cat_id:
        cats = await db.get_categories()
        cat_name = next((c["name_uz"] if lang == "uz" else c["name_ru"] for c in cats if c["id"] == cat_id), "")
        await cb.message.edit_text(
            t(lang, "products", cat=cat_name),
            reply_markup=await products_kb(cat_id, lang, cart),
            parse_mode="HTML"
        )
    else:
        await cb.message.edit_text(t(lang, "catalog"), reply_markup=await categories_kb(lang), parse_mode="HTML")

@router.callback_query(F.data == "back_cats")
async def back_to_cats(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(cb.from_user.id)
    await cb.message.edit_text(t(lang, "catalog"), reply_markup=await categories_kb(lang), parse_mode="HTML")

@router.callback_query(F.data == "back_main")
async def back_to_main(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(cb.from_user.id)
    await cb.message.delete()

# ══════════════════════════════════════════
# CHECKOUT
# ══════════════════════════════════════════
@router.callback_query(F.data == "checkout")
async def checkout(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(cb.from_user.id)
    data = await state.get_data()
    cart = data.get("cart", {})
    if not cart:
        await cb.answer(t(lang, "cart_empty"))
        return
    user = await db.get_user(cb.from_user.id)
    district = user["district"] if user else "Alijon MFY"
    min_sum = DISTRICTS.get(district, MIN_ALIJON)
    total = cart_total(cart)
    if total < min_sum:
        diff = min_sum - total
        await cb.answer(t(lang, "cart_min_warn", district=district, min=min_sum, diff=diff), show_alert=True)
        return
    await cb.message.edit_text(t(lang, "choose_delivery"), reply_markup=delivery_kb(lang), parse_mode="HTML")
    await state.set_state(Order.delivery)

@router.callback_query(Order.delivery, F.data.startswith("del_"))
async def choose_delivery(cb: CallbackQuery, state: FSMContext):
    delivery_type = cb.data.split("_")[1]
    lang = await get_lang(cb.from_user.id)
    await state.update_data(delivery_type=delivery_type)
    if delivery_type == "pickup":
        await state.update_data(address="O'zim olib ketaman")
        await proceed_to_confirm(cb, state, lang)
    else:
        await cb.message.edit_text(t(lang, "ask_address"), parse_mode="HTML")
        await state.set_state(Order.address)

@router.message(Order.address)
async def get_address(msg: Message, state: FSMContext):
    lang = await get_lang(msg.from_user.id)
    await state.update_data(address=msg.text)
    await proceed_to_confirm_msg(msg, state, lang)

async def proceed_to_confirm(cb: CallbackQuery, state: FSMContext, lang: str):
    data = await state.get_data()
    cart = data.get("cart", {})
    user = await db.get_user(cb.from_user.id)
    phone = user["phone"] if user else ""
    total = cart_total(cart)
    items_text = cart_text(cart, lang)
    dtype = "🚚 Yetkazib berish" if data.get("delivery_type") == "delivery" else "🏪 O'zim olib ketaman"
    await cb.message.edit_text(
        t(lang, "order_confirm",
          items=items_text, total=total,
          dtype=dtype, address=data.get("address", ""),
          phone=phone),
        reply_markup=confirm_kb(lang),
        parse_mode="HTML"
    )
    await state.set_state(Order.confirm)

async def proceed_to_confirm_msg(msg: Message, state: FSMContext, lang: str):
    data = await state.get_data()
    cart = data.get("cart", {})
    user = await db.get_user(msg.from_user.id)
    phone = user["phone"] if user else ""
    total = cart_total(cart)
    items_text = cart_text(cart, lang)
    dtype = "🚚 Yetkazib berish" if data.get("delivery_type") == "delivery" else "🏪 O'zim olib ketaman"
    await msg.answer(
        t(lang, "order_confirm",
          items=items_text, total=total,
          dtype=dtype, address=data.get("address", ""),
          phone=phone),
        reply_markup=confirm_kb(lang),
        parse_mode="HTML"
    )
    await state.set_state(Order.confirm)

@router.callback_query(Order.confirm, F.data == "order_confirm")
async def confirm_order(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(cb.from_user.id)
    data = await state.get_data()
    cart = data.get("cart", {})
    user = await db.get_user(cb.from_user.id)
    phone = user["phone"] if user else ""
    district = user["district"] if user else ""
    items_list = [
        {"id": int(k), "name_uz": v["name_uz"], "name_ru": v["name_ru"],
         "price": v["price"], "qty": v["qty"]}
        for k, v in cart.items()
    ]
    total = cart_total(cart)
    order_id = await db.create_order(
        cb.from_user.id, phone, district,
        data.get("delivery_type", "delivery"),
        data.get("address", ""),
        items_list, total
    )
    await state.update_data(cart={})
    await state.set_state(None)
    await cb.message.edit_text(
        t(lang, "order_placed", order_id=order_id), parse_mode="HTML"
    )
    order = await db.get_order(order_id)
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                format_order_for_admin(order, user),
                reply_markup=order_status_kb(order_id),
                parse_mode="HTML"
            )
        except Exception:
            pass

@router.callback_query(Order.confirm, F.data == "order_cancel")
async def cancel_order(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(cb.from_user.id)
    await state.clear()
    await cb.message.edit_text(t(lang, "order_cancelled"), parse_mode="HTML")

@router.callback_query(F.data == "clear_cart")
async def clear_cart(cb: CallbackQuery, state: FSMContext):
    await state.update_data(cart={})
    lang = await get_lang(cb.from_user.id)
    await cb.message.edit_text(t(lang, "cart_empty"), parse_mode="HTML")

# ══════════════════════════════════════════
# ORDER STATUS (ADMIN)
# ══════════════════════════════════════════
@router.callback_query(F.data.startswith("status_"))
async def update_order_status(cb: CallbackQuery):
    parts = cb.data.split("_")
    order_id = int(parts[1])
    status = parts[2]
    await db.update_order_status(order_id, status)
    order = await db.get_order(order_id)
    user = await db.get_user(order["user_id"]) if order else None
    label_uz = STATUS_LABELS.get(status, {}).get("uz", status)
    label_ru = STATUS_LABELS.get(status, {}).get("ru", status)
    if user:
        lang = user["lang"]
        label = label_uz if lang == "uz" else label_ru
        try:
            await bot.send_message(
                user["id"],
                f"📦 Zakaz #{order_id} holati yangilandi:\n<b>{label}</b>",
                parse_mode="HTML"
            )
        except Exception:
            pass
    await cb.answer(f"Status: {label_uz}")
    await cb.message.edit_reply_markup(reply_markup=order_status_kb(order_id))

# ══════════════════════════════════════════
# ADMIN PANEL
# ══════════════════════════════════════════
@router.message(Command("admin"))
async def admin_panel(msg: Message, state: FSMContext):
    if msg.from_user.id not in ADMIN_IDS:
        return
    await state.set_state(AdminSt.main)
    await msg.answer("🔧 Admin panel:", reply_markup=admin_main_kb())

@router.callback_query(AdminSt.main, F.data == "admin_users")
async def admin_users(cb: CallbackQuery):
    count = await db.get_total_users_count()
    await cb.answer(f"👥 Jami foydalanuvchilar: {count}", show_alert=True)

@router.callback_query(AdminSt.main, F.data == "admin_weekly")
async def admin_weekly(cb: CallbackQuery):
    sales = await db.get_weekly_sales()
    await cb.answer(
        f"📊 Haftalik savdo:\n💰 {sales['total']:,} so'm\n📦 {sales['count']} zakaz",
        show_alert=True
    )

@router.callback_query(AdminSt.main, F.data == "admin_top")
async def admin_top(cb: CallbackQuery):
    top = await db.get_weekly_top()
    if not top:
        await cb.answer("Hozircha ma'lumot yo'q", show_alert=True)
        return
    text = "🏆 TOP xaridorlar:\n\n"
    for i, row in enumerate(top, 1):
        text += f"{i}. {row['name']} — {row['order_count']} zakaz ({row['total_sum']:,} so'm)\n"
    await cb.message.answer(text)

@router.callback_query(AdminSt.main, F.data == "admin_orders")
async def admin_orders(cb: CallbackQuery):
    orders = await db.get_orders(status="new")
    if not orders:
        await cb.answer("Yangi zakazlar yo'q", show_alert=True)
        return
    for order in orders[:10]:
        user = await db.get_user(order["user_id"])
        await cb.message.answer(
            format_order_for_admin(order, user),
            reply_markup=order_status_kb(order["id"]),
            parse_mode="HTML"
        )

@router.callback_query(AdminSt.main, F.data == "admin_reviews")
async def admin_reviews(cb: CallbackQuery):
    reviews = await db.get_reviews()
    if not reviews:
        await cb.answer("Izohlar yo'q", show_alert=True)
        return
    text = "💬 So'nggi izohlar:\n\n"
    for r in reviews[:10]:
        text += f"⭐{'⭐'*r['rating']} {r['user_name']}: {r['text']}\n\n"
    await cb.message.answer(text)

@router.callback_query(AdminSt.main, F.data == "admin_products")
async def admin_products(cb: CallbackQuery):
    await cb.message.edit_text("📦 Mahsulotlar boshqaruvi:", reply_markup=admin_products_kb())

@router.callback_query(F.data == "admin_back")
async def admin_back(cb: CallbackQuery):
    await cb.message.edit_text("🔧 Admin panel:", reply_markup=admin_main_kb())

@router.callback_query(F.data == "admin_add_cat")
async def admin_add_cat_start(cb: CallbackQuery, state: FSMContext):
    await cb.message.answer("Kategoriya nomini O'zbekcha kiriting:")
    await state.set_state(AdminSt.add_cat_uz)

@router.message(AdminSt.add_cat_uz)
async def admin_add_cat_uz(msg: Message, state: FSMContext):
    await state.update_data(cat_name_uz=msg.text)
    await msg.answer("Kategoriya nomini Ruscha kiriting:")
    await state.set_state(AdminSt.add_cat_ru)

@router.message(AdminSt.add_cat_ru)
async def admin_add_cat_ru(msg: Message, state: FSMContext):
    await state.update_data(cat_name_ru=msg.text)
    await msg.answer("Emoji kiriting (masalan: 🥩):")
    await state.set_state(AdminSt.add_cat_emoji)

@router.message(AdminSt.add_cat_emoji)
async def admin_add_cat_emoji(msg: Message, state: FSMContext):
    data = await state.get_data()
    await db.add_category(data["cat_name_uz"], data["cat_name_ru"], msg.text)
    await state.set_state(AdminSt.main)
    await msg.answer("✅ Kategoriya qo'shildi!", reply_markup=admin_main_kb())

@router.callback_query(F.data == "admin_del_cat")
async def admin_del_cat_start(cb: CallbackQuery, state: FSMContext):
    cats = await db.get_categories()
    buttons = [[InlineKeyboardButton(
        text=f"{c['emoji']} {c['name_uz']}",
        callback_data=f"delcat_{c['id']}"
    )] for c in cats]
    await cb.message.answer("O'chirish uchun kategoriyani tanlang:",
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await state.set_state(AdminSt.del_cat)

@router.callback_query(AdminSt.del_cat, F.data.startswith("delcat_"))
async def admin_del_cat(cb: CallbackQuery, state: FSMContext):
    cat_id = int(cb.data.split("_")[1])
    await db.delete_category(cat_id)
    await state.set_state(AdminSt.main)
    await cb.message.edit_text("✅ Kategoriya o'chirildi!")

@router.callback_query(F.data == "admin_add_prod")
async def admin_add_prod_start(cb: CallbackQuery, state: FSMContext):
    cats = await db.get_categories()
    buttons = [[InlineKeyboardButton(
        text=f"{c['emoji']} {c['name_uz']}",
        callback_data=f"prodcat_{c['id']}"
    )] for c in cats]
    await cb.message.answer("Kategoriyani tanlang:",
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await state.set_state(AdminSt.add_prod_cat)

@router.callback_query(AdminSt.add_prod_cat, F.data.startswith("prodcat_"))
async def admin_add_prod_cat(cb: CallbackQuery, state: FSMContext):
    cat_id = int(cb.data.split("_")[1])
    await state.update_data(prod_cat_id=cat_id)
    await cb.message.answer("Mahsulot nomini O'zbekcha kiriting:")
    await state.set_state(AdminSt.add_prod_name_uz)

@router.message(AdminSt.add_prod_name_uz)
async def admin_add_prod_name_uz(msg: Message, state: FSMContext):
    await state.update_data(prod_name_uz=msg.text)
    await msg.answer("Mahsulot nomini Ruscha kiriting:")
    await state.set_state(AdminSt.add_prod_name_ru)

@router.message(AdminSt.add_prod_name_ru)
async def admin_add_prod_name_ru(msg: Message, state: FSMContext):
    await state.update_data(prod_name_ru=msg.text)
    await msg.answer("Narxini kiriting (so'mda):")
    await state.set_state(AdminSt.add_prod_price)

@router.message(AdminSt.add_prod_price)
async def admin_add_prod_price(msg: Message, state: FSMContext):
    try:
        price = int(msg.text.replace(" ", "").replace(",", ""))
        await state.update_data(prod_price=price)
        await msg.answer("O'lchov birligini kiriting (masalan: kg, dona, litr):")
        await state.set_state(AdminSt.add_prod_unit)
    except ValueError:
        await msg.answer("❌ Narxni to'g'ri kiriting (faqat raqam):")

@router.message(AdminSt.add_prod_unit)
async def admin_add_prod_unit(msg: Message, state: FSMContext):
    data = await state.get_data()
    await db.add_product(
        data["prod_cat_id"], data["prod_name_uz"], data["prod_name_ru"],
        data["prod_price"], msg.text, msg.text
    )
    await state.set_state(AdminSt.main)
    await msg.answer("✅ Mahsulot qo'shildi!", reply_markup=admin_main_kb())

@router.callback_query(F.data == "admin_del_prod")
async def admin_del_prod_start(cb: CallbackQuery, state: FSMContext):
    cats = await db.get_categories()
    buttons = [[InlineKeyboardButton(
        text=f"{c['emoji']} {c['name_uz']}",
        callback_data=f"delprodcat_{c['id']}"
    )] for c in cats]
    await cb.message.answer("Kategoriyani tanlang:",
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await state.set_state(AdminSt.del_prod)

@router.callback_query(AdminSt.del_prod, F.data.startswith("delprodcat_"))
async def admin_del_prod_cat(cb: CallbackQuery, state: FSMContext):
    cat_id = int(cb.data.split("_")[1])
    prods = await db.get_products(cat_id)
    buttons = [[InlineKeyboardButton(
        text=p["name_uz"],
        callback_data=f"delprod_{p['id']}"
    )] for p in prods]
    await cb.message.edit_text("Mahsulotni tanlang:",
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(AdminSt.del_prod, F.data.startswith("delprod_"))
async def admin_del_prod(cb: CallbackQuery, state: FSMContext):
    prod_id = int(cb.data.split("_")[1])
    await db.delete_product(prod_id)
    await state.set_state(AdminSt.main)
    await cb.message.edit_text("✅ Mahsulot o'chirildi!")

@router.callback_query(F.data == "admin_update_price")
async def admin_update_price_start(cb: CallbackQuery, state: FSMContext):
    cats = await db.get_categories()
    buttons = [[InlineKeyboardButton(
        text=f"{c['emoji']} {c['name_uz']}",
        callback_data=f"upcat_{c['id']}"
    )] for c in cats]
    await cb.message.answer("Kategoriyani tanlang:",
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await state.set_state(AdminSt.update_price_prod)

@router.callback_query(AdminSt.update_price_prod, F.data.startswith("upcat_"))
async def admin_update_price_cat(cb: CallbackQuery, state: FSMContext):
    cat_id = int(cb.data.split("_")[1])
    prods = await db.get_products(cat_id)
    buttons = [[InlineKeyboardButton(
        text=f"{p['name_uz']} — {p['price']:,}",
        callback_data=f"upprod_{p['id']}"
    )] for p in prods]
    await cb.message.edit_text("Mahsulotni tanlang:",
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(AdminSt.update_price_prod, F.data.startswith("upprod_"))
async def admin_update_price_prod(cb: CallbackQuery, state: FSMContext):
    prod_id = int(cb.data.split("_")[1])
    await state.update_data(update_prod_id=prod_id)
    await cb.message.answer("Yangi narxni kiriting:")
    await state.set_state(AdminSt.update_price_val)

@router.message(AdminSt.update_price_val)
async def admin_update_price_val(msg: Message, state: FSMContext):
    try:
        price = int(msg.text.replace(" ", "").replace(",", ""))
        data = await state.get_data()
        await db.update_product_price(data["update_prod_id"], price)
        await state.set_state(AdminSt.main)
        await msg.answer("✅ Narx yangilandi!", reply_markup=admin_main_kb())
    except ValueError:
        await msg.answer("❌ Narxni to'g'ri kiriting:")

@router.callback_query(AdminSt.main, F.data == "admin_broadcast")
async def admin_broadcast_start(cb: CallbackQuery, state: FSMContext):
    await cb.message.answer("Barcha foydalanuvchilarga yuboriladigan xabarni kiriting:")
    await state.set_state(AdminSt.broadcast)

@router.message(AdminSt.broadcast)
async def admin_broadcast(msg: Message, state: FSMContext):
    users = await db.get_all_users()
    sent = 0
    for user in users:
        try:
            await bot.send_message(user["id"], msg.text, parse_mode="HTML")
            sent += 1
        except Exception:
            pass
    await state.set_state(AdminSt.main)
    await msg.answer(f"✅ {sent} ta foydalanuvchiga yuborildi.", reply_markup=admin_main_kb())

@router.callback_query(AdminSt.main, F.data == "admin_send_akciya")
async def admin_send_akciya_start(cb: CallbackQuery, state: FSMContext):
    await cb.message.answer("Aksiya xabarini kiriting:")
    await state.set_state(AdminSt.send_akciya)

@router.message(AdminSt.send_akciya)
async def admin_send_akciya(msg: Message, state: FSMContext):
    users = await db.get_all_users()
    sent = 0
    for user in users:
        try:
            await bot.send_message(user["id"], f"🎁 <b>Aksiya!</b>\n\n{msg.text}", parse_mode="HTML")
            sent += 1
        except Exception:
            pass
    await state.set_state(AdminSt.main)
    await msg.answer(f"✅ {sent} ta foydalanuvchiga aksiya yuborildi.", reply_markup=admin_main_kb())

# ══════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════
async def main():
    await db.init_db()
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
