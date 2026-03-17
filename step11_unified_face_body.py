# =====================================================
# 第11步（统一版）：脸 + 身体从同一缩放模型提取
# 在 Blender 脚本编辑器里运行
#
# 解决问题：step9 和 step10 分别缩放导致脸和身体错位
# 方案：先统一缩放整个大黑塔，再分别提取脸/身体
# =====================================================

import bpy
import bmesh
import struct
import os
import zipfile
import re
from mathutils import kdtree as KDTree

# ── 路径配置 ──────────────────────────────────────────────────
IFF_IN  = r"F:\大卫李\png6794.iff"
IFF_OUT = r"F:\大卫李\sakura_output\png6794.iff"
OUT_TXT = r"C:\Users\Administrator\Documents\sakura_mod_work\step11_result.txt"
os.makedirs(r"F:\大卫李\sakura_output", exist_ok=True)

TARGET_FACES_BODY = 15000
TARGET_FACES_FACE = 5000

# ── 材质分类 ──────────────────────────────────────────────────
FACE_KEYWORDS = ['颜', 'face', '顔', 'skin', 'head']
FACE_EXCLUDE  = ['口', 'mouth', '牙', 'teeth', '眉', 'brow',
                 '目', 'eye', '睫', 'lash', '淚', 'tear',
                 '赤', 'blush', '舌', 'tongue', '翼', 'wing',
                 '髪', 'hair', '帽', 'hat']

BODY_KEYWORDS = ['肌', 'skin', 'body', 'Body', '体', '衣', '着',
                 'cloth', 'dress', 'coat', 'shirt', 'pants',
                 '上着', '下着', '服', 'suit', 'jacket',
                 'torso', 'arm', 'leg', 'hand', 'foot',
                 '腕', '足', '手', '胸', '腹', '脚']
BODY_EXCLUDE  = ['颜', 'face', '顔', '头', 'head',
                 '髪', 'hair', '帽', 'hat',
                 '目', 'eye', '眉', 'brow', '口', 'mouth',
                 '睫', 'lash', '淚', 'tear', '赤', 'blush',
                 '牙', 'teeth', '舌', 'tongue', '翼', 'wing']

def popup(msg, title="提示", icon='INFO'):
    ls = msg.split('\n')
    def draw(self, context):
        for l in ls:
            self.layout.label(text=l)
    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

def pack_normal(nx, ny, nz):
    x = max(0.0, min(1.0, nx*0.5+0.5))
    y = max(0.0, min(1.0, ny*0.5+0.5))
    z = max(0.0, min(1.0, nz*0.5+0.5))
    return (int(x*1023+0.5)&0x3FF) | \
           ((int(y*1023+0.5)&0x3FF)<<10) | \
           ((int(z*1023+0.5)&0x3FF)<<20) | (3<<30)

def pack_snorm16(v):
    return int(max(-1.0, min(1.0, v)) * 32767) & 0xFFFF

def find_pmx_mesh():
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and '大黑塔' in obj.name and 'mesh' in obj.name.lower():
            return obj
    meshes = [o for o in bpy.context.scene.objects
              if o.type == 'MESH' and len(o.data.vertices) > 50000]
    return max(meshes, key=lambda o: len(o.data.vertices)) if meshes else None

