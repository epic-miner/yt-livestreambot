import os
import subprocess
import telebot

# Replace this with your Telegram bot token
TELEGRAM_BOT_TOKEN = "8026602763:AAGwDwsj44nxRnKatGGmGOPz4guQo9fghww"

# Initialize the bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Dictionary to store user data (including FFmpeg processes)
user_data = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Welcome! To stream a video, follow these steps:\n"
                          "1. Send your YouTube stream key using /key <your_stream_key>.\n"
                          "2. Send the video URL using /url <video_url>.\n"
                          "Use /stop to stop the live stream.")

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
        # Start FFmpeg as a subprocess and store the process in user_data
        ffmpeg_process = subprocess.Popen(ffmpeg_command)
        user_data[chat_id]['ffmpeg_process'] = ffmpeg_process
        bot.send_message(chat_id, "Streaming started successfully!")
    except Exception as e:
        bot.send_message(chat_id, f"Failed to stream. Error: {str(e)}")

@bot.message_handler(commands=['stop'])
def stop_stream(message):
    chat_id = message.chat.id
    if chat_id in user_data and 'ffmpeg_process' in user_data[chat_id]:
        ffmpeg_process = user_data[chat_id]['ffmpeg_process']
        
        # Terminate the FFmpeg process
        ffmpeg_process.terminate()
        ffmpeg_process.wait()  # Ensure the process has terminated
        
        # Remove the FFmpeg process from user_data
        del user_data[chat_id]['ffmpeg_process']
        
        bot.reply_to(message, "Live stream stopped successfully!")
    else:
        bot.reply_to(message, "No active stream found. Use /url to start a new stream.")

@bot.message_handler(commands=['reset'])
def reset(message):
    chat_id = message.chat.id
    if chat_id in user_data:
        if 'ffmpeg_process' in user_data[chat_id]:
            # Stop the FFmpeg process if it's running
            ffmpeg_process = user_data[chat_id]['ffmpeg_process']
            ffmpeg_process.terminate()
            ffmpeg_process.wait()
            del user_data[chat_id]['ffmpeg_process']
        
        # Clear all user data
        user_data.pop(chat_id, None)
    
    bot.reply_to(message, "Your stream key, video URL, and stream have been reset.")

print("Bot is running...")
bot.polling()
