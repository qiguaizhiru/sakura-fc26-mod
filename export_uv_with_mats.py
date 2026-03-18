"""Export UV + material index per polygon"""
import bpy, os, math, json

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

bpy.ops.import_scene.fbx(filepath="F:/未命名.fbx")
objects = list(bpy.context.scene.objects)

for obj in objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = objects[0]
bpy.ops.transform.rotate(value=math.radians(-90), orient_axis='X')
bpy.ops.object.select_all(action='DESELECT')
bpy.context.view_layer.update()

mesh_obj = [o for o in objects if o.type == 'MESH'][0]
mesh = mesh_obj.data

OUT = "C:/Users/Administrator/Documents/sakura_mod_work"

uv_layer = mesh.uv_layers.active
uvs = uv_layer.data

export = {
    "materials": [m.name for m in mesh_obj.material_slots],
    "polygons": []
}

for poly in mesh.polygons:
    loop_uvs = [[uvs[li].uv.x, uvs[li].uv.y] for li in poly.loop_indices]
    vert_co = [[round((mesh_obj.matrix_world @ mesh.vertices[vi].co).x, 3),
                round((mesh_obj.matrix_world @ mesh.vertices[vi].co).y, 3),
                round((mesh_obj.matrix_world @ mesh.vertices[vi].co).z, 3)]
               for vi in poly.vertices]
    export["polygons"].append({
        "mat_idx": poly.material_index,
        "uvs": loop_uvs,
        "verts": vert_co,
        "center_z": round(poly.center.z, 3)
    })

out_path = os.path.join(OUT, "sakura_uv_mats.json")
with open(out_path, 'w') as f:
    json.dump(export, f)
print(f"Exported {len(export['polygons'])} polygons to {out_path}")
for i, m in enumerate(export["materials"]):
    count = sum(1 for p in export["polygons"] if p["mat_idx"] == i)
    print(f"  Material {i} '{m}': {count} polygons")
