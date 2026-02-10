import discord
from discord.ext import commands
from discord import app_commands
import pandas as pd
import pytz
from datetime import datetime

local_tz = pytz.timezone('America/Chicago')


class Meals(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.csv_path = 'Spring 26 Workschedule - Meal Schedule.csv'

    def get_meal_menu_logic(self, week, day, meal_type):
        try:
            df = pd.read_csv(self.csv_path)
            headers = df.iloc[0].tolist()
            col_name = f"Week {week} - {meal_type}"
            if col_name not in headers: return "Not Found"
            col_idx = headers.index(col_name)
            data_rows = df.iloc[1:]
            match = data_rows[data_rows['Unnamed: 0'].str.strip() == day]
            if match.empty: return "No data for this day"
            item = match.iloc[0, col_idx]
            return item if pd.notna(item) else "No meal scheduled"
        except Exception:
            return "Error loading menu"

    def is_uiuc_break(self, current_date):
        # Spring Break 2026: March 14 to March 22
        spring_break_start = datetime(2026, 3, 14, tzinfo=local_tz)
        spring_break_end = datetime(2026, 3, 22, 23, 59, tzinfo=local_tz)
        if spring_break_start <= current_date <= spring_break_end:
            return "Spring Break 🌸"
        return None

    @app_commands.command(name="today")
    async def today(self, interaction: discord.Interaction):
        now = datetime.now(local_tz)
        break_name = self.is_uiuc_break(now)
        if break_name:
            return await interaction.response.send_message(f"🏝️ **Enjoy your {break_name}!** No meals scheduled.")

        semester_start = datetime(2026, 1, 19, tzinfo=local_tz)
        days_since_start = (now - semester_start).days
        if now > datetime(2026, 3, 22, tzinfo=local_tz):
            days_since_start -= 7

        current_week = ((max(0, days_since_start) // 7) % 4) + 1
        day_name = now.strftime("%A")

        embed = discord.Embed(title=f"🍴 Menu for {day_name} (Week {current_week})", color=discord.Color.gold())
        embed.add_field(name="Lunch", value=self.get_meal_menu_logic(current_week, day_name, "Lunch"), inline=False)
        embed.add_field(name="Dinner", value=self.get_meal_menu_logic(current_week, day_name, "Dinner"), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return None


async def setup(bot):
    await bot.add_cog(Meals(bot))