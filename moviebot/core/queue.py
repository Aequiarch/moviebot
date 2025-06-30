import os
import json
import uuid
import time
from typing import List, Optional, Dict, Any
from pathlib import Path

from core.utils.logger import get_logger
from core.utils.filelock import read_locked_json, write_locked_json

log = get_logger("📂 queue")

PLAYLIST_PATH = Path("playlist.json")
NOW_PLAYING_PATH = Path("now_playing.txt")


def _generate_entry(title: str, filepath: str, duration: int, source: str, added_by: str) -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "title": title,
        "filepath": filepath,
        "duration": duration,
        "type": source,
        "added_by": added_by,
        "timestamp": int(time.time())
    }


def load_playlist() -> List[Dict[str, Any]]:
    if not PLAYLIST_PATH.exists():
        return []
    try:
        return read_locked_json(PLAYLIST_PATH)
    except Exception as e:
        log.error(f"📛 Failed to load playlist: {e}")
        return []


def save_playlist(data: List[Dict[str, Any]]) -> None:
    try:
        write_locked_json(PLAYLIST_PATH, data)
        log.debug("💾 Playlist saved successfully.")
    except Exception as e:
        log.error(f"📛 Failed to save playlist: {e}")


def add_to_queue(title: str, filepath: str, duration: int, source: str, added_by: str) -> Dict[str, Any]:
    queue = load_playlist()
    new_entry = _generate_entry(title, filepath, duration, source, added_by)
    queue.append(new_entry)
    save_playlist(queue)
    log.info(f"➕ Added to queue: {title} by {added_by}")
    return new_entry


def get_queue() -> List[Dict[str, Any]]:
    return load_playlist()


def pin_next(entry_id: str) -> bool:
    queue = load_playlist()
    for i, entry in enumerate(queue):
        if entry["id"] == entry_id:
            pinned = queue.pop(i)
            queue.insert(0, pinned)
            save_playlist(queue)
            log.info(f"📌 Pinned next: {pinned['title']}")
            return True
    log.warning(f"❌ Failed to pin, ID not found: {entry_id}")
    return False


def remove_by_id(entry_id: str) -> bool:
    queue = load_playlist()
    new_queue = [q for q in queue if q["id"] != entry_id]
    if len(new_queue) < len(queue):
        save_playlist(new_queue)
        log.info(f"🗑️ Removed entry by ID: {entry_id}")
        return True
    log.warning(f"⚠️ Entry ID not found for removal: {entry_id}")
    return False


def clear_queue() -> None:
    save_playlist([])
    log.warning("⚠️ Playlist cleared manually by user.")


def get_next_item() -> Optional[Dict[str, Any]]:
    queue = load_playlist()
    return queue[0] if queue else None


def remove_current() -> Optional[Dict[str, Any]]:
    queue = load_playlist()
    if not queue:
        return None
    removed = queue.pop(0)
    save_playlist(queue)
    log.info(f"🧹 Removed current item: {removed['title']}")
    return removed


def peek_current() -> Optional[Dict[str, Any]]:
    return get_next_item()


def is_empty() -> bool:
    return len(load_playlist()) == 0


def get_total_duration() -> int:
    total = sum(int(entry.get("duration", 0)) for entry in load_playlist())
    log.debug(f"⏱️ Total playlist duration: {total}s")
    return total


def set_now_playing(entry: Dict[str, Any]) -> None:
    try:
        with NOW_PLAYING_PATH.open("w", encoding="utf-8") as f:
            f.write(json.dumps({
                "id": entry.get("id"),
                "filepath": entry.get("filepath"),
                "timestamp": int(time.time())
            }))
        log.debug(f"🎶 Now playing set: {entry['title']}")
    except Exception as e:
        log.error(f"❌ Failed to write now_playing.txt: {e}")


def get_now_playing() -> Optional[Dict[str, Any]]:
    if not NOW_PLAYING_PATH.exists():
        return None
    try:
        with NOW_PLAYING_PATH.open("r", encoding="utf-8") as f:
            now_data = json.load(f)
        queue = load_playlist()
        for entry in queue:
            if entry["filepath"] == now_data.get("filepath"):
                return entry
        return {
            "title": Path(now_data.get("filepath", "")).stem,
            "filepath": now_data.get("filepath"),
            "duration": 0,
            "type": "unknown",
            "added_by": "unknown",
            "timestamp": now_data.get("timestamp", 0)
        }
    except Exception as e:
        log.error(f"❌ Failed to parse now_playing.txt: {e}")
        return None


def get_by_id(entry_id: str) -> Optional[Dict[str, Any]]:
    for entry in load_playlist():
        if entry.get("id") == entry_id:
            log.debug(f"🔍 Found entry by ID: {entry_id}")
            return entry
    log.warning(f"🔎 Entry ID not found: {entry_id}")
    return None


def update_entry(entry_id: str, new_data: Dict[str, Any]) -> bool:
    queue = load_playlist()
    updated = False
    for entry in queue:
        if entry["id"] == entry_id:
            entry.update(new_data)
            updated = True
            break
    if updated:
        save_playlist(queue)
        log.info(f"✏️ Updated entry ID: {entry_id}")
    else:
        log.warning(f"⚠️ Failed to update entry: ID not found {entry_id}")
    return updated
