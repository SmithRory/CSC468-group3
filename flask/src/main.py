import asyncio
from flask import Flask

loop = asyncio.get_event_loop()
app = Flask(__name__)

async def test():
    await asyncio.sleep(1)

@app.route("/")
def home():
    loop.run_until_complete(test())
    return "Asyncio test"

# if __name__ == "__main__":
#     app.run()