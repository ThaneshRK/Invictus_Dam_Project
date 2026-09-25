import { useState, useEffect } from 'react';
import DeckGL from '@deck.gl/react';
import { GeoJsonLayer } from '@deck.gl/layers';
import { ScenegraphLayer } from '@deck.gl/mesh-layers';
import { GLTFLoader } from '@loaders.gl/gltf';
import Map from 'react-map-gl/maplibre';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useProject } from '../context/ProjectContext';
import api from '../api';
import { Map as MapIcon, Play, Pause, Activity, RotateCcw, Layers } from 'lucide-react';

type BasemapStyle = 'dark' | 'satellite' | 'street' | 'voyager';

const createRasterStyle = (tileUrl: string, attribution: string = '') => ({
  version: 8,
  sources: {
    'raster-tiles': {
      type: 'raster',
      tiles: [tileUrl],
      tileSize: 256,
      attribution
    }
  },
  layers: [
    {
      id: 'simple-tiles',
      type: 'raster',
      source: 'raster-tiles',
      minzoom: 0,
      maxzoom: 19
    }
  ]
});

const MAP_STYLES: Record<BasemapStyle, object> = {
  dark: createRasterStyle('https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png', '&copy; CARTO'),
  satellite: createRasterStyle('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', 'Tiles &copy; Esri'),
  street: createRasterStyle('https://tile.openstreetmap.org/{z}/{x}/{y}.png', '&copy; OpenStreetMap'),
  voyager: createRasterStyle('https://a.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png', '&copy; CARTO')
};

