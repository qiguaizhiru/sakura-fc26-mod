# =====================================================
# 第10步：从大黑塔 PMX 提取身体网格，打包进 NBA2K IFF
# 在 Blender 脚本编辑器里运行
#
# 前提：场景里有大黑塔Ver1.0_mesh（运行step1导入PMX）
# 本脚本提取：皮肤 + 衣服 + 头部以外的所有主体材质
# =====================================================

import bpy
import bmesh
import struct
import os
import zipfile
import re

# ── 路径配置 ────────────────────────────────────────────────────
IFF_IN  = r"F:\大卫李\png6794.iff"                   # 原始主文件（或step9输出）
IFF_OUT = r"F:\大卫李\sakura_output\png6794.iff"     # 输出（会覆盖step9的输出）
OUT_TXT = r"C:\Users\Administrator\Documents\sakura_mod_work\step10_result.txt"

os.makedirs(r"F:\大卫李\sakura_output", exist_ok=True)

# ── 材质关键词配置 ───────────────────────────────────────────────
# 身体材质（皮肤 + 衣服等所有主体部分，不含头部/发型/配件）
BODY_KEYWORDS = [
    '肌', 'skin', 'body', 'Body', '体',
    '衣', '着', 'cloth', 'dress', 'coat', 'shirt', 'pants',
    '上着', '下着', '服', 'suit', 'jacket',
    'torso', 'chest', 'arm', 'leg', 'hand', 'foot',
    '腕', '足', '手', '胸', '腹', '脚',
]
# 排除头部、发型、配件（这些单独处理）
BODY_EXCLUDE = [
    '颜', 'face', '顔', '头', 'head',
    '髪', 'hair', '帽', 'hat', 'cap',
    '目', 'eye', '眉', 'brow', '口', 'mouth',
    '睫', 'lash', '淚', 'tear', '赤', 'blush',
    '牙', 'teeth', '舌', 'tongue',
    '翼', 'wing',
]

# ── NBA2K 身体坐标参考 ───────────────────────────────────────────
# 从 step9 知道头顶≈83.11，头底≈61.78（NBA2K游戏坐标单位）
# 完整身体：头顶83.11 → 脚底0.0（篮球运动员约200cm）
NBA2K_BODY_TOP = 83.11   # 头顶（与脸部脚本保持一致）
NBA2K_BODY_BOT = 0.0     # 脚底（地面=0）

# ── 辅助函数 ────────────────────────────────────────────────────
def popup(msg, title="提示", icon='INFO'):
    lines = msg.split('\n')
    def draw(self, context):
        for line in lines:
            self.layout.label(text=line)
    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

def pack_normal(nx, ny, nz):
    """法线压缩：float3 → R10G10B10A2_UNORM"""
    x = max(0.0, min(1.0, nx * 0.5 + 0.5))
    y = max(0.0, min(1.0, ny * 0.5 + 0.5))
    z = max(0.0, min(1.0, nz * 0.5 + 0.5))
    return (int(x*1023+0.5)&0x3FF) | \
           ((int(y*1023+0.5)&0x3FF)<<10) | \
           ((int(z*1023+0.5)&0x3FF)<<20) | (3<<30)

def pack_snorm16(v):
    """UV压缩：float → R16_SNORM"""
    return int(max(-1.0, min(1.0, v)) * 32767) & 0xFFFF

