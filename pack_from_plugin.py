"""
从 nba2k26_tool.py 插件输出的 NewVertexBuffer.bin 打包回 IFF
插件导出后会在 IFF 所在目录生成：
  F:/大卫李/NewVertexBuffer.bin  ← 修改后的顶点位置
"""
import zipfile
import os
import shutil
import struct

SRC_IFF  = 'F:/大卫李/png6794_geo_hair_parted.iff'
NEW_BIN  = 'F:/大卫李/NewVertexBuffer.bin'   # 插件导出路径
OUT_IFF  = 'F:/大卫李/sakura_output/png6794_geo_hair_parted.iff'
OUT_DIR  = 'F:/大卫李/sakura_output'

# 原始位置顶点缓冲区文件名（在IFF内部）
POS_BUF_NAME = 'VertexBuffer.b0f7128ab2b01763.bin'
SCNE_NAME    = 'hair_parted.SCNE'


def validate_new_bin(path, expected_bytes):
    """验证新顶点缓冲区大小是否匹配"""
    if not os.path.exists(path):
        print(f"[错误] 找不到插件导出文件: {path}")
        print("请确认已在Blender中点击 '导出模型(仅顶点)'")
        return False

    actual = os.path.getsize(path)
    if actual != expected_bytes:
        print(f"[警告] 文件大小不匹配:")
        print(f"  期望: {expected_bytes} bytes ({expected_bytes//12} 顶点)")
        print(f"  实际: {actual} bytes ({actual//12} 顶点)")
        # 仍然尝试继续，可能是顶点数不同
    else:
        print(f"✓ 文件大小匹配: {actual} bytes ({actual//12} 顶点)")
    return True


def update_scne_bounds(scne_text, new_bin_data):
    """根据新顶点数据更新SCNE包围盒"""
    import re, math

    n = len(new_bin_data) // 12
    verts = [struct.unpack_from('<fff', new_bin_data, i*12) for i in range(n)]

    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    zs = [v[2] for v in verts]

    mn = [min(xs), min(ys), min(zs)]
    mx = [max(xs), max(ys), max(zs)]
    cen = [(mn[i]+mx[i])/2 for i in range(3)]
    rad = math.sqrt(sum((mx[i]-cen[i])**2 for i in range(3)))

    def fmt3(lst):
        return '[ {:.7g}, {:.7g}, {:.7g} ]'.format(*lst)

    scne_text = re.sub(r'"Radius":\s*[\d.]+',
                       f'"Radius": {round(rad,7)}', scne_text, count=1)
    scne_text = re.sub(r'"Center":\s*\[.*?\]',
                       f'"Center": {fmt3(cen)}', scne_text, count=1)
    scne_text = re.sub(r'"Min":\s*\[.*?\]',
                       f'"Min": {fmt3(mn)}', scne_text, count=1)
    scne_text = re.sub(r'"Max":\s*\[.*?\]',
                       f'"Max": {fmt3(mx)}', scne_text, count=1)

    print(f"  包围盒更新: Min={[round(v,2) for v in mn]} Max={[round(v,2) for v in mx]}")
    return scne_text


def pack():
    os.makedirs(OUT_DIR, exist_ok=True)

    # 读取原始IFF中的位置缓冲区大小
    with zipfile.ZipFile(SRC_IFF, 'r') as z:
        orig_pos_size = z.getinfo(POS_BUF_NAME).file_size

    print(f"原始顶点缓冲区: {orig_pos_size} bytes ({orig_pos_size//12} 顶点)")

    # 验证插件输出
    if not validate_new_bin(NEW_BIN, orig_pos_size):
        return

    with open(NEW_BIN, 'rb') as f:
        new_pos_data = f.read()

    # 打包新IFF
    print("\n打包 png6794_geo_hair_parted.iff ...")
    with zipfile.ZipFile(SRC_IFF, 'r') as src:
        with zipfile.ZipFile(OUT_IFF, 'w', compression=zipfile.ZIP_DEFLATED) as out:
            for item in src.infolist():
                if item.filename == POS_BUF_NAME:
                    # 替换顶点位置
                    out.writestr(item, new_pos_data)
                    print(f"  ✓ 替换: {item.filename}")
                elif item.filename == SCNE_NAME:
                    # 更新包围盒
                    scne_txt = src.read(item.filename).decode('utf-8')
                    scne_txt = update_scne_bounds(scne_txt, new_pos_data)
                    out.writestr(item, scne_txt.encode('utf-8'))
                    print(f"  ✓ 更新: {item.filename} (包围盒)")
                else:
                    out.writestr(item, src.read(item.filename))

    print(f"\n完成！输出: {OUT_IFF}")
    print(f"文件大小: {os.path.getsize(OUT_IFF):,} bytes")


if __name__ == '__main__':
    print("═" * 50)
    print("  nba2k26_tool.py 插件输出 → IFF 打包工具")
    print("═" * 50 + "\n")
    pack()
