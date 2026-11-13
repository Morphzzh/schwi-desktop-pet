"""Match registered character materials to the actual v1 drawing, without redraws."""
from pathlib import Path
import hashlib
import json
import numpy as np
from PIL import Image, ImageFilter, ImageDraw, ImageOps
from calibrate_palette import rgb_to_hsv, hsv_to_rgb
from animation_specs import STATES, EXTRAS
from color_repairs import face_mask, stabilize_face, repair_pale_shoes, shoe_tone_profile, normalize_shoe_shadows

ROOT = Path(__file__).resolve().parent
ART = ROOT / 'artwork/release-1.0.3'
INPUT = ART / 'calibrated/qa/frames'
OUTPUT = ART / 'v1-palette'
W, H = 576, 624


def materials(im, running=False):
    rgba = np.asarray(im)
    hsv = rgb_to_hsv(rgba[..., :3].astype(np.float32) / 255)
    h, s, v = np.moveaxis(hsv, -1, 0)
    foreground = (rgba[..., 3] > 16) & ~((h > .18) & (h < .55) & (s > .5))
    yy, xx = np.where(foreground)
    y, x = np.indices(h.shape, dtype=np.float32)
    x = (x - xx.min()) / max(1, xx.max() - xx.min())
    y = (y - yy.min()) / max(1, yy.max() - yy.min())
    masks = {}
    purple = (h > .80) & (h < .98) & (s > .32)
    local_high = np.asarray(Image.fromarray(np.rint(v * 255).astype('uint8')).filter(ImageFilter.MaxFilter(5)), np.float32) / 255
    local_alpha = np.asarray(im.getchannel('A').filter(ImageFilter.MinFilter(3)))
    masks['line'] = (v < .26) & ((local_high > v + .06) | (local_alpha.astype(float) < rgba[..., 3].astype(float) - 30)) & foreground
    masks['shoe'] = purple & (y > .935) & (x > .32) & (x < .68)
    masks['sock'] = purple & (y > .80) & (x > .32) & (x < .68) & ~masks['shoe']
    if running:
        masks['shoe'] = purple & (y > .67) & (x > .39)
        masks['sock'] = np.zeros(h.shape, dtype=bool)
    masks['ear'] = purple & (y < .36) & ((x < .27) | (x > .73)) & (s < .82)
    if running:
        masks['ear'] = purple & (y < .27) & (x < .78) & (s < .82)
    masks['hair'] = purple & ~masks['ear'] & ~masks['shoe'] & ~masks['sock']
    masks['skin'] = ((h < .055) | (h > .965)) & (s < .38) & (v > .58)
    masks['cream'] = (h >= .055) & (h < .15) & (s < .32) & (v > .62)
    masks['cloth'] = (h >= .015) & (h < .115) & (s >= .30) & (v > .40) & ~masks['skin'] & ~masks['cream']
    masks['gold'] = (h >= .105) & (h < .19) & (s >= .32) & (v > .50)
    masks['red'] = ((h > .965) | (h < .015)) & (s >= .38) & (v > .40)
    masks['metal'] = (h > .50) & (h < .86) & (s < .32) & (v > .35)
    for name in masks:
        masks[name] &= foreground
        if name != 'line':
            masks[name] &= ~masks['line']
    return hsv, masks


def stats(hsv, mask, alpha):
    pixels = hsv[mask & (alpha > 220)]
    if len(pixels) < 12:
        return None
    # Unwrap red hues around zero before taking robust statistics.
    pixels = pixels.copy()
    pixels[:, 0] = np.where(pixels[:, 0] > .97, pixels[:, 0] - 1, pixels[:, 0])
    return np.quantile(pixels, [.10, .50, .90], axis=0)


def recolor(im, targets, running=False):
    rgba = np.asarray(im).copy()
    hsv, masks = materials(im, running)
    total = np.zeros(hsv.shape, np.float32)
    weights = np.zeros(hsv.shape[:2], np.float32)
    report = {}
    for name, mask in masks.items():
        source = stats(hsv, mask, rgba[..., 3])
        target = targets[name]
        if source is None or target is None:
            continue
        changed = hsv.copy()
        hue_delta = (target[1, 0] - source[1, 0] + .5) % 1 - .5
        changed[..., 0] = (hsv[..., 0] + hue_delta) % 1
        changed[..., 1] = np.clip(hsv[..., 1] + target[1, 1] - source[1, 1], 0, 1)
        # Continuous affine tone curve: retains local shading/highlight ordering.
        gain = np.clip((target[2, 2] - target[0, 2]) / max(.025, source[2, 2] - source[0, 2]), .65, 1.5)
        changed[..., 2] = np.clip(target[1, 2] + (hsv[..., 2] - source[1, 2]) * gain, 0, 1)
        if name == 'line':
            changed[..., 2] = hsv[..., 2]  # Keep the contour's contrast and width.
        # Feather material selections by one source pixel; never touch alpha.
        weight = np.asarray(Image.fromarray((mask * 255).astype('uint8')).filter(ImageFilter.GaussianBlur(.65)), np.float32) / 255
        weight *= rgba[..., 3] > 0
        total += hsv_to_rgb(changed) * weight[..., None]
        weights += weight
        report[name] = {'source': source.tolist(), 'reference': target.tolist()}
    original = rgba[..., :3].astype(np.float32) / 255
    mixed = total / np.maximum(weights[..., None], 1e-8)
    blend = np.clip(weights, 0, 1)[..., None]
    rgba[..., :3] = np.rint(np.clip(original * (1 - blend) + mixed * blend, 0, 1) * 255).astype('uint8')
    assert np.array_equal(rgba[..., 3], np.asarray(im)[..., 3])
    return Image.fromarray(rgba), report



