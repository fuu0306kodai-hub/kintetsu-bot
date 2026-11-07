import os
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import discord
from discord.ext import tasks, commands
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Botは元気に稼働中です！"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.start()

TOKEN = os.environ.get('DISCORD_BOT_TOKEN')
CHANNEL_ID = int(os.environ.get('DISCORD_CHANNEL_ID', 0))
YAHOO_URL = "https://yahoo.co.jp"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)
last_status = "平常運転"

@bot.event
async def on_ready():
    print(f'ログインしました: {bot.user.name}')
    check_kintetsu_status.start()

@tasks.loop(minutes=10)
async def check_kintetsu_status():
    global last_status
    if CHANNEL_ID == 0:
        return
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(YAHOO_URL) as response:
                if response.status != 200:
                    return
                html = await response.text()
        soup = BeautifulSoup(html, 'html.parser')
        status_tag = soup.select_one('#mdServiceStatus .trouble p')
        if not status_tag:
            return
        current_status = status_tag.text.strip()
        detail_tag = soup.select_one('#mdServiceStatus .trouble dl dt')
        detail_text = detail_tag.text.strip() if detail_tag else ""

        if current_status != last_status:
            last_status = current_status
            if "平常運転" not in current_status:
                channel = bot.get_channel(CHANNEL_ID)
                if channel:
                    embed = discord.Embed(
                        title="⚠️ 近鉄運行情報アラート",
                        description=f"**現在の状況:** {current_status}\n\n{detail_text}",
                        color=discord.Color.red()
                    )
                    embed.set_url(YAHOO_URL)
                    await channel.send(embed=embed)
            elif "平常運転" in current_status:
                channel = bot.get_channel(CHANNEL_ID)
                if channel:
                    embed = discord.Embed(
                        title="✅ 近鉄運行情報（復旧）",
                        description=f"近鉄線は**【平常運転】**に戻りました。",
                        color=discord.Color.green()
                    )
                    await channel.send(embed=embed)
    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    keep_alive()
    if TOKEN:
        bot.run(TOKEN)
