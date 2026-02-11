import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import pytz

local_tz = pytz.timezone('America/Chicago')


class Parking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.valid_spots = list(range(1, 34)) + list(range(41, 46))
        self.perm_guest = 46
        self.offers = {}  # {spot: {"user_id": int, "start": dt, "end": dt}}
        self.active_claims = {}  # {spot: {"claimer_id": int, "owner_id": int, "start": dt, "end": dt}}

    def parse_time(self, day_str, time_str):
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        target_day = days.index(day_str.lower().strip())
        now = datetime.now(local_tz)
        days_ahead = (target_day - now.weekday() + 7) % 7
        target_date = now + timedelta(days=days_ahead)
        time_obj = datetime.strptime(time_str.strip().upper(), "%I %p").time()
        return target_date.replace(hour=time_obj.hour, minute=0, second=0, microsecond=0)

    @app_commands.command(name="offer_spot", description="List your spot as available (Public)")
    async def offer_spot(self, interaction: discord.Interaction, spot: int, start_day: str, start_time: str,
                         end_day: str, end_time: str):
        if spot not in self.valid_spots:
            return await interaction.response.send_message(f"❌ {spot} is not a valid resident spot.", ephemeral=True)

        start_dt = self.parse_time(start_day, start_time)
        end_dt = self.parse_time(end_day, end_time)

        self.offers[spot] = {"user_id": interaction.user.id, "start": start_dt, "end": end_dt}

        await interaction.response.send_message(
            f"📢 **Spot {spot}** offered by {interaction.user.mention}\n"
            f"🗓️ Available: {start_day} {start_time} — {end_day} {end_time}", ephemeral=False
        )

    @app_commands.command(name="claim_spot", description="Claim a spot for a specific time (Public)")
    async def claim_spot(self, interaction: discord.Interaction, spot: int, end_day: str, end_time: str):
        if spot not in self.offers:
            return await interaction.response.send_message(f"❌ Spot {spot} is not currently available.", ephemeral=True)

        offer = self.offers[spot]
        claim_start = datetime.now(local_tz)
        claim_end = self.parse_time(end_day, end_time)

        # Time Validation
        if claim_end > offer["end"]:
            latest = offer["end"].strftime("%A %I %p")
            return await interaction.response.send_message(
                f"❌ Validation Error: Spot {spot} is only available until **{latest}**. "
                f"Your request for {end_day} {end_time} is too long.", ephemeral=True
            )

        # Move from offers to active_claims
        self.active_claims[spot] = {
            "claimer_id": interaction.user.id,
            "owner_id": offer["user_id"],
            "start": claim_start,
            "end": claim_end
        }
        del self.offers[spot]

        await interaction.response.send_message(
            f"✅ {interaction.user.mention} claimed **Spot {spot}** until {end_day} {end_time}.",
            ephemeral=False
        )

    @app_commands.command(name="unclaim_spot", description="Give back a spot you claimed (Public)")
    async def unclaim_spot(self, interaction: discord.Interaction, spot: int):
        if spot in self.active_claims and self.active_claims[spot]["claimer_id"] == interaction.user.id:
            data = self.active_claims.pop(spot)
            # Put it back in offers since there is time left
            self.offers[spot] = {"user_id": data["owner_id"], "start": datetime.now(local_tz), "end": data["end"]}

            return await interaction.response.send_message(
                f"🔄 {interaction.user.mention} relinquished **Spot {spot}**. It is available again until {data['end'].strftime('%A %I %p')}.",
                ephemeral=False
            )
        await interaction.response.send_message("❌ You are not the person currently claiming this spot.",
                                                ephemeral=True)

    @app_commands.command(name="reclaim_spot", description="Take your spot back from a claimer (Public)")
    async def reclaim_spot(self, interaction: discord.Interaction, spot: int):
        if spot in self.offers and self.offers[spot]["user_id"] == interaction.user.id:
            del self.offers[spot]
            return await interaction.response.send_message(f"🔄 **Spot {spot}** offer withdrawn by owner.",
                                                           ephemeral=False)

        if spot in self.active_claims and self.active_claims[spot]["owner_id"] == interaction.user.id:
            claimer_id = self.active_claims[spot]["claimer_id"]
            del self.active_claims[spot]
            return await interaction.response.send_message(
                f"⚠️ **Spot {spot}** reclaimed by owner. <@{claimer_id}>, please move your vehicle.", ephemeral=False
            )
        await interaction.response.send_message("❌ You are not the owner of this spot.", ephemeral=True)

    @app_commands.command(name="parking_status", description="See all currently available spots (Private)")
    async def parking_status(self, interaction: discord.Interaction):
        # Resident Offers
        if not self.offers:
            res_msg = "No resident spots currently offered."
        else:
            res_msg = "\n".join(
                [f"• **Spot {s}**: until {d['end'].strftime('%A %I %p')}" for s, d in self.offers.items()])

        # Guest Logic
        now = datetime.now(local_tz)
        day, hour = now.weekday(), now.hour
        is_guest_open = (day < 5 and hour >= 17) or (day == 5) or (day == 6 and hour >= 14)

        embed = discord.Embed(title="🚗 Current Parking Availability", color=discord.Color.blue())
        embed.add_field(name="Resident Spots (Open)", value=res_msg, inline=False)
        embed.add_field(name="Permanent Guest", value=f"Spot {self.perm_guest}: ✅ Available", inline=True)
        embed.add_field(name="Timed Guest Spots",
                        value="✅ Available" if is_guest_open else "❌ Closed (After 5PM/Weekends)", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Parking(bot))