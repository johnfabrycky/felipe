import logging
from datetime import datetime, timezone, timedelta

import discord
from discord import app_commands
from discord.ext import commands

from bot.services.roles_service import RolesService
from bot.config import (
    KOINONIAN_ROLE_ID,
    STRATFORDITE_ROLE_ID,
    ALUMNI_ROLE_ID,
    SUTTONITE_ROLE_ID,
    RA_LOG_CHANNEL_ID,  # Ensure this is defined in your config.py
)

logger = logging.getLogger(__name__)

# --- UI Components ---


class AlumniEmailModal(discord.ui.Modal, title="Alumni Network"):
    """A popup modal to optionally collect an email when someone selects Alumni."""

    email = discord.ui.TextInput(
        label="Personal Email (Optional)",
        placeholder="Leave blank if you prefer not to share",
        required=False,
        style=discord.TextStyle.short,
        max_length=100,
    )

    def __init__(
        self, service: RolesService, roles_to_remove: list, alumni_role: discord.Role
    ):
        super().__init__()
        self.service = service
        self.roles_to_remove = roles_to_remove
        self.alumni_role = alumni_role

    async def on_submit(self, interaction: discord.Interaction):
        # 1. Immediately defer so we have 15 minutes to do API calls safely
        await interaction.response.defer(ephemeral=True)

        provided_email = self.email.value.strip() or None

        # 2. Swap the Discord roles now that we are safe from timeouts
        if self.roles_to_remove:
            await interaction.user.remove_roles(*self.roles_to_remove)
        await interaction.user.add_roles(self.alumni_role)

        # 3. Write to database
        success = await self.service.update_resident_status(
            discord_id=interaction.user.id,
            username=interaction.user.display_name,
            role_slug="alumni",
            email=provided_email,
        )

        if success:
            if provided_email:
                msg = f"✅ You are now an Alumni! We'll keep in touch at `{provided_email}`."
            else:
                msg = "✅ You are now an Alumni! Your status has been updated."

            # --- AUDIT LOG ---
            log_channel = interaction.guild.get_channel(RA_LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(
                    f"🎓 **Role Update:** {interaction.user.mention} just assigned themselves **Alumni**."
                )
        else:
            msg = "⚠️ Your Discord role was updated, but we couldn't save your status to the database."

        # 4. Use followup since we deferred
        await interaction.followup.send(msg, ephemeral=True)


class CommunitySelect(discord.ui.Select):
    """The dropdown menu for mutually exclusive house selection."""

    def __init__(self, service: RolesService):
        self.service = service
        options = [
            discord.SelectOption(
                label="Koinonia",
                description="Resident of Koinonia",
                value="koinonian",
                emoji="🏠",
            ),
            discord.SelectOption(
                label="Stratford",
                description="Resident of Stratford",
                value="stratfordite",
                emoji="🏠",
            ),
            discord.SelectOption(
                label="Sutton",
                description="Resident of Sutton",
                value="suttonite",
                emoji="🏠",
            ),
            discord.SelectOption(
                label="Alumni",
                description="Former resident",
                value="alumni",
                emoji="🎓",
            ),
        ]
        super().__init__(
            placeholder="Select your community...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="persistent_community_select",
        )

    async def callback(self, interaction: discord.Interaction):
        # --- RATE LIMIT CHECK (Usually very fast) ---
        last_update_str = await self.service.get_last_update(interaction.user.id)

        if last_update_str and not interaction.user.guild_permissions.administrator:
            last_update = datetime.fromisoformat(last_update_str)
            now = datetime.now(timezone.utc)
            time_since = now - last_update

            if time_since < timedelta(days=30):
                days_left = 30 - time_since.days
                return await interaction.response.send_message(
                    f"⏳ **Rate Limited:** To prevent house snooping, you can only change your community role once every 30 days.\n\n"
                    f"You can change it again in **{days_left} days**. If you made a mistake, please ping an RA or Server Admin to manually fix your roles.",
                    ephemeral=True,
                )
        # --- END RATE LIMIT CHECK ---

        role_map = {
            "koinonian": interaction.guild.get_role(KOINONIAN_ROLE_ID),
            "stratfordite": interaction.guild.get_role(STRATFORDITE_ROLE_ID),
            "suttonite": interaction.guild.get_role(SUTTONITE_ROLE_ID),
            "alumni": interaction.guild.get_role(ALUMNI_ROLE_ID),
        }

        selected_slug = self.values[0]
        selected_role = role_map[selected_slug]

        if not selected_role:
            return await interaction.response.send_message(
                "❌ Configuration error: Role not found on the server.", ephemeral=True
            )

        roles_to_remove = [
            r for r in role_map.values() if r and r in interaction.user.roles
        ]

        # --- BRANCH LOGIC ---
        if selected_slug == "alumni":
            # Pass the role mapping into the modal and launch it immediately
            modal = AlumniEmailModal(self.service, roles_to_remove, selected_role)
            await interaction.response.send_modal(modal)

        else:
            # For standard houses, defer immediately to beat the 3-second clock
            await interaction.response.defer(ephemeral=True)

            # Do the heavy API lifting
            if roles_to_remove:
                await interaction.user.remove_roles(*roles_to_remove)
            await interaction.user.add_roles(selected_role)

            # Write to DB
            success = await self.service.update_resident_status(
                discord_id=interaction.user.id,
                username=interaction.user.display_name,
                role_slug=selected_slug,
            )

            # Followup response
            if success:
                await interaction.followup.send(
                    f"✅ You have been assigned the **{selected_role.name}** role!",
                    ephemeral=True,
                )

                log_channel = interaction.guild.get_channel(RA_LOG_CHANNEL_ID)
                if log_channel:
                    await log_channel.send(
                        f"🔄 **Role Update:** {interaction.user.mention} just assigned themselves the **{selected_role.name}** role."
                    )
            else:
                await interaction.followup.send(
                    f"⚠️ Assigned **{selected_role.name}**, but failed to sync to the directory.",
                    ephemeral=True,
                )


class CommunityView(discord.ui.View):
    """A persistent view holding the select menu."""

    def __init__(self, service: RolesService):
        super().__init__(timeout=None)
        self.add_item(CommunitySelect(service))


# --- The Cog ---


class Roles(commands.Cog):
    """Handles role assignments and directory synchronization."""

    def __init__(self, bot):
        self.bot = bot
        self.service = RolesService(bot.supabase)

    async def cog_load(self):
        """Register the persistent view on startup."""
        self.bot.add_view(CommunityView(self.service))
        logger.info("Persistent CommunityView loaded.")

    @app_commands.command(
        name="spawn_role_menu",
        description="[Admin] Spawns the persistent role selection menu in the current channel.",
    )
    @app_commands.default_permissions(administrator=True)
    async def spawn_role_menu(self, interaction: discord.Interaction):
        """Admin command to drop the persistent UI into a designated channel."""
        # 1. Immediately acknowledge the interaction to prevent the 3-second timeout
        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title="Community Selection",
            description="Please select your current status using the dropdown below. Choosing a new status will automatically remove your old one.\n\n*If you are moving on, select **Alumni**!*",
            color=discord.Color.blurple(),
        )

        # 2. Send the actual menu to the channel
        await interaction.channel.send(embed=embed, view=CommunityView(self.service))

        # 3. Use .followup.send() for the confirmation since we already deferred
        await interaction.followup.send("✅ Menu spawned successfully.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Roles(bot))