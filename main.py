import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta

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

# secret_role = "Gamer"

# bot = commands.Bot(command_prefix='!', intents=intents)
#
# secret_role = "Gamer"

@bot.event
async def on_ready():
    print(f"We are ready to go in, {bot.user.name}")

# @bot.event
# async def on_member_join(member):
#     await member.send(f"Welcome to the server {member.name}")

# @bot.event
# async def on_message(message):
#     if message.author == bot.user:
#         return
#
#     if "shit" in message.content.lower():
#         await message.delete()
#         await message.channel.send(f"{message.author.mention} - dont use that word!")
#
#     await bot.process_commands(message)
#
# @bot.command()
# async def hello(ctx):
#     await ctx.send(f"Hello {ctx.author.mention}!")

# @bot.command()
# async def assign(ctx):
#     role = discord.utils.get(ctx.guild.roles, name=secret_role)
#     if role:
#         await ctx.author.add_roles(role)
#         await ctx.send(f"{ctx.author.mention} is now assigned to {secret_role}")
#     else:
#         await ctx.send("Role doesn't exist")
#
# @bot.command()
# async def remove(ctx):
#     role = discord.utils.get(ctx.guild.roles, name=secret_role)
#     if role:
#         await ctx.author.remove_roles(role)
#         await ctx.send(f"{ctx.author.mention} has had the {secret_role} removed")
#     else:
#         await ctx.send("Role doesn't exist")

movie_sessions = {}


@bot.command(name="watch")
async def watch(ctx, start_time: str, duration_mins: int, location: str, *, movie_name: str):
    # Calculate end time
    now = datetime.now()
    end_time = now + timedelta(minutes=duration_mins)

    movie_sessions[movie_name.lower()] = {
        "location": location,
        "end_time": end_time,
        "original_name": movie_name
    }

    await ctx.send(f"🎬 Recorded! **{movie_name}** is playing at **{location}** for the next {duration_mins} minutes.")


@bot.command(name="where")
async def where(ctx):
    now = datetime.now()
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


@bot.command()
async def dm(ctx, *, msg):
    await ctx.author.send(f"You said {msg}")

@bot.command()
async def reply(ctx):
    await ctx.reply("This is a reply to your message!")

@bot.command()
async def poll(ctx, *, question):
    embed = discord.Embed(title="New Poll", description=question)
    poll_message = await ctx.send(embed=embed)
    await poll_message.add_reaction("👍")
    await poll_message.add_reaction("👎")

# @bot.command()
# @commands.has_role(secret_role)
# async def secret(ctx):
#     await ctx.send("Welcome to the club!")
#
# @secret.error
# async def secret_error(ctx, error):
#     if isinstance(error, commands.MissingRole):
#         await ctx.send("You do not have permission to do that!")

# 3. Start both
keep_alive()
bot.run(token, log_handler=handler, log_level=logging.DEBUG)