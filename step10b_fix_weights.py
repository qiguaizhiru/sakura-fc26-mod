# =====================================================
# 第10b步：修复身体骨骼权重
# 在 Blender 脚本编辑器里运行
#
# 原理：
#   1. 从原始 IFF 二进制数据读取顶点位置和骨骼权重
#   2. 用 KD-Tree 找最近顶点
#   3. 把原始权重映射到 bronya_body
#   4. 重新打包 IFF
# =====================================================

import bpy
import bmesh
import struct
import os
import zipfile
import re
import json
from mathutils import kdtree as KDTree

IFF_IN  = r"F:\大卫李\png6794.iff"
IFF_OUT = r"F:\大卫李\sakura_output\png6794.iff"
OUT_TXT = r"C:\Users\Administrator\Documents\sakura_mod_work\step10b_result.txt"

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

def main():
    lines = ["=== 第10b步：修复身体骨骼权重 ===\n"]

    # ── 1. 找 bronya_body ──────────────────────────────────
    dup = bpy.data.objects.get("bronya_body")
    if not dup:
        popup("找不到 bronya_body！\n请先运行 step10", title="错误", icon='ERROR')
        return
    lines.append(f"bronya_body: 顶点{len(dup.data.vertices)}")

    # ── 2. 从原始 IFF 读取二进制数据 ────────────────────────
    lines.append(f"\n读取原始IFF: {IFF_IN}")
    with zipfile.ZipFile(IFF_IN, 'r') as zin:
        names = zin.namelist()
        files = {n: zin.read(n) for n in names}

    # 找 SCNE 分析网格结构
    scne_name = next((n for n in names if n.lower().endswith('.scne')), None)
    scne_text = files[scne_name].decode('utf-8', errors='replace') if scne_name else ""

    # 列出所有 VertexBuffer 和 MatrixWeightsBuffer
    vb_files = sorted([(n, len(files[n])) for n in names if 'vertexbuffer' in n.lower()],
                      key=lambda x: x[1], reverse=True)
    mw_files = [(n, len(files[n])) for n in names if 'matrixweights' in n.lower()]
    ib_files = [(n, len(files[n])) for n in names if 'indexbuffer' in n.lower()]

    lines.append("\n原始IFF文件:")
    for n, sz in vb_files:
        lines.append(f"  VB: {n}  ({sz} B)")
    for n, sz in mw_files:
        lines.append(f"  MW: {n}  ({sz} B)")
    for n, sz in ib_files:
        lines.append(f"  IB: {n}  ({sz} B)")

    # ── 3. 确定哪些是身体的 Stream0（位置）──────────────────
    # Stream0 stride=12 (3xfloat32), Stream1 stride=16
    # 找配对：同一网格的 Stream1/Stream0 大小比 = 16/12 = 1.333
    # 身体网格是最大的那个

    # 尝试所有配对
    pairs = []
    used = set()
    for i, (n1, s1) in enumerate(vb_files):
        for j, (n2, s2) in enumerate(vb_files):
            if i == j: continue
            if i in used or j in used: continue
            # s1 是 stride16, s2 是 stride12
            if s2 > 0 and abs(s1 / s2 - 16.0/12.0) < 0.01:
                n_verts_check = s2 // 12
                pairs.append((n2, n1, n_verts_check))  # (stream0, stream1, verts)
                used.add(i); used.add(j)
                break

    if not pairs:
        # 没找到精确配对，按大小猜测
        # 最大的 VB 可能是 Stream1（stride=16），次大是 Stream0（stride=12）
        lines.append("\n未找到精确VB配对，按大小推测...")
        # 尝试所有 VB 找 stride=12 能整除的
        for n, sz in vb_files:
            if sz % 12 == 0:
                nv = sz // 12
                # 检查是否有对应的 stride=16 的 VB
                expected_s1 = nv * 16
                for n2, sz2 in vb_files:
                    if n2 != n and sz2 == expected_s1:
                        pairs.append((n, n2, nv))
                        break
                if pairs: break

    if not pairs:
        # 最后手段：直接找最大的 stride=12 整除的
        for n, sz in vb_files:
            if sz % 12 == 0 and sz > 100000:
                pairs.append((n, None, sz // 12))
                break

    lines.append(f"\nVB配对结果:")
    for s0, s1, nv in pairs:
        lines.append(f"  Stream0: {s0}  Stream1: {s1}  顶点: {nv}")

    if not pairs:
        popup("无法识别原始IFF的顶点缓冲区格式", title="错误", icon='ERROR')
        return

    # 取最大的那个 pair（身体）
    body_pair = max(pairs, key=lambda p: p[2])
    stream0_name, stream1_name, orig_nverts = body_pair

    # ── 4. 解析原始顶点位置（NBA2K 坐标：Y-up）──────────────
    s0_data = files[stream0_name]
    orig_positions = []  # NBA2K 空间 (x, y, z) 其中 y=up
    for i in range(orig_nverts):
        off = i * 12
        x, y, z = struct.unpack_from('<fff', s0_data, off)
        orig_positions.append((x, y, z))

    lines.append(f"\n原始身体顶点: {orig_nverts}")
    if orig_positions:
        xs = [p[0] for p in orig_positions]
        ys = [p[1] for p in orig_positions]
        zs = [p[2] for p in orig_positions]
        lines.append(f"  X: {min(xs):.2f} ~ {max(xs):.2f}")
        lines.append(f"  Y: {min(ys):.2f} ~ {max(ys):.2f}")
        lines.append(f"  Z: {min(zs):.2f} ~ {max(zs):.2f}")

    # ── 5. 解析原始骨骼权重 ──────────────────────────────────
    if not mw_files:
        popup("原始IFF中无MatrixWeightsBuffer", title="错误", icon='ERROR')
        return

    mw_name, mw_size = mw_files[0]
    mw_data = files[mw_name]
    mw_nverts = mw_size // 8  # 每顶点 8 字节

    lines.append(f"\n原始骨骼权重: {mw_nverts} 顶点")
    lines.append(f"  (需要匹配 {orig_nverts} 顶点)")

    # 如果 MW 顶点数和 Stream0 不匹配，可能是不同网格
    # 找最接近的匹配
    if mw_nverts != orig_nverts:
        lines.append(f"  ⚠ 数量不匹配！尝试其他VB...")
        # 重新找匹配 MW 的 VB
        for n, sz in vb_files:
            if sz % 12 == 0:
                nv = sz // 12
                if nv == mw_nverts:
                    stream0_name = n
                    orig_nverts = nv
                    s0_data = files[n]
                    orig_positions = []
                    for i in range(nv):
                        off = i * 12
                        x, y, z = struct.unpack_from('<fff', s0_data, off)
                        orig_positions.append((x, y, z))
                    lines.append(f"  ✔ 找到匹配VB: {n} ({nv} 顶点)")
                    break

    orig_weights = []  # [(idx0,idx1,idx2,idx3, w0,w1,w2,w3), ...]
    for i in range(min(mw_nverts, orig_nverts)):
        off = i * 8
        b0, b1, b2, b3, w0, w1, w2, w3 = struct.unpack_from('BBBBBBBB', mw_data, off)
        orig_weights.append((b0, b1, b2, b3, w0, w1, w2, w3))

    # 统计骨骼使用情况
    bone_set = set()
    for bw in orig_weights:
        for bi in range(4):
            if bw[bi+4] > 0:  # weight > 0
                bone_set.add(bw[bi])
    lines.append(f"  使用的骨骼索引: {sorted(bone_set)}")
    lines.append(f"  骨骼数: {len(bone_set)}")

    # ── 6. 建 KD-Tree（原始顶点位置）─────────────────────────
    # 注意坐标系：原始是 NBA2K (x, y_up, z)
    # bronya_body 在 Blender 空间 (x, y, z_up)
    # 需要转换 bronya_body → NBA2K: (bx, bz, -by)

    kd = KDTree.KDTree(len(orig_positions))
    for i, (ox, oy, oz) in enumerate(orig_positions):
        kd.insert((ox, oy, oz), i)
    kd.balance()
    lines.append(f"\n✔ KD-Tree 建立完成 ({len(orig_positions)} 点)")

    # ── 7. 转换 bronya_body 并映射权重 ──────────────────────
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
    has_uv = uv_layer is not None

    positions = []; normals_list = []; uvs = []; indices = []
    vert_map = {}
    vi_map = {}

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
                # Blender → NBA2K: (x, z, -y)
                px, py, pz = v.co.x, v.co.z, -v.co.y
                positions.append((px, py, pz))
                nx, ny, nz = loop.normal.x, loop.normal.z, -loop.normal.y
                normals_list.append((nx, ny, nz))
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
    lines.append(f"\nbronya_body 展开: 顶点{n_verts}  面{n_tris}")

    if n_verts > 65535:
        popup(f"顶点数 {n_verts} > 65535！", title="错误", icon='ERROR')
        return

    # ── 8. 用 KD-Tree 映射权重 ──────────────────────────────
    mapped_weights = []
    total_dist = 0.0
    for i, (px, py, pz) in enumerate(positions):
        co, idx, dist = kd.find((px, py, pz))
        total_dist += dist
        if idx < len(orig_weights):
            mapped_weights.append(orig_weights[idx])
        else:
            mapped_weights.append((0, 0, 0, 0, 255, 0, 0, 0))

    avg_dist = total_dist / max(n_verts, 1)
    lines.append(f"✔ 权重映射完成，平均距离: {avg_dist:.4f}")

    # ── 9. 打包二进制 ────────────────────────────────────────
    stream0 = bytearray()
    for px, py, pz in positions:
        stream0 += struct.pack('<fff', px, py, pz)

    stream1 = bytearray()
    for i, (nx, ny, nz) in enumerate(normals_list):
        np_ = pack_normal(nx, ny, nz)
        u, v = uvs[i]
        stream1 += struct.pack('<IHHHHi',
            np_,
            pack_snorm16(u*2-1), pack_snorm16(v*2-1),
            pack_snorm16(u*2-1), pack_snorm16(v*2-1),
            0)

    weight_buf = bytearray()
    for bw in mapped_weights:
        weight_buf += struct.pack('BBBBBBBB', *bw)

    idx_buf = bytearray()
    for idx in indices:
        idx_buf += struct.pack('<H', idx)

    lines.append(f"\nStream0: {len(stream0)} B  Stream1: {len(stream1)} B")
    lines.append(f"Index: {len(idx_buf)} B  Weights: {len(weight_buf)} B")

    # ── 10. 打包 IFF ─────────────────────────────────────────
    # 读 step9 的输出（已含脸部替换）或原始
    iff_src = IFF_OUT if os.path.exists(IFF_OUT) else IFF_IN
    lines.append(f"\n读取IFF: {iff_src}")

    with zipfile.ZipFile(iff_src, 'r') as zin:
        out_names = zin.namelist()
        out_files = {n: zin.read(n) for n in out_names}

    # 更新 SCNE
    scne_out = next((n for n in out_names if n.lower().endswith('.scne')), None)
    if scne_out:
        st = out_files[scne_out].decode('utf-8', errors='replace')
        st = re.sub(r'"vertexCount"\s*:\s*\d+',    f'"vertexCount": {n_verts}', st)
        st = re.sub(r'"indexCount"\s*:\s*\d+',      f'"indexCount": {len(indices)}', st)
        st = re.sub(r'"primitiveCount"\s*:\s*\d+',  f'"primitiveCount": {n_tris}', st)
        ax=[p[0] for p in positions]; ay=[p[1] for p in positions]; az=[p[2] for p in positions]
        for k, val in [("minX",min(ax)),("maxX",max(ax)),("minY",min(ay)),
                       ("maxY",max(ay)),("minZ",min(az)),("maxZ",max(az))]:
            st = re.sub(rf'"{k}"\s*:\s*[-\d.eE+]+', f'"{k}": {val:.6f}', st)
        out_files[scne_out] = st.encode('utf-8')

    # 替换 VB（最大两个）
    out_vb = sorted([(n, len(out_files[n])) for n in out_names if 'vertexbuffer' in n.lower()],
                    key=lambda x: x[1], reverse=True)
    if len(out_vb) >= 2:
        out_files[out_vb[0][0]] = bytes(stream1)
        out_files[out_vb[1][0]] = bytes(stream0)
        lines.append(f"✔ 替换 Stream1: {out_vb[0][0]}")
        lines.append(f"✔ 替换 Stream0: {out_vb[1][0]}")

    out_ib = next((n for n in out_names if 'indexbuffer' in n.lower()), None)
    if out_ib:
        out_files[out_ib] = bytes(idx_buf)
        lines.append(f"✔ 替换 IndexBuffer")

    out_mw = next((n for n in out_names if 'matrixweights' in n.lower()), None)
    if out_mw:
        out_files[out_mw] = bytes(weight_buf)
        lines.append(f"✔ 替换 MatrixWeights")

    with zipfile.ZipFile(IFF_OUT, 'w', zipfile.ZIP_DEFLATED) as zout:
        for n, data in out_files.items():
            zout.writestr(n, data)

    lines.append(f"\n✔ 输出: {IFF_OUT}")
    lines.append(f"  顶点: {n_verts}  面: {n_tris}")
    lines.append(f"  骨骼: {len(bone_set)} 个 (索引: {sorted(bone_set)})")
    lines.append(f"  平均映射距离: {avg_dist:.4f}")
    lines.append("\n✔ step10b 执行成功！骨骼权重已从原始IFF映射")

    msg = "\n".join(lines)
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(msg)

    popup(
        f"骨骼权重修复完成！\n"
        f"顶点: {n_verts}  面: {n_tris}\n"
        f"骨骼: {len(bone_set)} 个\n"
        f"平均映射距离: {avg_dist:.4f}\n\n"
        f"输出: {IFF_OUT}",
        title="第10b步完成", icon='INFO'
    )

main()
