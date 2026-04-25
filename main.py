# -*- coding: utf-8 -*-
import os
from flask import Flask
from threading import Thread
import asyncio
import logging
import aiohttp
import random
import urllib.parse
import psycopg2
from psycopg2 import extras
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, Message
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ===============================================================
# 1. ASOSIY SOZLAMALAR
# ===============================================================
API_TOKEN    = '8687399202:AAF7y9AgJOyV2tVDxAa1UbED-Ux2mTG_dzg'
ADMIN_ID     = 8504719505
SMM_API_KEY  = '67eb24f3527a3c189c37978af21d877f'
SMM_API_URL  = 'https://smmserver.uz/api/v2'
DOLLAR_RATE  = 12850
PROFIT_PCT   = 15
DB_URL = 'postgresql://postgres.phjafmxmxwnbabducrdw:799za7ve900aZ@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres'
BOT_USERNAME = 'Smratsmm_bot'   # <-- botingiz username (@ siz)

# "Referal" bo'limida chiqadigan Smart SMM rasmi file_id
SMARTSMM_PHOTO_ID = 'AgACAgIAAxkBAAMsaeocMo4fW3jsfe-kXg48wT6ccLIAAsIWaxvp4lBLEKrCN1oo9qMBAAMCAAN4AAM7BA'

# Majburiy obuna kanallari
REQUIRED_CHANNELS = [
    {"name": "Smart SMM", "link": "https://t.me/Smartsmm_org", "username": "Smartsmm_org"}
]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())

# ---------------------------------------------------------------
# KATEGORIYALAR
# ---------------------------------------------------------------
CATEGORIES = {
    "tg": [
        {"name": "\U0001f31f Premium 👤 Obunachi",            "ids": [4879, 4881]},
        {"name": "Onlayn \U0001f465Azolar + Izohlar\u2709\ufe0f",   "ids": [4911,4912,4913,4910,4914,4915]},
        {"name": "\u23f0Avto Ko'rish Prosmotr",     "ids": [4773,4774,4775,4776,4777,4778,4779,4817,4820]},
        {"name": "\u2764\ufe0f\U0001f44d\U0001f601\U0001f525 (Avto Reaksiyalar)",     "ids": [4884,4885]},
        {"name": "\U0001f465 Obunachilar",         "ids": [4764,4765,4766,4767,4768,4769,4770,4772]},
        {"name": "\U0001f44d\U0001f44e Reaksiyalar",  "ids": [4780,4781,4782,4783,4784,4785,4786,4787,4788,4789,4790,4791,4792,4793,4794,4922]},
        {"name": "\U0001f916 BOT Uchun Start",     "ids": [4795,4809]},
        {"name": "\u21a9\ufe0f Post Ulashishlar",  "ids": [4797,4798,4799]},
        {"name": "\U0001f441 Prosmotr Ko'rishlar",          "ids": [4811,4812,4813,4818,4819,4887,4888,4890]},
        {"name": "\U0001f441 Hikoya Ko'rishlar (istorya)",    "ids": [4821,4822]},
        {"name": "\U0001f4ca So'rovnoma Ovoz",     "ids": [4833]},
        {"name": "\U0001f680 Boost Ovoz",          "ids": [4863]},
        {"name": "\u2b50 Premium Reaksiya",        "ids": [4866,4867]},
    ],
    "inst": [
        {"name": "\U0001f464 A'zolar (\U0001f6ab Obunani bekor qilish 0%)", "ids": [4904,4905,4906,4907,4908]},
        {"name": "\u2764\ufe0f Like",              "ids": [4882]},
        {"name": "\U0001f3a5 Video Ko'rishlar",    "ids": [4834,4835,4836,4837,4868,4869,4883]},
        {"name": "\U0001f4d6 Istorya Ko'rishlar",  "ids": [4838,4839]},
        {"name": "\U0001f4ca Saqlash",             "ids": [4840]},
        {"name": "\u21a9\ufe0f Ulashishlar",       "ids": [4841,4842]},
        {"name": "\u270d\ufe0f Komentariya",       "ids": [4843,4844]},
        {"name": "\u2764\ufe0f Coment Like",       "ids": [4845,4846]},
        {"name": "\U0001f4ca Batl uchun ovozlar",  "ids": [4871,4872,4873,4874]},
    ],
    "yt": [
        {"name": "\U0001f465 Obunachi",            "ids": [4860,4886]},
        {"name": "\U0001f464 Obunachi + like",     "ids": [4889]},
    ],
    "tt": [
        {"name": "\U0001f465 Obunachi",            "ids": [4850,4851,4852]},
        {"name": "\U0001f441 Ko'rishlar",          "ids": [4852,4853]},
        {"name": "\U0001f441 Ko'rishlar+Ulashish", "ids": [4854,4855]},
    ],
    "free": [
        {"name": "\U0001f381 Telegram Bepul",      "ids": [4903]},
    ],
}

class BotStates(StatesGroup):
    qty              = State()
    link             = State()
    fill_amount      = State()
    fill_photo       = State()
    broadcast_msg    = State()
    add_balance_input= State()

# ===============================================================
# 2. DATABASE — SUPABASE (PostgreSQL + psycopg2)
# ===============================================================
def get_conn():
    return psycopg2.connect(DB_URL, connect_timeout=10)

def init_db():
    """Jadvallar mavjud bo'lmasa avtomatik yaratadi."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id         BIGINT PRIMARY KEY,
                    balance         FLOAT  DEFAULT 0,
                    referrer        BIGINT DEFAULT NULL,
                    total_deposited FLOAT  DEFAULT 0
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id           SERIAL PRIMARY KEY,
                    user_id      BIGINT,
                    order_id     TEXT,
                    service_name TEXT,
                    qty          INTEGER,
                    price        FLOAT,
                    status       TEXT DEFAULT 'Bajarilmoqda'
                )
            """)
        conn.commit()
        logging.info("Supabase: jadvallar tayyor.")
    finally:
        conn.close()

