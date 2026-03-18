"""Draw UV layout and analyze mesh using system Python + PIL"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image, ImageDraw
import json, os

OUT = "C:/Users/Administrator/Documents/sakura_mod_work"

with open(os.path.join(OUT, "sakura_mesh_data.json")) as f:
    data = json.load(f)

print(f"Mesh: {data['mesh_name']}")
print(f"Vertices: {data['vertex_count']}, Polygons: {data['polygon_count']}")
print(f"Materials: {data['materials']}")
print(f"UV layer: {data['uv_layer']}")

# ── Draw UV layout ──────────────────────────────────────────────────────────
SIZE = 1024
uv_img = Image.new('RGBA', (SIZE, SIZE), (15, 15, 25, 255))
draw = ImageDraw.Draw(uv_img)

# Draw UV grid reference
for i in range(0, SIZE, SIZE//8):
    draw.line([(i, 0), (i, SIZE)], fill=(40, 40, 60), width=1)
    draw.line([(0, i), (SIZE, i)], fill=(40, 40, 60), width=1)

for poly in data['uv_polygons']:
    pts = [(int(u * SIZE), int((1 - v) * SIZE)) for u, v in poly]
    for i in range(len(pts)):
        draw.line([pts[i], pts[(i + 1) % len(pts)]], fill=(80, 200, 100, 180), width=1)

uv_path = os.path.join(OUT, "sakura_uv_layout.png")
uv_img.save(uv_path)
print(f"\nUV layout saved: {uv_path}")

# ── Find head region from 3D vertex positions ───────────────────────────────
verts = data['vertices_3d']
zs = [v[2] for v in verts]
z_min, z_max = min(zs), max(zs)
total_height = z_max - z_min
print(f"\nModel height: {total_height:.1f} units")
print(f"Z range: {z_min:.2f} ~ {z_max:.2f}")

# Head is typically top 15% of model
head_z_threshold = z_max - total_height * 0.15
head_vert_indices = {i for i, v in enumerate(verts) if v[2] > head_z_threshold}
print(f"Head vertex count (top 15%): {len(head_vert_indices)}")

# Get UV coordinates of head vertices
polys = data['polygon_indices']
uv_polys = data['uv_polygons']

head_uvs = []
for poly_idx, (poly, uv_poly) in enumerate(zip(polys, uv_polys)):
    if any(vi in head_vert_indices for vi in poly):
        head_uvs.extend(uv_poly)

if head_uvs:
    us = [u for u, v in head_uvs]
    vs = [v for u, v in head_uvs]
    print(f"\nHead UV region:")
    print(f"  U: {min(us):.3f} ~ {max(us):.3f}")
    print(f"  V: {min(vs):.3f} ~ {max(vs):.3f}")

    # Draw head UV region highlighted
    SIZE2 = 1024
    head_img = Image.new('RGBA', (SIZE2, SIZE2), (15, 15, 25, 255))
    hdraw = ImageDraw.Draw(head_img)

    for i in range(0, SIZE2, SIZE2//8):
        hdraw.line([(i, 0), (i, SIZE2)], fill=(40, 40, 60), width=1)
        hdraw.line([(0, i), (SIZE2, i)], fill=(40, 40, 60), width=1)

    for poly_idx, (poly, uv_poly) in enumerate(zip(polys, uv_polys)):
        is_head = any(vi in head_vert_indices for vi in poly)
        pts = [(int(u * SIZE2), int((1 - v) * SIZE2)) for u, v in uv_poly]
        color = (220, 100, 80, 220) if is_head else (50, 80, 60, 100)
        width = 2 if is_head else 1
        for i in range(len(pts)):
            hdraw.line([pts[i], pts[(i + 1) % len(pts)]], fill=color, width=width)

    # Mark head UV bounding box
    x1, y1 = int(min(us)*SIZE2), int((1-max(vs))*SIZE2)
    x2, y2 = int(max(us)*SIZE2), int((1-min(vs))*SIZE2)
    hdraw.rectangle([x1, y1, x2, y2], outline=(255, 220, 0), width=3)

    head_uv_path = os.path.join(OUT, "sakura_head_uv.png")
    head_img.save(head_uv_path)
    print(f"Head UV map saved: {head_uv_path}")