def main():
    OUTPUT.mkdir(exist_ok=True)
    reference = Image.open(ART / 'palette-reference-v1.png').convert('RGBA')
    hsv, masks = materials(reference)
    targets = {name: stats(hsv, mask, np.asarray(reference)[..., 3]) for name, mask in masks.items()}
    assert all(value is not None for value in targets.values()), targets
    reference_face = np.median(np.asarray(reference)[..., :3][face_mask(reference)], axis=0)
    reference_shoes = shoe_tone_profile(reference)
    frames = {}
    records = {}
    counts = {name: len(times) for name, (_, times) in STATES.items()}
    counts.update({name: len(times) for name, times in EXTRAS.items()})
    counts.update({'look-row-9': 8, 'look-row-10-a': 4, 'look-row-10-b': 4})
    for name, count in counts.items():
        if name in ('running-left', 'look-row-10-b'):
            continue
        frames[name] = []
        for index in range(count):
            im = Image.open(INPUT / name / f'{index:02d}.png').convert('RGBA')
            result, report = recolor(im, targets, name == 'running-right')
            if name != 'running-right':
                result, corrected_pixels = repair_pale_shoes(result, targets['shoe'])
                report['shoe_collar_corrected_pixels'] = corrected_pixels
                result, report['shoe_shadows'] = normalize_shoe_shadows(result, reference_shoes)
            result, report['face_continuity'] = stabilize_face(result, reference_face, name == 'running-right')
            frames[name].append(result)
            records[f'{name}/{index:02d}'] = report
        print(name, count, flush=True)
    frames['running-left'] = [ImageOps.mirror(f) for f in frames['running-right']]
    frames['look-row-10-b'] = [ImageOps.mirror(frames['look-row-9'][i]) for i in (4, 3, 2, 1)]
    atlas = Image.new('RGBA', (8 * W, 11 * H))
    contact = Image.new('RGB', (1536, len(counts) * 232), '#eef2f1')
    draw = ImageDraw.Draw(contact)
    for row, (name, count) in enumerate(counts.items()):
        folder = OUTPUT / 'frames' / name
        folder.mkdir(parents=True, exist_ok=True)
        strip = Image.new('RGBA', (count * W, H))
        for i, frame in enumerate(frames[name]):
            frame.save(folder / f'{i:02d}.png')
            strip.alpha_composite(frame, (i * W, 0))
            small = frame.resize((192, 208), Image.Resampling.LANCZOS)
            contact.paste(small, (i * 192, row * 232 + 24), small)
        draw.text((8, row * 232 + 5), name, fill='#48243f')
        if name in STATES:
            atlas.alpha_composite(strip, (0, STATES[name][0] * H))
        elif name in EXTRAS:
            strip.save(ROOT / 'assets' / (name + '.png'))
        else:
            atlas.alpha_composite(strip, (4 * W if name.endswith('-b') else 0, (9 if name == 'look-row-9' else 10) * H))
    atlas.save(ROOT / 'assets/schwi.png')
    contact.save(OUTPUT / 'all-actions.png')
    canonical, _ = recolor(Image.open(ART / 'canonical.png').convert('RGBA'), targets)
    canonical.save(OUTPUT / 'canonical.png')
    summary = {'reference': 'palette-reference-v1.png',
        'reference_sha256': hashlib.sha256((ART / 'palette-reference-v1.png').read_bytes()).hexdigest(),
        'reference_origin': 'work/schwi/decoded/base.png, the actual v1 drawing',
        'frames': sum(counts.values()), 'alpha_unchanged': True,
        'shape_reference': 'canonical.png; approved 1.0.3 geometry retained',
        'target_material_median_hsv': {name: value[1].tolist() for name, value in targets.items()},
        'method': 'Continuous per-material tone matching; no redrawing, resizing or alpha changes'}
    (ART / 'palette-v1-summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    (OUTPUT / 'report.json').write_text(json.dumps({'reference': 'palette-reference-v1.png',
        'reference_sha256': hashlib.sha256((ART / 'palette-reference-v1.png').read_bytes()).hexdigest(),
        'frames': sum(counts.values()), 'alpha_unchanged': True,
        'method': 'Per-material continuous HSV tone matching; original geometry, alpha and contour contrast retained',
        'records': records}, indent=2), encoding='utf-8')


if __name__ == '__main__':
    # Keep the old entry point safe: never reapply the retired hard material masks.
    from rebuild_continuity import main as rebuild
    rebuild()
