Minecraft Server Juggler for minecraft co-op speedrunning seed finding.
Copyright (C) 2020  MiniaczQ

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License,
or any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

PURPOSE:
This application is dedicated to the speedrunning community of minecraft.
It allows for a more throught usage of hardware by the servers.
Thanks to it less time is wasted when finding worlds for your speedruns.
Although performance increase is expected, no guarantee can be given as it heavily depends on the user's hardware and settings.

HOW TO CONFIGURE:
1. Start the application once to generate 'servers' and 'logs' folders.
2. Put copies of the same server, with different folder names, into the 'servers' folder.
3. Modify the servers' properties to use different IP adresses (or ports).
4. Open and configure 'settings.json':
    a) List all the server folders you want to use,
    b) Change launch arguments to fit your needs (different 'server.jar', less/more max RAM, disable --nogui, etc.),
    c) Adjust minimal time before server launches as needed. This may be a subject of change in the future,
    d) Change advancements you want to keep track of.

HOW TO USE:
1. When the application is launched, 'ops', 'whitelist', 'banned-ips' and 'banned-players' files of first server will be copied to all others.
2. When you start the applicaiton it will be in a juggling mode.
   To cycle through worlds, join the active servers.
   To restart the servers, leave them.
   All players must leave for a reset to happen.
3. To enter priority mode type anything in chat.
   Prompt can be adjusted by modifying a RegEx expression in the code. (Marked with '#ThisIsThePrompt')
   Priority mode will kill every other server to give you the best performance.
4. To start a speedrun perform a '/time set 0' command.
   The time will be used as a reference for logging advancement times.
5. To go back to juggling mode, remove all players from the prioritized server.