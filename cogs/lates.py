import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import pytz

local_tz = pytz.timezone('America/Chicago')


class Lates(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Structure: { "Day": { "Meal": { user_id: data } } }
        self.days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        self.meals = ["Lunch", "Dinner"]
        self.lates = {day: {meal: {} for meal in self.meals} for day in self.days}

    @app_commands.command(name="late_me", description="Request food to be set aside")
    @app_commands.choices(
        day=[app_commands.Choice(name=d, value=d) for d in
             ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]],
        meal=[app_commands.Choice(name="Lunch", value="Lunch"), app_commands.Choice(name="Dinner", value="Dinner")],
        role=[
            app_commands.Choice(name="Koinonian", value="koinonian"),
            app_commands.Choice(name="Stratfordite", value="stratfordite"),
            app_commands.Choice(name="Suttonite", value="suttonite")
        ]
    )
    async def late_me(self, interaction: discord.Interaction, day: str, meal: str, role: str, permanent: bool = False):
        user_id = interaction.user.id

        # 1. Prevent duplicate requests for the same meal
        if user_id in self.lates[day][meal]:
            return await interaction.response.send_message(
                f"❌ You already have a late recorded for **{day} {meal}**! Use `/clear_late` first if you need to change it.",
                ephemeral=True
            )

        self.lates[day][meal][user_id] = {
            "name": interaction.user.display_name,
            "role": role,
            "permanent": permanent,
            "date_added": datetime.now(local_tz)
        }

        type_str = "Permanent" if permanent else "Temporary"
        await interaction.response.send_message(
            f"✅ **{type_str}** late recorded for **{day} {meal}** ({role.capitalize()}).",
            ephemeral=True
        )

    @app_commands.command(name="my_lates", description="See all the meals you've requested lates for")
    async def my_lates(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        now = datetime.now(local_tz)
        found_lates = []

        # Scan all days and meals for this user
        for day in self.days:
            for meal in self.meals:
                if user_id in self.lates[day][meal]:
                    info = self.lates[day][meal][user_id]

                    # Expiry check
                    if not info["permanent"] and now.isocalendar()[1] != info["date_added"].isocalendar()[1]:
                        del self.lates[day][meal][user_id]
                        continue

                    status = "🔄 Permanent" if info["permanent"] else "⏱️ This week only"
                    found_lates.append(f"• **{day} {meal}**: {status}")

        if not found_lates:
            return await interaction.response.send_message("You don't have any lates recorded currently.",
                                                           ephemeral=True)

        embed = discord.Embed(
            title=f"📋 Lates for {interaction.user.display_name}",
            description="\n".join(found_lates),
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="view_lates", description="See lates for your house")
    @app_commands.choices(
        day=[app_commands.Choice(name=d, value=d) for d in
             ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]],
        meal=[app_commands.Choice(name="Lunch", value="Lunch"), app_commands.Choice(name="Dinner", value="Dinner")],
        my_role=[
            app_commands.Choice(name="Koinonian", value="koinonian"),
            app_commands.Choice(name="Stratfordite", value="stratfordite"),
            app_commands.Choice(name="Suttonite", value="suttonite")
        ]
    )
    async def view_lates(self, interaction: discord.Interaction, day: str, meal: str, my_role: str):
        target_roles = ["koinonian"] if my_role == "koinonian" else ["stratfordite", "suttonite"]

        all_lates_for_meal = self.lates[day][meal]
        filtered_list = []

        for user_id, info in list(all_lates_for_meal.items()):
            now = datetime.now(local_tz)
            if not info["permanent"] and now.isocalendar()[1] != info["date_added"].isocalendar()[1]:
                del self.lates[day][meal][user_id]
                continue

            if info["role"] in target_roles:
                status = "🔄" if info["permanent"] else "⏱️"
                filtered_list.append(f"{status} **{info['name']}** ({info['role'].capitalize()})")

        if not filtered_list:
            return await interaction.response.send_message(f"No lates found for {day} {meal} for your house group.",
                                                           ephemeral=True)

        embed = discord.Embed(title=f"🍽️ Lates: {day} {meal}", description="\n".join(filtered_list),
                              color=discord.Color.blue())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="clear_late", description="Remove your late request")
    @app_commands.choices(
        day=[app_commands.Choice(name=d, value=d) for d in
             ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]],
        meal=[app_commands.Choice(name="Lunch", value="Lunch"), app_commands.Choice(name="Dinner", value="Dinner")]
    )
    async def clear_late(self, interaction: discord.Interaction, day: str, meal: str):
        if interaction.user.id in self.lates[day][meal]:
            del self.lates[day][meal][interaction.user.id]
            await interaction.response.send_message(f"🗑️ Your late for {day} {meal} has been cleared.", ephemeral=True)
        else:
            await interaction.response.send_message(f"You don't have a late recorded for {day} {meal}.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Lates(bot))