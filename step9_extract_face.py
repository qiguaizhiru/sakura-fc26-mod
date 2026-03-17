# =====================================================
# 第9步（重写）：从大黑塔 PMX 直接提取脸部网格
# 转换成 NBA2K 格式，替换面部IFF
# 在 Blender 脚本编辑器里运行
# 前提：场景里有大黑塔Ver1.0_mesh（运行step1导入PMX）
# =====================================================

import bpy
import bmesh
import struct
import os
import zipfile
import re

IFF_IN  = r"F:\大卫李\png6794.iff"
IFF_OUT = r"F:\大卫李\sakura_output\png6794.iff"
OUT_TXT = r"C:\Users\Administrator\Documents\sakura_mod_work\step9_result.txt"

os.makedirs(r"F:\大卫李\sakura_output", exist_ok=True)

# 大黑塔脸部材质关键词
FACE_KEYWORDS = ['颜', 'face', '顔', 'skin', 'head']
# 排除的关键词（非脸部）
FACE_EXCLUDE  = ['口', 'mouth', '牙', 'teeth', '眉', 'brow',
                 '目', 'eye', '睫', 'lash', '淚', 'tear', '赤', 'blush']

def popup(msg, title="提示", icon='INFO'):
    lines = msg.split('\n')
    def draw(self, context):
        for line in lines:
            self.layout.label(text=line)
    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

def pack_normal(nx, ny, nz):
    x = max(0.0, min(1.0, nx*0.5+0.5))
    y = max(0.0, min(1.0, ny*0.5+0.5))
    z = max(0.0, min(1.0, nz*0.5+0.5))
    return (int(x*1023+0.5)&0x3FF) | ((int(y*1023+0.5)&0x3FF)<<10) | \
           ((int(z*1023+0.5)&0x3FF)<<20) | (3<<30)

def pack_snorm16(v):
    return int(max(-1.0,min(1.0,v))*32767) & 0xFFFF

