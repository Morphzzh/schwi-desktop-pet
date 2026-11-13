"""Small, deterministic parts of the pet's behavior, independent of Qt."""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

DEFAULTS = {
    'scale': 1.25, 'topmost': True, 'random_idle': True,
    'follow_mouse': False, 'roam': False, 'paused': False,
    'x': None, 'y': None,
}
REACTIONS = ('shy', 'happy', 'surprised', 'waving', 'jumping', 'waiting')


class ReactionBag:
    """Shuffle without immediate repeats; every reaction appears in each bag."""
    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.bag = []
        self.last = None

    def next(self):
        if not self.bag:
            self.bag = list(REACTIONS)
            self.rng.shuffle(self.bag)
            if self.bag[-1] == self.last:
                self.bag[0], self.bag[-1] = self.bag[-1], self.bag[0]
        self.last = self.bag.pop()
        return self.last


def direction_index(dx: float, dy: float) -> int:
    """Screen coordinates; zero is up, indices advance clockwise."""
    return int(math.floor((math.degrees(math.atan2(dx, -dy)) % 360 + 11.25) / 22.5)) % 16


def clamp_position(x, y, width, height, bounds):
    left, top, screen_width, screen_height = bounds
    return (
        max(left, min(int(x), left + max(0, screen_width - width))),
        max(top, min(int(y), top + max(0, screen_height - height))),
    )


def load_settings(path: Path) -> dict:
    settings = dict(DEFAULTS)
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return settings
    if not isinstance(data, dict):
        return settings
    for key in ('topmost', 'random_idle', 'follow_mouse', 'roam', 'paused'):
        if isinstance(data.get(key), bool):
            settings[key] = data[key]
    value = data.get('scale')
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        settings['scale'] = max(.75, min(2.0, float(value)))
    for key in ('x', 'y'):
        value = data.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and abs(value) < 100000:
            settings[key] = value
    return settings


def save_settings(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)
