import logging

logger = logging.getLogger(__name__)


class RolesService:
    """Business logic and data access for role selection and directory updates."""

    def __init__(self, supabase):
        """Store the shared Supabase client."""
        self.supabase = supabase

    async def update_resident_status(
        self, discord_id: int, username: str, role_slug: str, email: str = None
    ) -> bool:
        """
        Upserts a resident's role status into Supabase.
        If an email is provided (for alumni), it updates that field as well.
        """
        payload = {
            "discord_id": str(discord_id),
            "username": username,
            "community_role": role_slug,
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