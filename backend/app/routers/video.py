import logging 

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.auth import authenticate_robot, authenticate_ui
from app.ws.video_hub import video_hub

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ws/video", tags=["video"])

@router.websocket("/robot")
async def video_in(sock: WebSocket): 
    if not await authenticate_robot(sock): 
        return 

    await sock.accept()
    await video_hub.set_robot(True)
    log.info("video link up")

    try: 
        async for chunk in sock.iter_bytes(): 
            await video_hub.broadcast(chunk)
    except WebSocketDisconnect:
        pass 
    finally: 
        await video_hub.set_robot(False)
        log.info("video link down")

@router.websocket("/ui")
async def video_out(sock: WebSocket): 
    if not await authenticate_ui(sock): 
        return 

    await sock.accept()
    await video_hub.add_viewer(sock)
    log.info("video viewer connected (%d total)", video_hub.viewer_count)

    try: 
        while True: 
            await sock.receive_text()
    except WebSocketDisconnect: 
        pass 
    finally: 
        await video_hub.remove_viewer(sock)