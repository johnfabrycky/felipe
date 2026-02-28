import discord
from discord.ext import commands
from discord import app_commands
from supabase import create_client, Client
import os


class Shifts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Ensure these are in your .env file or passed in your main bot file
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        self.supabase: Client = create_client(url, key)

    # --- HELPER DATA FOR DROPDOWNS ---
    SHIFT_TYPES = [
        "Lunch Prep", "Lunch Cleanup",
        "Dinner Prep", "Dinner Cleanup",
        "Saturday Dinner"
    ]
    DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    @app_commands.command(name="offer_shift", description="Post a shift you want someone else to take")
    @app_commands.choices(
        shift_type=[app_commands.Choice(name=st, value=st) for st in SHIFT_TYPES],
        day=[app_commands.Choice(name=d, value=d) for d in DAYS]
    )
    async def offer(self, interaction: discord.Interaction, shift_type: str, day: str, price: float):
        # Validation for Saturday Dinner constraint
        if shift_type == "Saturday Dinner" and day != "Saturday":
            return await interaction.response.send_message(
                "❌ **Error:** The 'Saturday Dinner' shift can only be offered for Saturday!", ephemeral=True)

        # Prepare data for Supabase
        payload = {
            "seller_id": str(interaction.user.id),
            "seller_name": interaction.user.display_name,
            "shift_type": shift_type,
            "day_of_week": day,
            "price": price
        }

        # Insert into database
        response = self.supabase.table("shifts").insert(payload).execute()
        new_shift = response.data[0]

        await interaction.response.send_message(
            f"✅ **Shift Posted!**\n**{shift_type}** on **{day}** for **${price:.2f}**. (ID: `{new_shift['id']}`)")

    @app_commands.command(name="view_market", description="See all available shifts for hire")
    async def view_market(self, interaction: discord.Interaction):
        # Query: Get shifts where claimed_by_id is null
        response = self.supabase.table("shifts").select("*").is_("claimed_by_id", "null").execute()
        available = response.data

        if not available:
            return await interaction.response.send_message("There are no shifts currently available for hire.",
                                                           ephemeral=True)

        embed = discord.Embed(title="🛒 Available Shifts", color=discord.Color.green())
        for s in available:
            embed.add_field(
                name=f"ID: {s['id']} | {s['shift_type']}",
                value=f"📅 **Day:** {s['day_of_week']}\n💰 **Bounty:** ${s['price']:.2f}\n👤 **Offered by:** {s['seller_name']}",
                inline=False
            )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="claim_shift", description="Take an available shift and get paid")
    async def claim(self, interaction: discord.Interaction, shift_id: int):
        # 1. Fetch the shift
        response = self.supabase.table("shifts").select("*").eq("id", shift_id).execute()

        if not response.data:
            return await interaction.response.send_message("❌ Shift ID not found.", ephemeral=True)

        shift = response.data[0]

        # 2. Logic Checks
        if shift["claimed_by_id"] is not None:
            return await interaction.response.send_message("❌ This shift has already been claimed!", ephemeral=True)

        if shift["seller_id"] == str(interaction.user.id):
            return await interaction.response.send_message("❌ You can't claim your own shift!", ephemeral=True)

        # 3. Update the shift in Supabase
        self.supabase.table("shifts").update({"claimed_by_id": str(interaction.user.id)}).eq("id", shift_id).execute()

        await interaction.response.send_message(
            f"🤝 **Shift Claimed!** {interaction.user.mention}, you have taken the **{shift['shift_type']}** on **{shift['day_of_week']}**.")

    @app_commands.command(name="my_shifts", description="View shifts you have claimed")
    async def my_shifts(self, interaction: discord.Interaction):
        # Query: Get shifts where claimed_by_id matches the user
        response = self.supabase.table("shifts").select("*").eq("claimed_by_id", str(interaction.user.id)).execute()
        mine = response.data

        if not mine:
            return await interaction.response.send_message("You haven't claimed any shifts yet.", ephemeral=True)

        embed = discord.Embed(title="📋 Your Claimed Shifts", color=discord.Color.blue())
        for s in mine:
            embed.add_field(
                name=f"{s['shift_type']} ({s['day_of_week']})",
                value=f"💰 **Earned:** ${s['price']:.2f}\n👤 **Originally for:** {s['seller_name']}",
                inline=False
            )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Shifts(bot))