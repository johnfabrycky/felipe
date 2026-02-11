import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import pytz

local_tz = pytz.timezone('America/Chicago')


class Parking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Resident spots as defined in your original configuration
        self.valid_spots = list(range(1, 34)) + list(range(41, 46))
        self.perm_guest = 46

        # Original data structures modified for multi-reservation support
        self.offers = {}  # {spot: {"user_id": int, "start": dt, "end": dt}}
        self.active_claims = {}  # {spot: [{"claimer_id": int, "owner_id": int, "start": dt, "end": dt}, ...]}

        # Staff Spot Tracking (Unnumbered pool of 2)
        self.total_staff_spots = 2
        self.staff_claims = {}  # {user_id: {"start": dt, "end": dt}}

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

    @app_commands.command(name="claim_spot", description="Reserve a resident spot for now or a future time")
    async def claim_spot(self, interaction: discord.Interaction, spot: int, start_day: str, start_time: str,
                         end_day: str, end_time: str):
        if spot not in self.offers:
            return await interaction.response.send_message(f"❌ Spot {spot} is not currently offered.", ephemeral=True)

        offer = self.offers[spot]
        try:
            claim_start = self.parse_time(start_day, start_time)
            claim_end = self.parse_time(end_day, end_time)
        except ValueError:
            return await interaction.response.send_message("❌ Invalid time format.", ephemeral=True)

        # Validate against the Offer Window
        if claim_start < offer["start"] or claim_end > offer["end"]:
            range_str = f"{offer['start'].strftime('%a %I%p')} to {offer['end'].strftime('%a %I%p')}"
            return await interaction.response.send_message(
                f"❌ Outside offer window: Spot {spot} is only available from **{range_str}**.", ephemeral=True
            )

        # Check for overlaps with existing claims on this spot
        spot_claims = self.active_claims.get(spot, [])
        for existing in spot_claims:
            if not (claim_end <= existing["start"] or claim_start >= existing["end"]):
                return await interaction.response.send_message(
                    f"❌ Spot {spot} is already reserved during that specific time.", ephemeral=True
                )

        if spot not in self.active_claims:
            self.active_claims[spot] = []

        self.active_claims[spot].append({
            "claimer_id": interaction.user.id,
            "owner_id": offer["user_id"],
            "start": claim_start,
            "end": claim_end
        })

        await interaction.response.send_message(
            f"✅ {interaction.user.mention} reserved **Spot {spot}**\n"
            f"🗓️ **From:** {start_day} {start_time}\n"
            f"🗓️ **Until:** {end_day} {end_time}", ephemeral=False
        )

    @app_commands.command(name="unclaim_spot", description="Cancel your reservation for a resident spot")
    async def unclaim_spot(self, interaction: discord.Interaction, spot: int):
        if spot in self.active_claims:
            user_claims = [c for c in self.active_claims[spot] if c["claimer_id"] == interaction.user.id]
            if not user_claims:
                return await interaction.response.send_message("❌ You don't have a reservation for this spot.",
                                                               ephemeral=True)

            self.active_claims[spot].remove(user_claims[0])
            return await interaction.response.send_message(
                f"🔄 {interaction.user.mention} cancelled their reservation for **Spot {spot}**.", ephemeral=False)
        await interaction.response.send_message("❌ No claims found for this spot.", ephemeral=True)

    @app_commands.command(name="reclaim_spot", description="Take your spot back from a claimer (Public)")
    async def reclaim_spot(self, interaction: discord.Interaction, spot: int):
        # Handle withdrawing the offer entirely
        if spot in self.offers and self.offers[spot]["user_id"] == interaction.user.id:
            del self.offers[spot]
            # Also clear any future claims if the owner withdraws the spot
            if spot in self.active_claims:
                del self.active_claims[spot]
            return await interaction.response.send_message(f"🔄 **Spot {spot}** offer withdrawn by owner.",
                                                           ephemeral=False)

        # Handle emergency reclaim if someone is currently in the spot
        if spot in self.active_claims:
            now = datetime.now(local_tz)
            current_claim = next((c for c in self.active_claims[spot] if
                                  c["owner_id"] == interaction.user.id and c["start"] <= now <= c["end"]), None)

            if current_claim:
                claimer_id = current_claim["claimer_id"]
                self.active_claims[spot].remove(current_claim)
                return await interaction.response.send_message(
                    f"⚠️ **Spot {spot}** reclaimed by owner. <@{claimer_id}>, please move your vehicle.",
                    ephemeral=False
                )
        await interaction.response.send_message("❌ You are not the owner of this spot or it is not currently occupied.",
                                                ephemeral=True)

    @app_commands.command(name="claim_staff", description="Claim a staff spot for now or a future date")
    async def claim_staff(self, interaction: discord.Interaction, start_day: str, start_time: str, end_day: str,
                          end_time: str):
        if interaction.user.id in self.staff_claims:
            return await interaction.response.send_message("❌ You already have a staff spot claimed.", ephemeral=True)

        try:
            claim_start = self.parse_time(start_day, start_time)
            claim_end = self.parse_time(end_day, end_time)
        except ValueError:
            return await interaction.response.send_message("❌ Invalid time format.", ephemeral=True)

        # Overlap Check for Pool
        overlapping_claims = 0
        for uid, times in self.staff_claims.items():
            if not (claim_end <= times["start"] or claim_start >= times["end"]):
                overlapping_claims += 1

        if overlapping_claims >= self.total_staff_spots:
            return await interaction.response.send_message("❌ Both staff spots are reserved for that time period.",
                                                           ephemeral=True)

        # Curfew Validation
        start_weekday = claim_start.weekday()
        curfew_hour = 2 if start_weekday in [4, 5] else 0  # 2 AM Fri/Sat, 12 AM otherwise
        curfew_dt = claim_start.replace(hour=curfew_hour, minute=0, second=0, microsecond=0) + timedelta(days=1)

        if claim_end > curfew_dt:
            limit_str = "2 AM" if curfew_hour == 2 else "12 AM"
            return await interaction.response.send_message(
                f"❌ Curfew: Staff spots must be cleared by {limit_str} for {start_day} night.", ephemeral=True)

        self.staff_claims[interaction.user.id] = {"start": claim_start, "end": claim_end}
        await interaction.response.send_message(
            f"✅ Staff Spot reserved from {start_day} {start_time} to {end_day} {end_time}.", ephemeral=False)

    @app_commands.command(name="unclaim_staff", description="Release your claimed staff spot")
    async def unclaim_staff(self, interaction: discord.Interaction):
        if interaction.user.id in self.staff_claims:
            self.staff_claims.pop(interaction.user.id)
            return await interaction.response.send_message(
                f"🔄 {interaction.user.mention} released their **Staff Spot**.", ephemeral=False)
        await interaction.response.send_message("❌ You do not have a staff spot claimed.", ephemeral=True)

    @app_commands.command(name="parking_status", description="See current and future availability (Private)")
    async def parking_status(self, interaction: discord.Interaction):
        now = datetime.now(local_tz)
        day = now.weekday()  # 0=Mon, 4=Fri, 5=Sat, 6=Sun
        hour = now.hour

        # 1. Resident Offers Logic (Updated for future start dates)
        lines = []
        for s, d in self.offers.items():
            current_claimer = next((c for c in self.active_claims.get(s, []) if c["start"] <= now <= c["end"]), None)

            if current_claimer:
                status = f"🔴 Occupied until {current_claimer['end'].strftime('%I %p')}"
            elif now < d['start']:
                # If the offer hasn't started yet
                status = f"📅 Available starting {d['start'].strftime('%a %I %p')}"
            else:
                # If we are within the offer window and no one has claimed it yet
                status = "🟢 Available Now"

            lines.append(f"• **Spot {s}**: {status} (Offer ends {d['end'].strftime('%a %I %p')})")

        res_msg = "\n".join(lines) if lines else "No resident spots currently offered."

        # 2. Staff Logic (Updated with your specific blackout hours)
        # Blackout 1: Mon-Fri 12 AM - 5 PM
        is_weekday_blackout = (day < 5 and hour < 17)
        # Blackout 2: Sunday 2 AM - 2 PM
        is_sunday_blackout = (day == 6 and 2 <= hour < 14)

        if is_weekday_blackout or is_sunday_blackout:
            staff_status = "❌ Closed (Permit Required)"
        else:
            current_staff_users = len([u for u, t in self.staff_claims.items() if t["start"] <= now <= t["end"]])
            open_staff = self.total_staff_spots - current_staff_users
            staff_status = f"✅ {open_staff}/2 Available Now" if open_staff > 0 else "❌ Fully Occupied"

        # 3. Build the Embed
        embed = discord.Embed(title="🚗 Current Parking Availability", color=discord.Color.blue())
        embed.add_field(name="Resident Spots", value=res_msg, inline=False)
        embed.add_field(name="Staff Spots", value=staff_status, inline=True)
        embed.add_field(name="Permanent Guest", value=f"Spot {self.perm_guest}: ✅ Available", inline=True)

        # Removed: Timed Guest Spots section is gone.

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Parking(bot))