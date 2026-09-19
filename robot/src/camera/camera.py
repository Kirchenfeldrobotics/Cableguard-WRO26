from picamera2 import Picamera2 
import time
import simplejpeg
import numpy as np 

# encode frame as JPEG
def encode(frame, quality=60): 
    h = frame.shape[0] * 2 // 3
    w = frame.shape[1]
    y = frame[:h]
    u = frame[h:h + h // 4].reshape(h // 2, w // 2)
    v = frame[h + h // 4:].reshape(h // 2, w // 2)
    return simplejpeg.encode_jpeg_yuv_planes(y, u, v, quality=quality)

class CameraPair: 
    def __init__(self, main_size=(640, 640), lores_size=(640, 480), fps=15, rotate=-1):
        self.lores_size = lores_size
        self.rotate     = rotate
        self._cams: list[Picamera2] = []

        for i in range(2):
            cam = Picamera2(camera_num=i)

            cam.configure(cam.create_video_configuration(
                main={"size": main_size, "format": "RGB888"},
                lores={"size": lores_size, "format": "RGB888"},
                buffer_count=4,
                controls={
                    "FrameRate": fps,
                    "AeEnable": False,
                    "ExposureTime": 20000,     
                    "AnalogueGain": 2.0,
                    "AwbEnable": False,
                    "ColourGains": (1.8, 2.2), 
                    "NoiseReductionMode": 1,  
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
        w, h = self.lores_size
        return [(i, self._upright(cam.capture_array("lores", wait=1.0)[:h, :w])) for i, cam in enumerate(self._cams)]
    
    # close both cameras
    def close(self): 
        for cam in self._cams: 
            cam.stop()
            cam.close()

     # turn the frame upright, ascontiguousarray because rot90 only returns a view
    def _upright(self, frame):
        if self.rotate == 0:
            return frame
        return np.ascontiguousarray(np.rot90(frame, self.rotate))

    def __enter__(self): 
        return self.start()

    def __exit__(self, *exc): 
        self.close()