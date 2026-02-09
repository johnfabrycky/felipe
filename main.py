import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from keep_alive import keep_alive

load_dotenv()
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command('help')

# Define which cogs to load
INITIAL_EXTENSIONS = [
    'cogs.meals',
    'cogs.movies'
]

@bot.event
async def on_ready():
    for extension in INITIAL_EXTENSIONS:
        try:
            await bot.load_extension(extension)
            print(f"✅ Loaded {extension}")
        except Exception as e:
            print(f"❌ Failed to load {extension}: {e}")
    print(f"🚀 {bot.user.name} is ready for action in Champaign!")

# Keep your help command and other simple commands here
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

if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv('DISCORD_TOKEN'))