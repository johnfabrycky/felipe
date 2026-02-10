import discord
from discord import app_commands
from discord.ext import commands
from keep_alive import keep_alive  # Import your helper

class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # This is your Slash Command
    @app_commands.command(name="today", description="Show the UIUC meal menu")
    async def today(self, interaction: discord.Interaction):
        # Your logic to read the CSV and find today's menu
        await interaction.response.send_message(content="Searching the menu...", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Utility(bot))

# In your main.py file:
# keep_alive()
# bot.run(TOKEN)