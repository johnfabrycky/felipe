import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta
import pytz
import pandas as pd

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

bot.remove_command('help')

@bot.event
async def on_ready():
    print(f"We are ready to go in, {bot.user.name}")

movie_sessions = {}


@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(
        title="🤖 Movie Bot Help",
        description="I help you track what movies are playing and where!",
        color=discord.Color.green()
    )

    embed.add_field(
        name="🎬 !watch",
        value=(
            "**Usage:** `!watch <duration> <location> <movie> [start_time]`\n"
            "Records a movie session. If no start time is given, it starts now.\n"
            "*Example:* `!watch 120 LivingRoom \"The Union\" 20:30`"
        ),
        inline=False
    )

    embed.add_field(
        name="🍿 !where",
        value="Shows all movies currently playing or starting soon.",
        inline=False
    )

    embed.set_footer(text="Pro-tip: Use \"quotes\" if your movie name has spaces!")

    await ctx.send(embed=embed)


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


@bot.command(name="meal")
async def meal(ctx, week: int, day: str, meal_type: str):
    """
    Usage: !meal 1 Monday Lunch
    """
    try:
        # Load the CSV (Ensure this file is in your GitHub repo)
        df = pd.read_csv('Copy of Spring 26 Workschedule - Meal Schedule 2.csv')

        # The actual headers are in row 0
        headers = df.iloc[0].tolist()

        # Format inputs
        day_query = day.strip().capitalize()
        meal_query = meal_type.strip().capitalize()
        col_name = f"Week {week} - {meal_query}"

        # 1. Find the column index
        if col_name not in headers:
            await ctx.send(f"❌ Could not find a column for **Week {week} {meal_query}**.")
            return

        col_idx = headers.index(col_name)

        # 2. Find the row for the day
        data_rows = df.iloc[1:]
        match = data_rows[data_rows['Unnamed: 0'].str.strip().str.capitalize() == day_query]

        if match.empty:
            await ctx.send(f"❌ Day **{day_query}** not found in the schedule.")
            return

        # 3. Extract and send the result
        menu_item = match.iloc[0, col_idx]

        if pd.isna(menu_item) or str(menu_item).lower() == 'nan':
            await ctx.send(f"🍽️ No {meal_query} is scheduled for {day_query} in Week {week}.")
        else:
            await ctx.send(f"🍴 **{day_query} Week {week} {meal_query}:** {menu_item}")

    except FileNotFoundError:
        await ctx.send("❌ Error: Meal schedule CSV file is missing from the server.")
    except Exception as e:
        await ctx.send(f"❌ An unexpected error occurred: {e}")


@meal.error
async def meal_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❓ **Usage:** `!meal <week_num> <day> <lunch/dinner>`\n*Example:* `!meal 1 Monday Dinner`")


# Helper function to reuse the CSV logic
def get_meal_menu_logic(week, day, meal_type):
    df = pd.read_csv('Copy of Spring 26 Workschedule - Meal Schedule 2.csv')
    headers = df.iloc[0].tolist()
    col_name = f"Week {week} - {meal_type}"

    if col_name not in headers: return "Not Found"

    col_idx = headers.index(col_name)
    data_rows = df.iloc[1:]
    match = data_rows[data_rows['Unnamed: 0'].str.strip() == day]

    if match.empty: return "No data for this day"

    item = match.iloc[0, col_idx]
    return item if pd.notna(item) else "No meal scheduled"

def is_uiuc_break(current_date):
    """Checks if the given date falls during UIUC Spring or Fall break."""
    # Spring Break 2026: March 14 to March 22
    spring_break_start = datetime(2026, 3, 14, tzinfo=local_tz)
    spring_break_end = datetime(2026, 3, 22, 23, 59, tzinfo=local_tz)

    # Thanksgiving Break 2026: Nov 21 to Nov 29
    fall_break_start = datetime(2026, 11, 21, tzinfo=local_tz)
    fall_break_end = datetime(2026, 11, 29, 23, 59, tzinfo=local_tz)

    if spring_break_start <= current_date <= spring_break_end:
        return "Spring Break 🌸"
    elif fall_break_start <= current_date <= fall_break_end:
        return "Thanksgiving Break 🍂"
    return None


@bot.command(name="today")
async def today(ctx):
    now = datetime.now(local_tz)

    # 1. Check if we are on break first
    break_name = is_uiuc_break(now)
    if break_name:
        await ctx.send(f"🏝️ **Enjoy your {break_name}!** No meals are scheduled today.")
        return

    # 2. Otherwise, proceed with normal logic
    day_name = now.strftime("%A")

    # Adjusted week calculation logic
    semester_start = datetime(2026, 1, 20, tzinfo=local_tz)  # Instruction begins Jan 20
    days_since_start = (now - semester_start).days

    # If we are past Spring Break, we subtract 7 days to keep the 4-week rotation in sync
    if now > datetime(2026, 3, 22, tzinfo=local_tz):
        days_since_start -= 7

    current_week = ((max(0, days_since_start) // 7) % 4) + 1

    lunch = get_meal_menu_logic(current_week, day_name, "Lunch")
    dinner = get_meal_menu_logic(current_week, day_name, "Dinner")

    embed = discord.Embed(
        title=f"🍴 Menu for {day_name} (Week {current_week})",
        color=discord.Color.gold()
    )
    embed.add_field(name="Lunch", value=lunch, inline=False)
    embed.add_field(name="Dinner", value=dinner, inline=False)

    await ctx.send(embed=embed)
# 3. Start both
keep_alive()
bot.run(token, log_handler=handler, log_level=logging.DEBUG)