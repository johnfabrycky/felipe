import discord
from discord.ext import commands
from discord import app_commands
import pandas as pd
import json
import os
import io
from datetime import datetime
import pytz

local_tz = pytz.timezone('America/Chicago')


class Lates(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = 'permanent_lates.json'
        self.days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        self.meals = ["Lunch", "Dinner"]
        self.lates = self.load_data()

    def load_data(self):
        # Create default empty structure
        initial_structure = {day: {meal: {} for meal in self.meals} for day in self.days}
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    loaded_data = json.load(f)
                    # Re-fill the structure to ensure no keys are missing
                    for day in self.days:
                        if day in loaded_data:
                            for meal in self.meals:
                                if meal in loaded_data[day]:
                                    initial_structure[day][meal] = loaded_data[day][meal]
                return initial_structure
            except Exception:
                return initial_structure
        return initial_structure

    def save_data(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.lates, f, indent=4)

    @app_commands.command(name="import_koinonia_lates", description="One-time import from Koinonia CSVs")
    @app_commands.checks.has_permissions(administrator=True)
    async def import_csv(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        files = {
            "Lunch": "Copy of Koinonia Lates Schedule - Permanent Lunch Lates.csv",
            "Dinner": "Copy of Koinonia Lates Schedule - Permanent Dinner Lates.csv"
        }

        members = interaction.guild.members
        match_count = 0
        missing_files = []

        for meal_type, filename in files.items():
            if not os.path.exists(filename):
                missing_files.append(filename)
                continue

            try:
                df = pd.read_csv(filename)
                # Strip spaces from column headers (handles "Thursday " vs "Thursday")
                df.columns = [c.strip() for c in df.columns]

                for day in [d for d in self.days if d in df.columns]:
                    names = df[day].dropna().unique()
                    for name_str in names:
                        name_clean = str(name_str).strip()
                        if not name_clean: continue

                        # Find best match in server nicknames/usernames
                        target_user = discord.utils.find(
                            lambda m: name_clean.lower() in m.display_name.lower(),
                            members
                        )

                        # Use User ID if found, otherwise an "imported_" string key
                        key = str(target_user.id) if target_user else f"imported_{name_clean}"
                        final_name = target_user.display_name if target_user else name_clean

                        self.lates[day][meal_type][key] = {
                            "name": final_name,
                            "role": "koinonian",
                            "permanent": True,
                            "date_added": datetime.now(local_tz).isoformat()
                        }
                        match_count += 1
            except Exception as e:
                return await interaction.followup.send(f"❌ Error processing {filename}: {e}", ephemeral=True)

        self.save_data()

        msg = f"✅ Imported {match_count} Koinonian lates."
        if missing_files:
            msg += f"\n⚠️ Files not found: {', '.join(missing_files)}"

        await interaction.followup.send(msg, ephemeral=True)

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
        # House Grouping
        target_roles = ["koinonian"] if my_role == "koinonian" else ["stratfordite", "suttonite"]

        filtered_list = []
        now = datetime.now(local_tz)

        # Ensure day/meal existence
        current_meal_dict = self.lates.get(day, {}).get(meal, {})

        for user_id, info in list(current_meal_dict.items()):
            date_added = datetime.fromisoformat(info["date_added"])

            # Auto-clear non-permanent lates from previous weeks
            if not info["permanent"] and now.isocalendar()[1] != date_added.isocalendar()[1]:
                del self.lates[day][meal][user_id]
                self.save_data()
                continue

            if info["role"] in target_roles:
                status = "🔄" if info["permanent"] else "⏱️"
                filtered_list.append(f"{status} **{info['name']}**")

        total_count = len(filtered_list)

        if total_count == 0:
            return await interaction.response.send_message(
                f"No lates recorded for **{day} {meal}** in your house group.", ephemeral=True)

        embed = discord.Embed(
            title=f"🍽️ Lates: {day} {meal} ({total_count} total)",
            description="\n".join(filtered_list),
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

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
        user_id = str(interaction.user.id)

        # Check for existing
        if user_id in self.lates[day][meal]:
            return await interaction.response.send_message(
                f"❌ You already have a late for **{day} {meal}**. Clear it first to change it.", ephemeral=True)

        self.lates[day][meal][user_id] = {
            "name": interaction.user.display_name,
            "role": role,
            "permanent": permanent,
            "date_added": datetime.now(local_tz).isoformat()
        }

        self.save_data()
        await interaction.response.send_message(f"✅ Late recorded for **{day} {meal}**.", ephemeral=True)

    @app_commands.command(name="clear_late", description="Remove your late request")
    @app_commands.choices(
        day=[app_commands.Choice(name=d, value=d) for d in
             ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]],
        meal=[app_commands.Choice(name="Lunch", value="Lunch"), app_commands.Choice(name="Dinner", value="Dinner")]
    )
    async def clear_late(self, interaction: discord.Interaction, day: str, meal: str):
        user_id = str(interaction.user.id)
        if user_id in self.lates[day][meal]:
            del self.lates[day][meal][user_id]
            self.save_data()
            await interaction.response.send_message(f"🗑️ Your late for {day} {meal} has been cleared.", ephemeral=True)
        else:
            await interaction.response.send_message("No late found to clear.", ephemeral=True)

    @app_commands.command(name="my_lates", description="See all the meals you've requested lates for")
    async def my_lates(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        now = datetime.now(local_tz)
        found_lates = []
        changed = False

        # Scan all days and meals for this user
        for day in self.days:
            for meal in self.meals:
                if user_id in self.lates[day][meal]:
                    info = self.lates[day][meal][user_id]
                    date_added = datetime.fromisoformat(info["date_added"])

                    # Expiry check: If temporary and from a different week, remove it
                    if not info["permanent"] and now.isocalendar()[1] != date_added.isocalendar()[1]:
                        del self.lates[day][meal][user_id]
                        changed = True
                        continue

                    status = "🔄 Permanent" if info["permanent"] else "⏱️ This week only"
                    found_lates.append(f"• **{day} {meal}**: {status}")

        if changed:
            self.save_data()

        if not found_lates:
            return await interaction.response.send_message("You don't have any active lates recorded currently.",
                                                           ephemeral=True)

        embed = discord.Embed(
            title=f"📋 Your Registered Lates",
            description="\n".join(found_lates),
            color=discord.Color.green()
        )
        embed.set_footer(text="Use /clear_late to remove any of these.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Lates(bot))