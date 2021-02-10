import asyncio as aio
import threading
import socket

class Redirector:
    def __init__(self, port_to, ip, port_from = 25565, packet_size = 8192):
        '''
        port_to     -   Port to redirect to (port of the server)\n
        ip          -   Server machine IP (on the network you port forward)\n
        port_from   -   Port to redirect from (port the people use)\n
        packet_size -   Bytes per transfer
        '''
        self.port_to = port_to
        self.port_from = port_from
        self.ip = ip
        self.packet_size = packet_size
        self.event = threading.Event()
        self.server = None

    async def stop(self):
        '''
        Attempts to stop the redirector.
        '''
        if self.server is not None:
            self.server.close()
            await self.server.wait_closed()
            self.event.set()
            self.server = None
        
    async def start(self):
        '''
        Attempts to start the redirector.
        '''
        if self.server is None:
            async def forward(src, dst):
                data = await src.read(self.packet_size)
                while data and not dst.is_closing():
                    dst.write(data)
                    if self.event.is_set():
                        dst.close()
                        break
                    data = await src.read(self.packet_size)
                await dst.wait_closed()

            async def pair_up(c_reader, c_writer):
                s_reader, s_writer = await aio.open_connection(self.ip, self.port_to, family=socket.AF_INET)
                f1 = aio.ensure_future(forward(s_reader, c_writer))
                f2 = aio.ensure_future(forward(c_reader, s_writer))
            
            self.event.clear()
            self.server = await aio.start_server(pair_up, self.ip, self.port_from, family=socket.AF_INET, backlog=5)





#   Testing

if __name__ == '__main__':
    '''
    async def main(r):
        print('start')
        await r.start()
        await aio.sleep(10)
        print('stop')
        await r.stop()
        await aio.sleep(10)
        print('start')
        await r.start()
        await aio.sleep(10)
        await r.stop()
        print('stop')
        await aio.sleep(5)
    '''
    async def main(r, f):
        while True:
            if f[0]:
                await r.start()
                f[0] = False
            await aio.sleep(1000)

    redirector = Redirector(26000, '192.168.1.2', 26003)
    f = [True]
    aio.run(main(redirector, f))