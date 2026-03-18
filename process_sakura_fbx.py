"""
Blender script: Import Sakura FBX, fix orientation, extract head, export UV layout
Run with: blender.exe --background --python process_sakura_fbx.py
"""
import bpy
import os
import math
import sys

# ── Paths ──────────────────────────────────────────────────────────────────
FBX_PATH  = "F:/未命名.fbx"
OUT_DIR   = "C:/Users/Administrator/Documents/sakura_mod_work"
os.makedirs(OUT_DIR, exist_ok=True)

print("\n" + "="*60)
print("Sakura FBX Processor")
print("="*60)

# ── 1. Clean scene ──────────────────────────────────────────────────────────
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# ── 2. Import FBX ──────────────────────────────────────────────────────────
print(f"\n[1] Importing: {FBX_PATH}")
bpy.ops.import_scene.fbx(filepath=FBX_PATH)

objects = bpy.context.scene.objects
print(f"    Objects imported: {len(list(objects))}")
for obj in objects:
    print(f"      - [{obj.type}] '{obj.name}'  loc={tuple(round(x,3) for x in obj.location)}")

# ── 3. Fix orientation (model is lying flat, rotate to stand upright) ───────
print("\n[2] Fixing orientation...")
for obj in objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = list(objects)[0]

# Apply: rotate 90° around X so model stands up
bpy.ops.transform.rotate(value=math.radians(90), orient_axis='X')

# Also rotate 180° around Z if facing wrong direction
bpy.ops.transform.rotate(value=math.radians(180), orient_axis='Z')

bpy.ops.object.select_all(action='DESELECT')
print("    Rotated 90° on X-axis, 180° on Z-axis")

# ── 4. Identify mesh objects ────────────────────────────────────────────────
meshes = [o for o in objects if o.type == 'MESH']
print(f"\n[3] Mesh objects found: {len(meshes)}")
for m in meshes:
    vert_count = len(m.data.vertices)
    print(f"      '{m.name}': {vert_count} vertices")

# ── 5. Find head mesh (usually the mesh with fewest vertices or named 'head') ─
# Heuristic: head mesh is smallest by vertex count among body parts,
# but larger than accessories
head_mesh = None
head_keywords = ['head', 'face', 'Head', 'Face', 'sakura']
for m in meshes:
    for kw in head_keywords:
        if kw.lower() in m.name.lower():
            head_mesh = m
            print(f"\n[4] Head mesh found by name: '{m.name}'")
            break
    if head_mesh:
        break

if not head_mesh and meshes:
    # Pick largest mesh (body+head combined) or smallest that makes sense
    sorted_by_verts = sorted(meshes, key=lambda o: len(o.data.vertices))
    # The head is usually mid-sized; if there's only one mesh, use it
    if len(meshes) == 1:
        head_mesh = meshes[0]
    else:
        # Use the mesh closest to Y=0 (head usually centered)
        head_mesh = sorted_by_verts[-1]  # largest = full body
    print(f"\n[4] Using mesh: '{head_mesh.name}' ({len(head_mesh.data.vertices)} verts)")

# ── 6. Export full model as OBJ (for reference) ────────────────────────────
print("\n[5] Exporting full model as OBJ...")
bpy.ops.object.select_all(action='SELECT')
obj_path = os.path.join(OUT_DIR, "sakura_full_model.obj")
bpy.ops.wm.obj_export(
    filepath=obj_path,
    export_selected_objects=False,
    export_uv=True,
    export_normals=True,
    export_materials=True,
    path_mode='COPY'
)
print(f"    Saved: {obj_path}")

# ── 7. Export UV layout as image ────────────────────────────────────────────
print("\n[6] Exporting UV layout...")
if head_mesh:
    bpy.ops.object.select_all(action='DESELECT')
    head_mesh.select_set(True)
    bpy.context.view_layer.objects.active = head_mesh

    # Switch to edit mode to export UV
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')

    # Export UV layout
    uv_path = os.path.join(OUT_DIR, "sakura_uv_layout.png")
    bpy.ops.uv.export_layout(
        filepath=uv_path,
        size=(1024, 1024),
        opacity=0.25
    )
    bpy.ops.object.mode_set(mode='OBJECT')
    print(f"    UV layout saved: {uv_path}")

# ── 8. Print bounding boxes to understand model scale ──────────────────────
print("\n[7] Bounding boxes (after rotation):")
for m in meshes:
    bbox = m.bound_box
    xs = [v[0] for v in bbox]
    ys = [v[1] for v in bbox]
    zs = [v[2] for v in bbox]
    print(f"    '{m.name}': X={min(xs):.2f}~{max(xs):.2f}, "
          f"Y={min(ys):.2f}~{max(ys):.2f}, Z={min(zs):.2f}~{max(zs):.2f}")

# ── 9. Save Blender file ────────────────────────────────────────────────────
blend_path = os.path.join(OUT_DIR, "sakura_processed.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print(f"\n[8] Blender file saved: {blend_path}")

print("\n=== DONE ===")
print(f"Output directory: {OUT_DIR}")
print("Files created:")
for f in os.listdir(OUT_DIR):
    if f.endswith(('.obj', '.mtl', '.png', '.blend')):
        size = os.path.getsize(os.path.join(OUT_DIR, f)) / 1024
        print(f"  {f}: {size:.1f} KB")
