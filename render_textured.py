"""Render Sakura face with full textures from correct paths"""
import bpy, os, math

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

OBJ_PATH = "E:/BaiduNetdiskDownload/角色/角色/小樱/Sakura.obj"
TEX_DIR  = "E:/BaiduNetdiskDownload/角色/角色/小樱"
OUT      = "C:/Users/Administrator/Documents/sakura_mod_work"

bpy.ops.wm.obj_import(filepath=OBJ_PATH)
bpy.context.view_layer.update()

# Fix texture paths
for mat in bpy.data.materials:
    mat.use_nodes = True
    for node in mat.node_tree.nodes:
        if node.type == 'TEX_IMAGE' and node.image:
            img = node.image
            fname = os.path.basename(img.filepath)
            correct_path = os.path.join(TEX_DIR, fname)
            if os.path.exists(correct_path):
                img.filepath = correct_path
                img.reload()
                print(f"  Fixed: {fname}")

obj = [o for o in bpy.context.scene.objects if o.type == 'MESH'][0]
mesh = obj.data

# Get all vertex positions to find bounding box
verts_world = [obj.matrix_world @ v.co for v in mesh.vertices]
xs = [v.x for v in verts_world]
ys = [v.y for v in verts_world]
zs = [v.z for v in verts_world]
cx = (max(xs)+min(xs))/2
z_max, z_min = max(zs), min(zs)
height = z_max - z_min

# Head center = top 8% of model
top_verts = [v for v in verts_world if v.z >= z_max - height*0.08]
if top_verts:
    hx = sum(v.x for v in top_verts)/len(top_verts)
    hy = sum(v.y for v in top_verts)/len(top_verts)
    hz = sum(v.z for v in top_verts)/len(top_verts)
else:
    hx, hy, hz = cx, (max(ys)+min(ys))/2, z_max - height*0.04

print(f"Head center estimate: ({hx:.2f}, {hy:.2f}, {hz:.2f})")
print(f"Front Y: {min(ys):.2f}")

# Camera: place in front of head (min Y side = front of character)
cam_y = min(ys) - height * 0.25
bpy.ops.object.camera_add(location=(hx, cam_y, hz))
cam_obj = bpy.context.object
cam_obj.rotation_euler = (math.radians(90), 0, 0)
cam_obj.data.lens = 100
bpy.context.scene.camera = cam_obj

# Lighting
bpy.ops.object.light_add(type='AREA', location=(hx, cam_y, hz+5))
bpy.data.lights[-1].energy = 500
bpy.ops.object.light_add(type='AREA', location=(hx+5, cam_y-2, hz))
bpy.data.lights[-1].energy = 200

sc = bpy.context.scene
sc.render.resolution_x = 512
sc.render.resolution_y = 512
sc.render.filepath = f"{OUT}/sakura_textured_face.png"
sc.render.image_settings.file_format = 'PNG'
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'STUDIO'
sc.display.shading.color_type = 'TEXTURE'
sc.display.shading.show_backface_culling = False

bpy.ops.render.render(write_still=True)
print("Rendered: sakura_textured_face.png")

# Also render full body
cam_obj.location.z = (z_max + z_min) / 2
cam_obj.location.y = min(ys) - height * 0.8
cam_obj.data.lens = 50
sc.render.filepath = f"{OUT}/sakura_textured_full.png"
sc.render.resolution_y = 768
bpy.ops.render.render(write_still=True)
print("Rendered: sakura_textured_full.png")
