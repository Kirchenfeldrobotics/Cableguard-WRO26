from picamera2 import Picamera2
import logging
import time
import simplejpeg

log = logging.getLogger(__name__)

# libcamera's autofocus controls, as the numbers its enums stand for
AF_MODE_CONTINUOUS = 2
AF_RANGE_MACRO     = 1      # 4 to 32 dioptres on the Wide lens, about 25 cm down to 3 cm
AF_SPEED_FAST      = 1
AF_STATE_FOCUSED   = 2
AF_STATE_FAILED    = 3

# The shutter waits this long at most for a lens that is still moving. The rope stays at the
# same distance, so normally there is nothing to wait for; any wait comes out of the scan cycle
FOCUS_WAIT_S = 0.5

# the first focus after start may sweep the whole macro range, about 3 s at 15 frames a second
START_FOCUS_S = 5.0

def encode(frame, quality=95):
    return simplejpeg.encode_jpeg(frame, quality=quality, colorspace="BGR")

class CameraPair:
    # The image sizes are fixed here for the run, everything else is a sensor control the
    # operator may change later, see configure()
    def __init__(self, main_size=(640, 640), lores_size=(640, 480), fps=15, exposure_us=20000,
                 gain=2.0):
        self.lores_size = lores_size
        self._cams: list[Picamera2] = []
        self._autofocus: list[bool] = []    # the lens focuses itself
        self._blurred: list[bool]   = []    # the last frame was taken out of focus

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
            focus = self._focus_controls(cam)
            cam_controls.update(focus)

            cam.configure(cam.create_video_configuration(
                main={"size": main_size, "format": "RGB888"},
                lores={"size": lores_size, "format": "RGB888"},
                buffer_count=4,
                controls=cam_controls
            ))

            self._cams.append(cam)
            self._autofocus.append(bool(focus))
            self._blurred.append(False)

    # Every lens finds the rope by itself. One locked position cannot suit both cameras, no two
    # lenses come to the same distance on the same setting. The rope sits closer than the
    # normal range reaches, hence macro. Skipped on fixed focus lenses
    def _focus_controls(self, cam):
        if "AfMode" not in cam.camera_controls:
            return {}

        return {
            "AfMode": AF_MODE_CONTINUOUS,
            "AfRange": AF_RANGE_MACRO,
            "AfSpeed": AF_SPEED_FAST,
        }

    # Exposure, gain and rate on both running cameras. The sensor takes these live,
    # so nothing has to be torn down and the video stream does not break
    def configure(self, fps, exposure_us, gain):
        for cam in self._cams:
            cam.set_controls({"FrameRate": fps, "ExposureTime": exposure_us, "AnalogueGain": gain})

    # start the cameras and let every lens find the rope before the first frame is wanted
    def start(self):
        for cam in self._cams:
            cam.start()
        time.sleep(1.0)

        # where each lens came to rest, which is how far apart the two units are
        for i, cam in enumerate(self._cams):
            if not self._autofocus[i]:
                continue
            _, meta = self._focused(i, cam, START_FOCUS_S)
            dioptres = meta.get("LensPosition")
            if dioptres:
                log.info("cam%d: lens at %.1f dpt, %.0f mm", i, dioptres, 1000.0 / dioptres)
        return self

    # The next frame of a camera and what the camera said about it. A frame taken while the
    # lens moves is blurred, so frames are passed over until the autofocus is through, found
    # or not, or until wait_s is up and the frame is taken as it is
    def _focused(self, i, cam, wait_s):
        deadline = time.monotonic() + wait_s
        (frame,), meta = cam.capture_arrays(["main"])
        while (self._autofocus[i] and time.monotonic() < deadline
               and meta.get("AfState") not in (AF_STATE_FOCUSED, AF_STATE_FAILED)):
            (frame,), meta = cam.capture_arrays(["main"])

        # said once and not every round, a lens that cannot find the rope would fill the log
        blurred = self._autofocus[i] and meta.get("AfState") != AF_STATE_FOCUSED
        if blurred and not self._blurred[i]:
            log.warning("cam%d: frame taken out of focus, the autofocus %s", i,
                        "found nothing" if meta.get("AfState") == AF_STATE_FAILED else "was still moving")
        elif self._blurred[i] and not blurred:
            log.info("cam%d: in focus again", i)
        self._blurred[i] = blurred
        return frame, meta

    # capture a frame from each camera (main stream), each with its lens at rest
    def capture(self):
        return [(i, self._focused(i, cam, FOCUS_WAIT_S)[0]) for i, cam in enumerate(self._cams)]

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
