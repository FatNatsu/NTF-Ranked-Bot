import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.voice_states = True
intents.message_content = True

class NTFBot(commands.Bot):
    async def setup_hook(self):
        await self.load_extension("cogs.setup")

        guild = discord.Object(id=int(os.getenv("GUILD_ID")))

        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)

        print(f"Synced {len(synced)} guild commands.")

bot = NTFBot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

bot.run(TOKEN)
