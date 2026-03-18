"""
Spring Sakura FC26 Head Mesh - LOD Fix Script
Fixes the "FBX does not contain any LODs" error in FET

Run this in Blender's Script editor:
  1. Open Blender
  2. Switch to Scripting workspace
  3. Open this file → Run Script

Output: head_260001_0_0_mesh.fbx  (replaces the old one)
"""

import bpy
import bmesh
import os

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE   = r"C:\Users\Administrator\Documents\sakura_mod_work"
OBJ    = os.path.join(BASE, "sakura_head_only.obj")
FC26   = r"C:\Users\Administrator\Downloads\新建文件夹\新建文件夹\head_121944_0_0_mesh.fbx"
OUT    = os.path.join(BASE, r"sakura_fc26_mod\sakura_260001\head_260001_0_0_mesh.fbx")

# LOD target ratios relative to LOD0 vertex count
LOD1_RATIO = 0.24   # ~764 / 3157
LOD2_RATIO = 0.11   # ~353 / 3157

# ─── 1. Clear scene ───────────────────────────────────────────────────────────
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
for col in list(bpy.data.collections):
    bpy.data.collections.remove(col)

# ─── 2. Import FC26 reference (for armature + weights) ────────────────────────
print("[1/7] Importing FC26 reference FBX …")
bpy.ops.import_scene.fbx(filepath=FC26)

fc26_arm  = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
fc26_lod0 = next(
    o for o in bpy.data.objects
    if o.type == 'MESH'
    and 'head_mat' in o.name.lower()
    and 'lod.000' in o.name.lower()
)
print(f"    FC26 armature : {fc26_arm.name}")
print(f"    FC26 LOD0     : {fc26_lod0.name}  ({len(fc26_lod0.data.vertices)} verts)")

# ─── 3. Import Sakura head OBJ ────────────────────────────────────────────────
print("[2/7] Importing Sakura head OBJ …")
before = {o.name for o in bpy.data.objects}
# Blender 4.0+ uses bpy.ops.wm.obj_import; older uses bpy.ops.import_scene.obj
if hasattr(bpy.ops.wm, 'obj_import'):
    bpy.ops.wm.obj_import(
        filepath=OBJ,
        forward_axis='NEGATIVE_Z',
        up_axis='Y',
    )
else:
    bpy.ops.import_scene.obj(
        filepath=OBJ,
        axis_forward='-Z',
        axis_up='Y',
    )
after  = {o.name for o in bpy.data.objects}
new_names = after - before
sk_raw = next(o for o in bpy.data.objects if o.name in new_names and o.type == 'MESH')
print(f"    Sakura raw    : {sk_raw.name}  ({len(sk_raw.data.vertices)} verts)")

# ─── 4. Apply any pending transforms on Sakura raw ────────────────────────────
bpy.context.view_layer.objects.active = sk_raw
sk_raw.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
sk_raw.select_set(False)

# ─── 5. Scale + align to FC26 head Z range ────────────────────────────────────
print("[3/7] Scaling and aligning Sakura head …")

def z_range(obj):
    coords = [obj.matrix_world @ v.co for v in obj.data.vertices]
    zs = [c.z for c in coords]
    return min(zs), max(zs)

sh_zmin, sh_zmax = z_range(sk_raw)
fc_zmin, fc_zmax = z_range(fc26_lod0)

sh_h = sh_zmax - sh_zmin
fc_h = fc_zmax - fc_zmin
scale = fc_h / sh_h if sh_h > 0 else 1.0

sk_raw.scale    = (scale, scale, scale)
sk_raw.location = (0, 0, 0)
bpy.context.view_layer.objects.active = sk_raw
sk_raw.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
sk_raw.select_set(False)

# re-centre to match FC26 head centroid
sh_zmin2, sh_zmax2 = z_range(sk_raw)
sh_cx = sum(v.co.x for v in sk_raw.data.vertices) / len(sk_raw.data.vertices)
sh_cy = sum(v.co.y for v in sk_raw.data.vertices) / len(sk_raw.data.vertices)
fc_cx = sum((fc26_lod0.matrix_world @ v.co).x for v in fc26_lod0.data.vertices) / len(fc26_lod0.data.vertices)
fc_cy = sum((fc26_lod0.matrix_world @ v.co).y for v in fc26_lod0.data.vertices) / len(fc26_lod0.data.vertices)
fc_cz = (fc_zmin + fc_zmax) / 2
sh_cz = (sh_zmin2 + sh_zmax2) / 2

sk_raw.location.x += (fc_cx - sh_cx)
sk_raw.location.y += (fc_cy - sh_cy)
sk_raw.location.z += (fc_cz - sh_cz)
bpy.context.view_layer.objects.active = sk_raw
sk_raw.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
sk_raw.select_set(False)

sh_zmin3, sh_zmax3 = z_range(sk_raw)
print(f"    Final Z range : {sh_zmin3:.4f} ~ {sh_zmax3:.4f}  (FC26: {fc_zmin:.4f} ~ {fc_zmax:.4f})")

# ─── 6. Transfer bone weights from FC26 LOD0 → Sakura ────────────────────────
print("[4/7] Transferring bone weights …")

