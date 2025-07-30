import os
from pyrogram import Client, filters
from pyrogram.types import Message
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")

bot = Client("thumb_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
mongo = MongoClient(MONGO_URL)
db = mongo.thumbbot
thumbs_col = db.thumbs

def get_thumb(user_id):
    data = thumbs_col.find_one({"user_id": user_id})
    return data["thumb_path"] if data else None

def save_thumb(user_id, path):
    thumbs_col.update_one({"user_id": user_id}, {"$set": {"thumb_path": path}}, upsert=True)

def delete_thumb(user_id):
    thumbs_col.delete_one({"user_id": user_id})

@bot.on_message(filters.command("start"))
async def start(client, message: Message):
    await message.reply_text(
        "**👋 Welcome!**\n\n"
        "This bot lets you add custom thumbnails to Telegram videos.\n\n"
        "**📌 How to use:**\n"
        "1. Send a photo – This becomes your thumbnail\n"
        "2. Send a video – The bot will send it back with the thumbnail\n\n"
        "**🔧 Commands:**\n"
        "`/show_thumb` – View current thumbnail\n"
        "`/del_thumb` – Delete saved thumbnail"
    )

@bot.on_message(filters.command("show_thumb"))
async def show_thumb(client, message: Message):
    user_id = message.from_user.id
    path = get_thumb(user_id)
    if path and os.path.exists(path):
        await message.reply_photo(path, caption="📸 Current Thumbnail")
    else:
        await message.reply_text("❌ No thumbnail set. Send a photo to set one.")

@bot.on_message(filters.command("del_thumb"))
async def delete_thumb_cmd(client, message: Message):
    user_id = message.from_user.id
    path = get_thumb(user_id)
    if path and os.path.exists(path):
        os.remove(path)
    delete_thumb(user_id)
    await message.reply_text("✅ Thumbnail deleted.")

@bot.on_message(filters.photo)
async def save_thumb_cmd(client, message: Message):
    user_id = message.from_user.id
    path = f"thumbs/{user_id}.jpg"
    os.makedirs("thumbs", exist_ok=True)
    await message.download(file_name=path)
    save_thumb(user_id, path)
    await message.reply_text("✅ Thumbnail saved!")

@bot.on_message(filters.video)
async def send_video_with_thumb(client, message: Message):
    user_id = message.from_user.id
    path = get_thumb(user_id)
    if not path or not os.path.exists(path):
        await message.reply_text("❌ No thumbnail found. Please send a photo first.")
        return
    await message.reply_chat_action("upload_video")
    await message.reply_video(
        video=message.video.file_id,
        thumb=path,
        caption="🎬 Video with your custom thumbnail"
    )

bot.run()
