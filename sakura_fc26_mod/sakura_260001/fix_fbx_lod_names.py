"""
Fix LOD Geometry node names in the exported Sakura head FBX.

Blender's FBX exporter names Geometry nodes lod.003/004/005 instead of
lod.000/001/002 due to internal naming conflict resolution.
Since string lengths are identical, we can safely replace bytes in-place.
"""

path = r"C:\Users\Administrator\Documents\sakura_mod_work\sakura_fc26_mod\sakura_260001\head_260001_0_0_mesh.fbx"

with open(path, "rb") as f:
    data = bytearray(f.read())

replacements = [
    (b"head_260001_0_0_mesh_lod.003", b"head_260001_0_0_mesh_lod.000"),
    (b"head_260001_0_0_mesh_lod.004", b"head_260001_0_0_mesh_lod.001"),
    (b"head_260001_0_0_mesh_lod.005", b"head_260001_0_0_mesh_lod.002"),
]

total = 0
for old, new in replacements:
    assert len(old) == len(new), "lengths must match for safe in-place replace"
    count = 0
    start = 0
    while True:
        idx = data.find(old, start)
        if idx == -1:
            break
        data[idx:idx+len(old)] = new
        start = idx + len(new)
        count += 1
    print(f"  {old.decode()} → {new.decode()} : {count} replacements")
    total += count

with open(path, "wb") as f:
    f.write(data)

print(f"\nDone — {total} total replacements written to:\n  {path}")

# Verify
import re
verify = bytes(data)
hits = re.findall(rb"head_260001_0_0_mesh_lod\.\d+", verify)
from collections import Counter
print("\nVerification — LOD name counts after fix:")
for name, cnt in sorted(Counter(hits).items()):
    print(f"  {name.decode()}: {cnt}")
