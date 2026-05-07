import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class RolesService:
    """Business logic and data access for role selection and directory updates."""

    def __init__(self, supabase):
        """Store the shared Supabase client."""
        self.supabase = supabase

    async def get_last_update(self, discord_id: int) -> str | None:
        """Fetches the ISO string of the user's last role update."""
        try:
            res = (
                await self.supabase.table("residents")
                .select("last_role_update")
                .eq("discord_id", str(discord_id))
                .execute()
            )
            if res.data and res.data[0].get("last_role_update"):
                return res.data[0]["last_role_update"]
            return None
        except Exception as e:
            logger.exception(f"Failed to fetch last role update for {discord_id}: {e}")
            return None

    async def update_resident_status(
        self, discord_id: int, username: str, role_slug: str, email: str = None
    ) -> bool:
        """
        Upserts a resident's role status into Supabase.
        If an email is provided (for alumni), it updates that field as well.
        Also timestamps the update to enforce the 30-day rate limit.
        """
        payload = {
            "discord_id": str(discord_id),
            "username": username,
            "community_role": role_slug,
            "last_role_update": datetime.now(timezone.utc).isoformat(),
        }

        # Only attach email to payload if it exists, so we don't accidentally overwrite
        # a previously saved email with a None value if they skip the modal later.
        if email:
            payload["email"] = email

        try:
            res = await self.supabase.table("residents").upsert(payload).execute()
            # If the data list is returned, the upsert was successful
            return bool(res.data)
        except Exception as e:
            logger.exception(f"Failed to update resident status for {username}: {e}")
            return False