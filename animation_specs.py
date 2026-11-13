"""Animation frame durations shared by rendering and schedule defaults."""
STATES = {
    'idle': (0, [650, 160, 180, 120, 180, 750]),
    'running-right': (1, [95] * 8),
    'running-left': (2, [95] * 8),
    'waving': (3, [250, 120, 240, 320, 140, 320]),
    'jumping': (4, [160, 140, 100, 230, 140, 120, 250]),
    'failed': (5, [180, 220, 280, 330, 600, 280, 220, 220]),
    'waiting': (6, [220, 260, 140, 450, 650, 140, 280, 220]),
    'running': (7, [220, 350, 500, 400, 400, 300]),
    'review': (8, [250, 300, 300, 400, 500, 300]),
}
EXTRAS = {
    'shy': [180, 300, 140, 650, 950, 450, 140, 500],
    'happy': [200, 140, 300, 700, 500, 140, 300, 350],
    'surprised': [180, 260, 140, 500, 650, 140, 300, 350],
    'excited': [220, 120, 160, 190, 160, 240, 140, 350],
    'sleepy': [400, 500, 650, 180, 850, 450, 180, 350],
}

# Positions refer to original source poses; two newly drawn in-betweens follow.
TRANSITION_AFTER = {
    'shy': (1,4), 'happy': (0,3), 'surprised': (1,3),
    'excited': (0,4), 'sleepy': (2,4), 'waving': (0,2),
    'jumping': (1,3), 'waiting': (1,3),
}
