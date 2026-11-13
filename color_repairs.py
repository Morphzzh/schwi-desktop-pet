"""Local, color-only continuity corrections for the approved sprite geometry."""
from collections import deque
import numpy as np
from PIL import Image, ImageFilter
from calibrate_palette import rgb_to_hsv, hsv_to_rgb


def face_mask(im, running=False):
    a = np.asarray(im)
    hsv = rgb_to_hsv(a[..., :3].astype(np.float32) / 255)
    h, s, v = np.moveaxis(hsv, -1, 0)
    foreground = (a[..., 3] > 220) & ~((h > .18) & (h < .55) & (s > .5))
    yy, xx = np.where(foreground)
    height = yy.max() - yy.min()
    y, x = np.indices(h.shape)
    xn = (x - xx.min()) / max(1, xx.max() - xx.min())
    yn = (y - yy.min()) / max(1, height)
    roi = (yn > .20) & (yn < .50) & (xn > .18) & (xn < .82)
    if running:
        roi = (yn > .14) & (yn < .44) & (xn > .68)
    # Pale pink skin was missed by the earlier narrow hue range.
    candidate = roi & foreground & ((h < .07) | (h > .90)) & (s < .39) & (v > .60)
    candidate &= (a[..., 0].astype(int) - a[..., 2].astype(int)) > 4
    iris = (h > .075) & (h < .19) & (s > .35) & (v > .50)
    protected_eyes = np.asarray(Image.fromarray((iris*255).astype('uint8')).filter(ImageFilter.MaxFilter(9))) > 0
    candidate &= ~protected_eyes
    seen = np.zeros(candidate.shape, dtype=bool)
    components = []
    for py, px in zip(*np.where(candidate)):
        if seen[py, px]:
            continue
        seen[py, px] = True
        queue = deque([(py, px)]); group = []
        while queue:
            cy, cx = queue.popleft(); group.append((cy, cx))
            for ny, nx in ((cy-1,cx),(cy+1,cx),(cy,cx-1),(cy,cx+1)):
                if 0 <= ny < im.height and 0 <= nx < im.width and candidate[ny,nx] and not seen[ny,nx]:
                    seen[ny,nx] = True; queue.append((ny,nx))
        components.append(group)
    result = np.zeros(candidate.shape, dtype=bool)
    if not components:
        return result
    # Eye whites and small isolated reflections are not face fill.
    cutoff = max(25, max(map(len, components)) * .07)
    for group in components:
        if len(group) >= cutoff:
            rows, cols = zip(*group); result[rows, cols] = True
    return result


def stabilize_face(im, reference_rgb, running=False):
    a = np.asarray(im).copy(); mask = face_mask(im, running)
    if mask.sum() < 50:
        return im, {'pixels': 0}
    before = np.median(a[..., :3][mask], axis=0)
    delta = np.asarray(reference_rgb) - before
    if abs(delta).max() <= 3:
        return im, {'pixels': 0, 'median_before': before.tolist(), 'median_after': before.tolist()}
    weight = np.asarray(Image.fromarray((mask*255).astype('uint8')).filter(ImageFilter.GaussianBlur(.55)), np.float32)/255
    # Only feather inward: no color changes to eyes, outlines or adjacent hair.
    weight *= mask
    a[..., :3] = np.rint(np.clip(a[..., :3].astype(float) + weight[..., None]*delta, 0, 255)).astype('uint8')
    return Image.fromarray(a), {'pixels': int(mask.sum()), 'median_before': before.tolist(),
        'median_after': np.median(a[..., :3][mask], axis=0).tolist()}


def repair_pale_shoes(im, shoe_palette):
    a = np.asarray(im).copy(); hsv = rgb_to_hsv(a[..., :3].astype(np.float32)/255)
    h,s,v = np.moveaxis(hsv,-1,0); ys = np.where(a[...,3]>220)[0]
    y,x = np.indices(v.shape)
    region = (y > ys.max()-.10*(ys.max()-ys.min())) & (abs(x-im.width/2)<70)
    mask = region & ((h<.30)|(h>.965)|(s<.60)) & (v>.35) & (a[...,3]>0)
    hsv[...,0][mask] = shoe_palette[1,0] % 1
    hsv[...,1][mask] = shoe_palette[1,1]
    hsv[...,2][mask] = shoe_palette[1,2]+(.25+.75*v[mask])*(shoe_palette[2,2]-shoe_palette[1,2])
    a[...,:3][mask] = np.rint(np.clip(hsv_to_rgb(hsv),0,1)*255).astype('uint8')[mask]
    return Image.fromarray(a), int(mask.sum())


SHOE_QUANTILES = np.array([0,.025,.05,.10,.25,.50,.75,.90,.95,.975,1])


def shoe_region(im):
    a=np.asarray(im);hsv=rgb_to_hsv(a[...,:3].astype(np.float32)/255)
    h,s,v=np.moveaxis(hsv,-1,0)
    fg=(a[...,3]>220)&~((h>.18)&(h<.55)&(s>.5))
    yy,xx=np.where(fg);y,x=np.indices(h.shape)
    region=(y>yy.max()-.07*(yy.max()-yy.min()))&(abs(x-(xx.min()+xx.max())/2)<.18*(xx.max()-xx.min()))
    mask=region&(h>.80)&(s>.10)&(a[...,3]>0)
    return hsv,mask


def shoe_tone_profile(im):
    hsv,mask=shoe_region(im);mask &= np.asarray(im)[...,3]>220
    return np.quantile(hsv[...,2][mask],SHOE_QUANTILES)


def normalize_shoe_shadows(im, reference_profile):
    a=np.asarray(im).copy();hsv,mask=shoe_region(im)
    source=shoe_tone_profile(im)
    if abs(source-reference_profile).max()<.018:
        return im,{'changed':False,'profile':source.tolist()}
    values,indices=np.unique(source,return_index=True)
    hsv[...,2][mask]=np.interp(hsv[...,2][mask],values,reference_profile[indices])
    rgb=np.rint(np.clip(hsv_to_rgb(hsv),0,1)*255).astype('uint8')
    a[...,:3][mask]=rgb[mask]
    return Image.fromarray(a),{'changed':True,'before':source.tolist(),'after':shoe_tone_profile(Image.fromarray(a)).tolist()}
