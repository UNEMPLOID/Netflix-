import telebot
from telebot import types
import logging
import time
import os
from pymongo import MongoClient, errors
from datetime import datetime, timedelta

# Enable logging
logging.basicConfig(level=logging.INFO)

# Bot token and log group ID
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7492081634:AAFc01F_exFFw4KhvFVn6Vu1xqx3WnH_53k')
LOG_GROUP_ID = int(os.getenv('LOG_GROUP_ID', '-1002155266073'))

# Channels and group
REQUIRED_CHANNELS = ["@falconsec", "@Falcon_security", "@Bot_Colony"]
REQUIRED_GROUP = "-1001685012914"
OWNER_ID = int(os.getenv('OWNER_ID', '5460343986'))

# Initialize bot
bot = telebot.TeleBot(TOKEN)

# Initialize MongoDB database
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb+srv://4caocfnwy8:SRwmd2AvS7a9iX1J@cluster0.inf9x.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')

try:
    client = MongoClient(MONGODB_URI)
    db = client["mydatabase"]
    logging.info("Connected to MongoDB using SRV connection string.")
except errors.ConfigurationError:
    MONGODB_URI = "mongodb://4caocfnwy8:SRwmd2AvS7a9iX1J@cluster0-shard-00-00.inf9x.mongodb.net:27017,cluster0-shard-00-01.inf9x.mongodb.net:27017,cluster0-shard-00-02.inf9x.mongodb.net:27017/mydatabase?ssl=true&replicaSet=atlas-abcdef-shard-0&authSource=admin&retryWrites=true&w=majority"
    client = MongoClient(MONGODB_URI)
    db = client["mydatabase"]
    logging.info("Connected to MongoDB using standard connection string.")

users_collection = db.users
logs_collection = db.logs
paid_members_collection = db.paid_members

def log_action(user_id, username, action):
    logs_collection.insert_one({
        'user_id': user_id,
        'username': username,
        'action': action,
        'timestamp': datetime.now()
    })

@bot.message_handler(commands=['start'])
def send_welcome(message: telebot.types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.username or f"User_{user_id}"

    users_collection.update_one(
        {'user_id': user_id},
        {'$set': {'username': user_name, 'received_netflix_button': False}},
        upsert=True
    )

    log_action(user_id, user_name, 'start')

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("FALCONSEC", url="https://t.me/falconsec"),
        types.InlineKeyboardButton("FALCON SECURITY", url="https://t.me/Falcon_security")
    )
    keyboard.add(
        types.InlineKeyboardButton("Support Chat", url="https://t.me/INDIAN_HACKER_GROUP"),
        types.InlineKeyboardButton("BOT COLONY", url="https://t.me/BOT_COLONY")
    )
    keyboard.add(
        types.InlineKeyboardButton("Verify", callback_data='verify')
    )
    keyboard.add(
        types.InlineKeyboardButton("Owner", url="https://t.me/Moon_God_Khonsu")
    )

    welcome_message = "Welcome! Please join all the required channels and group to use the bot."
    try:
        bot.send_photo(message.chat.id, "https://i.ibb.co/HCyYbzJ/IMG-20240818-123937-520.jpg", caption=welcome_message, reply_markup=keyboard)
    except telebot.apihelper.ApiTelegramException as e:
        logging.error(f"Failed to send welcome message to user {user_id}: {e}")
        bot.send_message(
            chat_id=LOG_GROUP_ID,
            text=f"Failed to send welcome message to user {user_id}: {e}"
        )

    try:
        total_users_count = users_collection.count_documents({})
        bot.send_message(
            chat_id=LOG_GROUP_ID,
            text=f"➕ New User Notification ➕\n\n👤 User: @{user_name}\n🆔 User ID: {user_id}\n🌝 Total Users Count: {total_users_count}"
        )
    except telebot.apihelper.ApiTelegramException as e:
        logging.error(f"Failed to log new user start for user {user_id}: {e}")

 @bot.callback_query_handler(func=lambda call: call.data == 'verify')
