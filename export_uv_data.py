"""Export UV + vertex data from Sakura FBX for external processing"""
import bpy, os, math, json

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

bpy.ops.import_scene.fbx(filepath="F:/未命名.fbx")
objects = list(bpy.context.scene.objects)

# Fix orientation
for obj in objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = objects[0]
bpy.ops.transform.rotate(value=math.radians(90), orient_axis='X')
bpy.ops.transform.rotate(value=math.radians(180), orient_axis='Z')
bpy.ops.object.select_all(action='DESELECT')

mesh_obj = [o for o in objects if o.type == 'MESH'][0]
mesh = mesh_obj.data
bpy.context.view_layer.update()

OUT = "C:/Users/Administrator/Documents/sakura_mod_work"

# Export UV polygons as JSON
uv_layer = mesh.uv_layers.active
uv_polys = []
if uv_layer:
    uvs = uv_layer.data
    for poly in mesh.polygons:
        loop_uvs = [[uvs[li].uv.x, uvs[li].uv.y] for li in poly.loop_indices]
        uv_polys.append(loop_uvs)

# Export vertex 3D positions (world space)
bpy.context.view_layer.update()
verts_3d = []
for v in mesh.vertices:
    wco = mesh_obj.matrix_world @ v.co
    verts_3d.append([round(wco.x, 4), round(wco.y, 4), round(wco.z, 4)])

# Export polygon vertex indices
polys_idx = [[vi for vi in p.vertices] for p in mesh.polygons]

data = {
    "mesh_name": mesh_obj.name,
    "vertex_count": len(mesh.vertices),
    "polygon_count": len(mesh.polygons),
    "uv_layer": uv_layer.name if uv_layer else None,
    "materials": [m.name for m in mesh_obj.material_slots],
    "uv_polygons": uv_polys,      # list of polys, each is list of [u,v]
    "vertices_3d": verts_3d,       # list of [x,y,z]
    "polygon_indices": polys_idx,  # list of polys, each is list of vert indices
}

json_path = os.path.join(OUT, "sakura_mesh_data.json")
with open(json_path, 'w') as f:
    json.dump(data, f)

print(f"Mesh data exported: {json_path}")
print(f"UV polygons: {len(uv_polys)}")
print(f"Vertices: {len(verts_3d)}")

# Also render a quick front-view screenshot
# Set up camera
bpy.ops.object.camera_add(location=(0, -200, -80))
cam = bpy.context.object
cam.rotation_euler = (math.radians(90), 0, 0)
bpy.context.scene.camera = cam

# Basic lighting
bpy.ops.object.light_add(type='SUN', location=(0, -100, 200))

# Render settings
scene = bpy.context.scene
scene.render.resolution_x = 512
scene.render.resolution_y = 512
scene.render.filepath = os.path.join(OUT, "sakura_render.png")
scene.render.image_settings.file_format = 'PNG'
scene.render.engine = 'BLENDER_WORKBENCH'

bpy.ops.render.render(write_still=True)
print(f"Render saved: {scene.render.filepath}")
