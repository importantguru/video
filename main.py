import os
import socket
import threading
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from pymongo import MongoClient
from dotenv import load_dotenv
from PIL import Image

# Load environment variables
load_dotenv()
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")

# Pyrogram client
bot = Client("thumb_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# MongoDB client
mongo = MongoClient(MONGO_URL)
db = mongo.thumbbot
thumbs_col = db.thumbs

# Health check thread (TCP, Koyeb)
def start_tcp_health_check():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("0.0.0.0", 8080))
    server_socket.listen(1)
    while True:
        conn, _ = server_socket.accept()
        conn.close()

threading.Thread(target=start_tcp_health_check, daemon=True).start()

# Ensure thumbnail folder
os.makedirs("thumbs", exist_ok=True)

# Helper functions
def get_thumb(user_id):
    data = thumbs_col.find_one({"user_id": user_id})
    return data["thumb_path"] if data else None

def save_thumb(user_id, path):
    thumbs_col.update_one({"user_id": user_id}, {"$set": {"thumb_path": path}}, upsert=True)

def delete_thumb(user_id):
    thumbs_col.delete_one({"user_id": user_id})

def resize_thumb(path):
    try:
        im = Image.open(path).convert("RGB")
        im.thumbnail((320, 180))
        im.save(path, "JPEG")
    except Exception as e:
        print(f"Thumbnail resize failed: {e}")

def is_video_doc(msg: Message):
    return msg.document and msg.document.mime_type and msg.document.mime_type.startswith("video/")

# Bot commands
@bot.on_message(filters.command("start"))
async def start(client, message: Message):
    await message.reply_text(
        "**👋 Welcome!**\n\n"
        "Send a photo to set a thumbnail.\n"
        "Then send a video or document and I’ll send it back with your thumbnail.\n\n"
        "**Commands:**\n"
        "`/show_thumb` – View thumbnail\n"
        "`/del_thumb` – Delete thumbnail"
    )

@bot.on_message(filters.command("show_thumb"))
async def show_thumb(client, message: Message):
    user_id = message.from_user.id
    path = get_thumb(user_id)
    if path and os.path.exists(path):
        await message.reply_photo(path, caption="📸 Current Thumbnail")
    else:
        await message.reply_text("❌ No thumbnail found.")

@bot.on_message(filters.command("del_thumb"))
async def del_thumb(client, message: Message):
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
    await message.download(file_name=path)
    resize_thumb(path)
    save_thumb(user_id, path)
    await message.reply_text("✅ Thumbnail saved!")

@bot.on_message(filters.video | filters.document)
async def process_video(client, message: Message):
    if not message.video and not is_video_doc(message):
        return  # Not a video or video document

    user_id = message.from_user.id
    thumb_path = get_thumb(user_id)

    if not thumb_path or not os.path.exists(thumb_path):
        await message.reply_text("❌ Please send a photo first to use as a thumbnail.")
        return

    await message.reply_chat_action(ChatAction.UPLOAD_VIDEO)
    video_path = await message.download()

    await message.reply_video(
        video=video_path,
        thumb=thumb_path,
        caption="🎬 Video with your custom thumbnail",
        supports_streaming=True
    )

    os.remove(video_path)

# Run bot
bot.run()
