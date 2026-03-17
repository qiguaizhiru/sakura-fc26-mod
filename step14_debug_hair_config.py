"""
诊断 geo_hair_parted.iff 和 config_parted.iff 的结构
直接在 Python 里运行（不需要 Blender）
"""
import zipfile
import os

OUT_TXT = r"C:\Users\Administrator\Documents\sakura_mod_work\step14_debug_result.txt"

files_to_check = {
    "原始 config":  r"F:\大卫李\png6794_config_parted.iff",
    "修改 config":  r"F:\大卫李\sakura_output\png6794_config_parted.iff",
    "原始 hair":    r"F:\大卫李\png6794_geo_hair_parted.iff",
    "修改 hair":    r"F:\大卫李\sakura_output\png6794_geo_hair_parted.iff",
    "原始 item":    r"F:\大卫李\png6794_item_hair_parted.iff",
    "修改 item":    r"F:\大卫李\sakura_output\png6794_item_hair_parted.iff",
}

lines = []

for label, path in files_to_check.items():
    lines.append(f"\n{'='*60}")
    lines.append(f"  {label}: {path}")
    lines.append(f"{'='*60}")

    if not os.path.exists(path):
        lines.append("  *** 文件不存在 ***")
        continue

    fsize = os.path.getsize(path)
    lines.append(f"  文件大小: {fsize} bytes")

    try:
        with zipfile.ZipFile(path, 'r') as z:
            names = z.namelist()
            lines.append(f"  ZIP 条目数: {len(names)}")
            for n in names:
                data = z.read(n)
                ext = os.path.splitext(n)[1].lower()
                desc = ""
                if ext == '.scne':
                    # 显示前500字符
                    txt = data.decode('utf-8', errors='replace')[:500]
                    desc = f"\n    SCNE前500字: {txt}"
                elif 'vertexbuffer' in n.lower():
                    nverts12 = len(data) // 12
                    nverts16 = len(data) // 16
                    nverts4 = len(data) // 4
                    desc = f"  (÷12={nverts12}, ÷16={nverts16}, ÷4={nverts4})"
                elif 'indexbuffer' in n.lower():
                    nidx = len(data) // 2
                    desc = f"  ({nidx} indices)"
                elif ext in ['.png', '.dds', '.tga']:
                    desc = f"  (texture)"
                lines.append(f"    {n}  ({len(data)} B){desc}")
    except Exception as e:
        lines.append(f"  *** 无法打开ZIP: {e} ***")

result = "\n".join(lines)
with open(OUT_TXT, "w", encoding="utf-8") as f:
    f.write(result)

print(result)
print(f"\n结果已保存到: {OUT_TXT}")
