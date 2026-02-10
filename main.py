import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
from keep_alive import keep_alive

load_dotenv()
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command('help')

# Define which cogs to load
INITIAL_EXTENSIONS = [
    'cogs.meals',
    'cogs.movies'
]

@bot.hybrid_command(name="test")
async def test(ctx):
    await ctx.send("This is a hybrid command!")

@bot.event
async def on_ready():
    # Load Extensions
    for extension in INITIAL_EXTENSIONS:
        try:
            # Check if already loaded to prevent errors on reconnect
            if extension not in bot.extensions:
                await bot.load_extension(extension)
                print(f"✅ Loaded {extension}")
        except Exception as e:
            print(f"❌ Failed to load {extension}: {e}")

    # 2. Sync Slash Commands
    try:
        # This makes /today and /where visible in Discord
        synced = await bot.tree.sync()
        print(f"🚀 Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"❌ Slash sync failed: {e}")

    print(f"🚀 {bot.user.name} is online and ready in Champaign!")

@bot.command()
@commands.has_permissions(administrator=True) # Only you (the owner) can run this
async def sync(ctx):
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"Successfully synced {len(synced)} commands to the tree.")
    except Exception as e:
        await ctx.send(f"Failed to sync: {e}")

# Keep your help command and other simple commands here
@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(
        title="🤖 Bot Command Center",
        description="I manage movie sessions and the UIUC meal schedule!",
        color=discord.Color.green()
    )

    # Movie Section
    embed.add_field(
        name="🎬 Movie Tracking",
        value=(
            "`!watch <mins> <loc> <movie> [time]` - Start a session.\n"
            "`!where` - See what is playing now."
        ),
        inline=False
    )

    # Meals Section
    embed.add_field(
        name="🍽️ Meal Schedule",
        value=(
            "`!today` - Automatically shows today's Lunch & Dinner.\n"
            "`!meal <week> <day> <type>` - Lookup a specific meal.\n"
            "*Example:* `!meal 2 Tuesday Dinner`"
        ),
        inline=False
    )

    # Status/Context Section
    embed.add_field(
        name="ℹ️ System Info",
        value=(
            "• Dates are synced to **Champaign, IL** time.\n"
            "• UIUC Spring/Fall breaks are automatically handled.\n"
            "• Week rotation resets every Monday morning."
        ),
        inline=False
    )

    embed.set_footer(text="Pro-tip: Use \"quotes\" if names or locations have spaces!")

    await ctx.send(embed=embed)

if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv('DISCORD_TOKEN'))