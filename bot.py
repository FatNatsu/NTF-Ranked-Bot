import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

from database.db import init_db

load_dotenv()

TOKEN = os.getenv("TOKEN")
GUILD_ID = os.getenv("GUILD_ID")

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.voice_states = True
intents.message_content = True

class NTFBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents
        )

    async def setup_hook(self):
        # Initialise database
        await init_db()

        # Load all cogs
        extensions = [
            "cogs.setup",
            "cogs.queue",
            "cogs.admin",
            "cogs.mode",
            "cogs.matchmaking",
            "cogs.session",
            "cogs.profile",
            "cogs.leaderboard",
        ]

        for extension in extensions:
            try:
                await self.load_extension(extension)
                print(f"✅ Loaded {extension}")
            except Exception as e:
                print(f"❌ Failed to load {extension}: {e}")

        # Sync slash commands
if GUILD_ID:
    guild = discord.Object(id=int(GUILD_ID))
    self.tree.copy_global_to(guild=guild)
    synced = await self.tree.sync(guild=guild)
else:
    synced = await self.tree.sync()

print(f"🟦 Synced {len(synced)} slash commands.", flush=True)

bot = NTFBot()

@bot.event
async def on_ready():
    print("=" * 40)
    print(f"Logged in as: {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print("=" * 40)

bot.run(TOKEN)
