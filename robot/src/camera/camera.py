from picamera2 import Picamera2 
import time
import simplejpeg

# fixed working distance of the rope in front of the lens
FOCUS_DISTANCE_M = 0.05
AF_MODE_MANUAL = 0

def encode(frame, quality=95):
    return simplejpeg.encode_jpeg(frame, quality=quality, colorspace="BGR")

# lens position is given in dioptres (1 / distance in metres)
def lens_position(distance_m):
    return 1.0 / distance_m

class CameraPair: 
    # The image sizes are fixed here for the run, everything else is a sensor control the
    # operator may change later, see configure()
    def __init__(self, main_size=(640, 640), lores_size=(640, 480), fps=15, exposure_us=20000,
                 gain=2.0, focus_distance_m=FOCUS_DISTANCE_M):
        self.lores_size = lores_size
        self.focus_distance_m = focus_distance_m
        self._cams: list[Picamera2] = []

        for i in range(2):
            cam = Picamera2(camera_num=i)

            cam_controls = {
                "FrameRate": fps,
                "AeEnable": False,
                "ExposureTime": exposure_us,
                "AnalogueGain": gain,
                "AwbEnable": False,
                "ColourGains": (1.8, 2.2), 
                "NoiseReductionMode": 1,  
            }
            cam_controls.update(self._focus_controls(cam))

            cam.configure(cam.create_video_configuration(
                main={"size": main_size, "format": "RGB888"},
                lores={"size": lores_size, "format": "RGB888"},
                buffer_count=4,
                controls=cam_controls
            ))

            self._cams.append(cam)

    # lock autofocus to the configured distance, skipped on fixed focus lenses
    def _focus_controls(self, cam):
        if "LensPosition" not in cam.camera_controls:
            return {}

        lo, hi, _ = cam.camera_controls["LensPosition"]
        position = min(max(lens_position(self.focus_distance_m), lo), hi)

        return {
            "AfMode": AF_MODE_MANUAL,
            "LensPosition": position,
        }

    # Exposure, gain, focus and rate on both running cameras. The sensor takes these live,
    # so nothing has to be torn down and the video stream does not break
    def configure(self, fps, exposure_us, gain, focus_distance_m):
        self.focus_distance_m = focus_distance_m
        for cam in self._cams:
            controls = {"FrameRate": fps, "ExposureTime": exposure_us, "AnalogueGain": gain}
            controls.update(self._focus_controls(cam))
            cam.set_controls(controls)

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
        return [(i, cam.capture_array("lores", wait=1.0)[:h, :w]) for i, cam in enumerate(self._cams)]
    
    # close both cameras
    def close(self): 
        for cam in self._cams: 
            cam.stop()
            cam.close()

    def __enter__(self): 
        return self.start()

    def __exit__(self, *exc): 
        self.close()