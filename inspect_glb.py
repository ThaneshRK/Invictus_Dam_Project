import json
import struct
import os

def analyze_glb(filepath):
    size = os.path.getsize(filepath)
    with open(filepath, 'rb') as f:
        magic = f.read(4)
        if magic != b'glTF':
            print("Not a GLB")
            return
        version = struct.unpack('<I', f.read(4))[0]
        length = struct.unpack('<I', f.read(4))[0]
        
        chunk0_len = struct.unpack('<I', f.read(4))[0]
        chunk0_type = f.read(4)
        if chunk0_type != b'JSON':
            print("First chunk is not JSON")
            return
        
        json_data = f.read(chunk0_len).decode('utf-8')
        gltf = json.loads(json_data)
        
        print("GLB Version:", version)
        print("File Size:", size)
        print("Meshes:", len(gltf.get('meshes', [])))
        print("Nodes:", len(gltf.get('nodes', [])))
        print("Materials:", len(gltf.get('materials', [])))
        print("Textures:", len(gltf.get('textures', [])))
        print("Images:", len(gltf.get('images', [])))
        print("Animations:", len(gltf.get('animations', [])))
        print("Scenes:", len(gltf.get('scenes', [])))
        print("Cameras:", len(gltf.get('cameras', [])))
        
        # Check extensions or extras for georeferencing
        print("Asset Info:", gltf.get('asset', {}))
        if 'extras' in gltf.get('asset', {}):
            print("Asset Extras:", gltf.get('asset', {})['extras'])
            
        nodes = gltf.get('nodes', [])
        for i, node in enumerate(nodes[:5]):
            print(f"Node {i}: {node.get('name', '')}, mesh: {node.get('mesh')}, translation: {node.get('translation')}, rotation: {node.get('rotation')}, scale: {node.get('scale')}")
        
        if len(nodes) > 5:
            print(f"... and {len(nodes) - 5} more nodes")
            
        accessors = gltf.get('accessors', [])
        print("Accessors:", len(accessors))
        
        # Look for position accessor to find bounding box
        for mesh in gltf.get('meshes', []):
            for primitive in mesh.get('primitives', []):
                pos_accessor_idx = primitive.get('attributes', {}).get('POSITION')
                if pos_accessor_idx is not None:
                    accessor = accessors[pos_accessor_idx]
                    print(f"Mesh {mesh.get('name')} Position Min:", accessor.get('min'))
                    print(f"Mesh {mesh.get('name')} Position Max:", accessor.get('max'))

analyze_glb('dam_this_is_crazy.glb')
