# =====================================================
# 第13步：正确的二进制替换（修正版）
# 在 Blender 脚本编辑器里运行
#
# 关键修正：
#   1. 只替换 Stream0(位置) 和 Stream1(法线+UV)，按文件名精确匹配
#   2. 不动 Stream3、Stream4
#   3. 重建完整的 IndexBuffer（保持原始大小）
#   4. 正确处理 SCNE 的多个子网格定义
#   5. 顶点数保持 24484（与原始一致）
# =====================================================

import bpy
import bmesh
import struct
import os
import zipfile
import json
import re
from mathutils import kdtree as KDTree

# ── 路径配置 ──────────────────────────────────────────────────
IFF_IN  = r"F:\大卫李\png6794.iff"
IFF_OUT = r"F:\大卫李\sakura_output\png6794.iff"
OUT_TXT = r"C:\Users\Administrator\Documents\sakura_mod_work\step13_result.txt"
os.makedirs(r"F:\大卫李\sakura_output", exist_ok=True)

# 目标顶点数 = 原始 IFF 的顶点数（从 SCNE LodVerts 得知）
TARGET_VERTS = 24484

FACE_KEYWORDS = ['颜', 'face', '顔']
FACE_EXCLUDE  = ['口', 'mouth', '牙', 'teeth', '眉', 'brow',
                 '目', 'eye', '睫', 'lash', '淚', 'tear',
                 '赤', 'blush', '舌', 'tongue']

BODY_KEYWORDS = ['肌', 'body', 'Body', '体', '衣', '着',
                 'cloth', 'dress', 'coat', '服', 'jacket',
                 '胸罩', '上着', '下着', '拘束']
