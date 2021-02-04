import os
import discord
from dotenv import load_dotenv

messages = {"servers": {}, "control": None}
isRunning = False
inARun = False
serverNamesStart = []

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL = int(os.getenv('DISCORD_CHANNEL'))

discordbot = discord.Client()
