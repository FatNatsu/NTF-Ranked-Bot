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
        for file in os.listdir("./cogs"):
            if file.endswith(".py"):
                await self.load_extension(f"cogs.{file[:-3]}")

        synced = await self.tree.sync()
        print(f"Synced {len(synced)} commands.")

bot = NTFBot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

bot.run(TOKEN)
