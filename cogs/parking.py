import discord
from discord import app_commands
from discord.ext import commands, tasks
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
        self.staff_claims = []
        self.total_staff_spots = 2

    # --- SHARED CHOICES ---
    DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    day_choices = [app_commands.Choice(name=d.capitalize(), value=d) for d in DAYS]
    time_choices = [app_commands.Choice(name=f"{i % 12 or 12} {'AM' if i < 12 else 'PM'}",
                                        value=f"{i % 12 or 12} {'AM' if i < 12 else 'PM'}") for i in range(24)]

    # --- INTERNAL UTILITIES ---
    def _parse_range(self, s_day, s_time, e_day, e_time):
        """Parses start/end choices into localized datetimes with 7-day wrap handling."""
        now = datetime.now(local_tz).replace(minute=0, second=0, microsecond=0)

        def to_dt(d_str, t_str):
            target_day = self.DAYS.index(d_str.lower())
            days_ahead = (target_day - now.weekday() + 7) % 7
            t_obj = datetime.strptime(t_str.strip().upper(), "%I %p").time()
            return (now + timedelta(days=days_ahead)).replace(hour=t_obj.hour)

        start, end = to_dt(s_day, s_time), to_dt(e_day, e_time)
        return start, (end + timedelta(days=7) if end <= start else end)

    def _get_overlap(self, start, end, existing_list):
        """Returns True if the timeframe overlaps with any entry in the list."""
        return any(not (end <= ex["start"] or start >= ex["end"]) for ex in existing_list)

    def _is_blackout(self, start, end):
        """Checks if range hits: Mon-Fri < 5PM or Sun 2AM-2PM."""
        curr = start
        while curr < end:
            d, h = curr.weekday(), curr.hour
            if (d < 5 and h < 17) or (d == 6 and 2 <= h < 14): return True
            curr += timedelta(hours=1)
        return False

    # --- COMMANDS ---
    @app_commands.command(name="my_parking", description="View your active offers and reservations")
    async def my_parking(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        now = datetime.now(local_tz)

        embed = discord.Embed(
            title="📋 My Parking Activity",
            color=discord.Color.green(),
            timestamp=now
        )

        # 1. Find spots the user has OFFERED (Resident spots)
        user_offers = [
            f"**Spot {spot}**: {off['start'].strftime('%a %I%p')} — {off['end'].strftime('%a %I%p')}"
            for spot, off in self.offers.items() if off["user_id"] == user_id
        ]
        embed.add_field(
            name="📤 My Offers (Listed for others)",
            value="\n".join(user_offers) if user_offers else "No active offers.",
            inline=False
        )

        # 2. Find spots the user has CLAIMED (Resident or Guest 46)
        user_claims = []
        for spot, claims in self.active_claims.items():
            for c in claims:
                if c["claimer_id"] == user_id:
                    status = "✅ Active" if c["start"] <= now <= c["end"] else "📅 Upcoming"
                    user_claims.append(
                        f"{status} **Spot {spot}**: {c['start'].strftime('%a %I%p')} — {c['end'].strftime('%a %I%p')}"
                    )

        # 3. Find STAFF spots the user has CLAIMED
        for sc in self.staff_claims:
            if sc["user_id"] == user_id:
                status = "✅ Active" if sc["start"] <= now <= sc["end"] else "📅 Upcoming"
                user_claims.append(
                    f"{status} **Staff Spot**: {sc['start'].strftime('%a %I%p')} — {sc['end'].strftime('%a %I%p')}"
                )

        embed.add_field(
            name="📥 My Reservations",
            value="\n".join(user_claims) if user_claims else "No active reservations.",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command(name="offer_spot", description="List your spot as available")
    @app_commands.choices(start_day=day_choices, end_day=day_choices, start_time=time_choices, end_time=time_choices)
    async def offer_spot(self, interaction: discord.Interaction, spot: int,
                         start_day: app_commands.Choice[str], start_time: app_commands.Choice[str],
                         end_day: app_commands.Choice[str], end_time: app_commands.Choice[str]):
        if spot not in self.valid_spots:
            return await interaction.response.send_message(f"❌ Spot {spot} is invalid.", ephemeral=True)

        start, end = self._parse_range(start_day.value, start_time.value, end_day.value, end_time.value)
        self.offers[spot] = {"user_id": interaction.user.id, "start": start, "end": end}
        await interaction.response.send_message(
            f"📢 **Spot {spot}** listed: {start.strftime('%a %I%p')} — {end.strftime('%a %I%p')}", ephemeral=False)

    @app_commands.command(name="claim_spot", description="Reserve a resident or guest spot")
    @app_commands.choices(start_day=day_choices, end_day=day_choices, start_time=time_choices, end_time=time_choices)
    async def claim_spot(self, interaction: discord.Interaction, spot: int,
                         start_day: app_commands.Choice[str], start_time: app_commands.Choice[str],
                         end_day: app_commands.Choice[str], end_time: app_commands.Choice[str]):

        c_start, c_end = self._parse_range(start_day.value, start_time.value, end_day.value, end_time.value)
        now = datetime.now(local_tz)

        # --- GUEST SPOT (46) LOGIC ---
        if spot == self.perm_guest:
            # Guest spot is always available for the next 14 days, no "offer" needed
            w_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            w_end = w_start + timedelta(days=7)
            owner_id = 0  # System owned

        # --- RESIDENT SPOT LOGIC ---
        elif spot in self.offers:
            off = self.offers[spot]
            w_start, w_end, owner_id = off["start"], off["end"], off["user_id"]

        else:
            return await interaction.response.send_message(f"❌ Spot {spot} is not currently offered by any resident.",
                                                           ephemeral=True)

        # --- UNIVERSAL VALIDATIONS ---

        # 1. Check if the requested time is within the allowed window
        if c_start < w_start or c_end > w_end:
            return await interaction.response.send_message(
                f"❌ Outside allowed window. For Spot {spot}, you can book between "
                f"{w_start.strftime('%a %I%p')} and {w_end.strftime('%a %I%p')}.", ephemeral=True)

        # 2. Check duration constraints (2h to 7 days)
        duration = c_end - c_start
        if not (timedelta(hours=2) <= duration <= timedelta(days=7)):
            return await interaction.response.send_message("❌ Reservations must be between 2 hours and 7 days long.",
                                                           ephemeral=True)

        # 3. CONFLICT CHECK: Validate against existing reservations in active_claims
        existing_claims = self.active_claims.get(spot, [])
        if self._get_overlap(c_start, c_end, existing_claims):
            return await interaction.response.send_message(f"❌ Spot {spot} is already reserved during that time.",
                                                           ephemeral=True)

        # --- COMMIT RESERVATION ---
        self.active_claims.setdefault(spot, []).append({
            "claimer_id": interaction.user.id,
            "owner_id": owner_id,
            "start": c_start,
            "end": c_end
        })

        await interaction.response.send_message(
            f"✅ **Spot {spot}** successfully reserved!\n"
            f"📅 {c_start.strftime('%a %I%p')} — {c_end.strftime('%a %I%p')}", ephemeral=False)

    @app_commands.command(name="claim_staff", description="Reserve a staff spot")
    @app_commands.choices(start_day=day_choices, end_day=day_choices, start_time=time_choices, end_time=time_choices)
    async def claim_staff(self, interaction: discord.Interaction,
                          start_day: app_commands.Choice[str], start_time: app_commands.Choice[str],
                          end_day: app_commands.Choice[str], end_time: app_commands.Choice[str]):

        c_start, c_end = self._parse_range(start_day.value, start_time.value, end_day.value, end_time.value)

        if self._is_blackout(c_start, c_end):
            return await interaction.response.send_message("❌ Blackout hours active (Mon-Fri < 5PM or Sun 2AM-2PM).",
                                                           ephemeral=True)

        # Count how many staff spots are already taken during this specific timeframe
        overlapping_claims = [t for t in self.staff_claims if not (c_end <= t["start"] or c_start >= t["end"])]

        if len(overlapping_claims) >= self.total_staff_spots:
            return await interaction.response.send_message("❌ Staff spots are full for this timeframe.", ephemeral=True)

        # Add the claim to the list
        self.staff_claims.append({"user_id": interaction.user.id, "start": c_start, "end": c_end})
        await interaction.response.send_message(
            f"✅ Staff Spot reserved: {c_start.strftime('%a %I%p')} — {c_end.strftime('%a %I%p')}", ephemeral=False)

    @app_commands.command(name="parking_status")
    async def parking_status(self, interaction: discord.Interaction):
        now = datetime.now(local_tz).replace(minute=0, second=0, microsecond=0)
        lines = []

        # Ensure Spot 46 is always included in the spots to check
        all_spots = sorted(set(list(self.offers.keys()) + [self.perm_guest]))

        for s in all_spots:
            # Define window: Spot 46 is always "offered" for the next 7 days
            if s == self.perm_guest:
                w_start = now.replace(hour=0)
                w_end = w_start + timedelta(days=7)
            else:
                w_start, w_end = self.offers[s]["start"], self.offers[s]["end"]

            # Calculate gaps (unclaimed time)
            claims = sorted(self.active_claims.get(s, []), key=lambda x: x['start'])
            blocks, ptr = [], w_start
            for c in claims:
                if (c['start'] - ptr) >= timedelta(hours=2):
                    blocks.append((ptr, c['start']))
                ptr = max(ptr, c['end'])
            if (w_end - ptr) >= timedelta(hours=2):
                blocks.append((ptr, w_end))

            # Status Formatting
            current = next((c for c in claims if c["start"] <= now < c["end"]), None)
            header = f"🔴 Busy until {current['end'].strftime('%a %I%p')}" if current else "🟢 Available Now"

            detail = " | ".join(
                [f"{'🟢' if b[0] <= now < b[1] else '📅'} {b[0].strftime('%a %I%p')}-{b[1].strftime('%a %I%p')}"
                 for b in blocks if b[1] > now])
            lines.append(f"**Spot {s}**: {header}\n└ *Free:* {detail or '❌ Fully Booked'}")

        # Staff Logic: Updated to handle self.staff_claims as a LIST
        is_blk = (now.weekday() < 5 and now.hour < 17) or (now.weekday() == 6 and 2 <= now.hour < 14)
        active_staff_count = len([t for t in self.staff_claims if t["start"] <= now < t["end"]])
        staff_status = "❌ Closed" if is_blk else f"✅ {self.total_staff_spots - active_staff_count}/{self.total_staff_spots} Free"

        embed = discord.Embed(title="🚗 Parking Status", color=discord.Color.blue())
        embed.add_field(name="Resident/Guest", value="\n".join(lines) or "No spots offered", inline=False)
        embed.add_field(name="Staff Spots", value=staff_status)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tasks.loop(minutes=1)
    async def parking_monitor(self):
        """Silent cleanup: Removes expired data so the status stays accurate."""
        now = datetime.now(local_tz)

        # 1. Cleanup Resident/Guest Claims
        for spot in list(self.active_claims.keys()):
            # Only keep claims that haven't ended yet
            self.active_claims[spot] = [c for c in self.active_claims[spot] if c["end"] > now]
            # Remove the spot key if no claims remain
            if not self.active_claims[spot]:
                del self.active_claims[spot]

        # 2. Cleanup Staff Claims
        self.staff_claims = [sc for sc in self.staff_claims if sc["end"] > now]

        # 3. Cleanup Offers
        # If an owner's offer window has passed, remove it from the list
        self.offers = {s: off for s, off in self.offers.items() if off["end"] > now}

    @app_commands.command(name="cancel")
    async def cancel(self, interaction: discord.Interaction, spot: int = None):
        """Unified cancel for staff or resident spots."""
        user_id = interaction.user.id
        found = False

        # 1. Check Staff Claims (Handle as list)
        initial_count = len(self.staff_claims)
        self.staff_claims = [c for c in self.staff_claims if not (spot is None and c["user_id"] == user_id)]
        if len(self.staff_claims) < initial_count:
            found = True
            await interaction.response.send_message("🔄 Staff spot reservation(s) cancelled.")

        # 2. Check Resident/Guest Claims
        if spot and spot in self.active_claims:
            orig_len = len(self.active_claims[spot])
            self.active_claims[spot] = [c for c in self.active_claims[spot] if c["claimer_id"] != user_id]
            if len(self.active_claims[spot]) < orig_len:
                msg = f"🔄 Cancelled reservation for **Spot {spot}**."
                if found:
                    await interaction.followup.send(msg)
                else:
                    await interaction.response.send_message(msg)
                found = True

        # 3. Check Offer Reclaim (Owner withdrawing)
        if spot and spot in self.offers and self.offers[spot]["user_id"] == user_id:
            del self.offers[spot]
            self.active_claims.pop(spot, None)
            msg = f"🔄 **Spot {spot}** withdrawn by owner."
            if found:
                await interaction.followup.send(msg)
            else:
                await interaction.response.send_message(msg)
            found = True

        if not found:
            await interaction.response.send_message("❌ No active record found to cancel.", ephemeral=True)

    @app_commands.command(name="parking_help", description="How to use the parking system")
    async def parking_help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🚗 Parking System Guide",
            description="Manage resident, guest, and staff parking spots efficiently.",
            color=discord.Color.blue()
        )

        # Basic Commands
        embed.add_field(
            name="📍 General Commands",
            value=(
                "`/parking_status` - View all currently available and reserved spots.\n"
                "`/cancel [spot]` - Cancel your reservation or withdraw your offer.\n"
                "   *Leave [spot] blank to cancel Staff reservations.*"
            ),
            inline=False
        )

        # Resident/Guest Section
        embed.add_field(
            name="🏠 Resident & Guest Spots",
            value=(
                "**Spot 46 (Guest):** Always available to claim up to 7 days in advance.\n"
                "**Resident Spots (1-33, 41-45):** Must be offered by the owner first.\n\n"
                "`/offer_spot` - Owners list their spot for others to use.\n"
                "`/claim_spot` - Reserve an offered resident spot or the guest spot.\n"
                "   *Note: Claims must be between 2 hours and 7 days long.*"
            ),
            inline=False
        )

        # Staff Section
        embed.add_field(
            name="👔 Staff Parking",
            value=(
                "`/claim_staff` - Reserve one of the 2 available staff spots.\n"
                "**Blackout Rules:** Staff spots cannot be reserved during:\n"
                "• Mon-Fri: Before 5:00 PM\n"
                "• Sunday: 2:00 AM - 2:00 PM"
            ),
            inline=False
        )

        embed.set_footer(text="All times are in America/Chicago (CST/CDT)")
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Parking(bot))