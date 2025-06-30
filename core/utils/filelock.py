# moviebot/core/utils/filelock.py

import os
import time
import fcntl
from pathlib import Path
from contextlib import contextmanager

from core.utils.logger import get_logger

log = get_logger("🔐 filelock")

# ⏲️ Configuration Constants
DEFAULT_TIMEOUT = 10  # Maximum time (in seconds) to wait for lock
DEFAULT_RETRY_DELAY = 0.1  # Delay between retries (in seconds)

# 🧰 Atomic File Locking with Context Manager
@contextmanager
def locked_file(path, mode="r+", timeout=DEFAULT_TIMEOUT, retry_delay=DEFAULT_RETRY_DELAY):
    """
    Secure context manager for atomic file access using POSIX locks (fcntl).

    Args:
        path (str | Path): Path to the file to lock.
        mode (str): File open mode (e.g., 'r+', 'w', etc.).
        timeout (int): How many seconds to wait before giving up on acquiring the lock.
        retry_delay (float): How long to sleep between retries.

    Example:
        with locked_file("data.json", "r") as f:
            data = json.load(f)
    """
    path = Path(path)

    if not path.exists() and ("w" in mode or "a" in mode):
        try:
            path.touch()
            log.debug(f"📁 Created missing file: {path}")
        except Exception as e:
            log.error(f"❌ Failed to create file {path}: {e}")
            raise

    start_time = time.time()

    with open(path, mode) as f:
        while True:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                log.debug(f"🔒 Lock acquired: {path.name}")
                break
            except BlockingIOError:
                if time.time() - start_time > timeout:
                    log.error(f"⏱️ Timeout: Lock on {path.name} not acquired after {timeout}s")
                    raise TimeoutError(f"Could not acquire lock on {path} within {timeout} seconds")
                time.sleep(retry_delay)

        try:
            yield f
        finally:
            try:
                fcntl.flock(f, fcntl.LOCK_UN)
                log.debug(f"🔓 Lock released: {path.name}")
            except Exception as e:
                log.warning(f"⚠️ Could not release lock on {path.name}: {e}")

# ✏️ Safe JSON Write Wrapper

def write_locked_json(filepath: str | Path, data: dict, indent: int = 2):
    """
    Atomically writes JSON to disk using file locking.

    Args:
        filepath (str | Path): Destination path.
        data (dict): JSON-serializable data.
        indent (int): Pretty print indentation level.

    Example:
        write_locked_json("output.json", {"a": 1})
    """
    try:
        with locked_file(filepath, mode="w") as f:
            import json
            json.dump(data, f, indent=indent)
            f.flush()
            os.fsync(f.fileno())
        log.info(f"💾 JSON written safely to {filepath}")
    except Exception as e:
        log.error(f"❌ Failed to write JSON to {filepath}: {e}")
        raise

# 🧪 Debug Mode (manual test)
if __name__ == "__main__":
    import json

    test_path = Path("/tmp/test_filelock.json")
    dummy_data = {"timestamp": time.time(), "message": "Hello from filelock!"}

    log.info("🧪 Testing file lock...")
    write_locked_json(test_path, dummy_data)

    with locked_file(test_path, mode="r") as f:
        content = json.load(f)
        log.info(f"📖 Read back content: {content}")