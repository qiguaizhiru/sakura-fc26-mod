"""
Find face polygons correctly and render face close-up with texture.
"""
import bpy, os, math, json

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

OBJ_PATH = "E:/BaiduNetdiskDownload/角色/角色/小樱/Sakura.obj"
OUT      = "C:/Users/Administrator/Documents/sakura_mod_work"

bpy.ops.wm.obj_import(filepath=OBJ_PATH)
bpy.context.view_layer.update()

obj = [o for o in bpy.context.scene.objects if o.type == 'MESH'][0]
mesh = obj.data
uv_layer = mesh.uv_layers.active
uvs = uv_layer.data
mats = [m.name if m else "" for m in obj.material_slots]

# World-space vertex Z for each polygon center
all_polys_info = []
for poly in mesh.polygons:
    mat_name = mats[poly.material_index] if poly.material_index < len(mats) else ""
    loop_uvs = [[uvs[li].uv.x, uvs[li].uv.y] for li in poly.loop_indices]
    wz = sum((obj.matrix_world @ mesh.vertices[vi].co).z for vi in poly.vertices) / len(poly.vertices)
    wx = sum((obj.matrix_world @ mesh.vertices[vi].co).x for vi in poly.vertices) / len(poly.vertices)
    wy = sum((obj.matrix_world @ mesh.vertices[vi].co).y for vi in poly.vertices) / len(poly.vertices)
    all_polys_info.append({"mat": mat_name, "uvs": loop_uvs, "wz": wz, "wx": wx, "wy": wy})

zs = [p["wz"] for p in all_polys_info]
z_min, z_max = min(zs), max(zs)
height = z_max - z_min
print(f"Z: {z_min:.2f} ~ {z_max:.2f}, height={height:.2f}")

# Try BOTH top and bottom 12% for head
for label, thresh_fn in [("TOP 12%", lambda z: z >= z_max - height*0.12),
                          ("BOTTOM 12%", lambda z: z <= z_min + height*0.12)]:
    face = [p for p in all_polys_info if thresh_fn(p["wz"]) and "sakura" in p["mat"].lower()]
    if face:
        us = [u for p in face for u,v in p["uvs"]]
        vs = [v for p in face for u,v in p["uvs"]]
        cx = sum(p["wx"] for p in face)/len(face)
        cy = sum(p["wy"] for p in face)/len(face)
        cz = sum(p["wz"] for p in face)/len(face)
        print(f"\n{label}: {len(face)} polys, center=({cx:.2f},{cy:.2f},{cz:.2f})")
        print(f"  UV U: {min(us):.4f}~{max(us):.4f}")
        print(f"  UV V: {min(vs):.4f}~{max(vs):.4f}")
        # Normalize V with mod
        vs_mod = [v % 1.0 for v in vs]
        print(f"  UV V mod1: {min(vs_mod):.4f}~{max(vs_mod):.4f}")

# ── Render with textured shading, from FRONT ───────────────────────────────
# Place camera looking at face (find the actual face center)
# Face is likely near center X, front of Y, near top or bottom of Z

# Take top 20% of model height (assume standing = head at top)
top_polys = [p for p in all_polys_info if p["wz"] >= z_max - height*0.20 and "sakura" in p["mat"].lower()]
if top_polys:
    cx = sum(p["wx"] for p in top_polys)/len(top_polys)
    cy = sum(p["wy"] for p in top_polys)/len(top_polys)
    cz = sum(p["wz"] for p in top_polys)/len(top_polys)
else:
    cx, cy, cz = 0, 0, z_max - height*0.10

print(f"\nCamera target: ({cx:.2f}, {cy:.2f}, {cz:.2f})")

# Camera from front (negative Y)
cam_dist = height * 0.3
bpy.ops.object.camera_add(location=(cx, cy - cam_dist, cz))
cam = bpy.context.object
cam.rotation_euler = (math.radians(90), 0, 0)
cam.data.lens = 85  # telephoto for face
bpy.context.scene.camera = cam

bpy.ops.object.light_add(type='SUN', location=(cx+10, cy-cam_dist, cz+20))
bpy.data.lights[-1].energy = 3.0

sc = bpy.context.scene
sc.render.resolution_x = 512
sc.render.resolution_y = 512
sc.render.filepath = f"{OUT}/sakura_face_front.png"
sc.render.image_settings.file_format = 'PNG'
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'STUDIO'
sc.display.shading.color_type = 'TEXTURE'

bpy.ops.render.render(write_still=True)
print("Rendered: sakura_face_front.png")
