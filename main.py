'''
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
'''

from subprocess import PIPE, Popen
from os import chdir, getcwd, remove, mkdir
from shutil import rmtree, copyfile
from datetime import datetime
from re import search, compile
from shlex import split
from json import load
from time import monotonic, sleep
from threading import Thread, Lock
from queue import Queue
from signal import signal, SIGTERM, SIGINT
from os.path import join
from enum import Enum
from sys import stdout
from discordbot_core import discordbot, discordbot_start, updates
from asyncio import create_task
from redirector import Redirector
import asyncio as aio

currentRedirection = None
cr_lock = Lock()


class PipeQueuer(Thread):
    '''
    Runs in a separate thread.
    Reads server logs and leaves them on a queue.
    '''

    def __init__(self, pipe, queue):
        Thread.__init__(self)
        self.pipe = pipe
        self.queue = queue

    def run(self):
        for line in iter(self.pipe.readline, ''):
            self.queue.put(line)


serverListeners = [compile(r'\[..:..:..\] \[Server thread/INFO\]: Starting minecraft server').search,
                   compile(
                       r'\[..:..:..\] \[Server thread/INFO\]: Preparing start region for dimension minecraft:overworld').search,
                   compile(
                       r'\[..:..:..\] \[Server thread/INFO\]: Done').search,
                   # ThisIsThePrompt
                   compile(
                       r'\[..:..:..\] \[Server thread/INFO\]: \[.*?: Automatic saving is now disabled\]').search,
                   compile(
                       r'\[..:..:..\] \[Server thread/INFO\]: \[.*?: Set the time to 0\]').search,
                   compile(r'\[..:..:..\] \[Server thread/INFO\]: Stopping server').search]


class playerListeners:
    JOINED = compile(
        r'\[..:..:..\] \[Server thread/INFO\]: .*? joined the game').search
    LEFT = compile(
        r'\[..:..:..\] \[Server thread/INFO\]: .*? left the game').search
    ADVANCEMENT = compile(
        r'\[..:..:..\] \[Server thread/INFO\]: .*? has made the advancement \[.*?\]').search


class extract:
    '''
    Namespace for extraction functions.
    '''

    def __init__(self):
        raise Exception('AbstractClass')

    @staticmethod
    def TIME(string):
        return string[:10]

    @staticmethod
    def ADVANCEMENT(string):
        return string[search(r'has made the advancement', string).end(0)+2:-2]

    @staticmethod
    def JOINED(string):
        return string[33:-17]


class Time:
    '''
    Specialized class for simple time management.
    '''

    def __init__(self, time):
        self.time = time

    @staticmethod
    def fromString(string):
        return Time(int(string[1:3]) * 3600 + int(string[4:6]) * 60 + int(string[7:9]))

    @staticmethod
    def delta(a, b):
        value = b.time - a.time
        if b.time < a.time:
            value += 60 * 60 * 24
        return Time(value)

    def toString(self):
        return f"[{self.time//3600:02}:{self.time%3600//60:02}:{self.time%60:02}]"


stateMessages = [None,
                 'Server starting.',
                 'World generation started.',
                 'World generation finished.',
                 'Server prioritized.',
                 'Speedrun started.']


def createFolders():
    flag = False
    try:
        mkdir('logs')
        flag = True
    except:
        pass
    return flag


def loadSettings():
    '''
    Loads and processes settings.
    '''
    with open('settings.json', 'r') as settings_file:
        settings = load(settings_file)
        settings_file.close()
    settings['arguments'] = split(settings['arguments'])
    return settings


def loadLogs():
    return (open(join('logs', f'{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}.txt'), 'w'), stdout)