def process_callback_verify(call: telebot.types.CallbackQuery):
    user_id = call.from_user.id
    user_name = call.from_user.username or f"User_{user_id}"

    # Check if the user has already received the Netflix button
    user_data = users_collection.find_one({'user_id': user_id})
    if user_data and user_data.get('received_netflix_button'):
        # Check if the user has a valid subscription
        paid_member = paid_members_collection.find_one({'user_id': user_id})
        if paid_member and paid_member['expiry'] > datetime.now():
            bot.send_message(
                chat_id=user_id,
                text="You have already received the Netflix button. Your subscription is still active."
            )
            return
        else:
            bot.send_message(
                chat_id=user_id,
                text="Your subscription has expired. Please start the bot again to get a new subscription."
            )
            return

    # Verification check
    try:
        is_verified = all([bot.get_chat_member(channel, user_id).status in ['member', 'administrator', 'creator'] for channel in REQUIRED_CHANNELS])
        is_verified &= bot.get_chat_member(REQUIRED_GROUP, user_id).status in ['member', 'administrator', 'creator']
    except telebot.apihelper.ApiTelegramException as e:
        logging.error(f"Verification check failed for user {user_id}: {e}")
        bot.send_message(
            chat_id=user_id,
            text="Error during verification. Please try again later."
        )
        return
    
    if is_verified:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton("Watch Netflix", web_app=types.WebAppInfo(url="https://iosmirror.cc/home?app=1"))
        )
        try:
            message = bot.send_message(
                chat_id=user_id,
                text="Thank you for using our service. Press the Watch Netflix button to use Netflix.",
                reply_markup=keyboard
            )
            log_action(user_id, user_name, 'verified')

            # Mark that the user has received the Netflix button
            users_collection.update_one(
                {'user_id': user_id},
                {'$set': {'received_netflix_button': True}}
            )

            # Delete the Netflix button message after 25 seconds
            time.sleep(25)
            bot.delete_message(chat_id=user_id, message_id=message.message_id)
            bot.send_message(chat_id=user_id, text="The Netflix button has expired. Please start the bot again.")
        except telebot.apihelper.ApiTelegramException as e:
            logging.error(f"Failed to send Netflix message to user {user_id}: {e}")
    else:
        try:
            bot.send_message(
                chat_id=user_id,
                text="Please join all the required channels and group first to use the bot."
            )
        except telebot.apihelper.ApiTelegramException as e:
            logging.error(f"Failed to send verification failure message to user {user_id}: {e}")

    else:
        try:
            bot.send_message(
                chat_id=user_id,
                text="Please join all the required channels and group first to use the bot."
            )
        except telebot.apihelper.ApiTelegramException as e:
            logging.error(f"Failed to send verification failure message to user {user_id}: {e}")

@bot.message_handler(commands=['broadcast'])
def broadcast(message: telebot.types.Message):
    if message.from_user.id == OWNER_ID:
        message_text = ' '.join(message.text.split()[1:])
        sent_count = 0
        for user in users_collection.find({}):
            user_id = user['user_id']
            try:
                bot.send_message(chat_id=user_id, text=message_text)
                sent_count += 1
            except telebot.apihelper.ApiTelegramException as e:
                logging.warning(f"Could not send message to {user_id}: {e}")
        try:
            bot.send_message(message.chat.id, f"Broadcast sent to {sent_count} users.")
            log_action(message.from_user.id, message.from_user.username, 'broadcast')
        except telebot.apihelper.ApiTelegramException as e:
            logging.error(f"Failed to send broadcast confirmation to owner: {e}")
    else:
        try:
            bot.send_message(message.chat.id, "You are not authorized to use this command.")
        except telebot.apihelper.ApiTelegramException as e:
            logging.error(f"Failed to send unauthorized message to user {message.from_user.id}: {e}")

@bot.message_handler(commands=['stats'])
def stats(message: telebot.types.Message):
    user_count = users_collection.count_documents({})
    try:
        bot.send_message(message.chat.id, f"Total users who started the bot: {user_count}")
    except telebot.apihelper.ApiTelegramException as e:
        logging.error(f"Failed to send stats to user {message.from_user.id}: {e}")

@bot.message_handler(commands=['add'])
def add_paid_member(message: telebot.types.Message):
    if message.from_user.id == OWNER_ID:
        try:
            _, user_id, duration = message.text.split()
            user_id = int(user_id)
            if duration.endswith('m'):
                expiry = datetime.now() + timedelta(days=int(duration[:-1]) * 30)
            elif duration.endswith('d'):
                expiry = datetime.now() + timedelta(days=int(duration[:-1]))
            else:
                bot.send_message(message.chat.id, "Invalid duration format. Use 'm' for months and 'd' for days.")
                return

            paid_members_collection.update_one(
                {'user_id': user_id},
                {'$set': {'expiry': expiry}},
                upsert=True
            )
            bot.send_message(message.chat.id, f"User {user_id} has been added as a paid member until {expiry}.")
        except Exception as e:
            bot.send_message(message.chat.id, "Failed to add paid member. Make sure you use the correct format.")
            logging.error(f"Error adding paid member: {e}")
    else:
        bot.send_message(message.chat.id, "You are not authorized to use this command.")

@bot.message_handler(commands=['remove'])
def remove_paid_member(message: telebot.types.Message):
    if message.from_user.id == OWNER_ID:
        try:
            _, user_id = message.text.split()
            user_id = int(user_id)
            paid_members_collection.delete_one({'user_id': user_id})
            bot.send_message(message.chat.id, f"User {user_id} has been removed from paid members.")
        except Exception as e:
            bot.send_message(message.chat.id, "Failed to remove paid member.")
            logging.error(f"Error removing paid member: {e}")
    else:
        bot.send_message(message.chat.id, "You are not authorized to use this command.")

# Start polling
while True:
    try:
        logging.info("Bot polling started.")
        bot.polling(none_stop=True)
    except Exception as e:
        logging.error(f"Bot polling failed: {e}")
        time.sleep(15)
        
