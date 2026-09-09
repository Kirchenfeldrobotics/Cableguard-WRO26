from picamera2 import Picamera2 
import time

class CameraPair: 
    def __init__(self, size=(640, 640), fps=15): 
        self._cams: list[Picamera2] = []
        for i in range(2): 
            cam = Picamera2(camera_num=i)

            # configure camera for video
            cam.configure(cam.create_video_configuration(
                main={"size": size, "format": "RGB888"}, 
                buffer_count=4, 
                controls={"FrameRate": fps}
            ))

            self._cams.append(cam)

    # start the cameras
    def start(self): 
        for cam in self._cams: 
            cam.start()
        time.sleep(1.0)
        return self

    # capture a frame from each camera 
    def capture(self): 
        return [(i, cam.capture_array("main")) for i, cam in enumerate(self._cams)]

    # close both cameras
    def close(self): 
        for cam in self._cams: 
            cam.stop()
            cam.close()

    def __enter__(self): 
        return self.start()

    def __exit__(self, *exc): 
        self.close()