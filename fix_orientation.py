"""Fix Sakura model orientation and re-export"""
import bpy, os, math

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

bpy.ops.import_scene.fbx(filepath="F:/未命名.fbx")
objects = list(bpy.context.scene.objects)

for obj in objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = objects[0]

# Rotate -90 on X (opposite direction) to stand upright correctly
bpy.ops.transform.rotate(value=math.radians(-90), orient_axis='X')

bpy.ops.object.select_all(action='DESELECT')
bpy.context.view_layer.update()

OUT = "C:/Users/Administrator/Documents/sakura_mod_work"
mesh_obj = [o for o in objects if o.type == 'MESH'][0]
verts = [mesh_obj.matrix_world @ v.co for v in mesh_obj.data.vertices]
zs = [v.z for v in verts]
print(f"Z range after fix: {min(zs):.2f} ~ {max(zs):.2f}")
print(f"Head should be at top (max Z)")

# Set up front-facing camera
bpy.ops.object.camera_add(location=(0, -250, 80))
cam = bpy.context.object
cam.rotation_euler = (math.radians(90), 0, 0)
bpy.context.scene.camera = cam

bpy.ops.object.light_add(type='SUN', location=(50, -100, 200))

scene = bpy.context.scene
scene.render.resolution_x = 512
scene.render.resolution_y = 768
scene.render.filepath = os.path.join(OUT, "sakura_upright.png")
scene.render.image_settings.file_format = 'PNG'
scene.render.engine = 'BLENDER_WORKBENCH'
bpy.ops.render.render(write_still=True)
print(f"Render saved: {scene.render.filepath}")

# Save blend
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "sakura_upright.blend"))
print("Done.")
