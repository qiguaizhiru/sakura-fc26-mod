import zipfile
import json
import os

IFF_IN = r"F:\大卫李\png6794.iff"
OUT_TXT = r"C:\Users\Administrator\Documents\sakura_mod_work\debug_scne_result.txt"

lines = []

with zipfile.ZipFile(IFF_IN, 'r') as z:
    names = z.namelist()
    lines.append("=== IFF 文件列表 ===\n")
    for n in names:
        data = z.read(n)
        lines.append(f"  {n}  ({len(data)} bytes)")

    # 找 SCNE
    scne_name = next((n for n in names if n.lower().endswith('.scne')), None)
    if scne_name:
        scne_data = z.read(scne_name)
        scne_text = scne_data.decode('utf-8', errors='replace')
        lines.append(f"\n=== SCNE 完整内容 ({scne_name}) ===\n")
        lines.append(scne_text)

    # 找 appearance_info
    app_name = next((n for n in names if 'appearance' in n.lower()), None)
    if app_name:
        app_data = z.read(app_name)
        lines.append(f"\n=== {app_name} ===\n")
        lines.append(app_data.decode('utf-8', errors='replace')[:2000])

with open(OUT_TXT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"结果已保存到: {OUT_TXT}")
