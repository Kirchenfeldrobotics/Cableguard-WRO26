import json
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

# Messages handed over in one go. The journal is picked up where the last batch ended, so
# this bounds how much is in flight, not how far behind the link may be
MAX_BATCH = 200

# A frame with a defect in it travels as a JPEG of about 100 KB. Reading and parsing a whole
# backlog of those at once would hold the event loop, and with it the stop command, so a
# batch also ends once it passes this many bytes
MAX_BATCH_BYTES = 2_000_000

# Once everything has been delivered the journal has done its job. Past this it is emptied
# rather than kept growing for the rest of the run
ROTATE_BYTES = 1_048_576


class Outbox:
    """Append-only journal for messages that have to survive a link outage.

    The detector writes a message per frame per camera, so the journal grows all run long.
    What has already gone out is remembered as a byte offset in a file next to it: reading
    costs the new bytes rather than the whole journal, and a restart picks up where the
    last one stopped instead of replaying everything.
    """

    def __init__(self, path="outbox.jsonl"):
        self._path  = Path(path)
        self._mark  = Path(f"{path}.sent")
        self._sizes = []                 # bytes each message of the last batch occupies
        self._offset = self._load_mark()

    # a journal that was truncated or replaced must not be read from a stale offset
    def _load_mark(self):
        try:
            offset = int(self._mark.read_text())
        except (OSError, ValueError):
            return 0
        size = self._path.stat().st_size if self._path.exists() else 0
        return offset if 0 <= offset <= size else 0

    def _write_mark(self):
        # losing this costs a replay of what it covered, not a lost message, so it is
        # written without an fsync of its own
        try:
            self._mark.write_text(str(self._offset))
        except OSError:
            log.exception("could not record how far the outbox has been sent")

    def add_msg(self, msg: dict):
        with open(self._path, "a") as f:
            f.write(json.dumps(msg) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def pending(self):
        if not self._path.exists():
            return []

        messages, self._sizes = [], []
        carry = 0                        # bytes of lines that carried no message
        taken = 0

        with open(self._path, "rb") as f:
            f.seek(self._offset)
            for raw in f:
                if not raw.endswith(b"\n"):
                    break                # still being written, it is whole next time
                try:
                    messages.append(json.loads(raw))
                except ValueError:
                    # one torn line must not take the link down with it
                    log.warning("skipping an unreadable line in %s", self._path.name)
                    carry += len(raw)
                    continue
                self._sizes.append(carry + len(raw))
                carry = 0
                taken += len(raw)
                if len(messages) >= MAX_BATCH or taken >= MAX_BATCH_BYTES:
                    break

        return messages

    def mark_sent(self, count: int):
        self._offset += sum(self._sizes[:count])
        del self._sizes[:count]
        self._write_mark()
        self._rotate()

    def _rotate(self):
        try:
            if self._offset < ROTATE_BYTES or self._offset != self._path.stat().st_size:
                return
            self._path.write_text("")
            self._offset = 0
            self._write_mark()
        except OSError:
            log.exception("could not rotate the outbox")
