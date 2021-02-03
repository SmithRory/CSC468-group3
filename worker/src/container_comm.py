import asyncio
import asyncio
import os
import sys

#messing around with async, nothing is final
class Comm:
    def __init__(self):
        self.reader = None
        self.writer = None
        
    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(
            "127.0.0.1",
            os.environ["BACKEND_PORT"]
        )

    async def send(self, data):
        self.writer.write(data.encode())
        await self.writer.drain()
