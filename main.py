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
    # (Existing Help Embed Code)
    pass

if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv('DISCORD_TOKEN'))