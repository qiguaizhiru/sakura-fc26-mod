"""
Step 1 of FMT workflow:
Load Pedro Mendes' exported head mesh from FMT + Sakura head geometry,
align them, and export the final head OBJ for FMT re-import.

Run this AFTER exporting Pedro's head with FMT on the other computer.
Place Pedro's exported OBJ as: C:/Users/Administrator/Documents/sakura_mod_work/pedro_head_export.obj
"""
import bpy, sys, os, math
sys.stdout.reconfigure(encoding='utf-8')

OUT = "C:/Users/Administrator/Documents/sakura_mod_work"
PEDRO_OBJ = f"{OUT}/pedro_head_export.obj"   # exported by FMT from FC26
SAKURA_HEAD = f"{OUT}/sakura_head_only.obj"

# Clear scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# --- Import Pedro's head (reference for bone weights + UV layout)
if os.path.exists(PEDRO_OBJ):
    bpy.ops.wm.obj_import(filepath=PEDRO_OBJ)
    pedro = bpy.context.selected_objects[0]
    pedro.name = "Pedro_Reference"
    # Get bounding box
    bbox = [pedro.matrix_world @ v.co for v in pedro.data.vertices]
    p_y_vals = [v.y for v in bbox]
    p_z_vals = [v.z for v in bbox]
    pedro_height = max(p_z_vals) - min(p_z_vals)
    pedro_center_x = 0
    pedro_center_y = (max(p_y_vals) + min(p_y_vals)) / 2
    pedro_bottom_z = min(p_z_vals)
    print(f"Pedro head: height={pedro_height:.3f}, center_y={pedro_center_y:.3f}")
else:
    print("WARNING: pedro_head_export.obj not found. Export it from FMT first.")
    pedro = None
    pedro_height = 20.0  # approximate

# --- Import Sakura head
bpy.ops.wm.obj_import(filepath=SAKURA_HEAD)
sakura = bpy.context.selected_objects[0]
sakura.name = "Sakura_Head"

# Get Sakura head bounding box
bbox_s = [sakura.matrix_world @ v.co for v in sakura.data.vertices]
s_y_vals = [v.y for v in bbox_s]
s_z_vals = [v.z for v in bbox_s]
sakura_height = max(s_z_vals) - min(s_z_vals)
sakura_bottom_z = min(s_z_vals)
print(f"Sakura head: height={sakura_height:.3f}")

# Scale Sakura to match Pedro's head size
if pedro and sakura_height > 0:
    scale_factor = pedro_height / sakura_height
    sakura.scale = (scale_factor, scale_factor, scale_factor)
    bpy.ops.object.transform_apply(scale=True)
    print(f"Scale factor: {scale_factor:.4f}")
    # Recompute after scaling
    bbox_s2 = [sakura.matrix_world @ v.co for v in sakura.data.vertices]
    s_y_center = (max([v.y for v in bbox_s2]) + min([v.y for v in bbox_s2])) / 2
    s_z_bottom = min([v.z for v in bbox_s2])
    # Translate to align centers
    sakura.location.x = 0
    sakura.location.y = pedro_center_y - s_y_center
    sakura.location.z = pedro_bottom_z - s_z_bottom
    bpy.ops.object.transform_apply(location=True)
    print(f"Aligned Sakura to Pedro's head position")

# Export aligned Sakura head
bpy.ops.object.select_all(action='DESELECT')
sakura.select_set(True)
bpy.context.view_layer.objects.active = sakura
out_path = f"{OUT}/sakura_head_aligned.obj"
bpy.ops.wm.obj_export(filepath=out_path, export_selected_objects=True)
print(f"\nSaved: sakura_head_aligned.obj")
print("Next: Import this into FMT as the replacement mesh")
