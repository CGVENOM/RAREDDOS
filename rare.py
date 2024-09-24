import telebot
import requests
import subprocess
import datetime
import random
import string
import time
import logging
import asyncio
from pymongo import MongoClient
from aiogram import Bot, Dispatcher, executor
from aiohttp import ClientSession

# Insert your Telegram bot token here
bot_token = '7447089126:AAEfFYR_UJdA8sn4XWZNBvL8KdhJEG0TUbA'
proxy_url = 'https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http,socks4,socks5&timeout=500&country=all&ssl=all&anonymity=all'  # Replace with your proxy server URL

# Admin user IDs
admin_id = {"6906270448"}

# MongoDB Setup
MONGO_URL = "mongodb+srv://rareowner:rareowner@rareowner.q3rdy.mongodb.net/?retryWrites=true&w=majority&appName=rareowner"  # Replace with your MongoDB URL
client = MongoClient(MONGO_URL)
db = client['rareowner']  # Change the database name as needed
users_collection = db['users']
keys_collection = db['keys']
logs_collection = db['logs']
command_logs_collection = db['command_logs']

# Cooldown settings
COOLDOWN_TIME = 0  # in seconds
CONSECUTIVE_ATTACKS_LIMIT = 5
CONSECUTIVE_ATTACKS_COOLDOWN = 10  # in seconds

# In-memory storage
rare_cooldown = {}
consecutive_attacks = {}

# Log command to MongoDB
def log_command(user_id, target, port, time):
    user_info = bot.get_chat(user_id)
    username = user_info.username if user_info.username else f"UserID: {user_id}"
    
    log_entry = {
        "username": username,
        "user_id": user_id,
        "target": target,
        "port": port,
        "time": time,
        "log_time": datetime.datetime.now()
    }
    logs_collection.insert_one(log_entry)

def record_command_logs(user_id, command, target=None, port=None, time=None):
    log_entry = {
        "user_id": user_id,
        "command": command,
        "target": target,
        "port": port,
        "time": time,
        "timestamp": datetime.datetime.now()
    }
    command_logs_collection.insert_one(log_entry)

def get_remaining_approval_time(user_id):
    user = users_collection.find_one({"_id": user_id})
    if user:
        expiry_date = user.get("expiry_date")
        if expiry_date:
            remaining_time = expiry_date - datetime.datetime.now()
            if remaining_time.days < 0:
                return "Expired"
            else:
                return str(remaining_time)
    return "N/A"

def generate_key(length=11):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def add_time_to_current_date(hours=0, days=0, years=0):
    return (datetime.datetime.now() + datetime.timedelta(hours=hours, days=days) + datetime.timedelta(days=years*365)).strftime('%Y-%m-%d %H:%M:%S')

