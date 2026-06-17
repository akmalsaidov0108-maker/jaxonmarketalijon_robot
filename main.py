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
