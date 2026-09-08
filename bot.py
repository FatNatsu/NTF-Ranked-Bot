
import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
load_dotenv()
bot=commands.Bot(command_prefix='!', intents=discord.Intents.all())
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
bot.run(os.getenv('TOKEN'))