def extract_part(src, slot_indices, part_name, target_faces, lines):
    """从 src 提取指定材质槽的面，减面后返回新对象"""
    old = bpy.data.objects.get(part_name)
    if old: bpy.data.objects.remove(old, do_unlink=True)

    bpy.ops.object.select_all(action='DESELECT')
    src.select_set(True)
    bpy.context.view_layer.objects.active = src
    bpy.ops.object.duplicate()
    dup = bpy.context.active_object
    dup.name = part_name + "_tmp"

    # 删除非目标面
    bpy.ops.object.mode_set(mode='OBJECT')
    for poly in dup.data.polygons:
        poly.select = poly.material_index not in slot_indices
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.delete(type='FACE')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.delete_loose(use_verts=True, use_edges=True, use_faces=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    dup.name = part_name

    nv = len(dup.data.vertices)
    nf = len(dup.data.polygons)
    lines.append(f"\n{part_name}: 顶点{nv}  面{nf}")

    if nv == 0:
        return dup

    # 删除形态键
    if dup.data.shape_keys:
        bpy.context.view_layer.objects.active = dup
        bpy.ops.object.shape_key_remove(all=True)
        lines.append(f"  ✔ 删除形态键")

    # 减面
    if nf > target_faces:
        ratio = target_faces / nf
        lines.append(f"  减面: {nf} → 目标{target_faces}  比率{ratio:.3f}")
        dec = dup.modifiers.new(name="Decimate", type='DECIMATE')
        dec.ratio = ratio
        dec.use_collapse_triangulate = True
        bpy.context.view_layer.objects.active = dup
        bpy.ops.object.modifier_apply(modifier="Decimate")
        lines.append(f"  减面后: 顶点{len(dup.data.vertices)}  面{len(dup.data.polygons)}")

    return dup

def mesh_to_nba2k(obj, lines):
    """把 Blender 对象转换为 NBA2K 二进制格式
    返回: (positions, normals, uvs, indices, vi_map)
    positions 已经是 NBA2K 坐标 (x, z, -y)"""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)
    mesh_eval = obj_eval.to_mesh()

    bm = bmesh.new()
    bm.from_mesh(mesh_eval)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(mesh_eval)
    bm.free()
    try: mesh_eval.calc_normals_split()
    except: pass

    uv_layer = mesh_eval.uv_layers.active
    has_uv = uv_layer is not None

    positions = []; normals_out = []; uvs = []; indices = []
    vert_map = {}; vi_map = {}

    for poly in mesh_eval.polygons:
        tri = []
        for li in poly.loop_indices:
            loop = mesh_eval.loops[li]
            vi = loop.vertex_index
            key = (vi, li)
            if key not in vert_map:
                out_idx = len(positions)
                vert_map[key] = out_idx
                vi_map[out_idx] = vi
                v = mesh_eval.vertices[vi]
                positions.append((v.co.x, v.co.z, -v.co.y))
                normals_out.append((loop.normal.x, loop.normal.z, -loop.normal.y))
                if has_uv:
                    uv = uv_layer.data[li].uv
                    uvs.append((uv[0], 1.0 - uv[1]))
                else:
                    uvs.append((0.0, 0.0))
            tri.append(vert_map[key])
        if len(tri) == 3:
            indices.extend(tri)

    obj_eval.to_mesh_clear()
    return positions, normals_out, uvs, indices, vi_map

def pack_buffers(positions, normals_out, uvs, indices, weight_data):
    """打包成 NBA2K 二进制缓冲区"""
    stream0 = bytearray()
    for px, py, pz in positions:
        stream0 += struct.pack('<fff', px, py, pz)

    stream1 = bytearray()
    for i, (nx, ny, nz) in enumerate(normals_out):
        np_ = pack_normal(nx, ny, nz)
        u, v = uvs[i]
        stream1 += struct.pack('<IHHHHi',
            np_,
            pack_snorm16(u*2-1), pack_snorm16(v*2-1),
            pack_snorm16(u*2-1), pack_snorm16(v*2-1),
            0)

    weight_buf = bytearray()
    for bw in weight_data:
        weight_buf += struct.pack('BBBBBBBB', *bw)

    idx_buf = bytearray()
    for idx in indices:
        idx_buf += struct.pack('<H', idx)

    return stream0, stream1, idx_buf, weight_buf

