import asyncio, websockets

# specify url format (local for server only)
URL = {
    "local": "ws://localhost:8021/api/ws/ui", 
    "remote": "wss://cableguard-interface.kirchenfeldrobotics.ch/api/ws/ui"
}["remote"]

# test socket
async def ui_ws_test():
    async with websockets.connect(URL) as s:
        print("connected")
        print(await s.recv())

asyncio.run(ui_ws_test())