async def get_user(uid: int) -> dict:
    loop = asyncio.get_event_loop()
    def _f():
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT user_id, balance, referrer, total_deposited FROM users WHERE user_id=%s', (uid,))
                row = cur.fetchone()
                if not row:
                    cur.execute('INSERT INTO users (user_id) VALUES (%s)', (uid,))
                    conn.commit()
                    return {'user_id': uid, 'balance': 0.0, 'referrer': None, 'total_deposited': 0.0}
                return {'user_id': row[0], 'balance': row[1], 'referrer': row[2], 'total_deposited': row[3] or 0.0}
        finally:
            conn.close()
    return await loop.run_in_executor(None, _f)

async def get_balance(uid: int) -> float:
    u = await get_user(uid)
    return u['balance']

async def update_balance(uid: int, amt: float):
    loop = asyncio.get_event_loop()
    def _f():
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute('UPDATE users SET balance=balance+%s WHERE user_id=%s', (amt, uid))
                if amt > 0:
                    cur.execute('UPDATE users SET total_deposited=total_deposited+%s WHERE user_id=%s', (amt, uid))
            conn.commit()
        finally:
            conn.close()
    await loop.run_in_executor(None, _f)

async def get_order_count(uid: int) -> int:
    loop = asyncio.get_event_loop()
    def _f():
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT COUNT(*) FROM orders WHERE user_id=%s', (uid,))
                return cur.fetchone()[0]
        finally:
            conn.close()
    return await loop.run_in_executor(None, _f)

async def get_referral_count(uid: int) -> int:
    loop = asyncio.get_event_loop()
    def _f():
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT COUNT(*) FROM users WHERE referrer=%s', (uid,))
                return cur.fetchone()[0]
        finally:
            conn.close()
    return await loop.run_in_executor(None, _f)

async def get_all_user_ids():
    loop = asyncio.get_event_loop()
    def _f():
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT user_id FROM users')
                return [r[0] for r in cur.fetchall()]
        finally:
            conn.close()
    return await loop.run_in_executor(None, _f)

async def insert_order(user_id, order_id, service_name, qty, price):
    loop = asyncio.get_event_loop()
    def _f():
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    'INSERT INTO orders (user_id,order_id,service_name,qty,price,status) VALUES (%s,%s,%s,%s,%s,%s)',
                    (user_id, str(order_id), service_name, qty, price, 'Bajarilmoqda')
                )
            conn.commit()
        finally:
            conn.close()
    await loop.run_in_executor(None, _f)

async def get_pending_orders():
    loop = asyncio.get_event_loop()
    def _f():
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, user_id, order_id FROM orders WHERE status='Bajarilmoqda'")
                return cur.fetchall()
        finally:
            conn.close()
    return await loop.run_in_executor(None, _f)

async def mark_order_done(db_id):
    loop = asyncio.get_event_loop()
    def _f():
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE orders SET status='Bajarildi' WHERE id=%s", (db_id,))
            conn.commit()
        finally:
            conn.close()
    await loop.run_in_executor(None, _f)

async def get_ref_row(uid):
    loop = asyncio.get_event_loop()
    def _f():
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT referrer FROM users WHERE user_id=%s', (uid,))
                return cur.fetchone()
        finally:
            conn.close()
    return await loop.run_in_executor(None, _f)

async def insert_user_with_ref(uid, ref_id):
    loop = asyncio.get_event_loop()
    def _f():
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    'INSERT INTO users (user_id, referrer) VALUES (%s,%s) ON CONFLICT DO NOTHING',
                    (uid, ref_id)
                )
            conn.commit()
        finally:
            conn.close()
    await loop.run_in_executor(None, _f)

# ===============================================================
# 3. SMM API
# ===============================================================
class SMMAPI:
    async def get_all_services(self):
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(SMM_API_URL, data={'key': SMM_API_KEY, 'action': 'services'}) as r:
                    return await r.json()
        except Exception as e:
            logging.error(f"SMM API: {e}")
            return []

    async def add_order(self, sid, link, qty):
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(SMM_API_URL, data={
                    'key': SMM_API_KEY, 'action': 'add',
                    'service': sid, 'link': link, 'quantity': qty
                }) as r:
                    return await r.json()
        except Exception as e:
            logging.error(f"SMM order: {e}")
            return {'error': str(e)}

    async def get_order_status(self, order_id):
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(SMM_API_URL, data={
                    'key': SMM_API_KEY, 'action': 'status', 'order': order_id
                }) as r:
                    return await r.json()
        except Exception as e:
            logging.error(f"SMM status: {e}")
            return {'error': str(e)}

smm_api = SMMAPI()

def calc_price(rate, qty=1000):
    return round((float(rate) / 1000 * qty * DOLLAR_RATE) * (1 + PROFIT_PCT / 100), 2)

