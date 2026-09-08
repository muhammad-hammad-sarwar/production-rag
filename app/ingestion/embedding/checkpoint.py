import json
from pathlib import Path

CHECKPOINT_PATH = Path("embedded_ids.json")


def load_checkpoint() -> set[str]:
    if CHECKPOINT_PATH.exists():
        return set(json.loads(CHECKPOINT_PATH.read_text()))
    return set()


def save_checkpoint(embedded_ids: set[str]):
    CHECKPOINT_PATH.write_text(json.dumps(sorted(embedded_ids)))