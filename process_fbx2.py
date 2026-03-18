import bpy, os, math, sys

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

bpy.ops.import_scene.fbx(filepath="F:/未命名.fbx")
objects = list(bpy.context.scene.objects)

# Fix orientation: lying flat -> standing upright
for obj in objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = objects[0]
bpy.ops.transform.rotate(value=math.radians(90), orient_axis='X')
bpy.ops.transform.rotate(value=math.radians(180), orient_axis='Z')
bpy.ops.object.select_all(action='DESELECT')

mesh_obj = [o for o in objects if o.type == 'MESH'][0]
mesh = mesh_obj.data

print(f"Mesh name: {mesh_obj.name}")
print(f"Vertices: {len(mesh.vertices)}")
print(f"Polygons: {len(mesh.polygons)}")
print(f"UV layers: {[uv.name for uv in mesh.uv_layers]}")
print(f"Materials: {[m.name for m in mesh_obj.material_slots]}")

bpy.context.view_layer.update()
bbox = [mesh_obj.matrix_world @ v.co for v in mesh.vertices]
xs = [v.x for v in bbox]
ys = [v.y for v in bbox]
zs = [v.z for v in bbox]
print(f"Bounds: X={min(xs):.3f}~{max(xs):.3f}")
print(f"Bounds: Y={min(ys):.3f}~{max(ys):.3f}")
print(f"Bounds: Z={min(zs):.3f}~{max(zs):.3f}")
print(f"Height: {max(zs)-min(zs):.3f}")

OUT = "C:/Users/Administrator/Documents/sakura_mod_work"

# Draw UV layout using PIL
uv_layer = mesh.uv_layers.active
if uv_layer:
    sys.path.insert(0, "C:/Users/Administrator/AppData/Local/Programs/Python/Python314/Lib/site-packages")
    from PIL import Image, ImageDraw
    SIZE = 1024
    uv_img = Image.new('RGBA', (SIZE, SIZE), (20, 20, 20, 255))
    draw = ImageDraw.Draw(uv_img)

    uvs = uv_layer.data
    for poly in mesh.polygons:
        loop_uvs = [uvs[li].uv for li in poly.loop_indices]
        pts = [(int(u * SIZE), int((1 - v) * SIZE)) for u, v in loop_uvs]
        for i in range(len(pts)):
            draw.line([pts[i], pts[(i + 1) % len(pts)]], fill=(100, 200, 100, 200), width=1)

    uv_path = os.path.join(OUT, "sakura_uv_layout.png")
    uv_img.save(uv_path)
    print(f"UV layout saved: {uv_path}")

# Save blend file
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "sakura_processed.blend"))
print("Blend file saved.")
