import os
import logging
import discord
from discord.ext import commands
import google.generativeai as genai

logger = logging.getLogger(__name__)


class GeminiChat(commands.Cog):
    """Cog for handling @mentions using the Gemini API."""

    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv("GEMINI_API_KEY")

        if self.api_key:
            genai.configure(api_key=self.api_key)
            # Using the gemini-1.5-flash model (available on the free tier)
            self.model = genai.GenerativeModel(
                "gemma-3-1b-it",
                system_instruction=(
                    "Right now someone has pinged you. Only respond with 'yes' or 'no'."
                ),
            )
        else:
            self.model = None
            logger.warning(
                "GEMINI_API_KEY not found! Gemini chat features will be disabled."
            )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore messages sent by bots (including Felipe himself)
        if message.author.bot:
            return

        # Check if the bot was mentioned in the message
        if self.bot.user in message.mentions:
            if not self.model:
                await message.reply(
                    "I'd love to roast you right now, but my developer forgot to give me a Gemini API key. 🧠💨"
                )
                return

            # Clean the mention out of the text so the model only sees the prompt
            user_prompt = message.clean_content.replace(
                f"@{self.bot.user.display_name}", ""
            ).strip()

            # If they just pinged without saying anything
            if not user_prompt:
                user_prompt = "I just pinged you without asking a question. Tell me a funny joke about being annoyed by pings."

            try:
                # Show the "Felipe is typing..." indicator in Discord
                async with message.channel.typing():
                    response = await self.model.generate_content_async(user_prompt)
                    await message.reply(response.text)
            except Exception as e:
                logger.error(f"Gemini API error: {e}")
                await message.reply(
                    "Whoops, I tried to be funny but my AI brain short-circuited. Try again later! 🤖⚡"
                )


async def setup(bot):
    """Register the gemini chat cog with the bot."""
    await bot.add_cog(GeminiChat(bot))