import sys
sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image, ImageDraw
import json, os

OUT = "C:/Users/Administrator/Documents/sakura_mod_work"
with open(os.path.join(OUT, "sakura_mesh_data.json")) as f:
    data = json.load(f)

uv_polys = data['uv_polygons']

# Find full UV range
all_us = [u for poly in uv_polys for u, v in poly]
all_vs = [v for poly in uv_polys for u, v in poly]
u_min, u_max = min(all_us), max(all_us)
v_min, v_max = min(all_vs), max(all_vs)
print(f"UV range: U={u_min:.3f}~{u_max:.3f}, V={v_min:.3f}~{v_max:.3f}")

# Draw full UV layout scaled to fit
SIZE = 1024
u_range = u_max - u_min
v_range = v_max - v_min

def to_px(u, v):
    px = int((u - u_min) / u_range * (SIZE - 20) + 10)
    py = int((1 - (v - v_min) / v_range) * (SIZE - 20) + 10)
    return px, py

img = Image.new('RGBA', (SIZE, SIZE), (15, 15, 25, 255))
draw = ImageDraw.Draw(img)

# Grid
for i in range(9):
    x = int(10 + i * (SIZE - 20) / 8)
    y = int(10 + i * (SIZE - 20) / 8)
    draw.line([(x, 10), (x, SIZE-10)], fill=(40, 40, 60))
    draw.line([(10, y), (SIZE-10, y)], fill=(40, 40, 60))

for poly in uv_polys:
    pts = [to_px(u, v) for u, v in poly]
    for i in range(len(pts)):
        draw.line([pts[i], pts[(i+1) % len(pts)]], fill=(80, 200, 100, 150), width=1)

img.save(os.path.join(OUT, "sakura_uv_full.png"))
print("Full UV saved: sakura_uv_full.png")

# ── Find face region by material index ──────────────────────────────────────
# Reload with material per polygon info
print(f"\nMaterials: {data['materials']}")
# We need poly material info - let's get it from Blender
