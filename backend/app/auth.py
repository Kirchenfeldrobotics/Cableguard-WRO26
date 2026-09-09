import hmac, os 
from fastapi import status

ROBOT_TOKEN = os.environ("CABLEGUARD_ROBOT_TOKEN")

async def authenticate_robot(sock): 
    header = sock.headers.get("authorization", "")
    token  = header.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(token, ROBOT_TOKEN): 
        await sock.close(code=status.WS_1008_POLICY_VIOLATION)
        return False 
    return True