# ── 主流程 ──────────────────────────────────────────────────────
def main():
    lines = ["=== 第10步：提取大黑塔身体 → NBA2K ===\n"]

    # ── 1. 找大黑塔主网格 ─────────────────────────────────────
    src = None
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and '大黑塔' in obj.name and 'mesh' in obj.name.lower():
            src = obj; break
    if not src:
        # 备用：找顶点数最多的网格
        meshes = [o for o in bpy.context.scene.objects
                  if o.type == 'MESH' and len(o.data.vertices) > 50000]
        src = max(meshes, key=lambda o: len(o.data.vertices)) if meshes else None
    if not src:
        popup("找不到大黑塔网格！\n请先运行step1导入PMX", title="错误", icon='ERROR')
        return

    lines.append(f"源网格: {src.name}  顶点:{len(src.data.vertices)}")

    # ── 2. 识别身体材质槽 ──────────────────────────────────────
    body_slots = []
    lines.append("\n所有材质槽:")
    for i, slot in enumerate(src.material_slots):
        if not slot.material: continue
        mname = slot.material.name
        is_body = any(k in mname for k in BODY_KEYWORDS)
        is_excl = any(k in mname for k in BODY_EXCLUDE)
        tag = ""
        if is_body and not is_excl:
            body_slots.append((i, mname))
            tag = "  ← 身体"
        lines.append(f"  [{i}] {mname}{tag}")

    lines.append(f"\n识别为身体的材质槽 ({len(body_slots)} 个):")
    for i, mn in body_slots:
        lines.append(f"  [{i}] {mn}")

    if not body_slots:
        # 如果自动识别失败，取除头部/发型以外的所有材质
        lines.append("\n⚠ 自动识别失败，改用排除法（剔除头/发，保留其余）")
        for i, slot in enumerate(src.material_slots):
            if not slot.material: continue
            mname = slot.material.name
            is_excl = any(k in mname for k in BODY_EXCLUDE)
            if not is_excl:
                body_slots.append((i, mname))
                lines.append(f"  [{i}] {mname}")

    if not body_slots:
        with open(OUT_TXT, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        popup("仍未找到身体材质！\n查看step10_result.txt", title="错误", icon='ERROR')
        return

    face_indices = {i for i, _ in body_slots}

    # ── 3. 复制并分离身体 ──────────────────────────────────────
    # 先删除可能存在的旧对象
    old = bpy.data.objects.get("bronya_body")
    if old:
        bpy.data.objects.remove(old, do_unlink=True)

    bpy.ops.object.select_all(action='DESELECT')
    src.select_set(True)
    bpy.context.view_layer.objects.active = src
    bpy.ops.object.duplicate()
    dup = bpy.context.active_object
    dup.name = "bronya_body_tmp"

    bpy.ops.object.mode_set(mode='OBJECT')
    for poly in dup.data.polygons:
        poly.select = poly.material_index in face_indices
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='INVERT')
    bpy.ops.mesh.delete(type='FACE')
    bpy.ops.object.mode_set(mode='OBJECT')

    dup.name = "bronya_body"
    lines.append(f"\n身体对象: bronya_body")
    lines.append(f"  顶点: {len(dup.data.vertices)}  面: {len(dup.data.polygons)}")

    if len(dup.data.vertices) == 0:
        popup("提取的身体顶点为0！\n请检查材质关键词配置", title="错误", icon='ERROR')
        return

    # ── 4. 缩放对齐到 NBA2K 身体坐标 ──────────────────────────
    zs = [v.co.z for v in dup.data.vertices]
    b_top = max(zs)
    b_bot = min(zs)
    b_h   = b_top - b_bot

    n_h   = NBA2K_BODY_TOP - NBA2K_BODY_BOT
    scale = n_h / b_h

    lines.append(f"\n大黑塔身体高度: {b_bot:.3f} ~ {b_top:.3f}  ({b_h:.3f} 单位)")
    lines.append(f"NBA2K 身体范围:  {NBA2K_BODY_BOT:.2f} ~ {NBA2K_BODY_TOP:.2f}")
    lines.append(f"缩放比例: {scale:.4f}")

    dup.scale = (scale, scale, scale)
    bpy.context.view_layer.update()

    # 对齐底部（脚）到0，X居中
    zs2 = [(dup.matrix_world @ v.co).z for v in dup.data.vertices]
    xs2 = [(dup.matrix_world @ v.co).x for v in dup.data.vertices]
    new_bot = min(zs2)
    new_cx  = (min(xs2) + max(xs2)) / 2

    dup.location.z += NBA2K_BODY_BOT - new_bot
    dup.location.x += 0.0 - new_cx        # X 居中
    bpy.context.view_layer.update()

    # 应用变换
    bpy.ops.object.select_all(action='DESELECT')
    dup.select_set(True)
    bpy.context.view_layer.objects.active = dup
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    final_zs = [v.co.z for v in dup.data.vertices]
    final_xs = [v.co.x for v in dup.data.vertices]
    lines.append(f"  对齐后 Z: {min(final_zs):.2f} ~ {max(final_zs):.2f}")
    lines.append(f"  对齐后 X: {min(final_xs):.2f} ~ {max(final_xs):.2f}")

    # ── 5. 转换为 NBA2K 顶点格式 ──────────────────────────────
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval  = dup.evaluated_get(depsgraph)
    mesh_eval = obj_eval.to_mesh()

    bm = bmesh.new()
    bm.from_mesh(mesh_eval)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(mesh_eval)
    bm.free()
    try:
        mesh_eval.calc_normals_split()
    except:
        pass  # Blender 4.0+ 不需要

    uv_layer = mesh_eval.uv_layers.active
    has_uv   = uv_layer is not None

    positions = []; normals = []; uvs = []; indices = []
    vert_map  = {}

    for poly in mesh_eval.polygons:
        tri = []
        for li in poly.loop_indices:
            loop = mesh_eval.loops[li]
            vi   = loop.vertex_index
            key  = (vi, li)
            if key not in vert_map:
                vert_map[key] = len(positions)
                v = mesh_eval.vertices[vi]
                # Blender Z-up → NBA2K Y-up：(x,y,z) → (x,z,-y)
                px, py, pz = v.co.x, v.co.y, v.co.z
                positions.append((px, pz, -py))
                nx, ny, nz = loop.normal.x, loop.normal.y, loop.normal.z
                normals.append((nx, nz, -ny))
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
    n_tris  = len(indices) // 3
    lines.append(f"\n展开后顶点: {n_verts}  三角面: {n_tris}")

    if n_verts > 65535:
        lines.append(f"⚠ 顶点数 {n_verts} 超过65535，尝试减面...")
        # 顶点数过多时，提示用户在 Blender 里手动减面
        with open(OUT_TXT, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        popup(
            f"身体顶点数 {n_verts} 超出65535！\n\n"
            f"请先在 Blender 里对 bronya_body 进行减面：\n"
            f"选中 bronya_body → 添加「重构网格」修改器\n"
            f"或：编辑模式 → 网格→清理→合并按距离\n\n"
            f"减面到65000以下后重新运行本脚本",
            title="顶点过多", icon='ERROR'
        )
        return

    # ── 6. 构建二进制缓冲区 ───────────────────────────────────
    # Stream0：位置（stride=12，R32G32B32_FLOAT）
    stream0 = bytearray()
    for px, py, pz in positions:
        stream0 += struct.pack('<fff', px, py, pz)

    # Stream1：法线+UV×2+骨骼（stride=16，R10G10B10A2+R16G16×2+R32）
    stream1 = bytearray()
    for i, (nx, ny, nz) in enumerate(normals):
        np_ = pack_normal(nx, ny, nz)    # 4字节
        u, v = uvs[i]
        stream1 += struct.pack('<IHHHHi',
            np_,
            pack_snorm16(u*2-1),         # UV1 U  2字节
            pack_snorm16(v*2-1),         # UV1 V  2字节
            pack_snorm16(u*2-1),         # UV2 U  2字节
            pack_snorm16(v*2-1),         # UV2 V  2字节
            0                            # 骨骼   4字节  → 共16字节
        )

    # 骨骼权重：全绑根骨骼0（索引0，权重255）
    weight_buf = bytearray()
    for _ in range(n_verts):
        weight_buf += struct.pack('BBBBBBBB', 0,0,0,0, 255,0,0,0)

    # 索引缓冲区：R16_UINT
    idx_buf = bytearray()
    for idx in indices:
        idx_buf += struct.pack('<H', idx)

    lines.append(f"Stream0: {len(stream0)} B  ({n_verts}×12)")
    lines.append(f"Stream1: {len(stream1)} B  ({n_verts}×16)")
    lines.append(f"Index:   {len(idx_buf)} B  ({len(indices)}×2)")
    lines.append(f"Weights: {len(weight_buf)} B  ({n_verts}×8)")

    # ── 7. 读取并更新 IFF ──────────────────────────────────────
    # 优先使用 step9 的输出（已包含脸部替换），没有则用原始文件
    iff_src = IFF_OUT if os.path.exists(IFF_OUT) else IFF_IN
    if not os.path.exists(iff_src):
        popup(f"找不到IFF文件：\n{iff_src}", title="错误", icon='ERROR')
        return

    lines.append(f"\n读取IFF: {iff_src}")

    with zipfile.ZipFile(iff_src, 'r') as zin:
        names  = zin.namelist()
        files  = {n: zin.read(n) for n in names}

    lines.append(f"IFF内文件数: {len(names)}")
    lines.append("文件列表:")
    for n in names:
        lines.append(f"  {n}  ({len(files[n])//1024} KB)")

    # ── 更新 SCNE 元数据 ──────────────────────────────────────
    scne_name = next((n for n in names if n.lower().endswith('.scne')), None)
    if scne_name:
        scne_text = files[scne_name].decode('utf-8', errors='replace')
        scne_text = re.sub(r'"vertexCount"\s*:\s*\d+',
                           f'"vertexCount": {n_verts}', scne_text)
        scne_text = re.sub(r'"indexCount"\s*:\s*\d+',
                           f'"indexCount": {len(indices)}', scne_text)
        scne_text = re.sub(r'"primitiveCount"\s*:\s*\d+',
                           f'"primitiveCount": {n_tris}', scne_text)
        ax = [p[0] for p in positions]
        ay = [p[1] for p in positions]
        az = [p[2] for p in positions]
        for k, val in [("minX", min(ax)), ("maxX", max(ax)),
                       ("minY", min(ay)), ("maxY", max(ay)),
                       ("minZ", min(az)), ("maxZ", max(az))]:
            scne_text = re.sub(
                rf'"{k}"\s*:\s*[-\d.eE+]+',
                f'"{k}": {val:.6f}', scne_text)
        files[scne_name] = scne_text.encode('utf-8')
        lines.append(f"✔ 更新SCNE: {scne_name}")

    # ── 替换 VertexBuffer ──────────────────────────────────────
    # 按大小排序：最小=Stream0(位置)，次小=Stream1(法线UV)
    vb_list = sorted(
        [(n, len(files[n])) for n in names if 'vertexbuffer' in n.lower()],
        key=lambda x: x[1]
    )
    lines.append(f"\n原始VertexBuffer文件 ({len(vb_list)} 个):")
    for vn, vs in vb_list:
        lines.append(f"  {vn}: {vs} B")

    if len(vb_list) >= 2:
        # 找最大的两个（身体最大）
        # Stream0 stride=12, Stream1 stride=16 → Stream1 > Stream0
        # 身体顶点数远多于脸部，所以最大的两个就是身体
        # 注意：如果step9已经替换了脸部，最大的可能还是原始身体
        #
        # 策略：替换最大的 VertexBuffer（最大=Stream1，次大=Stream0）
        vb_sorted_desc = sorted(vb_list, key=lambda x: x[1], reverse=True)
        stream1_name = vb_sorted_desc[0][0]   # 最大 → Stream1
        stream0_name = vb_sorted_desc[1][0]   # 次大 → Stream0
        files[stream0_name] = bytes(stream0)
        files[stream1_name] = bytes(stream1)
        lines.append(f"✔ 替换Stream0: {stream0_name} ({len(stream0)} B)")
        lines.append(f"✔ 替换Stream1: {stream1_name} ({len(stream1)} B)")
    elif len(vb_list) == 1:
        files[vb_list[0][0]] = bytes(stream0)
        lines.append(f"✔ 替换VertexBuffer: {vb_list[0][0]}")
    else:
        files['VertexBuffer_body_s0.bin'] = bytes(stream0)
        files['VertexBuffer_body_s1.bin'] = bytes(stream1)
        lines.append("✔ 新建 VertexBuffer_body_s0/s1.bin")

    # ── 替换 IndexBuffer ──────────────────────────────────────
    ib = next((n for n in names if 'indexbuffer' in n.lower()), None)
    if ib:
        files[ib] = bytes(idx_buf)
        lines.append(f"✔ 替换IndexBuffer: {ib}")

    # ── 替换 MatrixWeights ────────────────────────────────────
    mw = next((n for n in names if 'matrixweights' in n.lower()), None)
    if mw:
        files[mw] = bytes(weight_buf)
        lines.append(f"✔ 替换MatrixWeights: {mw}")

    # ── 写出新 IFF ────────────────────────────────────────────
    with zipfile.ZipFile(IFF_OUT, 'w', zipfile.ZIP_DEFLATED) as zout:
        for n, data in files.items():
            zout.writestr(n, data)

    lines.append(f"\n✔ 输出: {IFF_OUT}")
    lines.append(f"  顶点: {n_verts}  面: {n_tris}")
    lines.append("\n✔ step10 执行成功")
    lines.append("\n下一步：把 sakura_output/ 里所有 IFF 复制到游戏目录")

    msg = "\n".join(lines)
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(msg)

    popup(
        f"大黑塔身体提取完成！\n"
        f"顶点: {n_verts}  面: {n_tris}\n\n"
        f"输出:\n{IFF_OUT}\n\n"
        f"查看 step10_result.txt 确认详情",
        title="第10步完成", icon='INFO'
    )

main()
