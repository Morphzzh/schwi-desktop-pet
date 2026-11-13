"""Keep one stationary idle body while rendering blink expression layers."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter

# Regions are in the 576x624 runtime canvas, entirely inside the face.
EYE_REGIONS = ((216, 249, 72, 62), (307, 249, 70, 62))

def stabilize_idle(frames):
    base = frames[0]
    mask = QImage(base.size(), QImage.Format.Format_ARGB32_Premultiplied)
    mask.fill(Qt.GlobalColor.transparent)
    for x0, y0, width, height in EYE_REGIONS:
        for y in range(height):
            for x in range(width):
                distance = min(x, y, width - 1 - x, height - 1 - y)
                alpha = round(255 * min(1, distance / 4))
                mask.setPixelColor(x0+x, y0+y, QColor(255, 255, 255, alpha))
    result = []
    for index, source in enumerate(frames):
        output = base.copy()
        if index in (2, 3, 4):
            eyes = source.copy()
            painter = QPainter(eyes)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
            painter.drawImage(0, 0, mask)
            painter.end()
            painter = QPainter(output)
            painter.drawPixmap(0, 0, eyes)
            painter.end()
        result.append(output)
    return result
