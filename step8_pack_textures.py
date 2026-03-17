# =====================================================
# 第8步：把大黑塔贴图打包进 NBA2K IFF 文件
# 在命令行运行：python step8_pack_textures.py
# 前提：已运行 step2（bronya_tex 目录里有 DDS 文件）
# =====================================================

import os
import zipfile
import shutil

TEX_DIR    = r"C:\Users\Administrator\Documents\sakura_mod_work\bronya_tex"
OUT_DIR    = r"F:\大卫李\sakura_output"
os.makedirs(OUT_DIR, exist_ok=True)

# 原始 IFF 文件路径
IFF_FACE   = r"F:\大卫李\png6794_config_parted.iff"
IFF_HAIR_T = r"F:\大卫李\png6794_item_hair_parted.iff"
IFF_MAIN   = r"F:\大卫李\png6794.iff"

def replace_dds_in_iff(iff_in, iff_out, replacements):
    """
    replacements: dict { '原始文件名关键词': '新DDS文件路径' }
    """
    if not os.path.exists(iff_in):
        print(f"  ✘ 找不到: {iff_in}")
        return False

    with zipfile.ZipFile(iff_in, 'r') as zin:
        names = zin.namelist()
        files = {n: zin.read(n) for n in names}

    print(f"  原始文件列表: {names}")
    replaced = []

    for keyword, new_dds_path in replacements.items():
        if not os.path.exists(new_dds_path):
            print(f"  ✘ DDS 不存在: {new_dds_path}")
            continue
        with open(new_dds_path, 'rb') as f:
            new_data = f.read()

        matched = False
        for n in names:
            if keyword.lower() in n.lower():
                files[n] = new_data
                print(f"  ✔ 替换 {n} → {os.path.basename(new_dds_path)} ({len(new_data)//1024} KB)")
                replaced.append(n)
                matched = True
                break
        if not matched:
            # 直接新建同名文件
            new_name = os.path.basename(new_dds_path)
            files[new_name] = new_data
            print(f"  ✔ 新建 {new_name} ({len(new_data)//1024} KB)")
            replaced.append(new_name)

    with zipfile.ZipFile(iff_out, 'w', zipfile.ZIP_DEFLATED) as zout:
        for n, data in files.items():
            zout.writestr(n, data)

    print(f"  ✔ 输出: {iff_out}")
    return True

print("=" * 55)
print("第8步：打包大黑塔贴图到 NBA2K IFF")
print("=" * 55)

# ── 脸部贴图 IFF ────────────────────────────────────────────────────
print("\n[1] 脸部贴图 IFF:")
face_dds = os.path.join(TEX_DIR, "face_color_o.dds")
replace_dds_in_iff(
    IFF_FACE,
    os.path.join(OUT_DIR, "png6794_config_parted.iff"),
    {"face_color": face_dds,
     "face_col":   face_dds,
     "albedo":     face_dds,
     "color_o":    face_dds}
)

# ── 头发贴图 IFF ────────────────────────────────────────────────────
print("\n[2] 头发贴图 IFF:")
hair_dds = os.path.join(TEX_DIR, "hair_color_o.dds")
replace_dds_in_iff(
    IFF_HAIR_T,
    os.path.join(OUT_DIR, "png6794_item_hair_parted.iff"),
    {"hair_color": hair_dds,
     "hair_col":   hair_dds,
     "color_o":    hair_dds}
)

# ── 主文件 appearance_info.json（已在 sakura_mod_work 里修改过）──────
print("\n[3] 主文件（appearance_info.json）:")
appear_json = r"C:\Users\Administrator\Documents\sakura_mod_work\appearance_info.json"
if os.path.exists(appear_json) and os.path.exists(IFF_MAIN):
    replace_dds_in_iff(
        IFF_MAIN,
        os.path.join(OUT_DIR, "png6794.iff"),
        {"appearance_info": appear_json}
    )
else:
    # 直接复制原始主文件
    dst = os.path.join(OUT_DIR, "png6794.iff")
    if not os.path.exists(dst):
        shutil.copy2(IFF_MAIN, dst)
        print(f"  ✔ 复制原始主文件到输出目录")

# ── 汇总 ────────────────────────────────────────────────────────────
print("\n" + "=" * 55)
print("输出目录:", OUT_DIR)
out_files = os.listdir(OUT_DIR)
for f in out_files:
    fp = os.path.join(OUT_DIR, f)
    print(f"  {f}  ({os.path.getsize(fp)//1024} KB)")

print("\n✔ step8 执行成功")
print("\n最后：把 F:/大卫李/sakura_output/ 里的所有 IFF 文件")
print("复制到游戏对应目录覆盖原文件即可")
