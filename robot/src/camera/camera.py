from picamera2 import Picamera2 
import time
import simplejpeg

# encode frame as JPEG
def encode(frame, quality=60): 
    h = frame.shape[0] * 2 // 3
    w = frame.shape[1]
    y = frame[:h]
    u = frame[h:h + h // 4].reshape(h // 2, w // 2)
    v = frame[h + h // 4:].reshape(h // 2, w // 2)
    return simplejpeg.encode_jpeg_yuv_planes(y, u, v, quality=quality)

class CameraPair: 
    def __init__(self, main_size=(640, 640), lores_size=(480, 480), fps=15): 
        self._cams: list[Picamera2] = []
        for i in range(2): 
            cam = Picamera2(camera_num=i)

            # configure camera for video
            cam.configure(cam.create_video_configuration(
                main={"size": main_size, "format": "RGB888"}, 
                lores={"size": lores_size, "format": "YUV420"}, 
                buffer_count=4, 
                controls={
                    "FrameRate": fps,
                    "AeEnable": False,
                    "ExposureTime": 8000,
                    "AnalogueGain": 2.0,
                    "AwbEnable": False,
                    "ColourGains": (1.5, 1.5)
                }
            ))

            self._cams.append(cam)

    # start the cameras
    def start(self): 
        for cam in self._cams: 
            cam.start()
        time.sleep(1.0)
        return self

    # capture a frame from each camera (main stream)
    def capture(self): 
        return [(i, cam.capture_array("main")) for i, cam in enumerate(self._cams)]

    # capture a frame from each camera (lores stream)
    def capture_lores(self):
        return [(i, cam.capture_array("lores", wait=1.0)) for i, cam in enumerate(self._cams)]
    
    # close both cameras
    def close(self): 
        for cam in self._cams: 
            cam.stop()
            cam.close()

    def __enter__(self): 
        return self.start()

    def __exit__(self, *exc): 
        self.close()