# ===============================================================
# 4. KLAVIATURALAR
# ===============================================================
def main_kb(user_id: int) -> ReplyKeyboardMarkup:
    btns = [
        [KeyboardButton(text="\U0001f6cd Buyurtma berish")],
        [KeyboardButton(text="\U0001f6d2 Buyurtmalarim"), KeyboardButton(text="\U0001F465 Referal")],
        [KeyboardButton(text="\U0001f464 Hisobim"),       KeyboardButton(text="\U0001f4b3 Hisobni to'ldirish")],
        [KeyboardButton(text="\u260e\ufe0f Qo'llab-quvvatlash"), KeyboardButton(text="\U0001f4d6 Qo'llanma")],
    ]
    if user_id == ADMIN_ID:
        btns.append([KeyboardButton(text="\u2699\ufe0f Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=btns, resize_keyboard=True)

def back_kb() -> ReplyKeyboardMarkup:
    """Buyurtma oqimida paydo bo'ladigan katta Orqaga tugmasi"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="\U0001f519 Orqaga")]],
        resize_keyboard=True
    )

# ===============================================================
# 5. MAJBURIY OBUNA
# ===============================================================
async def check_subscription(user_id: int) -> bool:
    if user_id == ADMIN_ID:
        return True
    for ch in REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(f"@{ch['username']}", user_id)
            if member.status in ('left', 'kicked', 'banned'):
                return False
        except Exception as e:
            logging.warning(f"Obuna tekshiruv xato ({ch['username']}): {e}")
            return False
    return True

async def send_sub_required(m: Message):
    text = "<b>Botdan foydalanish uchun avval quyidagi kanallarga obuna bo'ling \U0001f447</b>"
    btns = [[InlineKeyboardButton(text=f"\u2795 Kanalga obuna bo'lish", url=ch['link'])]
            for ch in REQUIRED_CHANNELS]
    btns.append([InlineKeyboardButton(text="\u2705 Tekshirish", callback_data="check_sub")])
    await m.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")

async def sub_guard(m: Message) -> bool:
    if not await check_subscription(m.from_user.id):
        await send_sub_required(m)
        return False
    return True

@dp.callback_query(F.data == "check_sub")
async def check_sub_cb(c: CallbackQuery):
    if await check_subscription(c.from_user.id):
        await get_user(c.from_user.id)
        await c.message.delete()
        await c.message.answer(
            "<b>\U0001f680 \u00abSmart SMM\u00bb botiga xush kelibsiz! \U0001f389\n\n"
            "\U0001f4ca Ushbu bot sizga barcha ijtimoiy tarmoqlar uchun ishonchli va arzon SMM xizmatlarini taqdim etadi! \U0001f310\n\n"
            "\u2705 Marhamat, pastdagi tugmalardan kerakli bo'limni tanlang! \U0001f447</b>",
            reply_markup=main_kb(c.from_user.id), parse_mode="HTML"
        )
    else:
        await c.answer("\u274c Siz hali kanallarga obuna bo'lmagansiz", show_alert=True)

# ===============================================================
# 6. START
# ===============================================================
@dp.message(Command("start"))
async def cmd_start(m: Message, state: FSMContext):
    await state.clear()
    args = m.text.split()
    uid  = m.from_user.id

    # Referal qayd etish
    if len(args) > 1 and args[1].startswith("user"):
        try:
            ref_id = int(args[1].replace("user", ""))
            if ref_id != uid:
                row = await get_ref_row(uid)
                if row is None:
                    await insert_user_with_ref(uid, ref_id)
                    await update_balance(ref_id, 100)
                    try:
                        await bot.send_message(
                            ref_id,
                            "<b>\U0001f389 Yangi referal! Hisobingizga 100 so'm qo'shildi.</b>",
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass
        except Exception:
            pass

    await get_user(uid)

    if not await check_subscription(uid):
        await send_sub_required(m)
        return

    await m.answer(
        "<b>\U0001f680 \u00abSmart SMM\u00bb botiga xush kelibsiz! \U0001f389\n\n"
        "\U0001f4ca Ushbu bot sizga barcha ijtimoiy tarmoqlar uchun ishonchli va arzon SMM xizmatlarini taqdim etadi! \U0001f310\n\n"
        "\u2705 Marhamat, pastdagi tugmalardan kerakli bo'limni tanlang! \U0001f447</b>",
        reply_markup=main_kb(uid), parse_mode="HTML"
    )

# ===============================================================
# 7. ORQAGA TUGMASI
# ===============================================================
@dp.message(F.text == "\U0001f519 Orqaga")
async def go_back(m: Message, state: FSMContext):
    await state.clear()
    await m.answer(
        "<b>\U0001f3e0 Asosiy menyudasiz!</b>",
        reply_markup=main_kb(m.from_user.id), parse_mode="HTML"
    )

# ===============================================================
# 8. ADMIN PANEL
# ===============================================================
async def _admin_panel_text_kb():
    loop = asyncio.get_event_loop()
    def _stats():
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT COUNT(*) FROM users')
                uc = cur.fetchone()[0]
                cur.execute('SELECT COUNT(*) FROM orders')
                oc = cur.fetchone()[0]
                cur.execute('SELECT COALESCE(SUM(price),0) FROM orders')
                ts = cur.fetchone()[0]
            return uc, oc, ts
        finally:
            conn.close()
    uc, oc, ts = await loop.run_in_executor(None, _stats)
    text = (
        "<b>\u2699\ufe0f Admin Panel\n\n"
        f"\U0001f465 Foydalanuvchilar: {uc} ta\n"
        f"\U0001f6d2 Buyurtmalar: {oc} ta\n"
        f"\U0001f4b0 Jami savdo: {ts:,.0f} so'm\n\n"
        "Amal tanlang:</b>"
    ).replace(',', ' ')
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\U0001f4cb Buyurtmalar",     callback_data="adm_all_orders")],
        [InlineKeyboardButton(text="\U0001f465 Foydalanuvchilar",callback_data="adm_users")],
        [InlineKeyboardButton(text="\U0001f4e2 Xabar yuborish",  callback_data="adm_broadcast")],
        [InlineKeyboardButton(text="\U0001f4b8 Balans qo'shish", callback_data="adm_add_balance")],
    ])
    return text, kb

@dp.message(F.text == "\u2699\ufe0f Admin Panel")
async def admin_panel(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    text, kb = await _admin_panel_text_kb()
    await m.answer(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "adm_back")
async def adm_back(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID: return
    text, kb = await _admin_panel_text_kb()
    await c.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "adm_all_orders")
async def adm_orders(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID: return
    loop = asyncio.get_event_loop()
    def _f():
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT user_id,order_id,service_name,qty,price,status FROM orders ORDER BY id DESC LIMIT 10')
                return cur.fetchall()
        finally:
            conn.close()
    rows = await loop.run_in_executor(None, _f)
    if not rows:
        await c.answer("Buyurtmalar yo'q!", show_alert=True); return
    text = "<b>\U0001f4cb Oxirgi 10 buyurtma:\n\n</b>"
    for r in rows:
        text += (f"<b>\U0001f464 {r[0]} | \U0001f194 {r[1]}\n"
                 f"\U0001f6e0 {r[2]} | {r[3]} ta\n"
                 f"\U0001f4b5 {r[4]:,.0f} so'm | {r[5]}\n---\n</b>").replace(',', ' ')
    await c.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\U0001F519 Orqaga", callback_data="adm_back")]
    ]), parse_mode="HTML")

@dp.callback_query(F.data == "adm_users")
async def adm_users(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID: return
    loop = asyncio.get_event_loop()
    def _f():
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT user_id,balance FROM users ORDER BY balance DESC LIMIT 15')
                return cur.fetchall()
        finally:
            conn.close()
    rows = await loop.run_in_executor(None, _f)
    text = "<b>\U0001f465 Top 15 foydalanuvchi:\n\n</b>"
    for r in rows:
        text += f"<b>ID: {r[0]} | {r[1]:,.0f} so'm\n</b>".replace(',', ' ')
    await c.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\U0001F519 Orqaga", callback_data="adm_back")]
    ]), parse_mode="HTML")

@dp.callback_query(F.data == "adm_broadcast")
async def adm_broadcast(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID: return
    await c.message.answer("<b>\U0001f4e2 Xabarni yozing:</b>", parse_mode="HTML")
    await state.set_state(BotStates.broadcast_msg)

@dp.message(BotStates.broadcast_msg)
async def do_broadcast(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID: return
    ids = await get_all_user_ids()
    sent = fail = 0
    for uid in ids:
        try:
            await bot.send_message(uid, m.text, parse_mode="HTML"); sent += 1
        except Exception:
            fail += 1
    await state.clear()
    await m.answer(f"<b>\u2705 Yuborildi: {sent} | \u274c Xato: {fail}</b>", parse_mode="HTML")

@dp.callback_query(F.data == "adm_add_balance")
async def adm_add_bal(c: CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID: return
    await c.message.answer(
        "<b>\U0001f4b8 Format: <code>USER_ID MIQDOR</code>\nMisol: <code>123456 50000</code></b>",
        parse_mode="HTML"
    )
    await state.set_state(BotStates.add_balance_input)

@dp.message(BotStates.add_balance_input)
async def do_add_balance(m: Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID: return
    try:
        uid, amt = int(m.text.split()[0]), float(m.text.split()[1])
        await update_balance(uid, amt)
        await bot.send_message(uid,
            f"<b>\u2705 Hisobingiz {amt:,.0f} so'm ga to'ldirildi!</b>".replace(',', ' '),
            parse_mode="HTML")
        await m.answer(f"<b>\u2705 {uid} ga {amt:,.0f} so'm qo'shildi.</b>".replace(',', ' '), parse_mode="HTML")
    except Exception:
        await m.answer("<b>\u274c Format: <code>USER_ID MIQDOR</code></b>", parse_mode="HTML")
    await state.clear()

# ===============================================================
# 9. ADMIN TO'LOV TASDIQLASH / RAD ETISH
# ===============================================================
@dp.callback_query(F.data.startswith("adm_ok_"))
async def adm_confirm(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID: return
    p   = c.data.split("_")
    uid = int(p[2]); amt = int(p[3])
    await update_balance(uid, amt)
    await bot.send_message(uid,
        f"<b>Hisob to'ldirish haqidagi so'rovingiz admin tomonidan tastiqlandi "
        f"va botdagi hisobingizga {amt:,} so'm muvaffaqiyatli o'tkazildi \u2705 \U0001f4b0</b>".replace(',', ' '),
        parse_mode="HTML"
    )
    try:
        await c.message.edit_caption(
            caption=c.message.caption + "\n\n<b>\u2705 TASDIQLANDI</b>", parse_mode="HTML"
        )
    except Exception:
        pass
    await c.answer("Tasdiqlandi!", show_alert=True)

@dp.callback_query(F.data.startswith("adm_no_"))
async def adm_reject(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID: return
    uid = int(c.data.split("_")[2])
    pay_id = c.data.split("_")[3] if len(c.data.split("_")) > 3 else "—"
    await bot.send_message(uid,
        f"<b>\u26a0\ufe0f To'lov tasdiqlanmadi.\n\n"
        f"<blockquote>\U0001f6ab To'lov o'tkazilmagan. Soxta to'lov chekini yuborish "
        f"hisobingizni bloklanishiga olib kelishi mumkin!</blockquote>\n\n"
        f"\U0001f194 To'lov ID: {pay_id}</b>",
        parse_mode="HTML"
    )
    try:
        await c.message.edit_caption(
            caption=c.message.caption + "\n\n<b>\u274c RAD ETILDI</b>", parse_mode="HTML"
        )
    except Exception:
        pass
    await c.answer("Rad etildi!", show_alert=True)

# ===============================================================
# 10. HISOBNI TO'LDIRISH
# ===============================================================
@dp.message(F.text == "\U0001f4b3 Hisobni to'ldirish")
async def fill_balance_start(m: Message):
    if not await sub_guard(m): return
    text = (
        "<b>\U0001f4f2 To'lov tizimi: \U0001f4b3 Karta orqali\n\n"
        "\U0001f4b3 Hamyon: <code>9860 3566 3517 7633</code>\n"
        "\U0001f464 Ega: Xusanboy botirov\n"
        "\U0001f3e6 Bank: TBC\n\n"
        "\U0001f91d Hisobingizni muvaffaqiyatli to'ldirish uchun quyidagi harakatlarni amalga oshiring:\n\n"
        "1) Pul miqdorini tepadagi Hamyonga tashlang.\n"
        "2) \"\u2705 To'lov qildim\" tugmasini bosing;\n"
        "4) Qancha pul miqdorini yuborganingizni kiriting;\n"
        "3) To'lov haqidagi surat (skrinshot)ni botga yuboring;\n"
        "3) Operator tomonidan to'lov tasdiqlanishini kuting!\n\n"
        "<blockquote>\u26a0\ufe0f Minimal 5500 so'm undan kam summaga to'ldirib bo'lmaydi.</blockquote></b>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\u2705 To'lov qildim", callback_data="paid")],
    ])
    await m.answer(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "paid")
async def paid_cb(c: CallbackQuery, state: FSMContext):
    # Eski to'lov sahifasi xabarini o'chirish
    try:
        await c.message.delete()
    except Exception:
        pass
    await c.message.answer(
        "<b>\U0001f4b8 To'lov miqdorini kiriting.\n\n"
        "<i>Kartaga qancha tashlagan bo'lsangiz shuni kiriting!</i></b>",
        reply_markup=back_kb(), parse_mode="HTML"
    )
    await state.set_state(BotStates.fill_amount)

@dp.message(BotStates.fill_amount)
async def proc_amt(m: Message, state: FSMContext):
    if m.text == "\U0001f519 Orqaga":
        await state.clear()
        await m.answer("<b>\U0001f3e0 Asosiy menyudasiz!</b>",
                       reply_markup=main_kb(m.from_user.id), parse_mode="HTML")
        return
    if not m.text or not m.text.isdigit():
        return await m.answer("<b>\u274c Faqat raqam kiriting!</b>", parse_mode="HTML")
    amt = int(m.text)
    if amt < 5500:
        return await m.answer("<b>\u26a0\ufe0f Minimal to'ldirish 5500 so'm.</b>", parse_mode="HTML")
    await state.update_data(fill_amt=amt)
    await m.answer(
        "<b>\U0001f4c4 To'lov chekini rasmini yuboring.</b>",
        reply_markup=back_kb(), parse_mode="HTML"
    )
    await state.set_state(BotStates.fill_photo)

@dp.message(BotStates.fill_photo)
async def proc_photo(m: Message, state: FSMContext):
    if m.text == "\U0001f519 Orqaga":
        await state.clear()
        await m.answer("<b>\U0001f3e0 Asosiy menyudasiz!</b>",
                       reply_markup=main_kb(m.from_user.id), parse_mode="HTML")
        return
    if not m.photo:
        return await m.answer(
            "<b>\u26a0\ufe0f Iltimos! To'lov chekni faqat rasm ko'rinishda yuboring.</b>",
            parse_mode="HTML"
        )
    data   = await state.get_data()
    pay_id = random.randint(10000, 99999)
    username = f"@{m.from_user.username}" if m.from_user.username else str(m.from_user.id)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\u2705 Tastiqlash",
                              callback_data=f"adm_ok_{m.from_user.id}_{data['fill_amt']}_{pay_id}")],
        [InlineKeyboardButton(text="\u274c Rad etish",
                              callback_data=f"adm_no_{m.from_user.id}_{pay_id}")]
    ])
    caption = (
        f"<b>\U0001f4b0 YANGI TO'LOV\n\n"
        f"\U0001f194 To'lov ID: {pay_id}\n"
        f"\U0001f464 Foydalanuvchi: {username} ({m.from_user.id})\n"
        f"\U0001f4b5 Miqdor: {data['fill_amt']:,} so'm</b>"
    ).replace(',', ' ')
    await bot.send_photo(ADMIN_ID, m.photo[-1].file_id,
                         caption=caption, parse_mode="HTML", reply_markup=kb)

    await m.answer(
        f"<b>\U0001f194 Tolov ID: {pay_id}\n\n"
        "\U0001f552 To'lovingiz cheki administratoriga yuborildi!\n\n"
        "<blockquote>\u2705 To'lovingiz tekshirilishi 6 soatgacha vaqt olishi mumkin.</blockquote>\n\n"
        "<blockquote>\u2139\ufe0f To'lov cheki tekshirilgach holat haqida xabar yuboriladi.</blockquote></b>",
        reply_markup=main_kb(m.from_user.id), parse_mode="HTML"
    )
    await state.clear()

# ===============================================================
# 11. HISOBIM
# ===============================================================
@dp.message(F.text == "\U0001f464 Hisobim")
async def my_acc(m: Message):
    if not await sub_guard(m): return
    uid    = m.from_user.id
    u      = await get_user(uid)
    orders = await get_order_count(uid)
    refs   = await get_referral_count(uid)
    text = (
        f"<b>\U0001f464 Sizning ID raqamingiz: <code>{uid}</code>\n\n"
        f"\U0001f4b5 Balansingiz: {u['balance']:,.0f} so'm\n"
        f"\U0001f4ca Buyurtmalaringiz: {orders} ta\n"
        f"\U0001f465 Referallaringiz: {refs} ta\n"
        f"\U0001f4b8 Botga kiritgan pullaringiz: {u['total_deposited']:,.0f} so'm</b>"
    ).replace(',', ' ')
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\U0001f4b0 Hisob to'ldirish", callback_data="goto_fill")],
        [InlineKeyboardButton(text="\U0001F519 Orqaga",          callback_data="close_hisobim")],
    ])
    await m.answer(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "goto_fill")
async def goto_fill(c: CallbackQuery):
    await c.message.delete()
    text = (
        "<b>\U0001f4f2 To'lov tizimi: \U0001f4b3 Karta orqali\n\n"
        "\U0001f4b3 Hamyon: <code>9860 3566 3517 7633</code>\n"
        "\U0001f464 Ega: Xusanboy botirov\n"
        "\U0001f3e6 Bank: TBC\n\n"
        "\U0001f91d Hisobingizni muvaffaqiyatli to'ldirish uchun quyidagi harakatlarni amalga oshiring:\n\n"
        "1) Pul miqdorini tepadagi Hamyonga tashlang.\n"
        "2) \"\u2705 To'lov qildim\" tugmasini bosing;\n"
        "4) Qancha pul miqdorini yuborganingizni kiriting;\n"
        "3) To'lov haqidagi surat (skrinshot)ni botga yuboring;\n"
        "3) Operator tomonidan to'lov tasdiqlanishini kuting!\n\n"
        "<blockquote>\u26a0\ufe0f Minimal 5500 so'm undan kam summaga to'ldirib bo'lmaydi.</blockquote></b>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\u2705 To'lov qildim", callback_data="paid")],
    ])
    await c.message.answer(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "close_hisobim")
async def close_hisobim(c: CallbackQuery):
    try:
        await c.message.delete()
    except Exception:
        pass

# ===============================================================
# 12. QO'LLANMA
# ===============================================================
@dp.message(F.text == "\U0001f4d6 Qo'llanma")
async def guide(m: Message):
    if not await sub_guard(m): return
    text = (
        "<b>\U0001f4d5 Botdan foydalanish yo'riqnomasi:\n\n"
        "\U0001f504 Buyurtma bekor qilindimi?\n"
        "<i>Xavotir olmang! Mablag'ingiz avtomatik ravishda hisobingizga qaytariladi.</i>\n\n"
        "\U0001f55b To'lovdan so'ng kutish vaqti:\n"
        "<i>Pullar hisobingizga 24 soat ichida tushadi, sabrli bo'ling.</i>\n\n"
        "\U0001f6ab Mablag'lar qaytarilmaydi!\n"
        "<i>Botga joylashtirilgan mablag'lar qaytarib berilmaydi. To'g'ri va aniq harakat qiling.</i>\n\n"
        "\U0001f4e9 Buyurtma haqida savol bormi?\n"
        "<i>Muammo yoki savol tug'ilsa, adminlarga murojaat qiling.</i>\n\n"
        "\u26a0\ufe0f Bitta xizmat — bitta buyurtma:\n"
        "<i>Bir vaqtda faqat bitta buyurtma berishingiz mumkin. Ko'proq buyurtma uchun vaqt tanlashingiz kerak.</i>\n\n"
        "\U0001f3af Referal mukofoti:\n"
        "<i>Agar referallingiz kanallarga qo'shilmasa, mukofot puli berilmaydi.</i>\n\n"
        "\u2757 Xatolik yoki muammolar uchun:\n@smartsmmHelp</b>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\U0001F519 Orqaga", callback_data="close_guide")]
    ])
    await m.answer(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "close_guide")
async def close_guide(c: CallbackQuery):
    try:
        await c.message.delete()
    except Exception:
        pass

# ===============================================================
# 13. REFERAL 
# ===============================================================
@dp.message(F.text == "\U0001F465 Referal")
async def earn_money(m: Message):
    if not await sub_guard(m): return
    uid  = m.from_user.id
    refs = await get_referral_count(uid)
    ref_link = f"https://t.me/{BOT_USERNAME}?start=user{uid}"

    caption = (
        f"<b>\U0001f4a5 Sizning referal havolangiz:\n\n"
        f"\U0001f517 <code>{ref_link}</code>\n\n"
        f"\U0001f4b8 Sizga har bir taklif qilgan referalingiz uchun 100 so'm beriladi.\n\n"
        f"Eslatma: Siz taklif qilgan referall majburiy kanalga a'zo bo'lib "
        f"[\u2705tekshirish] tugmasini bosmasa referall puli berilmaydi.\n\n"
        f"\U0001f464 Referallaringiz: {refs} ta</b>"
    )
    share_text = (
        f"\U0001F3AF Telegram va Instagram uchun arzon va sifatli SMM xizmatlari kerakmi?\n\n"
        f"Kanal/Guruh uchun obunachilar \U0001F464\n"
        f"Postlaringiz uchun ko'rishlar \U0001F440\n"
        f"Postlaringiz uchun reaksiyalar \U0001F525\n"
        f"So'rovnomalar uchun ovozlar \U0001F4CA\n"
        f"Postlaringizga yoqtirishlar \U00002764\ufe0f\n\n"
        f"\U0001F381 BEPUL xizmatlar \U0001F381\n\n"
        f"\U0001F447 Boshlash uchun bosing:\n{ref_link}"
    )
    import urllib.parse
    share_url = f"https://t.me/share/url?url={urllib.parse.quote(ref_link)}&text={urllib.parse.quote(share_text)}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\u267b\ufe0f Do'stlarga ulashish",  switch_inline_query=share_text)],
    ])
    if SMARTSMM_PHOTO_ID and SMARTSMM_PHOTO_ID != 'YOUR_PHOTO_FILE_ID_HERE':
        await m.answer_photo(SMARTSMM_PHOTO_ID, caption=caption,
                             reply_markup=kb, parse_mode="HTML")
    else:
        await m.answer(caption, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "close_earn")
async def close_earn(c: CallbackQuery):
    try:
        await c.message.delete()
    except Exception:
        pass

# ===============================================================
# 14. QO'LLAB-QUVVATLASH
# ===============================================================
@dp.message(F.text == "\u260e\ufe0f Qo'llab-quvvatlash")
async def support(m: Message):
    if not await sub_guard(m): return
    await m.answer(
        "<b>\U0001f198 Texnik yordam uchun:\n\n@SmartsmmHelp</b>",
        parse_mode="HTML"
    )

# ===============================================================
# 15. BUYURTMALARIM
# ===============================================================
@dp.message(F.text == "\U0001f6d2 Buyurtmalarim")
async def my_orders(m: Message):
    if not await sub_guard(m): return
    loop = asyncio.get_event_loop()
    def _f():
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT order_id,service_name,qty,price,status FROM orders '
                    'WHERE user_id=%s ORDER BY id DESC LIMIT 5', (m.from_user.id,)
                )
                return cur.fetchall()
        finally:
            conn.close()
    rows = await loop.run_in_executor(None, _f)
    if not rows:
        text = "<b>\U0001f6d2 Sizda hali buyurtmalar mavjud emas.</b>"
    else:
        text = "<b>\U0001f6d2 Oxirgi buyurtmalaringiz:\n\n</b>"
        for r in rows:
            text += (
                f"<b>\U0001f194 Order ID: {r[0]}\n"
                f"\U0001f6e0 Xizmat: {r[1]}\n"
                f"\U0001f522 Miqdor: {r[2]} ta\n"
                f"\U0001f4b5 Narx: {r[3]:,.0f} so'm\n"
                f"\u231b Holati: \u23f3 {r[4]}\n"
                "------------------------\n</b>"
            ).replace(',', ' ')
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\U0001F519 Orqaga", callback_data="delete_msg")]
    ])
    await m.answer(text, reply_markup=kb, parse_mode="HTML")

# ===============================================================
# 16. BUYURTMA BERISH — Asosiy kategoriyalar
# ===============================================================
@dp.message(F.text == "\U0001f6cd Buyurtma berish")
async def order_main(m: Message):
    if not await sub_guard(m): return
    kb = [
        [InlineKeyboardButton(text="\U0001f6cd TELEGRAM",  callback_data="cat_tg"),
         InlineKeyboardButton(text="\U0001f6cd INSTAGRAM", callback_data="cat_inst")],
        [InlineKeyboardButton(text="\U0001f6cd YOUTUBE",   callback_data="cat_yt"),
         InlineKeyboardButton(text="\U0001f6cd TIKTOK",    callback_data="cat_tt")],
        [InlineKeyboardButton(text="\U0001f381 BEPUL XIZMATLAR", callback_data="cat_free")],
    ]
    # Faqat kategoriyalar inline chiqadi — back_kb bu yerda CHIQMAYDI
    await m.answer(
        "<b>Quyidagi ijtimoiy tarmoqlardan birini tanlang: \U0001f447</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("cat_"))
async def sub_cat_menu(c: CallbackQuery):
    cat = c.data.split("_")[1]
    sub_cats = CATEGORIES.get(cat, [])
    if not sub_cats:
        await c.answer("Xizmatlar topilmadi!", show_alert=True); return
    kb = [[InlineKeyboardButton(text=sc['name'], callback_data=f"subcat_{cat}_{i}")]
          for i, sc in enumerate(sub_cats)]
    kb.append([InlineKeyboardButton(text="\u2b05\ufe0f Orqaga", callback_data="back_order_main")])
    names = {"tg":"TELEGRAM","inst":"INSTAGRAM","yt":"YOUTUBE","tt":"TIKTOK","free":"BEPUL"}
    await c.message.edit_text(
        f"<b>{names.get(cat,cat.upper())} xizmat turini tanlang: \U0001f447</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML"
    )

@dp.callback_query(F.data == "back_order_main")
async def back_order(c: CallbackQuery):
    kb = [
        [InlineKeyboardButton(text="\U0001f6cd TELEGRAM",  callback_data="cat_tg"),
         InlineKeyboardButton(text="\U0001f6cd INSTAGRAM", callback_data="cat_inst")],
        [InlineKeyboardButton(text="\U0001f6cd YOUTUBE",   callback_data="cat_yt"),
         InlineKeyboardButton(text="\U0001f6cd TIKTOK",    callback_data="cat_tt")],
        [InlineKeyboardButton(text="\U0001f381 BEPUL XIZMATLAR", callback_data="cat_free")],
    ]
    await c.message.edit_text("<b>Quyidagi ijtimoiy tarmoqlardan birini tanlang: \U0001f447</b>",
                              reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@dp.callback_query(F.data.startswith("subcat_"))
async def services_menu(c: CallbackQuery):
    _, cat, idx_s = c.data.split("_")
    idx = int(idx_s)
    sub = CATEGORIES[cat][idx]
    await c.answer("\u23f3 Yuklanmoqda...")
    all_s = await smm_api.get_all_services()
    kb = []
    for s in all_s:
        if int(s['service']) in sub['ids']:
            p = calc_price(s['rate'], 1000)
            kb.append([InlineKeyboardButton(
                text=f"{s['name']} | {p:,.0f} so'm".replace(',', ' '),
                callback_data=f"buy_{s['service']}_{cat}_{idx}"
            )])
    if not kb:
        await c.message.edit_text(
            "<b>\u274c Bu bo'limda xizmatlar mavjud emas.</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="\U0001F519 Orqaga", callback_data=f"cat_{cat}")]
            ]), parse_mode="HTML"
        ); return
    kb.append([InlineKeyboardButton(text="\U0001F519 Orqaga", callback_data=f"cat_{cat}")])
    await c.message.edit_text(
        f"<b>{sub['name']} xizmatidan birini tanlang: \U0001f447</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML"
    )

# ===============================================================
# 17. XIZMAT TANLANDI — PDF p.1 SHABLON
# ===============================================================
@dp.callback_query(F.data.startswith("buy_"))
async def show_service(c: CallbackQuery, state: FSMContext):
    parts = c.data.split("_")
    sid, cat, idx = parts[1], parts[2], parts[3]
    await c.answer("\u23f3 Ma'lumot olinmoqda...")
    all_s = await smm_api.get_all_services()
    s = next((x for x in all_s if str(x['service']) == sid), None)
    if not s:
        await c.answer("Xizmat topilmadi!", show_alert=True); return
    p1000 = calc_price(s['rate'], 1000)
    avg   = s.get('average_time', 0)
    # PDF p.1 — Xizmat ma'lumotlari shabloni (to'liq moslashtirish)
    text = (
        f"<b>\U0001f680 Xizmat nomi: {s['name']}\n\n"
        f"\U0001f511 Xizmat IDsi: {s['service']}\n"
        f"\U0001f4b5 Narxi (1000x): {p1000:,.0f} so'm\n"
        f"\u23f0 Bajarilish vaqti: {avg} daqiqa\n\n"
        "<blockquote>Ommaviy va shaxsiy xavola orqali buyurtma berishingiz mumkin \u2705</blockquote>\n\n"
        f"\U0001f53d Minimal buyurtma: {s['min']} ta\n"
        f"\U0001f53c Maksimal buyurtma: {s['max']} ta\n\n"
        "Davom etish uchun \u2705 <b>Buyurtma berish</b> tugmasini bosing! \U0001f447</b>"
    ).replace(',', ' ')
    # PDF p.1 — Buyurtma berish va Orqaga inline tugmalari
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\u2705 Buyurtma berish", callback_data=f"startorder_{sid}_{cat}_{idx}")],
        [InlineKeyboardButton(text="\U0001f519 Orqaga",       callback_data=f"subcat_{cat}_{idx}")],
    ])
    await state.update_data(s=s, cat=cat, idx=idx)
    await c.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

# ===============================================================
# 18. BUYURTMA MIQDORI — PDF p.2 SHABLON
# ===============================================================
@dp.callback_query(F.data.startswith("startorder_"))
async def ask_qty(c: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    s = data.get('s')
    if not s:
        await c.answer("Xato! Qaytadan urinib ko'ring.", show_alert=True); return
    # Miqdor shablonini inline xabarga edit qilamiz
    await c.message.edit_text(
        f"<b>\u27a1\ufe0f Buyurtma miqdorini kiriting\n\n"
        f"\u2199\ufe0f Min: <b>{s['min']}</b> ta\n"
        f"\u2197\ufe0f Max: <b>{s['max']}</b> ta</b>",
        parse_mode="HTML"
    )
    # back_kb faqat shu xabar orqali ko'rinadi — matn minimal
    await c.message.answer(
        f"\u2199\ufe0f {s['min']} — {s['max']} \u2197\ufe0f",
        reply_markup=back_kb()
    )
    await state.set_state(BotStates.qty)

# ===============================================================
# 19. MIQDOR QABUL — PDF p.2 SHABLON (saqlandi + havola so'rash)
# ===============================================================
@dp.message(BotStates.qty)
async def get_qty(m: Message, state: FSMContext):
    if m.text == "\U0001f519 Orqaga":
        await state.clear()
        await m.answer("<b>\U0001f3e0 Asosiy menyudasiz!</b>",
                       reply_markup=main_kb(m.from_user.id), parse_mode="HTML"); return
    if not m.text or not m.text.isdigit():
        return await m.answer("<b>\u274c Faqat raqam kiriting!</b>", parse_mode="HTML")
    qty  = int(m.text)
    data = await state.get_data()
    s    = data.get('s')
    if qty < int(s['min']) or qty > int(s['max']):
        # PDF p.3 — Noto'g'ri miqdor shabloni, BotStates.qty da qoladi
        return await m.answer(
            f"<b>\u26a0\ufe0f Buyurtma miqdorini noto'g'ri kiritilmoqda\n\n"
            f"\u2196\ufe0f Minimal: {s['min']} dan kam\n"
            f"\u2197\ufe0f Maksimal: {s['max']} dan ko'p bo'lmasligi kerak\n\n"
            f"\U0001f522 Boshqa miqdor kiriting!</b>",
            parse_mode="HTML"
        )
    await state.update_data(qty=qty)
    # Miqdor saqlandi + havola kiriting
    await m.answer(
        f"<b>\u2705 {qty} saqlandi\n\n"
        f"\U0001f517 Buyurtma havolasini kiriting (https://):</b>",
        reply_markup=back_kb(), parse_mode="HTML"
    )
    await state.set_state(BotStates.link)

# ===============================================================
# 20. HAVOLA QABUL — PDF p.3 SHABLON (ma'lumotlar tasdiq)
# ===============================================================
@dp.message(BotStates.link)
async def get_link(m: Message, state: FSMContext):
    if m.text == "\U0001f519 Orqaga":
        await state.clear()
        await m.answer("<b>\U0001f3e0 Asosiy menyudasiz!</b>",
                       reply_markup=main_kb(m.from_user.id), parse_mode="HTML"); return
    # Havola https:// bilan boshlanishi kerak
    if not m.text or not m.text.startswith("http"):
        return await m.answer(
            "<b>\u274c Iltimos, to'g'ri havola kiriting (https:// bilan boshlanishi kerak)!</b>",
            parse_mode="HTML"
        )
    data  = await state.get_data()
    qty, s = data['qty'], data['s']
    total = calc_price(s['rate'], qty)
    await state.update_data(link=m.text, total=total)
    text = (
        f"<b>\U0001f4cb Ma'lumotlarni o'qib chiqing:\n\n"
        f"\U0001f4b5 Buyurtma narxi: {total:,.0f} so'm\n"
        f"\U0001f517 Buyurtma manzili: {m.text}\n"
        f"\U0001f522 Buyurtma miqdori: {qty}\n\n"
        f"Yuqoridagi ma'lumotlarni to'g'ri kiritgan bo'lsangiz, buyurtmani tasdiqlash uchun "
        f"\u00ab\u2705 Tasdiqlash\u00bb tugmasini bosing va sizning hisobingizdan "
        f"{total:,.0f} so'm yechiladi.</b>"
    ).replace(',', ' ')
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\u2705 Tasdiqlash", callback_data="confirm")]
    ])
    await m.answer(text, reply_markup=kb, parse_mode="HTML")

# ===============================================================
# 21. TASDIQLASH — PDF p.3 SHABLON (Qabul qilindi)
# ===============================================================
@dp.callback_query(F.data == "confirm")
async def final_confirm(c: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if data.get('total') is None:
        await c.answer("Xato! Qaytadan buyurtma bering.", show_alert=True); return
    bal = await get_balance(c.from_user.id)
    # PDF p.4 — Yetarli mablag' yo'q shabloni (tugmasiz)
    if bal < data['total']:
        return await c.message.edit_text(
            (f"<b>\u2716\ufe0f Yetarli mablag' mavjud emas\n"
             f"\U0001f4b5 Narxi: {data['total']:,.0f} so'm\n\n"
             "Hisobni to'ldirib qaytadan urinib ko'ring:</b>").replace(',', ' '),
            parse_mode="HTML"
        )
    res = await smm_api.add_order(data['s']['service'], data['link'], data['qty'])
    if 'order' in res:
        await update_balance(c.from_user.id, -data['total'])
        await insert_order(c.from_user.id, res['order'], data['s']['name'], data['qty'], data['total'])
        # PDF p.3 — Qabul qilindi shabloni
        await c.message.edit_text(
            f"<b>\u2705 Qabul qilindi\n\n"
            f"\U0001f194 Buyurtma idsi: {res['order']}\n"
            f"\u2640\ufe0f Buyurtma holati: \u23f3 Bajarilmoqda</b>",
            parse_mode="HTML"
        )
        await state.clear()
    else:
        err_msg = res.get('error', "Noma'lum xato")
        await c.message.edit_text(
            f"<b>\u274c Xato: {err_msg}\n\nQaytadan urinib ko'ring.</b>",
            parse_mode="HTML"
        )

# ===============================================================
# 22. YORDAMCHI CALLBACKLAR
# ===============================================================
@dp.callback_query(F.data == "delete_msg")
async def del_msg(c: CallbackQuery):
    try:
        await c.message.delete()
    except Exception:
        pass

# ===============================================================
# 23. BUYURTMA HOLATI TEKSHIRUVCHI (Background Task)
#     PDF p.3 — "Sizning XXXX raqamli buyurtmangiz bajarildi."
# ===============================================================
async def check_orders_task():
    """Har 1 daqiqada bajarilgan buyurtmalarni tekshiradi va foydalanuvchiga xabar beradi."""
    while True:
        await asyncio.sleep(300)  # 1 daqiqa
        try:
            rows = await get_pending_orders()
            for row in rows:
                db_id, user_id, order_id = row
                res = await smm_api.get_order_status(order_id)
                if res.get('status') in ('Completed', 'Partial'):
                    await mark_order_done(db_id)
                    # PDF p.3 — Buyurtma bajarildi shabloni
                    try:
                        await bot.send_message(
                            user_id,
                            f"<b>\u2705 Sizning {order_id} raqamli buyurtmangiz bajarildi.</b>",
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        logging.warning(f"Xabar yuborib bo'lmadi {user_id}: {e}")
        except Exception as e:
            logging.error(f"check_orders_task xato: {e}")
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# ===============================================================
# 24. ISHGA TUSHIRISH
# ===============================================================
async def main():
    init_db() 
keep_alive ()  # sinxron — bot ishga tushishdan oldin jadvallar tayyorlanadi
    asyncio.create_task(check_orders_task())
    logging.info("Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
