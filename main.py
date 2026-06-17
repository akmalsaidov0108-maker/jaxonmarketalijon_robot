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