class ServerFolder:
    '''
    Instance of a server folder.
    '''
    syncFiles = ['whitelist.json',
                 'ops.json',
                 'banned-ips.json',
                 'banned-players.json']

    def __init__(self, settings, logs, folder):
        self.settings = settings
        self.logs = logs
        self.folder = folder
        self.redirector = Redirector(
            self.getPort(), "192.168.2.129", 26003, packet_size=65536)
        self.r_lock = aio.Lock()
        self.isRedirecting = False

    def getPort(self):
        with open(join(self.folder, "server.properties"), "r") as spFile:
            for i in spFile.readlines():
                if "server-port" == i[:len("server-port")]:
                    return int(i.split("=")[1])

    def start(self):
        self.server = Server(Popen(
            settings['arguments'], cwd=self.folder, stdout=PIPE, text=True, stdin=PIPE))
        self.state = 0

    def start_redirecting_thread(self):
        aio.start(self.start_redirecting())    

    def stop_redirecting_thread(self):
        aio.start(self.stop_redirecting())    

    async def start_redirecting(self):
        self.isRedirecting = True
        await self.redirector.start()
        await self.r_lock.acquire()
        await self.r_lock.acquire()
        await self.r_lock.release()

    async def stop_redirecting(self):
        self.isRedirecting = False
        await self.redirector.stop()
        await self.r_lock.release()

    def kill(self):
        global activeServers, currentRedirection
        if self.isRedirecting:
            with cr_lock:
                Thread(target=self.stop_redirecting_thread).run()
                currentRedirection = None
                for i in activeServers:
                    if i.state == 3:
                        Thread(target=i.start_redirecting_thread).run()
                        currentRedirection = i
        self.server.process.kill()
        del self.server

    def reset(self):
        '''
        Attempts to delete the world file.
        '''
        rmtree(join(getcwd(), self.folder, 'world'), ignore_errors=True)
        try:
            remove(join(getcwd(), self.folder, 'ops.json'))
        except:
            pass
        try:
            remove(join(getcwd(), self.folder, 'whitelist.json'))
        except:
            pass

    def read(self):
        '''
        Generator, returns all unread server logs.
        '''
        while not self.server.queue.empty():
            yield self.server.queue.get()

    def sync(self, folder):
        '''
        Copies specific files from provided template folder.
        '''
        mwd = getcwd()
        src = join(mwd, folder)
        dst = join(mwd, self.folder)
        chdir(dst)
        for file in ServerFolder.syncFiles:
            try:
                remove(file)
            except:
                pass
            try:
                copyfile(join(src, file), join(dst, file))
            except:
                pass
        chdir(mwd)

    def write(self, string):
        '''
        Leaves a message in the console and log file.
        '''
        time = datetime.now().strftime("%H:%M:%S")
        msg = f'[{time}] [Server {self.folder}] {string}\n'
        self.logs[0].write(msg)
        self.logs[1].write(msg)
        self.logs[1].flush()


def initiateServers(settings, logs, inactiveServers):
    '''
    Synchronizes and initiates all servers.
    '''
    templateFolder = None
    for folder in settings['servers']:
        server = ServerFolder(settings, logs, folder)
        inactiveServers.append(server)
        if templateFolder:
            server.sync(templateFolder)
        else:
            templateFolder = folder


class Server:
    '''
    Instance of one server execution.
    '''

    def __init__(self, process):
        self.process = process
        self.queue = Queue()
        self.pipeQueuer = PipeQueuer(self.process.stdout, self.queue)
        self.pipeQueuer.daemon = True
        self.pipeQueuer.start()

        self.players = 0
        self.playerList = {}
        self.startTime = 0
        self.advancements = {}

    def run_command(self, command):
        self.process.stdin.write(command+"\n")
        self.process.stdin.flush()


def event_playerJoined(server, line):
    playerName = extract.JOINED(line)

    if server.server.players == 0:
        server.server.run_command(f'op {playerName}')

    server.server.run_command(f'whitelist add {playerName}')

    server.server.players += 1
    server.server.playerList[playerName] = True
    # LOG
    server.write(f'Player {playerName} joined.')


def event_playerLeft(server):
    server.server.players -= 1
    # LOG
    server.write('Player left.')
    if server.server.players == 0:
        server.kill()
        # LOG
        server.write('All players left. Killing server.')
        updates.append([server.folder, "S"])
        return True
    return False


def event_serverStop(server):
    server.kill()
    # LOG
    server.write('Server killed from outside.')
    updates.append([server.folder, "S"])


def event_serverProgress(server):
    global cr_lock, currentRedirection
    server.state += 1
    # LOG
    server.write(stateMessages[server.state])

    if server.state == 1:
        server.server.run_command("whitelist off")
        updates.append([server.folder, "L"])
    elif server.state == 3:
        updates.append([server.folder, "D"])
        with cr_lock:
            if currentRedirection is None:
                currentRedirection = server
                Thread(target=server.start_redirecting_thread).run()

    elif server.state == 5:
        server.server.run_command("whitelist on")
        updates.append([server.folder, "R"])


def event_serverAdvancement(server, line):
    advancement = extract.ADVANCEMENT(line)
    if advancement in server.settings['advancements']:
        if advancement not in server.server.advancements:
            timeString = Time.toString(Time.delta(
                server.server.startTime, Time.fromString(extract.TIME(line))))
            server.server.advancements[advancement] = timeString
            # LOG
            server.write(
                f'Advancement [{advancement}] achieved at {timeString}.')


