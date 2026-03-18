import re, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('F:/未命名.fbx', 'rb') as f:
    data = f.read()

models = re.findall(rb'Model::[^\x00\x01-\x1f]{1,60}', data)
geoms  = re.findall(rb'Geometry::[^\x00\x01-\x1f]{1,60}', data)
mats   = re.findall(rb'Material::[^\x00\x01-\x1f]{1,60}', data)
texs   = re.findall(rb'Texture::[^\x00\x01-\x1f]{1,60}', data)

print("=== Models ===")
for m in sorted(set(models)):
    print(" ", m.decode('utf-8', 'ignore'))

print("\n=== Geometries ===")
for g in sorted(set(geoms)):
    print(" ", g.decode('utf-8', 'ignore'))

print("\n=== Materials ===")
for m in sorted(set(mats)):
    print(" ", m.decode('utf-8', 'ignore'))

print("\n=== Textures ===")
for t in sorted(set(texs)):
    print(" ", t.decode('utf-8', 'ignore'))

# Count vertices roughly
verts = data.count(b'Vertices')
polys = data.count(b'PolygonVertexIndex')
print(f"\nVertex arrays: {verts}, Polygon arrays: {polys}")

# Check for UV maps
uvs = re.findall(rb'UV[^\x00\x01-\x1f]{1,40}', data)
print("\n=== UV layers ===")
for u in sorted(set(uvs))[:10]:
    print(" ", u.decode('utf-8', 'ignore'))
