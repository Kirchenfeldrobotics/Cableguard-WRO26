import asyncio, json, os, sys, websockets

TARGET = sys.argv[1] if len(sys.argv) > 1 else "local"

URL = {
    "local": "ws://localhost:8021/api/ws/robot",
    "remote": "wss://cableguard-interface.kirchenfeldrobotics.ch/api/ws/robot",
}[TARGET]

TOKEN = os.environ["CABLEGUARD_ROBOT_TOKEN"]

async def robot_ws_test():
    print(f"connecting to {URL}")
    async with websockets.connect(URL, additional_headers={"Authorization": f"Bearer {TOKEN}"}) as s:
        print("connected")
        print(await s.recv())


asyncio.run(robot_ws_test())