def main():
    lines = ["=== 第9步：提取大黑塔脸部 → NBA2K ===\n"]

    # 找大黑塔主网格
    src = None
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and '大黑塔' in obj.name and 'mesh' in obj.name.lower():
            src = obj; break
    if not src:
        meshes = [o for o in bpy.context.scene.objects
                  if o.type=='MESH' and len(o.data.vertices)>50000]
        src = max(meshes, key=lambda o: len(o.data.vertices)) if meshes else None
    if not src:
        popup("找不到大黑塔网格！请先运行step1导入PMX", title="错误", icon='ERROR')
        return

    lines.append(f"源网格: {src.name}  顶点:{len(src.data.vertices)}")

    # 找脸部材质槽
    face_slots = []
    for i, slot in enumerate(src.material_slots):
        if not slot.material: continue
        mname = slot.material.name
        is_face = any(k in mname for k in FACE_KEYWORDS)
        is_excl = any(k in mname for k in FACE_EXCLUDE)
        if is_face and not is_excl:
            face_slots.append((i, mname))

    lines.append(f"\n识别为脸部的材质槽 ({len(face_slots)} 个):")
    for i, mn in face_slots:
        lines.append(f"  [{i}] {mn}")

    if not face_slots:
        # 列出所有材质
        lines.append("\n未识别，所有材质槽:")
        for i, s in enumerate(src.material_slots):
            if s.material:
                lines.append(f"  [{i}] {s.material.name}")
        with open(OUT_TXT,"w",encoding="utf-8") as f: f.write("\n".join(lines))
        popup("未找到脸部材质！查看step9_result.txt", title="错误", icon='ERROR')
        return

    face_indices = [i for i,_ in face_slots]

    # ── 复制并分离脸部 ──────────────────────────────────────────────
    bpy.ops.object.select_all(action='DESELECT')
    src.select_set(True)
    bpy.context.view_layer.objects.active = src
    bpy.ops.object.duplicate()
    dup = bpy.context.active_object
    dup.name = "bronya_face_source"

    bpy.ops.object.mode_set(mode='OBJECT')
    for face in dup.data.polygons:
        face.select = face.material_index in face_indices
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='INVERT')
    bpy.ops.mesh.delete(type='FACE')
    bpy.ops.object.mode_set(mode='OBJECT')

    dup.name = "bronya_face"
    lines.append(f"\n脸部对象: bronya_face")
    lines.append(f"  顶点: {len(dup.data.vertices)}  面: {len(dup.data.polygons)}")

    # ── 对齐缩放到 NBA2K 头部 ──────────────────────────────────────
    # 读取 NBA2K 主 IFF 的 SCNE 获取头部范围
    nba2k_head_top = 83.11
    nba2k_head_bot = 61.78
    nba2k_head_cx  = 0.0

    zs = [v.co.z for v in dup.data.vertices]
    b_top = max(zs); b_bot = min(zs); b_h = b_top - b_bot
    n_h = nba2k_head_top - nba2k_head_bot
    scale = n_h / b_h

    dup.scale = (scale, scale, scale)
    bpy.context.view_layer.update()

    # 重新算包围盒后对齐
    zs2 = [(dup.matrix_world @ v.co).z for v in dup.data.vertices]
    ys2 = [(dup.matrix_world @ v.co).y for v in dup.data.vertices]
    xs2 = [(dup.matrix_world @ v.co).x for v in dup.data.vertices]
    new_bot = min(zs2)
    new_cx  = (min(xs2)+max(xs2))/2

    dup.location.z += nba2k_head_bot - new_bot
    dup.location.x += nba2k_head_cx  - new_cx
    bpy.context.view_layer.update()

    # 应用变换
    bpy.ops.object.select_all(action='DESELECT')
    dup.select_set(True)
    bpy.context.view_layer.objects.active = dup
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    final_zs = [v.co.z for v in dup.data.vertices]
    lines.append(f"  对齐后Z: {min(final_zs):.2f} ~ {max(final_zs):.2f}")
    lines.append(f"  缩放比例: {scale:.4f}")

    # ── 导出为 NBA2K 顶点格式 ────────────────────────────────────
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval  = dup.evaluated_get(depsgraph)
    mesh_eval = obj_eval.to_mesh()

    bm = bmesh.new()
    bm.from_mesh(mesh_eval)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(mesh_eval)
    bm.free()
    try: mesh_eval.calc_normals_split()
    except: pass

    uv_layer = mesh_eval.uv_layers.active
    has_uv   = uv_layer is not None

    positions=[]; normals=[]; uvs=[]; indices=[]
    vert_map={}
    for poly in mesh_eval.polygons:
        tri=[]
        for li in poly.loop_indices:
            loop = mesh_eval.loops[li]
            vi   = loop.vertex_index
            key  = (vi, li)
            if key not in vert_map:
                vert_map[key] = len(positions)
                v = mesh_eval.vertices[vi]
                px,py,pz = v.co.x, v.co.y, v.co.z
                positions.append((px, pz, -py))      # Z-up→Y-up
                nx,ny,nz = loop.normal.x,loop.normal.y,loop.normal.z
                normals.append((nx, nz, -ny))
                if has_uv:
                    uv = uv_layer.data[li].uv
                    uvs.append((uv[0], 1.0-uv[1]))
                else:
                    uvs.append((0.0,0.0))
            tri.append(vert_map[key])
        if len(tri)==3: indices.extend(tri)

    obj_eval.to_mesh_clear()

    n_verts = len(positions)
    n_tris  = len(indices)//3
    lines.append(f"\n展开后顶点: {n_verts}  三角面: {n_tris}")

    if n_verts > 65535:
        popup(f"顶点数{n_verts}超出65535！", title="错误", icon='ERROR'); return

    # Stream0 位置
    stream0 = bytearray()
    for px,py,pz in positions:
        stream0 += struct.pack('<fff', px, py, pz)

    # Stream1 法线+UV
    stream1 = bytearray()
    for i,(nx,ny,nz) in enumerate(normals):
        np_ = pack_normal(nx,ny,nz)
        u,v = uvs[i]
        stream1 += struct.pack('<IHHHHi',
            np_,
            pack_snorm16(u*2-1), pack_snorm16(v*2-1),
            pack_snorm16(u*2-1), pack_snorm16(v*2-1),
            0)

    # 骨骼权重（全绑头部骨骼0）
    weight_buf = bytearray()
    for _ in range(n_verts):
        weight_buf += struct.pack('BBBBBBBB',0,0,0,0,255,0,0,0)

    # 索引缓冲区
    idx_buf = bytearray()
    for idx in indices:
        idx_buf += struct.pack('<H', idx)

    lines.append(f"Stream0: {len(stream0)} B  Stream1: {len(stream1)} B")
    lines.append(f"Index:   {len(idx_buf)} B  Weights: {len(weight_buf)} B")

    # ── 打包回 IFF ────────────────────────────────────────────────
    if not os.path.exists(IFF_IN):
        popup(f"找不到原始IFF:\n{IFF_IN}", title="错误", icon='ERROR'); return

    with zipfile.ZipFile(IFF_IN,'r') as zin:
        names = zin.namelist()
        files = {n: zin.read(n) for n in names}

    lines.append(f"\n原始IFF文件数: {len(names)}")

    # 更新 SCNE
    scne_name = next((n for n in names if n.lower().endswith('.scne')), None)
    if scne_name:
        scne_text = files[scne_name].decode('utf-8', errors='replace')
        scne_text = re.sub(r'"vertexCount"\s*:\s*\d+', f'"vertexCount": {n_verts}', scne_text)
        scne_text = re.sub(r'"indexCount"\s*:\s*\d+',  f'"indexCount": {len(indices)}', scne_text)
        scne_text = re.sub(r'"primitiveCount"\s*:\s*\d+', f'"primitiveCount": {n_tris}', scne_text)
        ax=[p[0] for p in positions]; ay=[p[1] for p in positions]; az=[p[2] for p in positions]
        for k,val in [("minX",min(ax)),("maxX",max(ax)),("minY",min(ay)),("maxY",max(ay)),
                      ("minZ",min(az)),("maxZ",max(az))]:
            scne_text = re.sub(rf'"{k}"\s*:\s*[-\d.eE+]+', f'"{k}": {val:.6f}', scne_text)
        files[scne_name] = scne_text.encode('utf-8')
        lines.append(f"✔ 更新SCNE: {scne_name}")

    # 替换缓冲区（按大小排序）
    vb = sorted([(n,len(files[n])) for n in names if 'vertexbuffer' in n.lower()], key=lambda x:x[1])
    if len(vb)>=2:
        files[vb[0][0]] = bytes(stream0)
        files[vb[1][0]] = bytes(stream1)
        lines.append(f"✔ 替换Stream0: {vb[0][0]}")
        lines.append(f"✔ 替换Stream1: {vb[1][0]}")
    elif len(vb)==1:
        files[vb[0][0]] = bytes(stream0)

    ib = next((n for n in names if 'indexbuffer' in n.lower()), None)
    if ib: files[ib] = bytes(idx_buf); lines.append(f"✔ 替换IndexBuffer: {ib}")

    mw = next((n for n in names if 'matrixweights' in n.lower()), None)
    if mw: files[mw] = bytes(weight_buf); lines.append(f"✔ 替换MatrixWeights: {mw}")

    with zipfile.ZipFile(IFF_OUT,'w',zipfile.ZIP_DEFLATED) as zout:
        for n,data in files.items():
            zout.writestr(n, data)

    lines.append(f"\n✔ 输出: {IFF_OUT}")
    lines.append(f"  顶点: {n_verts}  面: {n_tris}")
    lines.append("\n✔ step9 执行成功")

    msg = "\n".join(lines)
    with open(OUT_TXT,"w",encoding="utf-8") as f: f.write(msg)

    popup(f"大黑塔脸部提取完成！\n顶点:{n_verts}  面:{n_tris}\n\n输出:\n{IFF_OUT}",
          title="第9步完成", icon='INFO')

main()
