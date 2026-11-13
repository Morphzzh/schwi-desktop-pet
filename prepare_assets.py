"""Register generated six-pose strips using the bundled connected-pose extractor."""
import argparse
import importlib.util
import json
from pathlib import Path
from PIL import Image, ImageDraw

p = argparse.ArgumentParser()
p.add_argument('--extractor', type=Path, required=True)
a = p.parse_args()
spec = importlib.util.spec_from_file_location('pose_extractor', a.extractor)
extractor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extractor)
root = Path(__file__).resolve().parent
records = {}
sheet = Image.new('RGB', (192 * 6, 232 * 3), '#eef2f1')
for row, name in enumerate(('shy', 'happy', 'surprised')):
    source = Image.open(root / 'artwork' / (name + '.png')).convert('RGBA')
    frames = extractor.extract_component_frames(source, 6)
    if frames is None:
        raise RuntimeError(f'{name}: six complete pose groups not found')
    target = Image.new('RGBA', (1152, 208))
    previews = []
    for i, im in enumerate(frames):
        # One uniform row transform. Same 170px body height / 202px baseline as original atlas.
        canvas = Image.new('RGBA', (192, 208))
        canvas.alpha_composite(im.resize((165, 179), Image.Resampling.LANCZOS), (14, 28))
        canvas.putdata([(r,g,b,alpha) if alpha else (0,0,0,0) for r,g,b,alpha in canvas.getdata()])
        target.alpha_composite(canvas, (192 * i, 0))
        bg = Image.new('RGB', (192, 208), '#eef2f1')
        bg.paste(canvas, (0,0), canvas)
        previews.append(bg)
        sheet.paste(bg, (192*i, row*232+24))
    target.save(root / 'assets' / (name + '.png'))
    durations = {'shy':[180,300,650,950,450,500], 'happy':[200,300,700,500,300,350], 'surprised':[180,260,500,650,300,350]}[name]
    previews[0].save(root/'artwork'/(name+'-preview.gif'),save_all=True,append_images=previews[1:],duration=durations,loop=0)
    ImageDraw.Draw(sheet).text((8,row*232+5),name,fill='#48243f')
    records[name] = {'frames':6,'source_size':list(source.size),'output_size':list(target.size),'source_alpha_preserved':True}
sheet.save(root/'artwork/new-reactions.png')
(root/'artwork/extraction.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
atlas=Image.open(root/'assets/schwi.png').convert('RGBA')
icon=atlas.crop((0,0,192,208))
square=Image.new('RGBA',(208,208));square.alpha_composite(icon,(8,0))
square.save(root/'assets/schwi.ico',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
print(json.dumps(records))
