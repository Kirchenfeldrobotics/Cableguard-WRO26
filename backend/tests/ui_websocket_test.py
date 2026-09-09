import asyncio, sys, websockets

# either remote or local for server only (d: local)
TARGET = sys.argv[1] if len(sys.argv) > 1 else "local"

URL = {
    "local": "ws://localhost:8021/api/ws/ui",
    "remote": "wss://cableguard-interface.kirchenfeldrobotics.ch/api/ws/ui",
}[TARGET]

# test ui websocket
async def ui_ws_test():
    print(f"connecting to {URL}")
    async with websockets.connect(URL) as s:
        print("connected")
        print(await s.recv())

asyncio.run(ui_ws_test())