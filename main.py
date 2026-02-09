import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta
import pytz

local_tz = pytz.timezone('America/Chicago')

# 1. Setup a tiny Flask server
app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run():
  app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# 2. Discord bot logic

load_dotenv()
token = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f"We are ready to go in, {bot.user.name}")

movie_sessions = {}


@bot.command(name="watch")
async def watch(ctx, duration_mins: int, location: str, movie_name: str, start_time: str = None):
    # 1. Determine the start time
    if start_time is None:
        # Use current time in Champaign/Chicago
        start_dt = datetime.now(local_tz)
    else:
        try:
            # Try to parse the user's input (assumes HH:MM format)
            input_time = datetime.strptime(start_time, "%H:%M").time()
            start_dt = datetime.now(local_tz).replace(
                hour=input_time.hour,
                minute=input_time.minute,
                second=0,
                microsecond=0
            )
        except ValueError:
            await ctx.send("❌ Invalid time format! Please use HH:MM (e.g., 14:30).")
            return

    # 2. Calculate end time
    end_dt = start_dt + timedelta(minutes=duration_mins)

    movie_sessions[movie_name.lower()] = {
        "location": location,
        "end_time": end_dt,
        "original_name": movie_name
    }

    start_str = start_dt.strftime("%I:%M %p")
    await ctx.send(f"🎬 **{movie_name}** recorded! Starting at **{start_str}** in **{location}**.")


@watch.error
async def watch_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title="🎬 How to use !watch",
            description="It looks like you missed some details! Here is the correct format:",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Format",
            value="`!watch <duration_mins> <location> <movie_name> [start_time]`",
            inline=False
        )
        embed.add_field(
            name="Examples",
            value=(
                "**Start now:** `!watch 120 LivingRoom \"The Union\"` \n"
                "**Start later:** `!watch 90 Theater \"Inception\" 20:30`"
            ),
            inline=False
        )
        embed.set_footer(text="Note: If location or movie name has spaces, use \"quotes\".")

        await ctx.send(embed=embed)

@bot.command(name="where")
async def where(ctx):
    now = datetime.now(local_tz)
    active_movies = []

    # Clean up expired movies and find active ones
    for name, data in list(movie_sessions.items()):
        if now < data["end_time"]:
            active_movies.append(f"• **{data['original_name']}** is at **{data['location']}**")
        else:
            del movie_sessions[name]

    if active_movies:
        response = "🍿 **Current Movies Playing:**\n" + "\n".join(active_movies)
    else:
        response = "Currently, no movies are being watched. Use `!watch` to start one!"

    await ctx.send(response)

# 3. Start both
keep_alive()
bot.run(token, log_handler=handler, log_level=logging.DEBUG)