# First parent Sakura to FC26 armature (needed for Data Transfer to write vertex groups)
sk_raw.parent = fc26_arm
sk_raw.parent_type = 'OBJECT'
# Add armature modifier
arm_mod = sk_raw.modifiers.new("Armature", 'ARMATURE')
arm_mod.object = fc26_arm

# Add Data Transfer modifier for vertex weights
dt = sk_raw.modifiers.new("DT_Weights", 'DATA_TRANSFER')
dt.object                 = fc26_lod0
dt.use_vert_data          = True
dt.data_types_verts       = {'VGROUP_WEIGHTS'}
dt.vert_mapping           = 'NEAREST'
dt.layers_vgroup_select_src = 'ALL'
dt.layers_vgroup_select_dst = 'NAME'

bpy.context.view_layer.objects.active = sk_raw
sk_raw.select_set(True)
bpy.ops.object.datalayout_transfer(modifier="DT_Weights")
bpy.ops.object.modifier_apply(modifier="DT_Weights")
sk_raw.select_set(False)
print(f"    Transferred {len(sk_raw.vertex_groups)} vertex groups")

# ─── 7. Create LOD1 and LOD2 via Decimate ─────────────────────────────────────
print("[5/7] Creating LOD1 and LOD2 …")

def make_lod(source_obj, ratio, suffix):
    """Duplicate source, decimate to ratio, rename to LOD suffix."""
    bpy.ops.object.select_all(action='DESELECT')
    source_obj.select_set(True)
    bpy.context.view_layer.objects.active = source_obj
    bpy.ops.object.duplicate(linked=False)
    lod_obj = bpy.context.active_object

    # Remove Armature modifier first so Decimate is the first modifier
    # (applying a non-first modifier causes Blender to rename mesh data internally)
    for mod in list(lod_obj.modifiers):
        if mod.type == 'ARMATURE':
            lod_obj.modifiers.remove(mod)

    dec = lod_obj.modifiers.new("Decimate", 'DECIMATE')
    dec.ratio         = ratio
    dec.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier="Decimate")

    # Re-add armature modifier so FBX exporter writes skinning data
    arm_mod2 = lod_obj.modifiers.new("Armature", 'ARMATURE')
    arm_mod2.object = fc26_arm

    lod_obj.name = suffix
    lod_obj.data.name = suffix
    print(f"    {suffix}: {len(lod_obj.data.vertices)} verts")
    return lod_obj

# Rename LOD0 to the FC26 naming convention
LOD0_NAME = "head_mat:head_260001_0_0_mesh_lod.000"
LOD1_NAME = "head_mat:head_260001_0_0_mesh_lod.001"
LOD2_NAME = "head_mat:head_260001_0_0_mesh_lod.002"

sk_raw.name      = LOD0_NAME
sk_raw.data.name = LOD0_NAME
print(f"    LOD0: {len(sk_raw.data.vertices)} verts  → renamed to {LOD0_NAME}")

lod0_vcount = len(sk_raw.data.vertices)
lod1 = make_lod(sk_raw, LOD1_RATIO, LOD1_NAME)
lod2 = make_lod(sk_raw, LOD2_RATIO, LOD2_NAME)

# ─── 8. Assign material ───────────────────────────────────────────────────────
print("[6/7] Assigning materials …")
mat = bpy.data.materials.get("head_mat") or bpy.data.materials.new("head_mat")
for obj in [sk_raw, lod1, lod2]:
    if not obj.data.materials:
        obj.data.materials.append(mat)
    else:
        obj.data.materials[0] = mat

# ─── 9. Select only our three LODs + armature for export ──────────────────────
print("[7/7] Exporting FBX …")
bpy.ops.object.select_all(action='DESELECT')
for obj in [fc26_arm, sk_raw, lod1, lod2]:
    obj.select_set(True)

# Hide / deselect FC26 original LODs so they don't pollute the export
for o in bpy.data.objects:
    if 'head_121944' in o.name or 'mouthbag_121944' in o.name:
        o.select_set(False)

bpy.ops.export_scene.fbx(
    filepath            = OUT,
    use_selection       = True,
    add_leaf_bones      = False,
    bake_anim           = False,
    use_tspace          = True,        # tangent space — required by FET
    use_triangles       = True,
    mesh_smooth_type    = 'FACE',
    axis_forward        = '-Z',
    axis_up             = 'Y',
    global_scale        = 1.0,
    path_mode           = 'AUTO',
    embed_textures      = False,
)

print()
print("=" * 60)
print(f"✅  Done! Exported to:\n    {OUT}")
print("=" * 60)
print()
print("The FBX now contains 3 LOD meshes:")
print(f"  LOD0: {len(sk_raw.data.vertices):5d} verts  ({LOD0_NAME})")
print(f"  LOD1: {len(lod1.data.vertices):5d} verts  ({LOD1_NAME})")
print(f"  LOD2: {len(lod2.data.vertices):5d} verts  ({LOD2_NAME})")
print()
print("Next step: In FET → right-click player_260000 → Add Face → Import Face")
print("           select the folder containing this FBX + the PNG textures.")
