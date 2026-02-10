import discord
import interaction
from discord.ext import commands
from datetime import datetime, timedelta
import pytz

local_tz = pytz.timezone('America/Chicago')

class Movies(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Note: This is stored in memory; it resets when the Render service restarts
        self.movie_sessions = {}

    @commands.command(name="watch")
    async def watch(self, ctx, duration_mins: int, location: str, movie_name: str, start_time: str = None):
        if start_time is None:
            start_dt = datetime.now(local_tz)
        else:
            try:
                input_time = datetime.strptime(start_time, "%H:%M").time()
                start_dt = datetime.now(local_tz).replace(
                    hour=input_time.hour, minute=input_time.minute, second=0, microsecond=0
                )
            except ValueError:
                return await ctx.send("❌ Invalid time format! Please use HH:MM (e.g., 14:30).")

        end_dt = start_dt + timedelta(minutes=duration_mins)
        self.movie_sessions[movie_name.lower()] = {
            "location": location,
            "end_time": end_dt,
            "original_name": movie_name
        }

        start_str = start_dt.strftime("%I:%M %p")
        await ctx.send(f"🎬 **{movie_name}** recorded! Starting at **{start_str}** in **{location}**.")

    @watch.error
    async def watch_error(self, ctx, error):
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

    @commands.command(name="where")
    async def where(self, ctx):
        now = datetime.now(local_tz)
        active_movies = []

        for name, data in list(self.movie_sessions.items()):
            if now < data["end_time"]:
                active_movies.append(f"• **{data['original_name']}** is at **{data['location']}**")
            else:
                del self.movie_sessions[name]

        response = "🍿 **Current Movies Playing:**\n" + "\n".join(active_movies) if active_movies else "Currently, no movies are being watched."
        await interaction.response.send_message(content=response, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Movies(bot))