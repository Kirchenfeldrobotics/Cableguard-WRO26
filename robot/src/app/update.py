import asyncio
import getpass
import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

# The repository this program runs from, and the script that updates it: it pulls the latest
# software and restarts the service this program runs as. The script belongs to the
# installation and not to the software it replaces, so it sits beside the repository
REPO   = Path(__file__).resolve().parents[3]
SCRIPT = REPO.parent / "update.sh"

# what the script printed on its last run, which is where a failed update says why
LOG = REPO.parent / "update.log"

# The script restarts this program, and systemd takes down everything a service started
# along with it. Run from here the script would be killed by its own restart, whatever it
# had left to do undone, so it runs as a unit of its own
UNIT = "cableguard-update"

# how often a running script is looked at
POLL_S = 0.5

# the error travels in every telemetry packet, so it is kept to a line
ERROR_CHARS = 200


# The commit this program runs from, as the settings page shows it. Read once at startup: a
# pull changes the checkout, not the program that is already running
def software_version():
    try:
        done = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, timeout=10, check=True)
    except (OSError, subprocess.SubprocessError):
        log.warning("git does not say which commit this is")
        return None
    return done.stdout.strip() or None


# The script as a systemd unit of its own, run as this user from the script's folder, the way
# it is run by hand over ssh. The login shell gives it the PATH an ssh session has
def _command():
    return [
        "sudo", "-n",
        "systemd-run", "--unit", UNIT, "--collect", "--wait", "--quiet",
        "--uid", getpass.getuser(), "--working-directory", str(SCRIPT.parent),
        "/bin/sh", "-c", 'exec /bin/bash -l "$0" >"$1" 2>&1', str(SCRIPT), str(LOG),
    ]


# the last thing that was printed, which is where a script that gave up says what on
def _last_line(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1][:ERROR_CHARS] if lines else None


class Updater:
    def __init__(self, drive):
        self._drive = drive
        self._asked = asyncio.Event()

        # both go out in the motion telemetry, which is all the webapp knows of an update
        self.running = False
        self.error   = None      # why the last update did not go through

    # The operator asked for an update. It restarts this program, and with it goes the
    # position a run is measured from, so a robot that is driving refuses
    def request(self):
        if self.running:
            log.info("update requested while one is running")
            return
        if self._drive.moving:
            log.warning("update refused, the robot is moving")
            self.error = "the robot is moving"
            return
        self.running = True
        self.error   = None
        self._asked.set()

    # run the script every time it is asked for
    async def run(self):
        while True:
            await self._asked.wait()
            self._asked.clear()
            try:
                self.error = await self._update()
            except Exception as exc:
                log.exception("update failed")
                self.error = str(exc)[:ERROR_CHARS]
            self.running = False

    # Run the script and wait for it. Returns why it failed, or None. An update that works
    # does not come back: the script restarts this program before it is through
    async def _update(self):
        if not SCRIPT.is_file():
            return f"no update script at {SCRIPT}"

        log.info("updating, %s runs as %s.service", SCRIPT, UNIT)
        # what is left of the last run must not explain this one
        LOG.unlink(missing_ok=True)
        proc = subprocess.Popen(_command(), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE, text=True)
        # polled rather than waited on in a thread: a thread stuck on the script would hold
        # up the very shutdown the script is waiting for
        while proc.poll() is None:
            await asyncio.sleep(POLL_S)
        complaint = proc.stderr.read()

        if proc.returncode == 0:
            log.info("the update script finished without restarting the robot")
            return None

        try:
            printed = LOG.read_text(errors="replace")
        except OSError:
            printed = ""
        # the script's own last word, or sudo's and systemd's if it never got to run
        reason = _last_line(printed) or _last_line(complaint) or f"exit code {proc.returncode}"
        log.error("update failed: %s", reason)
        return reason
