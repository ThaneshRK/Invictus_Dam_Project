import { useState, useEffect } from 'react';
import DeckGL from '@deck.gl/react';
import { ScenegraphLayer } from '@deck.gl/mesh-layers';
import { GLTFLoader } from '@loaders.gl/gltf';
import Map from 'react-map-gl/maplibre';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useProject } from '../context/ProjectContext';
import api, { API_ORIGIN } from '../api';
import { Map as MapIcon, Upload, Save } from 'lucide-react';

const MAP_STYLE = {
  version: 8,
  sources: {
    'satellite-tiles': {
      type: 'raster',
      tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],
      tileSize: 256,
      attribution: 'Tiles &copy; Esri'
    }
  },
  layers: [
    { id: 'satellite', type: 'raster', source: 'satellite-tiles', minzoom: 0, maxzoom: 19 }
  ]
};

const AssetAlignment = () => {
  const { activeProject } = useProject();
  
  const [asset, setAsset] = useState<any>(null);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  
  const [lat, setLat] = useState(activeProject?.latitude || 9.85);
  const [lng, setLng] = useState(activeProject?.longitude || 76.97);
  const [elevation, setElevation] = useState(0);
  
  const [rotX, setRotX] = useState(0);
  const [rotY, setRotY] = useState(0);
  const [rotZ, setRotZ] = useState(0);
  
  const [scaleX, setScaleX] = useState(1);
  const [scaleY, setScaleY] = useState(1);
  const [scaleZ, setScaleZ] = useState(1);

  const [viewState, setViewState] = useState({
    longitude: lng,
    latitude: lat,
    zoom: 14,
    pitch: 45,
    bearing: 0
  });

  useEffect(() => {
    if (activeProject) {
      api.get(`/projects/${activeProject.id}/assets`).then(res => {
        if (res.data && res.data.length > 0) {
          const a = res.data[0];
          setAsset(a);
          setLat(a.origin_lat || activeProject.latitude || 9.85);
          setLng(a.origin_lon || activeProject.longitude || 76.97);
          setElevation(a.origin_elevation || 0);
          setRotX(a.rotation_x || 0);
          setRotY(a.rotation_y || 0);
          setRotZ(a.rotation_z || 0);
          setScaleX(a.scale_x || 1);
          setScaleY(a.scale_y || 1);
          setScaleZ(a.scale_z || 1);
          
          setViewState(v => ({
            ...v,
            longitude: a.origin_lon || activeProject.longitude || 76.97,
            latitude: a.origin_lat || activeProject.latitude || 9.85
          }));
        }
      });
    }
  }, [activeProject]);

  const handleUpload = async () => {
    if (!file || !activeProject) return;
    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await api.post(`/projects/${activeProject.id}/assets`, formData);
      setAsset(res.data);
      alert("Asset uploaded successfully");
    } catch (e) {
      console.error(e);
      alert("Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleSave = async () => {
    if (!asset) return;
    setSaving(true);
    try {
      await api.put(`/assets/${asset.id}`, {
        origin_lat: lat,
        origin_lon: lng,
        origin_elevation: elevation,
        rotation_x: rotX,
        rotation_y: rotY,
        rotation_z: rotZ,
        scale_x: scaleX,
        scale_y: scaleY,
        scale_z: scaleZ
      });
      alert("Alignment saved successfully");
    } catch (e) {
      console.error(e);
      alert("Failed to save alignment");
    } finally {
      setSaving(false);
    }
  };
  
  const handleMapClick = (info: any) => {
    if (info.coordinate) {
      setLng(info.coordinate[0]);
      setLat(info.coordinate[1]);
    }
  };

  const layers = [];
  
  if (asset) {
    layers.push(
      new ScenegraphLayer({
        id: 'scenegraph-layer',
        data: [{
          position: [lng, lat, elevation],
          orientation: [rotX, rotY, rotZ],
          scale: [scaleX, scaleY, scaleZ]
        }],
        pickable: true,
        scenegraph: `${API_ORIGIN}/${asset.file_path}`,
        loaders: [GLTFLoader],
        getPosition: (d: any) => d.position,
        getOrientation: (d: any) => d.orientation,
        getScale: (d: any) => d.scale,
        sizeScale: 1,
        _lighting: 'pbr'
      })
    );
  }

  return (
    <div style={{ display: 'flex', width: '100%', height: 'calc(100vh - 60px)', backgroundColor: '#090d16' }}>
      <div style={{ width: '350px', padding: '20px', overflowY: 'auto', borderRight: '1px solid rgba(255,255,255,0.1)', color: 'white' }}>
        <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
          <MapIcon size={20} color="#38bdf8" /> 3D Asset Alignment
        </h3>
        
        {!asset ? (
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px' }}>Upload GLB File</label>
            <input type="file" accept=".glb" onChange={(e) => setFile(e.target.files?.[0] || null)} style={{ marginBottom: '10px' }} />
            <button className="btn-primary" onClick={handleUpload} disabled={!file || uploading || !activeProject} style={{ width: '100%', justifyContent: 'center' }}>
              <Upload size={16} style={{ marginRight: '8px' }} /> {uploading ? 'Uploading...' : 'Upload GLB'}
            </button>
          </div>
        ) : (
          <div>
            <div style={{ padding: '10px', backgroundColor: 'rgba(56, 189, 248, 0.1)', border: '1px solid #38bdf8', borderRadius: '6px', marginBottom: '20px', fontSize: '13px' }}>
              Asset Loaded: {asset.file_path.split('/').pop()}
            </div>
            
            <div style={{ marginBottom: '16px' }}>
              <label style={{ fontSize: '12px', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Anchor Point (Click map to set)</label>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <div>
                  <label style={{ fontSize: '10px' }}>Lat</label>
                  <input type="number" step="0.000001" value={lat} onChange={e => setLat(parseFloat(e.target.value) || 0)} style={{ width: '100%', padding: '4px', backgroundColor: '#1e293b', color: 'white', border: '1px solid #334155', borderRadius: '4px' }} />
                </div>
                <div>
                  <label style={{ fontSize: '10px' }}>Lng</label>
                  <input type="number" step="0.000001" value={lng} onChange={e => setLng(parseFloat(e.target.value) || 0)} style={{ width: '100%', padding: '4px', backgroundColor: '#1e293b', color: 'white', border: '1px solid #334155', borderRadius: '4px' }} />
                </div>
              </div>
              <div style={{ marginTop: '8px' }}>
                  <label style={{ fontSize: '10px' }}>Elevation (m)</label>
                  <input type="number" step="0.1" value={elevation} onChange={e => setElevation(parseFloat(e.target.value) || 0)} style={{ width: '100%', padding: '4px', backgroundColor: '#1e293b', color: 'white', border: '1px solid #334155', borderRadius: '4px' }} />
              </div>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ fontSize: '12px', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Rotation (degrees)</label>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '4px' }}>
                <input type="number" step="1" value={rotX} onChange={e => setRotX(parseFloat(e.target.value) || 0)} placeholder="X" style={{ width: '100%', padding: '4px', backgroundColor: '#1e293b', color: 'white', border: '1px solid #334155', borderRadius: '4px' }} />
                <input type="number" step="1" value={rotY} onChange={e => setRotY(parseFloat(e.target.value) || 0)} placeholder="Y" style={{ width: '100%', padding: '4px', backgroundColor: '#1e293b', color: 'white', border: '1px solid #334155', borderRadius: '4px' }} />
                <input type="number" step="1" value={rotZ} onChange={e => setRotZ(parseFloat(e.target.value) || 0)} placeholder="Z" style={{ width: '100%', padding: '4px', backgroundColor: '#1e293b', color: 'white', border: '1px solid #334155', borderRadius: '4px' }} />
              </div>
            </div>
            
            <div style={{ marginBottom: '24px' }}>
              <label style={{ fontSize: '12px', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Scale</label>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '4px' }}>
                <input type="number" step="0.1" value={scaleX} onChange={e => setScaleX(parseFloat(e.target.value) || 1)} placeholder="X" style={{ width: '100%', padding: '4px', backgroundColor: '#1e293b', color: 'white', border: '1px solid #334155', borderRadius: '4px' }} />
                <input type="number" step="0.1" value={scaleY} onChange={e => setScaleY(parseFloat(e.target.value) || 1)} placeholder="Y" style={{ width: '100%', padding: '4px', backgroundColor: '#1e293b', color: 'white', border: '1px solid #334155', borderRadius: '4px' }} />
                <input type="number" step="0.1" value={scaleZ} onChange={e => setScaleZ(parseFloat(e.target.value) || 1)} placeholder="Z" style={{ width: '100%', padding: '4px', backgroundColor: '#1e293b', color: 'white', border: '1px solid #334155', borderRadius: '4px' }} />
              </div>
            </div>

            <button className="btn-primary" onClick={handleSave} disabled={saving} style={{ width: '100%', justifyContent: 'center' }}>
              <Save size={16} style={{ marginRight: '8px' }} /> {saving ? 'Saving...' : 'Save Alignment'}
            </button>
          </div>
        )}
      </div>

      <div style={{ flex: 1, position: 'relative' }}>
        <DeckGL
          initialViewState={viewState}
          controller={true}
          layers={layers}
          onClick={handleMapClick}
          onViewStateChange={(e: any) => setViewState(e.viewState)}
        >
          <Map
            mapLib={maplibregl as any}
            mapStyle={MAP_STYLE as any}
          />
        </DeckGL>
      </div>
    </div>
  );
};

export default AssetAlignment;
