"""Record the exact release image bytes for source and packaged smoke checks."""
import hashlib
import json
from pathlib import Path
from PIL import Image
from platform_support import APP_VERSION
from main import CELL_W, CELL_H, SPRITE_W, SPRITE_H
from animation_specs import STATES, EXTRAS

root=Path(__file__).resolve().parent
names=['schwi.png','shy.png','happy.png','surprised.png','excited.png','sleepy.png','schwi-portrait.png','schwi.ico']
files={}
for name in names:
    path=root/'assets'/name
    with Image.open(path) as im:
        files[name]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'size':list(im.size)}
frame_count=sum(len(t) for _,t in STATES.values())+sum(map(len,EXTRAS.values()))+16
manifest={'version':APP_VERSION,'cell_size':[SPRITE_W,SPRITE_H],
          'logical_cell_size':[CELL_W,CELL_H],'frames':frame_count,'files':files,
          'running_left':'horizontal reflection of right cycle; same phase',
          'left_upper_gaze':'right gaze indices 4,3,2,1 reflected per frame',
          'left_lower_gaze':'right gaze indices 7,6,5 reflected per frame',
          'artwork':'complete redraw from a fixed master; whole-frame scaling and reflection only'}
(root/'assets/manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'version':APP_VERSION,'images':len(files),'frames':frame_count}))