# ────────────────────────────────────────────────────────────────
def main():
    lines = ["=== 第11步：统一缩放 + 脸/身体提取 ===\n"]

    # ── 1. 找大黑塔网格 ──────────────────────────────────────
    src = find_pmx_mesh()
    if not src:
        popup("找不到大黑塔网格！\n请先运行step1", title="错误", icon='ERROR')
        return
    lines.append(f"大黑塔: {src.name}  顶点:{len(src.data.vertices)}")

    # ── 2. 读取原始 IFF 的坐标范围和骨骼权重 ────────────────
    with zipfile.ZipFile(IFF_IN, 'r') as zin:
        iff_names = zin.namelist()
        iff_files = {n: zin.read(n) for n in iff_names}

    # 找 VB 配对
    vb_files = sorted([(n, len(iff_files[n])) for n in iff_names if 'vertexbuffer' in n.lower()],
                      key=lambda x: x[1], reverse=True)
    mw_files = [(n, len(iff_files[n])) for n in iff_names if 'matrixweights' in n.lower()]

    # 找 stride=12 的 position stream
    stream0_name = None
    orig_nverts = 0
    for n, sz in vb_files:
        if sz % 12 == 0:
            nv = sz // 12
            expected_s1 = nv * 16
            for n2, sz2 in vb_files:
                if n2 != n and sz2 == expected_s1:
                    stream0_name = n
                    orig_nverts = nv
                    break
            if stream0_name:
                break

    if not stream0_name:
        for n, sz in vb_files:
            if sz % 12 == 0 and sz > 50000:
                stream0_name = n
                orig_nverts = sz // 12
                break

    # 解析原始顶点位置 (NBA2K 空间: x, y_up, z)
    s0_data = iff_files[stream0_name]
    orig_positions = []
    for i in range(orig_nverts):
        x, y, z = struct.unpack_from('<fff', s0_data, i * 12)
        orig_positions.append((x, y, z))

    oys = [p[1] for p in orig_positions]  # Y = up in NBA2K
    orig_top = max(oys)
    orig_bot = min(oys)
    lines.append(f"\n原始NBA2K身体: {orig_nverts} 顶点")
    lines.append(f"  Y范围(高度): {orig_bot:.2f} ~ {orig_top:.2f}")

    # 解析原始骨骼权重
    mw_data = iff_files[mw_files[0][0]] if mw_files else b""
    mw_nverts = len(mw_data) // 8
    orig_weights = []
    for i in range(mw_nverts):
        orig_weights.append(struct.unpack_from('BBBBBBBB', mw_data, i * 8))

    # 建 KD-Tree
    kd = KDTree.KDTree(len(orig_positions))
    for i, pos in enumerate(orig_positions):
        kd.insert(pos, i)
    kd.balance()

    # ── 3. 统一缩放大黑塔 ───────────────────────────────────
    # 大黑塔在 Blender (Z-up): 脚在最低Z，头在最高Z
    # NBA2K (Y-up): 脚在最低Y，头在最高Y
    # 目标：大黑塔 Blender Z 范围 = NBA2K Y 范围

    src_zs = [v.co.z for v in src.data.vertices]
    src_top = max(src_zs)
    src_bot = min(src_zs)
    src_h = src_top - src_bot
    nba_h = orig_top - orig_bot
    if src_h < 0.001: src_h = 1.0
    scale = nba_h / src_h
    lines.append(f"\n大黑塔Z: {src_bot:.2f} ~ {src_top:.2f}  高度: {src_h:.2f}")
    lines.append(f"NBA2K高度: {nba_h:.2f}")
    lines.append(f"统一缩放比: {scale:.4f}")

    # 创建缩放后的副本
    old_scaled = bpy.data.objects.get("bronya_scaled")
    if old_scaled: bpy.data.objects.remove(old_scaled, do_unlink=True)

    bpy.ops.object.select_all(action='DESELECT')
    src.select_set(True)
    bpy.context.view_layer.objects.active = src
    bpy.ops.object.duplicate()
    scaled = bpy.context.active_object
    scaled.name = "bronya_scaled"

    scaled.scale = (scale, scale, scale)
    bpy.context.view_layer.update()

    # Z 底部对齐 NBA2K 底部
    scaled_zs = [(scaled.matrix_world @ v.co).z for v in scaled.data.vertices]
    scaled.location.z += orig_bot - min(scaled_zs)

    # X 居中
    orig_xs = [p[0] for p in orig_positions]
    orig_cx = (min(orig_xs) + max(orig_xs)) / 2
    bpy.context.view_layer.update()
    scaled_xs = [(scaled.matrix_world @ v.co).x for v in scaled.data.vertices]
    scaled.location.x += orig_cx - (min(scaled_xs) + max(scaled_xs)) / 2

    # Y 居中 (对应 NBA2K Z)
    orig_zs_nba = [p[2] for p in orig_positions]
    orig_cz = (min(orig_zs_nba) + max(orig_zs_nba)) / 2
    bpy.context.view_layer.update()
    scaled_ys = [(scaled.matrix_world @ v.co).y for v in scaled.data.vertices]
    scaled.location.y += -orig_cz - (min(scaled_ys) + max(scaled_ys)) / 2
    # 注意: Blender Y → NBA2K -Z，所以 NBA2K Z 对应 Blender -Y

    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    scaled.select_set(True)
    bpy.context.view_layer.objects.active = scaled
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    final_zs = [v.co.z for v in scaled.data.vertices]
    lines.append(f"缩放后Z: {min(final_zs):.2f} ~ {max(final_zs):.2f}")

    # ── 4. 识别材质槽 ───────────────────────────────────────
    face_slots = set()
    body_slots = set()
    lines.append("\n材质分类:")
    for i, slot in enumerate(scaled.material_slots):
        if not slot.material: continue
        mname = slot.material.name
        is_face = any(k in mname for k in FACE_KEYWORDS) and not any(k in mname for k in FACE_EXCLUDE)
        is_body = any(k in mname for k in BODY_KEYWORDS) and not any(k in mname for k in BODY_EXCLUDE)
        if is_face:
            face_slots.add(i)
            lines.append(f"  脸: [{i}] {mname}")
        elif is_body:
            body_slots.add(i)
            lines.append(f"  体: [{i}] {mname}")
        else:
            lines.append(f"  跳: [{i}] {mname}")

    if not face_slots:
        lines.append("⚠ 未识别脸部材质！")
    if not body_slots:
        lines.append("⚠ 未识别身体材质！")

    # ── 5. 提取脸部 ──────────────────────────────────────────
    if face_slots:
        face_obj = extract_part(scaled, face_slots, "bronya_face", TARGET_FACES_FACE, lines)
        face_pos, face_nrm, face_uv, face_idx, face_vimap = mesh_to_nba2k(face_obj, lines)
        n_face = len(face_pos)
        lines.append(f"脸部展开: 顶点{n_face}  面{len(face_idx)//3}")

        # 映射脸部骨骼权重
        face_weights = []
        for px, py, pz in face_pos:
            co, idx, dist = kd.find((px, py, pz))
            if idx < len(orig_weights):
                face_weights.append(orig_weights[idx])
            else:
                face_weights.append((0,0,0,0,255,0,0,0))

        face_s0, face_s1, face_ib, face_wb = pack_buffers(
            face_pos, face_nrm, face_uv, face_idx, face_weights)
        lines.append(f"脸部缓冲区: S0={len(face_s0)} S1={len(face_s1)} IB={len(face_ib)} W={len(face_wb)}")
    else:
        face_pos = []; face_idx = []

    # ── 6. 提取身体 ──────────────────────────────────────────
    if body_slots:
        body_obj = extract_part(scaled, body_slots, "bronya_body2", TARGET_FACES_BODY, lines)
        body_pos, body_nrm, body_uv, body_idx, body_vimap = mesh_to_nba2k(body_obj, lines)
        n_body = len(body_pos)
        lines.append(f"身体展开: 顶点{n_body}  面{len(body_idx)//3}")

        # 映射身体骨骼权重
        body_weights = []
        for px, py, pz in body_pos:
            co, idx, dist = kd.find((px, py, pz))
            if idx < len(orig_weights):
                body_weights.append(orig_weights[idx])
            else:
                body_weights.append((0,0,0,0,255,0,0,0))

        body_s0, body_s1, body_ib, body_wb = pack_buffers(
            body_pos, body_nrm, body_uv, body_idx, body_weights)
        lines.append(f"身体缓冲区: S0={len(body_s0)} S1={len(body_s1)} IB={len(body_ib)} W={len(body_wb)}")
    else:
        body_pos = []; body_idx = []

    # ── 7. 合并脸+身体写入 IFF ──────────────────────────────
    # 使用身体数据作为主体（最大的VB），脸部覆盖次大的VB
    # （因为 NBA2K IFF 里最大VB=身体，次大VB=脸部）
    lines.append(f"\n--- 打包 IFF ---")

    with zipfile.ZipFile(IFF_IN, 'r') as zin:
        out_names = zin.namelist()
        out_files = {n: zin.read(n) for n in out_names}

    out_vb = sorted([(n, len(out_files[n])) for n in out_names if 'vertexbuffer' in n.lower()],
                    key=lambda x: x[1], reverse=True)
    out_ib = next((n for n in out_names if 'indexbuffer' in n.lower()), None)
    out_mw = next((n for n in out_names if 'matrixweights' in n.lower()), None)

    lines.append("原始VB:")
    for n, sz in out_vb:
        lines.append(f"  {n}  ({sz} B)")

    if body_pos and face_pos:
        # 身体 = 最大两个 VB, 脸部需要合并到身体里
        # 或者：把脸+身体合并成一个网格
        # NBA2K 的 IFF 可能只有一组 VB 用于整个模型
        # 最安全：合并脸+身体为一个网格

        all_pos = body_pos + face_pos
        all_nrm = body_nrm + face_nrm
        all_uv  = body_uv + face_uv
        # 脸部索引需要偏移
        offset = len(body_pos)
        all_idx = body_idx + [i + offset for i in face_idx]
        all_weights = body_weights + face_weights

        n_total = len(all_pos)
        n_tris  = len(all_idx) // 3
        lines.append(f"\n合并: 顶点{n_total}  面{n_tris}")

        if n_total > 65535:
            lines.append(f"⚠ 合并顶点{n_total} > 65535! 尝试只用身体...")
            all_pos = body_pos; all_nrm = body_nrm; all_uv = body_uv
            all_idx = body_idx; all_weights = body_weights
            n_total = len(all_pos); n_tris = len(all_idx) // 3

        s0, s1, ib, wb = pack_buffers(all_pos, all_nrm, all_uv, all_idx, all_weights)

    elif body_pos:
        all_pos = body_pos; all_idx = body_idx
        n_total = len(all_pos); n_tris = len(all_idx) // 3
        s0, s1, ib, wb = body_s0, body_s1, body_ib, body_wb
    elif face_pos:
        all_pos = face_pos; all_idx = face_idx
        n_total = len(all_pos); n_tris = len(all_idx) // 3
        s0, s1, ib, wb = face_s0, face_s1, face_ib, face_wb
    else:
        popup("脸和身体都为空！", title="错误", icon='ERROR')
        return

    # 替换最大两个 VB
    if len(out_vb) >= 2:
        out_files[out_vb[0][0]] = bytes(s1)   # 最大 → Stream1
        out_files[out_vb[1][0]] = bytes(s0)   # 次大 → Stream0
        lines.append(f"✔ 替换 Stream1: {out_vb[0][0]}")
        lines.append(f"✔ 替换 Stream0: {out_vb[1][0]}")

    if out_ib:
        out_files[out_ib] = bytes(ib)
        lines.append(f"✔ 替换 IndexBuffer")
    if out_mw:
        out_files[out_mw] = bytes(wb)
        lines.append(f"✔ 替换 MatrixWeights")

    # 更新 SCNE
    scne_name = next((n for n in out_names if n.lower().endswith('.scne')), None)
    if scne_name:
        st = out_files[scne_name].decode('utf-8', errors='replace')
        st = re.sub(r'"vertexCount"\s*:\s*\d+',    f'"vertexCount": {n_total}', st)
        st = re.sub(r'"indexCount"\s*:\s*\d+',      f'"indexCount": {len(all_idx)}', st)
        st = re.sub(r'"primitiveCount"\s*:\s*\d+',  f'"primitiveCount": {n_tris}', st)
        ax=[p[0] for p in all_pos]; ay=[p[1] for p in all_pos]; az=[p[2] for p in all_pos]
        for k, val in [("minX",min(ax)),("maxX",max(ax)),("minY",min(ay)),
                       ("maxY",max(ay)),("minZ",min(az)),("maxZ",max(az))]:
            st = re.sub(rf'"{k}"\s*:\s*[-\d.eE+]+', f'"{k}": {val:.6f}', st)
        out_files[scne_name] = st.encode('utf-8')
        lines.append(f"✔ SCNE 已更新")

    with zipfile.ZipFile(IFF_OUT, 'w', zipfile.ZIP_DEFLATED) as zout:
        for n, data in out_files.items():
            zout.writestr(n, data)

    lines.append(f"\n✔ 输出: {IFF_OUT}")
    lines.append(f"  总顶点: {n_total}  总面: {n_tris}")
    lines.append(f"  脸: {len(face_pos)} 顶点  身体: {len(body_pos)} 顶点")
    lines.append("\n✔ step11 完成！脸和身体使用统一缩放，位置对齐")

    msg = "\n".join(lines)
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(msg)

    # 清理临时对象
    for name in ["bronya_scaled"]:
        tmp = bpy.data.objects.get(name)
        if tmp: bpy.data.objects.remove(tmp, do_unlink=True)

    popup(
        f"统一替换完成！\n"
        f"脸: {len(face_pos)} 顶点\n"
        f"身体: {len(body_pos)} 顶点\n"
        f"合计: {n_total} 顶点  {n_tris} 面\n\n"
        f"输出: {IFF_OUT}",
        title="第11步完成", icon='INFO'
    )

main()
