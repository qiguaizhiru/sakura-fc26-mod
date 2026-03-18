"""
Blender script: Load Sakura.obj, identify face polygons by material/UV,
render face close-up, and export face UV data for texture extraction.
"""
import bpy, os, math, json

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

OBJ_PATH = "E:/BaiduNetdiskDownload/角色/角色/小樱/Sakura.obj"
OUT      = "C:/Users/Administrator/Documents/sakura_mod_work"

print("[1] Importing Sakura.obj ...")
bpy.ops.wm.obj_import(filepath=OBJ_PATH)
bpy.context.view_layer.update()

objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
print(f"    Meshes: {[o.name for o in objects]}")

# ── Collect all UV + material data ─────────────────────────────────────────
all_polys = []
for obj in objects:
    mesh = obj.data
    uv_layer = mesh.uv_layers.active
    if not uv_layer:
        continue
    uvs = uv_layer.data
    mats = [m.name if m else "" for m in obj.material_slots]
    for poly in mesh.polygons:
        mat_name = mats[poly.material_index] if poly.material_index < len(mats) else ""
        loop_uvs = [[round(uvs[li].uv.x, 5), round(uvs[li].uv.y, 5)]
                    for li in poly.loop_indices]
        vert_co  = [(obj.matrix_world @ mesh.vertices[vi].co)
                    for vi in poly.vertices]
        center_z = sum(v.z for v in vert_co) / len(vert_co)
        all_polys.append({
            "mat": mat_name,
            "uvs": loop_uvs,
            "cz":  round(center_z, 3),
            "obj": obj.name,
        })

print(f"    Total polygons: {len(all_polys)}")

# Material breakdown
from collections import Counter
mat_counts = Counter(p["mat"] for p in all_polys)
for mat, cnt in mat_counts.items():
    print(f"    Mat '{mat}': {cnt} polys")

# ── Find head/face polygons ─────────────────────────────────────────────────
# The head is at the TOP of the model.
all_z = [p["cz"] for p in all_polys]
z_max, z_min = max(all_z), min(all_z)
height = z_max - z_min
print(f"\n    Z range: {z_min:.2f} ~ {z_max:.2f}  height={height:.2f}")

# Head = top 12% of model, using the 'sakura' material (ntxr000)
head_z_thresh = z_max - height * 0.12
face_polys = [p for p in all_polys
              if p["cz"] >= head_z_thresh
              and "sakura" in p["mat"].lower()]
print(f"    Face polygons (top 12%, sakura mat): {len(face_polys)}")

if face_polys:
    us = [u for p in face_polys for u, v in p["uvs"]]
    vs = [v for p in face_polys for u, v in p["uvs"]]
    print(f"    Face UV U: {min(us):.4f} ~ {max(us):.4f}")
    print(f"    Face UV V: {min(vs):.4f} ~ {max(vs):.4f}")

# ── Save polygon data ───────────────────────────────────────────────────────
json.dump({"polys": all_polys, "face_polys": face_polys,
           "z_max": z_max, "z_min": z_min},
          open(f"{OUT}/sakura_obj_data.json", "w"))
print(f"\n    Saved: sakura_obj_data.json")

# ── Set up scene for face close-up render ──────────────────────────────────
# Position camera looking at the head area
head_z_center = z_max - height * 0.06  # center of head region

bpy.ops.object.camera_add(location=(0, -80, head_z_center))
cam = bpy.context.object
cam.rotation_euler = (math.radians(90), 0, 0)
bpy.context.scene.camera = cam

# Wide sun light
bpy.ops.object.light_add(type='SUN', location=(20, -60, head_z_center + 20))

scene = bpy.context.scene
scene.render.resolution_x = 512
scene.render.resolution_y = 512
scene.render.filepath = f"{OUT}/sakura_face_closeup.png"
scene.render.image_settings.file_format = 'PNG'
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'MATCAP'
scene.display.shading.color_type = 'TEXTURE'

bpy.ops.render.render(write_still=True)
print(f"    Face render: sakura_face_closeup.png")
