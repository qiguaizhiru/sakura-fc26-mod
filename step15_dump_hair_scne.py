"""
Dump hair SCNE full content for analysis
"""
import zipfile

IFF = r"F:\大卫李\png6794_geo_hair_parted.iff"
OUT = r"C:\Users\Administrator\Documents\sakura_mod_work\step15_hair_scne.txt"

with zipfile.ZipFile(IFF, 'r') as z:
    for n in z.namelist():
        if n.endswith('.SCNE'):
            data = z.read(n).decode('utf-8', errors='replace')
            with open(OUT, 'w', encoding='utf-8') as f:
                f.write(data)
            print(f"SCNE saved: {len(data)} chars -> {OUT}")
            break

print("Done")
