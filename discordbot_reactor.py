#	Events that execute an action on discord
from discordbot_init import discordbot, TOKEN, CHANNEL, messages, isRunning

STATUSDICT = {
    "Done": "✅",
    "Loading": "⌛",
    "Sleeping": "💤",
    "Running": "🏃‍♂️",
    "D": "✅",
    "L": "⌛",
    "S": "💤",
    "R": "🏃‍♂️"
}

@discordbot.event
async def setupServerMessages(serverNames=["1", "2", "3"]):
    messages["servers"] = {}
    messages["control"] = {}

    channel = discordbot.get_channel(CHANNEL)

    for message in await channel.history(limit=1000).flatten():
        await message.delete()

    for serverName in serverNames:
        messages["servers"][serverName] = await channel.send(f"`Server {serverName}` - 💤")

    #messages["control"] = await channel.send("Press ▶ to start the servers.")
    #await messages["control"].add_reaction("▶")

@discordbot.event
async def updateServerStatus(serverName, status):
    """
    status can be set to:
    "D" for done (✅)
    "L" for loading (⌛)
    "S" for sleeping (💤)
    """
    await messages["servers"][serverName].edit(content=f"`Server {serverName}` - {STATUSDICT[status]}")

@discordbot.event
async def swapState():
    await setRunning(not isRunning)

@discordbot.event
async def setRunning(value):
    global isRunning, messages
    if not value:
        # for serverName in list(messages["servers"]):
        #    await updateServerStatus(serverName, "S")
        await messages["control"].edit(content="Press ▶ to start the servers.")
        await messages["control"].add_reaction("▶")
    else:
        # for serverName in list(messages["servers"]):
        #    await updateServerStatus(serverName, "L")
        await messages["control"].edit(content="Press 🛑 to stop the servers.")
        await messages["control"].add_reaction("🛑")
    isRunning = value

    # send signal to servers
