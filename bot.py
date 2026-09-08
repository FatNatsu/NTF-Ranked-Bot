import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.voice_states = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Load cogs automatically
async def load_extensions():
    for file in os.listdir("./cogs"):
        if file.endswith(".py"):
            await bot.load_extension(f"cogs.{file[:-3]}")

@bot.event
async def on_ready():
    await load_extensions()
    await bot.tree.sync()
    print(f"✅ {bot.user} is online.")

bot.run(os.getenv("TOKEN"))
