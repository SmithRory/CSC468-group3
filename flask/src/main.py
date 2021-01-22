import asyncio
from flask import Flask
import motor.motor_asyncio
import time

loop = asyncio.get_event_loop()
flask_app = Flask(__name__)
db_client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://mongo:27017")

async def async_sleep_1_sec():
    await asyncio.sleep(1)

@flask_app.route("/")
def home():
    start = time.time()
    tasks = asyncio.gather(
        async_sleep_1_sec(),
        async_sleep_1_sec(),
        async_sleep_1_sec(),
        async_sleep_1_sec(),
        async_sleep_1_sec()
    )

    loop.run_until_complete(tasks)

    

    return f"Time taken: {time.time() - start}"