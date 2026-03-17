"""
修复 config_parted.iff：从原始文件复制，去掉多余的 face_color_o.dds
在命令行运行（不需要 Blender）
"""
import zipfile
import os

IFF_ORIG = r"F:\大卫李\png6794_config_parted.iff"
IFF_OUT  = r"F:\大卫李\sakura_output\png6794_config_parted.iff"

os.makedirs(os.path.dirname(IFF_OUT), exist_ok=True)

# 读取原始文件所有条目
with zipfile.ZipFile(IFF_ORIG, 'r') as z_in:
    names = z_in.namelist()
    files = {n: z_in.read(n) for n in names}

# 如果之前修改版有替换的贴图，尝试读取
bronya_face_tex = None
try:
    with zipfile.ZipFile(IFF_OUT, 'r') as z_mod:
        # 检查是否有不带hash的 face_color_o.dds（之前的替换贴图）
        if "face_color_o.dds" in z_mod.namelist():
            bronya_face_tex = z_mod.read("face_color_o.dds")
            print(f"找到之前替换的脸部贴图: {len(bronya_face_tex)} bytes")
except:
    pass

# 如果有替换贴图，替换原始的hashed版本
if bronya_face_tex:
    for n in names:
        if n.startswith("face_color_o.") and n.endswith(".dds"):
            print(f"替换: {n} ({len(files[n])} -> {len(bronya_face_tex)} bytes)")
            files[n] = bronya_face_tex
            break

# 写出（只包含原始文件名，不加多余条目）
with zipfile.ZipFile(IFF_OUT, 'w', compression=zipfile.ZIP_STORED) as z_out:
    for n in names:
        z_out.writestr(n, files[n])

print(f"\n✔ 输出: {IFF_OUT}")
print(f"  条目数: {len(names)} (与原始一致)")
print(f"  贴图{'已替换' if bronya_face_tex else '保持原始'}")