@bot.message_handler(commands=['genkey'])
def generate_key_command(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        command = message.text.split()
        if len(command) == 3:
            try:
                time_amount = int(command[1])
                time_unit = command[2].lower()
                if time_unit == 'hours':
                    expiration_date = add_time_to_current_date(hours=time_amount)
                elif time_unit == 'days':
                    expiration_date = add_time_to_current_date(days=time_amount)
                elif time_unit == 'years':  # Added support for years
                    expiration_date = add_time_to_current_date(years=time_amount)
                else:
                    raise ValueError("Invalid time unit")
                key = generate_key()
                
                # Store key and expiration in MongoDB
                keys_collection.insert_one({"key": key, "expiration_date": expiration_date})
                
                response = f"𝐋𝐢𝐜𝐞𝐧𝐬𝐞: {key}\n𝐄𝐬𝐩𝐢𝐫𝐞𝐬 𝐎𝐧: {expiration_date}\n𝐀𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞 𝐅𝐨𝐫 1 𝐓𝐞𝐥𝐞𝐠𝐫𝐚𝐦 𝐀𝐜𝐜𝐨𝐮𝐧𝐭 "
            except ValueError:
                response = "𝐏𝐥𝐞𝐚𝐬𝐞 𝐒𝐩𝐞𝐜𝐢𝐟𝐲 𝐀 𝐕𝐚𝐥𝐢𝐝 𝐍𝐮𝐦𝐛𝐞𝐫 𝐚𝐧𝐝 𝐮𝐧𝐢𝐭 𝐨𝐟 𝐓𝐢𝐦𝐞 (hours/days/years)."
        else:
            response = "𝐔𝐬𝐚𝐠𝐞: /genkey <amount> <hours/days/years>"
    else:
        response = "𝐎𝐧𝐥𝐲 𝐏𝐚𝐩𝐚 𝐎𝐟 𝐛𝐨𝐭 𝐜𝐚𝐧 𝐝𝐨 𝐭𝐡𝐢𝐬"

    bot.reply_to(message, response)

@bot.message_handler(commands=['redeem'])
def redeem_key_command(message):
    user_id = str(message.chat.id)
    command = message.text.split()
    if len(command) == 2:
        key = command[1]
        key_entry = keys_collection.find_one({"key": key})
        if key_entry:
            expiration_date = key_entry['expiration_date']
            
            user = users_collection.find_one({"_id": user_id})
            if user:
                user_expiration = datetime.datetime.strptime(user['expiry_date'], '%Y-%m-%d %H:%M:%S')
                new_expiration_date = max(user_expiration, datetime.datetime.now()) + datetime.timedelta(hours=1)
                users_collection.update_one({"_id": user_id}, {"$set": {"expiry_date": new_expiration_date.strftime('%Y-%m-%d %H:%M:%S')}})
            else:
                users_collection.insert_one({"_id": user_id, "expiry_date": expiration_date})
            
            keys_collection.delete_one({"key": key})
            response = f"✅𝐊𝐞𝐲 𝐫𝐞𝐝𝐞𝐞𝐦𝐞𝐝 𝐒𝐮𝐜𝐜𝐞𝐬𝐬𝐟𝐮𝐥𝐥𝐲! 𝐀𝐜𝐜𝐞𝐬𝐬 𝐆𝐫𝐚𝐧𝐭𝐞𝐝 𝐔𝐧𝐭𝐢𝐥: {expiration_date}"
        else:
            response = "𝐄𝐱𝐩𝐢𝐫𝐞𝐝 𝐊𝐞𝐲."
    else:
        response = "𝐔𝐬𝐚𝐠𝐞: /redeem <key>"

    bot.reply_to(message, response)

@bot.message_handler(commands=['myinfo'])
def get_user_info(message):
    user_id = str(message.chat.id)
    user_info = bot.get_chat(user_id)
    username = user_info.username if user_info.username else "N/A"
    user_role = "Admin" if user_id in admin_id else "User"
    remaining_time = get_remaining_approval_time(user_id)
    response = f"👤 Your Info:\n\n🆔 User ID: <code>{user_id}</code>\n📝 Username: {username}\n🔖 Role: {user_role}\n⏳ Remaining Approval Time: {remaining_time}"
    bot.reply_to(message, response, parse_mode="HTML")

@bot.message_handler(commands=['clearlogs'])
def clear_logs_command(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        logs_collection.delete_many({})
        command_logs_collection.delete_many({})
        response = "𝐅𝐮𝐜𝐤𝐞𝐝 𝐓𝐡𝐞 𝐋𝐨𝐠𝐬 𝐒𝐮𝐜𝐜𝐞𝐬𝐬𝐟𝐮𝐥𝐥𝐲✅"
    else:
        response = "𝐀𝐁𝐄 𝐆𝐀𝐍𝐃𝐔 𝐉𝐈𝐒𝐊𝐀 𝐁𝐎𝐓 𝐇 𝐖𝐀𝐇𝐈 𝐔𝐒𝐄 𝐊𝐑 𝐒𝐊𝐓𝐀 𝐄𝐒𝐄 𝐁𝐀𝐒."
    bot.reply_to(message, response)

# For proxy integration, use a ClientSession for aiogram and proxy for telebot:
async def on_startup(dp):
    async with ClientSession(trust_env=True) as session:
        bot = Bot(token=bot_token, session=session, proxy=proxy_url)
        await bot.send_message(chat_id="YOUR_CHAT_ID", text="Bot started with proxy")


@bot.message_handler(commands=['logs'])
def show_recent_logs(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        logs = logs_collection.find().sort("log_time", -1).limit(10)
        if logs:
            response = "Recent logs:\n\n"
            for log in logs:
                response += f"User: {log['username']}, Target: {log['target']}, Port: {log['port']}, Time: {log['time']}\n"
        else:
            response = "No logs found."
    else:
        response = "𝐁𝐇𝐀𝐆𝐉𝐀 𝐁𝐒𝐃𝐊 𝐎𝐍𝐋𝐘 𝐎𝐖𝐍𝐄𝐑 𝐂𝐀𝐍 𝐑𝐔𝐍 𝐓𝐇𝐀𝐓 𝐂𝐎𝐌𝐌𝐀𝐍𝐃"
    bot.reply_to(message, response)

@bot.message_handler(commands=['id'])
def show_user_id(message):
    user_id = str(message.chat.id)
    response = f"𝐋𝐄 𝐑𝐄 𝐋𝐔𝐍𝐃 𝐊𝐄 𝐓𝐄𝐑𝐈 𝐈𝐃: {user_id}"
    bot.reply_to(message, response)

@bot.message_handler(commands=['mylogs'])
def show_command_logs(message):
    user_id = str(message.chat.id)
    if user_id in users:
        try:
            with open(LOG_FILE, "r") as file:
                command_logs = file.readlines()
                user_logs = [log for log in command_logs if f"UserID: {user_id}" in log]
                if user_logs:
                    response = "𝐋𝐞 𝐫𝐞 𝐋𝐮𝐧𝐝 𝐤𝐞 𝐘𝐞 𝐭𝐞𝐫𝐢 𝐟𝐢𝐥𝐞:\n" + "".join(user_logs)
                else:
                    response = "𝐔𝐒𝐄 𝐊𝐑𝐋𝐄 𝐏𝐄𝐇𝐋𝐄 𝐅𝐈𝐑 𝐍𝐈𝐊𝐀𝐋𝐔𝐍𝐆𝐀 𝐓𝐄𝐑𝐈 𝐅𝐈𝐋𝐄."
        except FileNotFoundError:
            response = "No command logs found."
    else:
        response = "𝐘𝐄 𝐆𝐀𝐑𝐄𝐄𝐁 𝐄𝐒𝐊𝐈 𝐌𝐀𝐊𝐈 𝐂𝐇𝐔𝐓 𝐀𝐂𝐂𝐄𝐒𝐒 𝐇𝐈 𝐍𝐀𝐇𝐈 𝐇 𝐄𝐒𝐊𝐄 𝐏𝐀𝐒"

    bot.reply_to(message, response)

@bot.message_handler(commands=['help'])
def show_help(message):
    help_text = '''𝐌𝐄𝐑𝐀 𝐋𝐀𝐍𝐃 𝐊𝐀𝐑𝐄 𝐇𝐄𝐋𝐏 𝐓𝐄𝐑𝐈 𝐋𝐄 𝐅𝐈𝐑 𝐁𝐇𝐈 𝐁𝐀𝐓𝐀 𝐃𝐄𝐓𝐀:
💥 /rare 𝐁𝐆𝐌𝐈 𝐊𝐄 𝐒𝐄𝐑𝐕𝐄𝐑 𝐊𝐈 𝐂𝐇𝐔𝐃𝐀𝐘𝐈.
💥 /rules: 𝐅𝐨𝐥𝐥𝐨𝐰 𝐞𝐥𝐬𝐞 𝐑𝐚𝐩𝐞.
💥 /mylogs: 𝐀𝐏𝐊𝐄 𝐏𝐎𝐎𝐑𝐀𝐍𝐄 𝐊𝐀𝐀𝐑𝐍𝐀𝐌𝐄 𝐉𝐀𝐍𝐍𝐄 𝐊 𝐋𝐈𝐘𝐄.
💥 /plan: 𝐉𝐢𝐧𝐝𝐠𝐢 𝐦𝐞 𝐊𝐨𝐞 𝐏𝐋𝐀𝐍 𝐧𝐚𝐡𝐢 𝐡𝐨𝐧𝐚 𝐂𝐡𝐚𝐡𝐢𝐲𝐞.
💥 /redeem <key>: 𝐊𝐞𝐲 𝐑𝐞𝐝𝐞𝐞𝐦 𝐰𝐚𝐥𝐚 𝐂𝐨𝐦𝐦𝐚𝐧𝐝.

🤖 Admin commands:
💥 /genkey <amount> <hours/days>: 𝐓𝐎 𝐌𝐀𝐊𝐄 𝐊𝐄𝐘.
💥 /allusers: 𝐋𝐢𝐒𝐓 𝐎𝐅 𝐂𝐇𝐔𝐓𝐘𝐀 𝐔𝐒𝐄𝐑𝐒.
💥 /logs: 𝐀𝐀𝐏𝐊𝐄 𝐊𝐀𝐑𝐓𝐎𝐎𝐓𝐄 𝐉𝐀𝐍𝐍𝐄 𝐖𝐀𝐋𝐀 𝐂𝐎𝐌𝐌𝐀𝐍𝐃.
💥 /clearlogs: 𝐅𝐔𝐂𝐊 𝐓𝐇𝐄 𝐋𝐎𝐆 𝐅𝐈𝐋𝐄.
💥 /broadcast <message>: 𝐁𝐑𝐎𝐀𝐃𝐂𝐀𝐒𝐓 𝐊𝐀 𝐌𝐀𝐓𝐋𝐀𝐁 𝐓𝐎 𝐏𝐀𝐓𝐀 𝐇𝐎𝐆𝐀 𝐀𝐍𝐏𝐀𝐃.
'''
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['start'])
def welcome_start(message):
    user_name = message.from_user.first_name
    response = f'''𝐐 𝐫𝐞 𝐂𝐇𝐀𝐏𝐑𝐈, {user_name}! 𝐓𝐡𝐢𝐬 𝐢𝐒 𝐘𝐎𝐔𝐑 𝐅𝐀𝐓𝐇𝐑𝐞𝐫𝐒 𝐁𝐨𝐓 𝐒𝐞𝐫𝐯𝐢𝐜𝐞.
🤖𝐀𝐍𝐏𝐀𝐃 𝐔𝐒𝐄 𝐇𝐄𝐋𝐏 𝐂𝐎𝐌𝐌𝐀𝐍𝐃: /help
'''
    bot.reply_to(message, response)

@bot.message_handler(commands=['rules'])
def welcome_rules(message):
    user_name = message.from_user.first_name
    response = f'''{user_name}, 𝐅𝐎𝐋𝐋𝐎𝐖 𝐓𝐇𝐈𝐒 𝐑𝐔𝐋𝐄𝐒 𝐄𝐋𝐒𝐄 𝐘𝐎𝐔𝐑 𝐌𝐎𝐓𝐇𝐄𝐑 𝐈𝐒 𝐌𝐈𝐍𝐄:

1. Don't run too many attacks to avoid a ban from the bot.
2. Don't run 2 attacks at the same time to avoid a ban from the bot.
3. We check the logs daily, so follow these rules to avoid a ban!
'''
    bot.reply_to(message, response)

@bot.message_handler(commands=['plan'])
def welcome_plan(message):
    user_name = message.from_user.first_name
    response = f'''{user_name}, 𝐏𝐋𝐀𝐍 𝐃𝐄𝐊𝐇𝐄𝐆𝐀 𝐓𝐔 𝐆𝐀𝐑𝐄𝐄𝐁😂:

VIP 🌟:
-> Attack time: 1000 seconds
-> After attack limit: 1 minutes
-> Concurrent attacks: 3

𝐓𝐄𝐑𝐈 𝐀𝐔𝐊𝐀𝐃 𝐒𝐄 𝐁𝐀𝐇𝐀𝐑 💸:
1𝐃𝐚𝐲: 200 𝐫𝐬
3𝐃𝐚𝐲: 450 𝐫𝐬
1𝐖𝐞𝐞𝐤: 800 𝐫𝐬
2𝐖𝐞𝐞𝐤: 1200 𝐫𝐬
𝐌𝐨𝐧𝐓𝐡: 1700 𝐫𝐬 
@RARExxOWNER 💥
'''
    bot.reply_to(message, response)

@bot.message_handler(commands=['admincmd'])
def admin_commands(message):
    user_name = message.from_user.first_name
    response = f'''{user_name}, 𝐋𝐞 𝐫𝐞 𝐥𝐮𝐧𝐝 𝐊𝐞 𝐘𝐞 𝐑𝐡𝐞 𝐓𝐞𝐫𝐞 𝐜𝐨𝐦𝐦𝐚𝐧𝐝:

💥 /genkey 𝐆𝐞𝐧𝐞𝐫𝐚𝐭𝐞 𝐚 𝐤𝐞𝐲.
💥 /allusers: 𝐋𝐢𝐬𝐭 𝐨𝐟 𝐜𝐡𝐮𝐭𝐲𝐚 𝐮𝐬𝐞𝐫𝐬.
💥 /logs: 𝐒𝐡𝐨𝐰 𝐥𝐨𝐠𝐬 𝐟𝐢𝐥𝐞.
💥 /clearlogs: 𝐅𝐮𝐜𝐤 𝐓𝐡𝐞 𝐥𝐨𝐆 𝐟𝐢𝐥𝐞.
💥 /broadcast <message>: 𝐁𝐫𝐨𝐚𝐝𝐜𝐚𝐬𝐭.
'''
    bot.reply_to(message, response)

@bot.message_handler(commands=['remove'])
def remove_user(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        command = message.text.split()
        if len(command) == 2:
            target_user_id = command[1]
            if target_user_id in users:
                del users[target_user_id]
                save_users()
                response = f"𝐔𝐬𝐞𝐫 {target_user_id} 𝐒𝐮𝐜𝐜𝐞𝐬𝐟𝐮𝐥𝐥𝐲 𝐅𝐮𝐂𝐤𝐞𝐃."
            else:
                response = "𝐋𝐎𝐋 𝐮𝐬𝐞𝐫 𝐧𝐨𝐭 𝐟𝐨𝐮𝐧𝐝😂"
        else:
            response = "Usage: /remove <user_id>"
    else:
        response = "𝐎𝐍𝐋𝐘 𝐁𝐎𝐓 𝐊𝐄 𝐏𝐄𝐄𝐓𝐀𝐉𝐈 𝐂𝐀𝐍 𝐃𝐎 𝐓𝐇𝐈𝐒"

    bot.reply_to(message, response)

@bot.message_handler(commands=['broadcast'])
def broadcast_message(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        command = message.text.split(maxsplit=1)
        if len(command) > 1:
            message_to_broadcast = "𝐌𝐄𝐒𝐒𝐀𝐆𝐄 𝐅𝐑𝐎𝐌 𝐘𝐎𝐔𝐑 𝐅𝐀𝐓𝐇𝐄𝐑:\n\n" + command[1]
            for user_id in users:
                try:
                    bot.send_message(user_id, message_to_broadcast)
                except Exception as e:
                    print(f"Failed to send broadcast message to user {user_id}: {str(e)}")
            response = "Broadcast message sent successfully to all users 👍."
        else:
            response = "𝐁𝐑𝐎𝐀𝐃𝐂𝐀𝐒𝐓 𝐊𝐄 𝐋𝐈𝐘𝐄 𝐌𝐄𝐒𝐒𝐀𝐆𝐄 𝐓𝐎 𝐋𝐈𝐊𝐇𝐃𝐄 𝐆𝐀𝐍𝐃𝐔"
    else:
        response = "𝐎𝐍𝐋𝐘 𝐁𝐎𝐓 𝐊𝐄 𝐏𝐄𝐄𝐓𝐀𝐉𝐈 𝐂𝐀𝐍 𝐑𝐔𝐍 𝐓𝐇𝐈𝐒 𝐂𝐎𝐌𝐌𝐀𝐍𝐃"

    bot.reply_to(message, response)

if __name__ == "__main__":
    load_data()
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(e)
            # Add a small delay to avoid rapid looping in case of persistent errors
            time.sleep(15)