def juggle(state, inactiveServers, activeServers):
    '''
    Launch servers in even intervals.
    Close servers when they turn empty.
    Change into priority mode when needed.
    '''

    def processBuffer(A, buffer, B):
        for i in buffer[::-1]:
            B.append(A.pop(i))

    def killAllButOne(activeServers, inactiveServers, prioritized):
        toInactiveBuffer = []
        for i, server in enumerate(activeServers):
            if server.folder != prioritized.folder:
                server.kill()
                toInactiveBuffer.append(i)
                # LOG
                server.write('Priority mode enabled. Killing server.')
                updates.append([server.folder, "S"])
        processBuffer(activeServers, toInactiveBuffer, inactiveServers)

    def attemptStart(inactiveServers, activeServers, lastLaunch):
        '''
        Launch a new server if cooldown is over.
        '''
        if inactiveServers:
            server = inactiveServers[0]
            currentTime = monotonic()
            if currentTime - lastLaunch > server.settings['interval']:
                server.reset()
                server.start()
                activeServers.append(inactiveServers.pop(0))
                return currentTime
        return lastLaunch

    def listen(activeServers, inactiveServers, state):
        '''
        Listen to player joins, player leaves and server status updates.
        '''
        toInactiveBuffer = []
        for i, server in enumerate(activeServers):
            for line in server.read():
                if serverListeners[5](line):
                    event_serverStop(server)
                    toInactiveBuffer.append(i)
                    break
                if serverListeners[server.state](line):
                    event_serverProgress(server)
                    if server.state > 3:
                        state[0] = 1
                        return server
                elif playerListeners.JOINED(line):
                    event_playerJoined(server, line)
                elif playerListeners.LEFT(line):
                    if event_playerLeft(server):
                        toInactiveBuffer.append(i)
                        break
        processBuffer(activeServers, toInactiveBuffer, inactiveServers)

    lastLaunch = 0
    prioritized = None
    while state[0] == 0:
        sleep(1)
        lastLaunch = attemptStart(inactiveServers, activeServers, lastLaunch)
        prioritized = listen(activeServers, inactiveServers, state)
    if state[0] == 1:
        killAllButOne(activeServers, inactiveServers, prioritized)


def prioritize(state, inactiveServers, activeServers):
    def listen(activeServers, inactiveServers, state):
        '''
        Listen to player joins, player leaves and server status updates.
        '''
        server = activeServers[0]
        for line in server.read():
            if serverListeners[5](line):
                event_serverStop(server)
                inactiveServers.append(activeServers.pop(0))
                state[0] = 0
                break
            if serverListeners[server.state](line):
                event_serverProgress(server)
                if server.state == 5:
                    state[0] = 2
                    server.server.startTime = Time.fromString(
                        extract.TIME(line))
            elif playerListeners.JOINED(line):
                event_playerJoined(server, line)
            elif playerListeners.LEFT(line):
                if event_playerLeft(server):
                    inactiveServers.append(activeServers.pop(0))
                    state[0] = 0
                    break

    while state[0] == 1:
        listen(activeServers, inactiveServers, state)
        sleep(1)


def speedrun(state, inactiveServers, activeServers):
    def listen(activeServers, inactiveServers, state):
        '''
        Listen to player joins, player leaves and server status updates.
        '''
        server = activeServers[0]
        for line in server.read():
            if serverListeners[5](line):
                event_serverStop(server)
                inactiveServers.append(activeServers.pop(0))
                state[0] = 0
                break
            if playerListeners.ADVANCEMENT(line):
                event_serverAdvancement(server, line)
            elif playerListeners.JOINED(line):
                event_playerJoined(server, line)
            elif playerListeners.LEFT(line):
                if event_playerLeft(server):
                    inactiveServers.append(activeServers.pop(0))
                    state[0] = 0
                    break

    while state[0] == 2:
        listen(activeServers, inactiveServers, state)
        sleep(1)


states = [juggle,
          prioritize,
          speedrun]

cr = '''Minecraft Server Juggler  Copyright (C) 2020  MiniaczQ
This program comes with ABSOLUTELY NO WARRANTY.
This is free software, and you are welcome to redistribute it
under certain conditions.

'''


def mainLoopStuff():
    while True:
        states[state[0]](state, inactiveServers, activeServers)


# Application loop
if __name__ == '__main__':

    def redirectingStuff():
        pass

    if not createFolders():
        stdout.write(cr)
        stdout.flush()

        settings = loadSettings()
        logs = loadLogs()

        activeServers = []
        inactiveServers = []

        def onTerminate(signum, frame):
            '''
            Kill all servers and close log file.
            '''
            for _, server in activeServers:
                server.kill()
            logs[0].close()
            logs[1].close()
        signal(SIGTERM, onTerminate)

        def onInterrupt(signum, frame):
            '''
            Kill all servers, close log file and raise an exception.
            '''
            onTerminate(signum, frame)
            raise KeyboardInterrupt
        signal(SIGINT, onInterrupt)

        initiateServers(settings, logs, inactiveServers)

        state = [0]

        mls = Thread(target=mainLoopStuff)
        mls.start()

        discordbot_start(settings['servers'])
