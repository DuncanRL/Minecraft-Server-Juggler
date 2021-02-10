from discordbot_init import *
import discordbot_listener
import discordbot_reactor
import time

updates = []
alreadyStarted = False

@discordbot.event
async def on_ready():
    global serverNamesStart, updates, alreadyStarted
    if not alreadyStarted:
        alreadyStarted = True
        channel = discordbot.get_channel(CHANNEL)
        guild = channel.guild

        print(f"MSJ2 Discord Bot connected to #{channel.name} in {guild.name}")

        if len (serverNamesStart) > 0:
            await discordbot.setupServerMessages(serverNamesStart)

        while True:
            time.sleep(0.2)
            if len(updates) > 0:
                update = updates.pop(0)
                await discordbot.updateServerStatus(update[0],update[1])

def discordbot_start(serverNames=[]):
    global serverNamesStart
    serverNamesStart = serverNames
    discordbot.run(TOKEN)

if __name__ == "__main__":
    discordbot_start()