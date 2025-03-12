import os
import subprocess
import telebot

# Replace this with your Telegram bot token
TELEGRAM_BOT_TOKEN = "7260616953:AAE4Ht4aVoSWm4oH-UWUGkvIROdI_cpmEMg"

# Initialize the bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Dictionary to store user data
user_data = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Welcome! To stream a video, follow these steps:\n"
                          "1. Send your YouTube stream key using /key <your_stream_key>.\n"
                          "2. Send the video URL using /url <video_url>.")

@bot.message_handler(commands=['key'])
def set_stream_key(message):
    try:
        stream_key = message.text.split()[1]
        user_data[message.chat.id] = {'stream_key': stream_key}
        bot.reply_to(message, f"Stream key set to: {stream_key}")
    except IndexError:
        bot.reply_to(message, "Please provide your stream key like this:\n/key <your_stream_key>")

@bot.message_handler(commands=['url'])
def set_video_url(message):
    chat_id = message.chat.id
    try:
        video_url = message.text.split()[1]
        if chat_id not in user_data or 'stream_key' not in user_data[chat_id]:
            bot.reply_to(message, "Please set your stream key first using /key <your_stream_key>.")
            return

        user_data[chat_id]['video_url'] = video_url
        bot.reply_to(message, f"Video URL set to: {video_url}")

        # Start downloading and streaming the video
        download_and_stream(chat_id, video_url)
    except IndexError:
        bot.reply_to(message, "Please provide the video URL like this:\n/url <video_url>")

def download_and_stream(chat_id, video_url):
    stream_key = user_data[chat_id].get('stream_key')
    video_file = "stream.mp4"

    # Step 1: Download the video using yt-dlp
    try:
        bot.send_message(chat_id, "Downloading video...")
        download_command = ["yt-dlp", "-o", video_file, video_url]
        subprocess.run(download_command, check=True)
        bot.send_message(chat_id, "Video downloaded successfully.")
    except subprocess.CalledProcessError:
        bot.send_message(chat_id, "Failed to download the video. Please check the URL.")
        return

    # Step 2: Start streaming using FFmpeg
    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    ffmpeg_command = [
        "ffmpeg",
        "-re",
        "-stream_loop", "-1",
        "-i", video_file,
        "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-b:v", "3000k",
        "-maxrate", "3000k",
        "-bufsize", "6000k",
        "-pix_fmt", "yuv420p",
        "-g", "50",
        "-c:a", "aac",
        "-b:a", "160k",
        "-ar", "44100",
        "-f", "flv",
        rtmp_url
    ]
    
    bot.send_message(chat_id, "Starting stream...")

    try:
        subprocess.Popen(ffmpeg_command)  # Run FFmpeg in the background
        bot.send_message(chat_id, "Streaming started successfully!")
    except Exception as e:
        bot.send_message(chat_id, f"Failed to stream. Error: {str(e)}")

@bot.message_handler(commands=['reset'])
def reset(message):
    user_data.pop(message.chat.id, None)
    bot.reply_to(message, "Your stream key and video URL have been reset.")

print("Bot is running...")
bot.polling()
