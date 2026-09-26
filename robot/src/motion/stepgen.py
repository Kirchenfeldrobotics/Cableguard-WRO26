import ctypes
import os

# The step pulses come from PIO state machines on the RP1 (stepgen.c), not from Linux, which
# cannot time them evenly. Build the library on the Pi before the first run
_lib = ctypes.CDLL(os.path.join(os.path.dirname(os.path.abspath(__file__)), "libstepgen.so"))
_lib.stepgen_open.argtypes  = [ctypes.c_uint]
_lib.stepgen_put.argtypes   = [ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
_lib.stepgen_done.argtypes  = [ctypes.c_int]
_lib.stepgen_close.argtypes = [ctypes.c_int]
_lib.stepgen_close.restype  = None

# Blocks a channel may have outstanding, counted from the last one the PIO reported played.
# The RP1's FIFOs hold eight words each way (piolib declares fifo_depth 8 for this chip),
# and an outstanding block sits in exactly one of them: waiting in the TX FIFO, on the state
# machine, or played and waiting to be read from the RX FIFO. Eight therefore fills neither.
# A ninth would either end the process on a full TX FIFO or drop a played report, and a
# dropped report is a step count that never arrives
FIFO_DEPTH = 8


# takes the pin over and returns the channel to address it by
def open_channel(pin: int) -> int:
    channel = _lib.stepgen_open(pin)
    if channel < 0:
        raise OSError(-channel, f"cannot drive GPIO{pin} from /dev/pio0: {os.strerror(-channel)}")
    return channel


# queues one block of `steps` pulses, period_us apart
def put(channel: int, period_us: int, steps: int) -> bool:
    return _lib.stepgen_put(channel, period_us, steps) == 0


# blocks the channel has played since the last call
def done(channel: int) -> int:
    return _lib.stepgen_done(channel)


def close(channel: int):
    _lib.stepgen_close(channel)
