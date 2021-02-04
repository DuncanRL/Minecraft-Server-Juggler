#	Parsing and interpreting discord input
from discordbot_init import discordbot, TOKEN, CHANNEL, messages, isRunning
import discordbot_reactor

#@discordbot.event
#async def on_message(message):
#    if "showonthebotplease" in message.content:
#        print(message.content)

#@discordbot.event
#async def on_reaction_add(reaction, user):
#    global isRunning
#    if reaction.message.id == messages["control"].id and not user.bot:
#        await reaction.remove(user)
#        await reaction.remove(discordbot.user)
#        await discordbot.swapState()