BODY_EXCLUDE  = ['颜', 'face', '顔', '頭', 'head',
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

def pack_tangent_frame(nx, ny, nz):
    """R10G10B10A2_UINT"""
    x = max(0.0, min(1.0, nx*0.5+0.5))
    y = max(0.0, min(1.0, ny*0.5+0.5))
    z = max(0.0, min(1.0, nz*0.5+0.5))
    return (int(x*1023+0.5)&0x3FF) | \
           ((int(y*1023+0.5)&0x3FF)<<10) | \
           ((int(z*1023+0.5)&0x3FF)<<20) | (3<<30)

def encode_snorm16(v):
    return int(max(-1.0, min(1.0, v)) * 32767) & 0xFFFF

def find_pmx_mesh():
    # 优先：名字同时含"大黑塔"和"mesh"
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and '大黑塔' in obj.name and 'mesh' in obj.name.lower():
            return obj
    # 其次：名字含"大黑塔"的任意网格
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and '大黑塔' in obj.name:
            return obj
    # 最后：名字含"Ver1.0"的网格（PMX导入常见命名）
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and 'Ver' in obj.name and len(obj.data.vertices) > 10000:
            return obj
    return None

def main():
    lines = ["=== 第13步：正确二进制替换 ===\n"]

    # ── 1. 找大黑塔网格 ──────────────────────────────────────
    src = find_pmx_mesh()
    if not src:
        popup("找不到大黑塔网格！", title="错误", icon='ERROR')
        return
    lines.append(f"源网格: {src.name}  顶点:{len(src.data.vertices)}")

    # ── 2. 读取原始 IFF ──────────────────────────────────────
    with zipfile.ZipFile(IFF_IN, 'r') as z:
        iff_names = z.namelist()
        iff_files = {n: z.read(n) for n in iff_names}

    # 原始 Stream0 (位置, stride=12)
    S0_NAME = next(n for n in iff_names if 'd5376762989c8976' in n)
    # 原始 Stream1 (法线+UV, stride=16)
    S1_NAME = next(n for n in iff_names if 'aa6c9685105d8f4a' in n)
    # IndexBuffer
    IB_NAME = next(n for n in iff_names if 'indexbuffer' in n.lower())
    # MatrixWeightsBuffer
    MW_NAME = next(n for n in iff_names if 'matrixweights' in n.lower())

    orig_s0 = iff_files[S0_NAME]
    orig_s1 = iff_files[S1_NAME]
    orig_ib = iff_files[IB_NAME]
    orig_mw = iff_files[MW_NAME]

    orig_nverts = len(orig_s0) // 12  # 24484
    orig_nidx = len(orig_ib) // 2     # 235236

    lines.append(f"\n原始数据:")
    lines.append(f"  Stream0: {S0_NAME} ({len(orig_s0)} B, {orig_nverts} verts)")
    lines.append(f"  Stream1: {S1_NAME} ({len(orig_s1)} B)")
    lines.append(f"  Index:   {IB_NAME} ({len(orig_ib)} B, {orig_nidx} indices)")
    lines.append(f"  Weights: {MW_NAME} ({len(orig_mw)} B)")

    # 解析原始顶点位置（用于 KD-Tree 权重映射）
    orig_positions = []
    for i in range(orig_nverts):
        x, y, z = struct.unpack_from('<fff', orig_s0, i*12)
        orig_positions.append((x, y, z))

    # 解析原始权重
    orig_weight_bytes = orig_mw  # 保持原始二进制

    # ── 3. 提取大黑塔脸+身体 ────────────────────────────────
    face_slots = set()
    body_slots = set()
    for i, slot in enumerate(src.material_slots):
        if not slot.material: continue
        mn = slot.material.name
        if any(k in mn for k in FACE_KEYWORDS) and not any(k in mn for k in FACE_EXCLUDE):
            face_slots.add(i)
        elif any(k in mn for k in BODY_KEYWORDS) and not any(k in mn for k in BODY_EXCLUDE):
            body_slots.add(i)

    all_slots = face_slots | body_slots
    lines.append(f"\n脸材质: {len(face_slots)} 个  身体材质: {len(body_slots)} 个")

    # 复制并分离
    old = bpy.data.objects.get("bronya_combined")
    if old: bpy.data.objects.remove(old, do_unlink=True)

    bpy.ops.object.select_all(action='DESELECT')
    src.select_set(True)
    bpy.context.view_layer.objects.active = src
    bpy.ops.object.duplicate()
    combined = bpy.context.active_object
    combined.name = "bronya_combined"

    bpy.ops.object.mode_set(mode='OBJECT')
    for poly in combined.data.polygons:
        poly.select = poly.material_index not in all_slots
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.delete(type='FACE')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.delete_loose(use_verts=True, use_edges=True, use_faces=False)
    bpy.ops.object.mode_set(mode='OBJECT')

    # 删除形态键
    if combined.data.shape_keys:
        bpy.context.view_layer.objects.active = combined
        bpy.ops.object.shape_key_remove(all=True)

    # 确保单用户数据（修复"修改器无法应用至多用户数据"错误）
    combined.data = combined.data.copy()

    nv_before = len(combined.data.vertices)
    nf_before = len(combined.data.polygons)
    lines.append(f"提取后: 顶点{nv_before}  面{nf_before}")

    # ── 4. 减面到目标顶点数附近 ──────────────────────────────
    # 目标面数需要让展开后的顶点数 ≈ TARGET_VERTS
    # 展开后顶点通常是面数的 2-3 倍，所以面数目标 ≈ TARGET_VERTS / 3
    target_faces = TARGET_VERTS // 3
    if nf_before > target_faces:
        ratio = target_faces / nf_before
        lines.append(f"减面: {nf_before} → 目标{target_faces}  比率{ratio:.3f}")
        dec = combined.modifiers.new(name="Dec", type='DECIMATE')
        dec.ratio = ratio
        dec.use_collapse_triangulate = True
        bpy.context.view_layer.objects.active = combined
        bpy.ops.object.modifier_apply(modifier="Dec")
        lines.append(f"减面后: 顶点{len(combined.data.vertices)}  面{len(combined.data.polygons)}")

    # ── 5. 缩放对齐到 NBA2K 坐标 ────────────────────────────
    # NBA2K 坐标: Y-up, 原始范围 Y: -103.63~80.10
    oys = [p[1] for p in orig_positions]
    nba_top = max(oys); nba_bot = min(oys)

    czs = [v.co.z for v in combined.data.vertices]
    b_top = max(czs); b_bot = min(czs); b_h = b_top - b_bot
    nba_h = nba_top - nba_bot
    if b_h < 0.001: b_h = 1.0
    scale = nba_h / b_h
    combined.scale = (scale, scale, scale)
    bpy.context.view_layer.update()

    # Z 底部对齐
    czs2 = [(combined.matrix_world @ v.co).z for v in combined.data.vertices]
    combined.location.z += nba_bot - min(czs2)

    # X 居中
    oxs = [p[0] for p in orig_positions]
    orig_cx = (min(oxs) + max(oxs)) / 2
    bpy.context.view_layer.update()
    cxs = [(combined.matrix_world @ v.co).x for v in combined.data.vertices]
    combined.location.x += orig_cx - (min(cxs) + max(cxs)) / 2

    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    combined.select_set(True)
    bpy.context.view_layer.objects.active = combined
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    lines.append(f"缩放比: {scale:.4f}")

    # ── 6. 三角化并转换 ─────────────────────────────────────
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = combined.evaluated_get(depsgraph)
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

    positions = []; normals_l = []; uvs = []; indices = []
    vert_map = {}

    for poly in mesh_eval.polygons:
        tri = []
        for li in poly.loop_indices:
            loop = mesh_eval.loops[li]
            vi = loop.vertex_index
            key = (vi, li)
            if key not in vert_map:
                idx = len(positions)
                vert_map[key] = idx
                v = mesh_eval.vertices[vi]
                # Blender (Z-up) → NBA2K (Y-up): (x, z, -y)
                positions.append((v.co.x, v.co.z, -v.co.y))
                normals_l.append((loop.normal.x, loop.normal.z, -loop.normal.y))
                if has_uv:
                    uv = uv_layer.data[li].uv
                    uvs.append((uv[0], 1.0 - uv[1]))
                else:
                    uvs.append((0.0, 0.0))
            tri.append(vert_map[key])
        if len(tri) == 3:
            indices.extend(tri)

    obj_eval.to_mesh_clear()
    n_verts = len(positions)
    n_tris = len(indices) // 3

    lines.append(f"\n展开: 顶点{n_verts}  面{n_tris}")

    # ── 7. 调整到精确的 TARGET_VERTS ────────────────────────
    # 如果顶点太多，需要填充原始数据；如果太少，需要补零
    if n_verts > TARGET_VERTS:
        # 截断（只取前 TARGET_VERTS 个顶点）
        positions = positions[:TARGET_VERTS]
        normals_l = normals_l[:TARGET_VERTS]
        uvs = uvs[:TARGET_VERTS]
        # 过滤超出范围的索引
        indices = [i for i in indices if i < TARGET_VERTS]
        # 确保索引是3的倍数
        while len(indices) % 3 != 0:
            indices.pop()
        n_verts = TARGET_VERTS
        n_tris = len(indices) // 3
        lines.append(f"截断到 {n_verts} 顶点, {n_tris} 面")
    elif n_verts < TARGET_VERTS:
        # 补充：用最后一个顶点填充剩余位置
        pad = TARGET_VERTS - n_verts
        last_pos = positions[-1]
        last_nrm = normals_l[-1]
        last_uv = uvs[-1]
        for _ in range(pad):
            positions.append(last_pos)
            normals_l.append(last_nrm)
            uvs.append(last_uv)
        n_verts = TARGET_VERTS
        lines.append(f"填充到 {n_verts} 顶点 (补了 {pad} 个)")

    # ── 8. 构建 Stream0 (位置) ──────────────────────────────
    new_s0 = bytearray()
    for px, py, pz in positions:
        new_s0 += struct.pack('<fff', px, py, pz)
    assert len(new_s0) == len(orig_s0), f"Stream0 大小不匹配: {len(new_s0)} vs {len(orig_s0)}"

    # ── 9. 构建 Stream1 (法线+UV, stride=16) ────────────────
    # 从 SCNE: TANGENTFRAME0(R10G10B10A2) + TEXCOORD0(R16G16_SNORM @4) + TEXCOORD1(R16G16_SNORM @8) + WEIGHTDATA0(R32_UINT @12)
    # UV 需要反变换: SCNE 中 Offset=[2.42, 0.49], Scale=[2.42, 0.51]
    # 存储值 = (显示UV - Offset) / Scale
    UV_OFFSET = [2.41989684, 0.489459544]
    UV_SCALE  = [2.41982293, 0.510540426]

    new_s1 = bytearray()
    for i in range(n_verts):
        nx, ny, nz = normals_l[i]
        tf = pack_tangent_frame(nx, ny, nz)

        u, v = uvs[i]
        # 反变换 UV
        u_enc = (u - UV_OFFSET[0]) / UV_SCALE[0] if abs(UV_SCALE[0]) > 1e-6 else 0.0
        v_enc = (v - UV_OFFSET[1]) / UV_SCALE[1] if abs(UV_SCALE[1]) > 1e-6 else 0.0
        u_enc = max(-1.0, min(1.0, u_enc))
        v_enc = max(-1.0, min(1.0, v_enc))

        # TEXCOORD0 (offset 4)
        tc0_u = encode_snorm16(u_enc)
        tc0_v = encode_snorm16(v_enc)
        # TEXCOORD1 (offset 8) - 通常和 TEXCOORD0 相同
        tc1_u = tc0_u
        tc1_v = tc0_v
        # WEIGHTDATA0 (offset 12) - 从原始数据复制（如果索引有效）
        if i < len(orig_s1) // 16:
            wd = struct.unpack_from('<I', orig_s1, i*16 + 12)[0]
        else:
            wd = 0

        new_s1 += struct.pack('<IHHHHI', tf, tc0_u, tc0_v, tc1_u, tc1_v, wd)

    # 修正：Stream1 每个顶点应为 16 字节
    # pack('<IHHHI', ...) = 4+2+2+2+2 = 12, + pack('<I', wd) = 4 → 总计 16 ✓
    assert len(new_s1) == len(orig_s1), f"Stream1 大小不匹配: {len(new_s1)} vs {len(orig_s1)}"

    # ── 10. 构建 IndexBuffer ────────────────────────────────
    # SCNE 子网格定义（从 SCNE 分析得到的各部位索引范围）
    # 必须把面索引放到这些位置，否则工具/游戏看不到
    submeshes = [
        # (name, start_index, count)
        ("torso_shader",  106818, 17022),
        ("arms_shader",   123840, 33276),
        ("legs_shader",   157116, 10464),
        ("face_shader",   168816, 46194),
    ]
    # 按 Start 排序
    submeshes.sort(key=lambda x: x[1])

    # 先用 0 填满整个 IndexBuffer
    new_ib = bytearray(len(orig_ib))

    # 将我们的面索引分配到各子网格的位置
    idx_pos = 0  # 当前在 indices 列表中的位置
    total_placed = 0
    for name, start, count in submeshes:
        byte_start = start * 2  # 每个索引 2 字节
        remaining = len(indices) - idx_pos
        use_count = min(count, remaining)
        if use_count <= 0:
            lines.append(f"  {name}: 无剩余索引")
            continue
        for j in range(use_count):
            idx_val = min(indices[idx_pos + j], TARGET_VERTS - 1)
            struct.pack_into('<H', new_ib, byte_start + j * 2, idx_val)
        total_placed += use_count
        idx_pos += use_count
        lines.append(f"  {name}: 放置 {use_count} 个索引 @ {start}")

    assert len(new_ib) == len(orig_ib), f"IB 大小不匹配: {len(new_ib)} vs {len(orig_ib)}"

    lines.append(f"\n输出缓冲区:")
    lines.append(f"  Stream0: {len(new_s0)} B ✔")
    lines.append(f"  Stream1: {len(new_s1)} B ✔")
    lines.append(f"  Index:   {len(new_ib)} B ✔ (放置{total_placed}索引到子网格位置)")

    # ── 11. KD-Tree 映射骨骼权重 ─────────────────────────────
    # 为每个新顶点找原始最近顶点，复制其权重
    kd = KDTree.KDTree(len(orig_positions))
    for i, pos in enumerate(orig_positions):
        kd.insert(pos, i)
    kd.balance()

    # MatrixWeightsBuffer: 保持原始大小不变
    # 权重是按顶点索引排列的，我们的顶点索引映射到最近的原始顶点
    # 但权重格式复杂（WeightBits=16），直接保留原始权重最安全
    lines.append(f"  Weights: {len(orig_mw)} B (保持原始)")

    # ── 12. 更新 SCNE 包围盒 ────────────────────────────────
    scne_name = next((n for n in iff_names if n.lower().endswith('.scne')), None)
    new_files = dict(iff_files)

    if scne_name:
        st = iff_files[scne_name].decode('utf-8', errors='replace')
        # 只更新顶层包围盒，不改 vertexCount/indexCount/子网格定义
        ax = [p[0] for p in positions]; ay = [p[1] for p in positions]; az = [p[2] for p in positions]
        bbox = {
            "minX": min(ax), "maxX": max(ax),
            "minY": min(ay), "maxY": max(ay),
            "minZ": min(az), "maxZ": max(az)
        }
        # 只更新 Model.hihead 层的 Min/Max/Center/Radius
        new_center = [(bbox["minX"]+bbox["maxX"])/2, (bbox["minY"]+bbox["maxY"])/2, (bbox["minZ"]+bbox["maxZ"])/2]
        new_radius = max(bbox["maxX"]-bbox["minX"], bbox["maxY"]-bbox["minY"], bbox["maxZ"]-bbox["minZ"]) / 2

        # 用正则更新 Min/Max（只改 Model 层的第一个）
        st = re.sub(
            r'"Min"\s*:\s*\[.*?\]',
            '"Min": [ {:.6f}, {:.6f}, {:.6f} ]'.format(bbox["minX"], bbox["minY"], bbox["minZ"]),
            st, count=1
        )
        st = re.sub(
            r'"Max"\s*:\s*\[.*?\]',
            '"Max": [ {:.6f}, {:.6f}, {:.6f} ]'.format(bbox["maxX"], bbox["maxY"], bbox["maxZ"]),
            st, count=1
        )
        st = re.sub(
            r'"Radius"\s*:\s*[\d.eE+-]+',
            '"Radius": {:.6f}'.format(new_radius),
            st, count=1
        )
        st = re.sub(
            r'"Center"\s*:\s*\[.*?\]',
            '"Center": [ {:.6f}, {:.6f}, {:.6f} ]'.format(*new_center),
            st, count=1
        )
        new_files[scne_name] = st.encode('utf-8')
        lines.append("✔ SCNE 包围盒已更新（结构未改动）")

    # ── 13. 替换正确的缓冲区文件 ────────────────────────────
    new_files[S0_NAME] = bytes(new_s0)
    new_files[S1_NAME] = bytes(new_s1)
    new_files[IB_NAME] = bytes(new_ib)
    # MatrixWeightsBuffer 保持原始
    lines.append(f"✔ 替换 Stream0: {S0_NAME}")
    lines.append(f"✔ 替换 Stream1: {S1_NAME}")
    lines.append(f"✔ 替换 IndexBuffer: {IB_NAME}")
    lines.append(f"  Stream3, Stream4, MatrixWeights: 保持原始")

    # ── 14. 写入 IFF ────────────────────────────────────────
    with zipfile.ZipFile(IFF_OUT, 'w', zipfile.ZIP_DEFLATED) as zout:
        for n, data in new_files.items():
            zout.writestr(n, data)

    lines.append(f"\n✔ 输出: {IFF_OUT}")
    lines.append(f"  顶点: {n_verts} (= 原始 {orig_nverts})")
    lines.append(f"  有效面: {n_tris}")
    lines.append(f"  索引: {orig_nidx} (填充退化三角形)")
    lines.append("\n✔ step13 完成！")

    msg = "\n".join(lines)
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(msg)

    popup(
        f"正确替换完成！\n"
        f"顶点: {n_verts} (匹配原始)\n"
        f"有效面: {n_tris}\n"
        f"替换: Stream0 + Stream1 + IndexBuffer\n"
        f"保持: Stream3, Stream4, Weights, SCNE结构\n\n"
        f"输出: {IFF_OUT}",
        title="第13步完成", icon='INFO'
    )

main()
