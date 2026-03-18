"""Inspect the Sakura FBX file structure"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')

FBX_PATH = "F:/未命名.fbx"

# Read raw FBX and extract text info
with open(FBX_PATH, 'rb') as f:
    data = f.read()

print(f"File size: {len(data):,} bytes")
print(f"Format: {data[:20]}")

# Extract readable strings (node names, mesh names, etc.)
import re
# Find ASCII strings >= 4 chars
strings = re.findall(rb'[ -~]{4,}', data)
unique = []
seen = set()
for s in strings:
    t = s.decode('ascii', errors='ignore').strip()
    if t and t not in seen and len(t) > 3:
        seen.add(t)
        unique.append(t)

print(f"\n=== Key identifiers in FBX ===")
keywords = ['Mesh', 'Model', 'Geometry', 'Material', 'Texture',
            'Head', 'Face', 'Hair', 'Body', 'Bone', 'Armature',
            'head', 'face', 'hair', 'body', 'sakura', 'Sakura']
for s in unique:
    for kw in keywords:
        if kw.lower() in s.lower() and len(s) < 80:
            print(f"  {s}")
            break

print(f"\n=== All object names (short strings) ===")
# FBX node names are typically short
for s in unique:
    if 4 <= len(s) <= 50 and not s.startswith('http') and '\\' not in s:
        # Filter likely node/mesh names
        if any(c.isalpha() for c in s):
            print(f"  {s}")