const Map3DViewer: React.FC = () => {
  const { activeProject } = useProject();
  
  const [basemap, setBasemap] = useState<BasemapStyle>('dark');
  
  // Animation State
  const [time, setTime] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [asset, setAsset] = useState<any>(null);
  const [simulationData, setSimulationData] = useState<any>(null); // To be filled with REAL data
  
  const lat = activeProject?.latitude || 9.85;
  const lng = activeProject?.longitude || 76.97;

  const [initialViewState, setInitialViewState] = useState({
    longitude: lng,
    latitude: lat,
    zoom: 12,
    pitch: 55,
    bearing: -20
  });

  useEffect(() => {
    if (activeProject) {
      api.get(`/projects/${activeProject.id}/assets`).then(res => {
        if (res.data && res.data.length > 0) {
          setAsset(res.data[0]);
          setInitialViewState(v => ({
            ...v,
            longitude: res.data[0].origin_lon,
            latitude: res.data[0].origin_lat,
            zoom: 14
          }));
        }
      });
      
      api.get(`/projects/${activeProject.id}/simulations`).then(async res => {
          const completed = res.data.filter((j: any) => j.status === 'COMPLETED');
          if (completed.length > 0) {
              const job = completed[0];
              if (job.result_references && job.result_references.result_id) {
                  try {
                      const result = await api.get(`/results/${job.result_references.result_id}`);
                      if (result.data && result.data.outputs && result.data.outputs.inundation_polygon) {
                          setSimulationData(result.data.outputs.inundation_polygon);
                      }
                  } catch (err) {
                      console.error("Failed to load sim results", err);
                  }
              }
          }
      });
    }
  }, [activeProject]);

  const layers = [];
  
  if (asset) {
    layers.push(
      new ScenegraphLayer({
        id: 'scenegraph-layer',
        data: [{
          position: [asset.origin_lon, asset.origin_lat, asset.origin_elevation],
          orientation: [asset.rotation_x, asset.rotation_y, asset.rotation_z],
          scale: [asset.scale_x, asset.scale_y, asset.scale_z]
        }],
        pickable: true,
        scenegraph: `http://localhost:8000/${asset.file_path}`,
        loaders: [GLTFLoader],
        getPosition: (d: any) => d.position,
        getOrientation: (d: any) => d.orientation,
        getScale: (d: any) => d.scale,
        sizeScale: 1,
        _lighting: 'pbr'
      })
    );
  }

  if (simulationData) {
      layers.push(
          new GeoJsonLayer({
              id: 'flood-polygon',
              data: simulationData,
              getFillColor: [0, 150, 255, 120],
              getLineColor: [0, 100, 255, 200],
              lineWidthMinPixels: 2,
              extruded: true,
              getElevation: 5,
              pickable: true
          })
      );
  }
  return (
    <div style={{ position: 'relative', width: '100%', height: 'calc(100vh - 60px)', backgroundColor: '#090d16' }}>
      <div style={{ 
        position: 'absolute', top: '20px', left: '20px', zIndex: 10, 
        backgroundColor: 'rgba(15, 23, 42, 0.92)', padding: '20px', 
        borderRadius: '12px', border: '1px solid rgba(100, 200, 255, 0.25)', 
        color: 'white', width: '320px',
        backdropFilter: 'blur(12px)',
        boxShadow: '0 12px 40px rgba(0,0,0,0.6)'
      }}>
        <h3 style={{ margin: '0 0 16px 0', fontSize: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <MapIcon size={20} color="#38bdf8" /> 3D Flood Command Center
        </h3>
        
        <div style={{ marginBottom: '16px' }}>
          <div style={{ fontSize: '11px', color: '#94a3b8', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '1px' }}>Active Project</div>
          <div style={{ fontWeight: 600, fontSize: '15px' }}>{activeProject ? activeProject.name : 'None Selected'}</div>
        </div>

        <div style={{ marginBottom: '16px' }}>
          <div style={{ fontSize: '11px', color: '#94a3b8', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '1px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Layers size={13} color="#38bdf8" /> Map Theme
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
            {(['dark', 'satellite', 'street', 'voyager'] as BasemapStyle[]).map(style => (
              <button
                key={style}
                onClick={() => setBasemap(style)}
                style={{
                  padding: '6px 10px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontWeight: basemap === style ? 600 : 400,
                  border: basemap === style ? '1px solid #38bdf8' : '1px solid rgba(255,255,255,0.1)',
                  backgroundColor: basemap === style ? 'rgba(56, 189, 248, 0.2)' : 'rgba(0,0,0,0.3)',
                  color: basemap === style ? '#38bdf8' : '#cbd5e1',
                  cursor: 'pointer',
                  textTransform: 'capitalize',
                  transition: 'all 0.15s ease'
                }}
              >
                {style}
              </button>
            ))}
          </div>
        </div>

        <div style={{ marginBottom: '16px', padding: '16px', background: 'linear-gradient(135deg, rgba(0,100,255,0.15), rgba(0,200,255,0.05))', borderRadius: '8px', border: '1px solid rgba(56,189,248,0.2)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <div style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px', fontSize: '14px' }}>
              <Activity size={16} color="#38bdf8" /> Real Simulation Data
            </div>
            <div style={{ fontSize: '13px', color: '#38bdf8', fontFamily: 'monospace', fontWeight: 700 }}>
              T+ {time} min
            </div>
          </div>
          
          <div style={{ display: 'flex', gap: '8px' }}>
            <button 
              className={`btn-${playing ? 'secondary' : 'primary'}`}
              style={{ flex: 1, justifyContent: 'center', padding: '10px' }}
              onClick={() => setPlaying(!playing)}
            >
              {playing ? <><Pause size={14} /> Pause</> : <><Play size={14} /> Play</>}
            </button>
            <button 
              className="btn-secondary"
              style={{ padding: '10px 14px' }}
              onClick={() => setTime(0)}
              title="Reset simulation"
            >
              <RotateCcw size={14} />
            </button>
          </div>
          <div style={{ marginTop: '10px', fontSize: '12px', color: simulationData ? '#22c55e' : '#ef4444' }}>
            {simulationData ? '[Real Simulation Linked]' : '[Awaiting backend simulation result connection]'}
          </div>
        </div>

      </div>
      
      <DeckGL
        key={`${activeProject?.id || 'default'}-${basemap}`}
        initialViewState={initialViewState}
        controller={true}
        layers={layers}
      >
        <Map
          mapLib={maplibregl as any}
          mapStyle={MAP_STYLES[basemap] as any}
        />
      </DeckGL>
    </div>
  );
};

export default Map3DViewer;
