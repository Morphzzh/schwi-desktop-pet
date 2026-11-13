"""Crop an existing full-body drawing into an upper-body application icon."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('source', type=Path)
parser.add_argument('--box', type=int, nargs=4, required=True)
parser.add_argument('--green-screen', action='store_true')
args = parser.parse_args()
portrait = Image.open(args.source).convert('RGBA').crop(tuple(args.box))
# Match whole-frame assembly's removal of near-invisible background noise.
portrait.putalpha(portrait.getchannel('A').point(lambda a: 0 if a <= 16 else a))
if args.green_screen:
    # Remove only the original green background; retain character RGB values.
    pixels = list(portrait.get_flattened_data())
    portrait.putdata([(0,0,0,0) if g>90 and g>r*1.2 and g>b*1.2 else (r,g,b,a)
                      for r,g,b,a in pixels])
assert portrait.width == portrait.height
portrait.save(root/'assets/schwi-portrait.png')
portrait.save(root/'assets/schwi.ico',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
report = {'source': args.source.name, 'source_sha256': hashlib.sha256(args.source.read_bytes()).hexdigest(),
          'crop_box': args.box, 'method': 'Existing full-body image cropped; no character redraw.',
          'green_background_removed': args.green_screen}
(root/'artwork').mkdir(exist_ok=True)
(root/'artwork/icon-crop.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
