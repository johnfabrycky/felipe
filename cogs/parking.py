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
        self.offers = {}
        self.active_claims = {}
        self.total_staff_spots = 2
        self.staff_claims = {}

    # REUSABLE DROPDOWNS
    day_choices = [app_commands.Choice(name=d.capitalize(), value=d) for d in
                   ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]]
    time_choices = [app_commands.Choice(name=f"{i % 12 or 12} {'AM' if i < 12 else 'PM'}",
                                        value=f"{i % 12 or 12} {'AM' if i < 12 else 'PM'}") for i in range(24)]

    def parse_time(self, day_str, time_str):
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        target_day = days.index(day_str.lower().strip())
        now = datetime.now(local_tz)
        days_ahead = (target_day - now.weekday() + 7) % 7
        target_date = now + timedelta(days=days_ahead)
        time_obj = datetime.strptime(time_str.strip().upper(), "%I %p").time()
        # Ensure we round to the hour to prevent minute-overlap errors
        return target_date.replace(hour=time_obj.hour, minute=0, second=0, microsecond=0)

    @app_commands.command(name="offer_spot", description="List your spot as available (Public)")
    @app_commands.describe(spot="Spot number", start_day="Start day", start_time="Start hour", end_day="End day",
                           end_time="End hour")
    @app_commands.choices(start_day=day_choices, end_day=day_choices, start_time=time_choices, end_time=time_choices)
    async def offer_spot(self, interaction: discord.Interaction, spot: int,
                         start_day: app_commands.Choice[str], start_time: app_commands.Choice[str],
                         end_day: app_commands.Choice[str], end_time: app_commands.Choice[str]):
        if spot not in self.valid_spots:
            return await interaction.response.send_message(f"❌ {spot} is not a valid resident spot.", ephemeral=True)

        start_dt = self.parse_time(start_day.value, start_time.value)
        end_dt = self.parse_time(end_day.value, end_time.value)
        if end_dt <= start_dt: end_dt += timedelta(days=7)

        self.offers[spot] = {"user_id": interaction.user.id, "start": start_dt, "end": end_dt}
        await interaction.response.send_message(
            f"📢 **Spot {spot}** offered: {start_dt.strftime('%a %I%p')} — {end_dt.strftime('%a %I%p')}")

    @app_commands.command(name="claim_spot", description="Reserve a resident spot (Public)")
    @app_commands.describe(spot="Spot number", start_day="Start day", start_time="Start hour", end_day="End day",
                           end_time="End hour")
    @app_commands.choices(start_day=day_choices, end_day=day_choices, start_time=time_choices, end_time=time_choices)
    async def claim_spot(self, interaction: discord.Interaction, spot: int,
                         start_day: app_commands.Choice[str], start_time: app_commands.Choice[str],
                         end_day: app_commands.Choice[str], end_time: app_commands.Choice[str]):

        # Handle windows for Spot 46 vs regular offers
        if spot == self.perm_guest:
            # Virtual offer window: from now until 2 weeks out
            off_start = datetime.now(local_tz).replace(hour=0, minute=0, second=0, microsecond=0)
            off_end = off_start + timedelta(days=14)
            owner_id = 0
        elif spot in self.offers:
            off_start = self.offers[spot]["start"]
            off_end = self.offers[spot]["end"]
            owner_id = self.offers[spot]["user_id"]
        else:
            return await interaction.response.send_message(f"❌ Spot {spot} is not currently offered.", ephemeral=True)

        c_start = self.parse_time(start_day.value, start_time.value)
        c_end = self.parse_time(end_day.value, end_time.value)
        if c_end <= c_start: c_end += timedelta(days=7)

        # Update your validation to use 'off_start' and 'off_end' instead of 'offer'
        if c_start < off_start or c_end > off_end:
            return await interaction.response.send_message(
                f"❌ Outside window: {off_start.strftime('%a %I%p')} to {off_end.strftime('%a %I%p')}", ephemeral=True)

        claim_start = self.parse_time(start_day.value, start_time.value)
        claim_end = self.parse_time(end_day.value, end_time.value)
        if claim_end <= claim_start: claim_end += timedelta(days=7)

        # Duration checks
        duration = claim_end - claim_start
        if duration < timedelta(hours=2) or duration > timedelta(days=7):
            return await interaction.response.send_message("❌ Reservations must be between 2 hours and 7 days.",
                                                           ephemeral=True)

        # Offer window check
        if claim_start < offer["start"] or claim_end > offer["end"]:
            return await interaction.response.send_message(
                f"❌ Outside window: {offer['start'].strftime('%a %I%p')} to {offer['end'].strftime('%a %I%p')}",
                ephemeral=True)

        # Overlap check
        spot_claims = self.active_claims.get(spot, [])
        for existing in spot_claims:
            if not (claim_end <= existing["start"] or claim_start >= existing["end"]):
                return await interaction.response.send_message("❌ Spot already reserved during that time.",
                                                               ephemeral=True)

        if spot not in self.active_claims: self.active_claims[spot] = []
        self.active_claims[spot].append(
            {"claimer_id": interaction.user.id, "owner_id": offer["user_id"], "start": claim_start, "end": claim_end})

        await interaction.response.send_message(
            f"✅ {interaction.user.mention} reserved **Spot {spot}** until {claim_end.strftime('%a %I%p')}")

    @app_commands.command(name="claim_staff", description="Claim a staff spot (Respects Blackouts)")
    @app_commands.describe(start_day="Start day", start_time="Start hour", end_day="End day", end_time="End hour")
    @app_commands.choices(start_day=day_choices, end_day=day_choices, start_time=time_choices, end_time=time_choices)
    async def claim_staff(self, interaction: discord.Interaction,
                          start_day: app_commands.Choice[str], start_time: app_commands.Choice[str],
                          end_day: app_commands.Choice[str], end_time: app_commands.Choice[str]):
        if interaction.user.id in self.staff_claims:
            return await interaction.response.send_message("❌ You already have a staff spot claimed.", ephemeral=True)

        claim_start = self.parse_time(start_day.value, start_time.value)
        claim_end = self.parse_time(end_day.value, end_time.value)
        if claim_end <= claim_start: claim_end += timedelta(days=7)

        # Blackout Check
        check_time = claim_start
        while check_time < claim_end:
            d, h = check_time.weekday(), check_time.hour
            if (d < 5 and h < 17) or (d == 6 and 2 <= h < 14):
                return await interaction.response.send_message(
                    f"❌ Closed during blackout hours (Mon-Fri 12AM-5PM, Sun 2AM-2PM).", ephemeral=True)
            check_time += timedelta(hours=1)

        # Pool Check
        overlapping = sum(
            1 for t in self.staff_claims.values() if not (claim_end <= t["start"] or claim_start >= t["end"]))
        if overlapping >= self.total_staff_spots:
            return await interaction.response.send_message("❌ Staff spots full.", ephemeral=True)

        self.staff_claims[interaction.user.id] = {"start": claim_start, "end": claim_end}
        await interaction.response.send_message(f"✅ Staff Spot reserved until {claim_end.strftime('%a %I%p')}")

    @app_commands.command(name="parking_status", description="See current availability (Private)")
    async def parking_status(self, interaction: discord.Interaction):
        now = datetime.now(local_tz).replace(minute=0, second=0, microsecond=0)
        day, hour = now.weekday(), now.hour
        lines = []

        # Logic for all possible spots (Offers + Permanent Guest)
        relevant_spots = set(list(self.offers.keys()) + [self.perm_guest])

        for s in sorted(relevant_spots):
            if s == self.perm_guest:
                d_start = now.replace(hour=0)
                d_end = d_start + timedelta(days=7)
                label = "Permanent Guest (46)"
            else:
                d_start = self.offers[s]["start"]
                d_end = self.offers[s]["end"]
                label = f"Spot {s}"
            # 1. Sort claims to find the gaps (Available Blocks)
            spot_claims = sorted(self.active_claims.get(s, []), key=lambda x: x['start'])
            available_blocks = []
            curr_ptr = d['start']

            for c in spot_claims:
                if (c['start'] - curr_ptr) >= timedelta(hours=2):
                    available_blocks.append((curr_ptr, c['start']))
                curr_ptr = max(curr_ptr, c['end'])

            if (d['end'] - curr_ptr) >= timedelta(hours=2):
                available_blocks.append((curr_ptr, d['end']))

            # 2. Check if the spot is currently occupied
            current_claimer = next((c for c in spot_claims if c["start"] <= now < c["end"]), None)

            if current_claimer:
                header = f"🔴 Occupied until {current_claimer['end'].strftime('%a %I%p')}"
            else:
                is_currently_free = any(start <= now < end for start, end in available_blocks)
                header = "🟢 Available Now" if is_currently_free else "⚪ Currently Off-Schedule"

            # 3. Build the "Upcoming" list: ONLY show unclaimed blocks
            # Since available_blocks only contains the GAPS between claims,
            # we just need to filter out blocks that have already passed.
            upcoming = []
            for start, end in available_blocks:
                if end > now:
                    icon = "🟢" if start <= now < end else "📅"
                    upcoming.append(f"{icon} {start.strftime('%a %I%p')}-{end.strftime('%a %I%p')}")

            # If a block is claimed, it naturally won't exist in 'upcoming' anymore.
            avail_detail = " | ".join(upcoming) if upcoming else "❌ No remaining 2hr+ blocks"
            lines.append(f"• **Spot {s}**: {header}\n  └ *Available Blocks:* {avail_detail}")

        # Staff blackout logic
        is_blackout = (day < 5 and hour < 17) or (day == 6 and 2 <= hour < 14)
        if is_blackout:
            staff_status = "❌ Closed (Permit Required)"
        else:
            active_staff_claims = len([t for t in self.staff_claims.values() if t["start"] <= now < t["end"]])
            open_staff = self.total_staff_spots - active_staff_claims
            staff_status = f"✅ {open_staff}/2 Available Now" if open_staff > 0 else "❌ Fully Occupied"

        embed = discord.Embed(title="🚗 Parking Availability", color=discord.Color.blue())
        embed.add_field(name="Resident Spots (Unclaimed 2hr+ blocks)",
                        value="\n".join(lines) if lines else "None offered.", inline=False)
        embed.add_field(name="Staff Spots", value=staff_status, inline=True)
        # embed.add_field(name="Permanent Guest", value=f"Spot 46: ✅ Available", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="unclaim_spot", description="Cancel your reservation")
    async def unclaim_spot(self, interaction: discord.Interaction, spot: int):
        if spot in self.active_claims:
            user_claims = [c for c in self.active_claims[spot] if c["claimer_id"] == interaction.user.id]
            if user_claims:
                self.active_claims[spot].remove(user_claims[0])
                return await interaction.response.send_message(f"🔄 Cancelled reservation for **Spot {spot}**.")
        await interaction.response.send_message("❌ No reservation found.", ephemeral=True)

    @app_commands.command(name="reclaim_spot", description="Reclaim your spot (Owner Only)")
    async def reclaim_spot(self, interaction: discord.Interaction, spot: int):
        if spot in self.offers and self.offers[spot]["user_id"] == interaction.user.id:
            del self.offers[spot]
            if spot in self.active_claims: del self.active_claims[spot]
            return await interaction.response.send_message(f"🔄 **Spot {spot}** withdrawn.")
        await interaction.response.send_message("❌ Not your spot.", ephemeral=True)

    @app_commands.command(name="unclaim_staff", description="Release staff spot")
    async def unclaim_staff(self, interaction: discord.Interaction):
        if self.staff_claims.pop(interaction.user.id, None):
            return await interaction.response.send_message("🔄 Staff spot released.")
        await interaction.response.send_message("❌ No claim found.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Parking(bot))