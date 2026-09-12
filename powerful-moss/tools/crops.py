"""De-obscure each numeral and render a legible crop of the words around it.

Palette facts: 133 = wordlist text seen through a numeral, 83 = numeral fill
over background, 177 = plain text, 117 = background.  Mapping 133->177 and
83->117 removes the numeral and restores the text underneath, so the marked
word can be read by eye instead of inferred from a centroid rule.
A crosshair marks the numeral's bbox centre.
"""
import json, sys
import numpy as np
from PIL import Image

a = np.array(Image.open('ocp/2-mid-prizes/logicbeach-powerful-moss-0-54eth/'
                        'clues/powerfulmoss-poap.png').convert('RGB')).astype(np.int16)
R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]

# text = anything whose max channel is near 177 (plain, under-ray, under-title)
# or near 133 (under a numeral).  Render text black on white.
mx = a.max(axis=2)
text = (np.abs(mx - 177) <= 14) | (np.abs(mx - 133) <= 12)
canvas = np.where(text, 0, 255).astype(np.uint8)

NUM = json.load(open('numerals.json'))
ROWS = json.load(open('rows.json'))
hours = [int(h) for h in sys.argv[1:]] or list(range(1, 13))

for h in hours:
    d = NUM[str(h)]
    cx, cy = (d['x0'] + d['x1']) / 2, (d['y0'] + d['y1']) / 2
    x0, x1 = int(cx - 330), int(cx + 330)
    y0, y1 = int(cy - 110), int(cy + 110)
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(canvas.shape[1], x1), min(canvas.shape[0], y1)
    crop = canvas[y0:y1, x0:x1].copy()
    rgb = np.stack([crop] * 3, axis=2)
    # red crosshair at the numeral bbox centre
    ix, iy = int(cx) - x0, int(cy) - y0
    if 0 <= iy < rgb.shape[0]:
        rgb[iy, :, 0] = 255; rgb[iy, :, 1] = 0; rgb[iy, :, 2] = 0
    if 0 <= ix < rgb.shape[1]:
        rgb[:, ix, 0] = 255; rgb[:, ix, 1] = 0; rgb[:, ix, 2] = 0
    im = Image.fromarray(rgb).resize(((x1 - x0) * 2, (y1 - y0) * 2), Image.LANCZOS)
    im.save(f'crop_h{h:02d}.png')
    print(f'h{h}: crop x[{x0}-{x1}] y[{y0}-{y1}] centre=({cx:.0f},{cy:.0f})')
