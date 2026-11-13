"""Record the exact release image bytes for source and packaged smoke checks."""
import hashlib
import json
from pathlib import Path
from PIL import Image
from platform_support import APP_VERSION

root=Path(__file__).resolve().parent
names=['schwi.png','shy.png','happy.png','surprised.png','excited.png','sleepy.png','schwi-portrait.png','schwi.ico']
files={}
for name in names:
    path=root/'assets'/name
    with Image.open(path) as im:
        files[name]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'size':list(im.size)}
manifest={'version':APP_VERSION,'cell_size':[192,208],'frames':103,'files':files,
          'running_left':'horizontal reflection of right cycle; same phase',
          'left_upper_gaze':'right gaze indices 4,3,2,1 reflected per frame'}
(root/'assets/manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'version':APP_VERSION,'images':len(files),'frames':103}))
