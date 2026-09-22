import React, { useState, useEffect, useCallback } from 'react';
import DeckGL from '@deck.gl/react';
import { PolygonLayer, ScatterplotLayer } from '@deck.gl/layers';
import Map from 'react-map-gl/maplibre';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useProject } from '../context/ProjectContext';
import api from '../api';
import { Map as MapIcon, CloudRain, Play, Pause, Activity, RotateCcw, Layers } from 'lucide-react';

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
  
  const [loadingSat, setLoadingSat] = useState(false);
  const [satResult, setSatResult] = useState<any>(null);
  const [basemap, setBasemap] = useState<BasemapStyle>('dark');
  
  // Animation State
  const [time, setTime] = useState(0);
  const [playing, setPlaying] = useState(false);

  const animateRef = React.useRef<number>(0);

  const animate = useCallback(() => {
    setTime(t => {
      if (t >= 600) return 600; // Stop at max
      return t + 1;
    });
    animateRef.current = requestAnimationFrame(animate);
  }, []);

  useEffect(() => {
    if (playing) {
      animateRef.current = requestAnimationFrame(animate);
    } else if (animateRef.current) {
      cancelAnimationFrame(animateRef.current);
    }
    return () => {
      if (animateRef.current) cancelAnimationFrame(animateRef.current);
    };
  }, [playing, animate]);

  const lat = activeProject?.latitude || 9.85;
  const lng = activeProject?.longitude || 76.97;

  const initialViewState = {
    longitude: lng,
    latitude: lat,
    zoom: 12,
    pitch: 55,
    bearing: -20
  };

  // Generate realistic downstream flood flow
  const progress = time / 600; // 0 to 1

  // Generate multiple expanding flood zones that simulate water flowing downstream
  const generateFloodZones = () => {
    if (progress <= 0) return [];
    
    const zones = [];
    const numZones = Math.min(Math.floor(progress * 8) + 1, 8);
    
    for (let i = 0; i < numZones; i++) {
      const zoneProgress = Math.max(0, progress - (i * 0.08));
      if (zoneProgress <= 0) continue;
      
      const offsetLat = -i * 0.008 * Math.min(zoneProgress * 3, 1);
      const offsetLng = (Math.sin(i * 1.2) * 0.003) * Math.min(zoneProgress * 3, 1);
      
      const baseRadius = 0.004 + (zoneProgress * 0.015);
      const segments = 48;
      const contour = [];
      
      for (let s = 0; s < segments; s++) {
        const angle = (s / segments) * Math.PI * 2;
        const stretchY = 1.0 + (Math.abs(Math.sin(angle)) < 0.5 ? 0.3 : 0);
        const wave = Math.sin(angle * 6 + time * 0.03 + i) * 0.2;
        const r = baseRadius * (1 + wave);
        
        contour.push([
          lng + offsetLng + Math.cos(angle) * r,
          lat + offsetLat + Math.sin(angle) * r * stretchY
        ]);
      }
      
      zones.push({
        contour,
        depth: Math.max(2, 30 * zoneProgress * (1 - i * 0.1)),
        zone: i
      });
    }
    
    return zones;
  };

  // Generate particle scatter to simulate flowing water particles
  const generateWaterParticles = () => {
    if (progress <= 0) return [];
    
    const particles = [];
    const numParticles = Math.floor(progress * 200);
    
    for (let i = 0; i < numParticles; i++) {
      const seed = i * 137.5;
      const particleAge = Math.max(0, progress - (i / 300));
      if (particleAge <= 0) continue;
      
      const spreadAngle = (seed % 360) * (Math.PI / 180);
      const distance = particleAge * 0.04 * (0.5 + Math.random() * 0.5);
      const biasLat = -particleAge * 0.01;
      
      particles.push({
        position: [
          lng + Math.cos(spreadAngle) * distance * 0.7,
          lat + biasLat + Math.sin(spreadAngle) * distance * 0.5
        ],
        radius: 30 + Math.random() * 60,
        color: [0, 140 + Math.floor(Math.random() * 60), 255, 120 + Math.floor(Math.random() * 80)]
      });
    }
    
    return particles;
  };

  const floodZones = generateFloodZones();
  const waterParticles = generateWaterParticles();

  const handleReset = () => {
    setPlaying(false);
    setTime(0);
  };

  const fetchSatelliteData = async () => {
    setLoadingSat(true);
    try {
      const bounds = [[lng - 0.1, lat - 0.1], [lng + 0.1, lat + 0.1]];
      const res = await api.post('/satellite/extract', {
        bounds,
        start_date: '2024-08-01',
        end_date: '2024-08-15'
      });
      setSatResult(res.data);
    } catch (e) {
      console.error(e);
      alert("Failed to fetch satellite data");
    } finally {
      setLoadingSat(false);
    }
  };

  const layers = [
    // Animated flood zones (extruded 3D polygons showing water depth)
    new PolygonLayer({
      id: 'flood-zones',
      data: floodZones,
      pickable: true,
      stroked: true,
      filled: true,
      extruded: true,
      wireframe: false,
      opacity: 0.75,
      getPolygon: (d: any) => d.contour,
      getElevation: (d: any) => d.depth * 10,
      getFillColor: (d: any) => {
        const intensity = Math.min(255, d.depth * 8);
        return [0, 120 + (135 - intensity), 255, 190];
      },
      getLineColor: [100, 220, 255, 120],
      getLineWidth: 2,
      updateTriggers: {
        getPolygon: [time],
        getElevation: [time],
        getFillColor: [time]
      }
    }),
    
    // Water particles for flow effect
    new ScatterplotLayer({
      id: 'water-particles',
      data: waterParticles,
      pickable: false,
      opacity: 0.7,
      filled: true,
      getPosition: (d: any) => d.position,
      getRadius: (d: any) => d.radius,
      getFillColor: (d: any) => d.color,
      updateTriggers: {
        getPosition: [time],
        getRadius: [time]
      }
    })
  ];

  // Calculate stats
  const floodedAreaKm2 = (progress * 12.5).toFixed(1);
  const maxDepthM = (progress * 8.2).toFixed(1);
  const affectedPopulation = Math.floor(progress * 45000);

  return (
    <div style={{ position: 'relative', width: '100%', height: 'calc(100vh - 60px)', backgroundColor: '#090d16' }}>
      {/* HUD Panel */}
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

        {/* Basemap Selection */}
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

        {/* Animation Controls */}
        <div style={{ marginBottom: '16px', padding: '16px', background: 'linear-gradient(135deg, rgba(0,100,255,0.15), rgba(0,200,255,0.05))', borderRadius: '8px', border: '1px solid rgba(56,189,248,0.2)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <div style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px', fontSize: '14px' }}>
              <Activity size={16} color="#38bdf8" /> Dam Breach Simulation
            </div>
            <div style={{ fontSize: '13px', color: '#38bdf8', fontFamily: 'monospace', fontWeight: 700 }}>
              T+ {Math.floor(time / 10)} min
            </div>
          </div>
          
          {/* Progress bar */}
          <div style={{ width: '100%', height: '4px', backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: '2px', marginBottom: '12px' }}>
            <div style={{ width: `${progress * 100}%`, height: '100%', backgroundColor: '#38bdf8', borderRadius: '2px', transition: 'width 0.1s' }} />
          </div>
          
          <div style={{ display: 'flex', gap: '8px' }}>
            <button 
              className={`btn-${playing ? 'secondary' : 'primary'}`}
              style={{ flex: 1, justifyContent: 'center', padding: '10px' }}
              onClick={() => setPlaying(!playing)}
            >
              {playing ? <><Pause size={14} /> Pause</> : <><Play size={14} /> {time > 0 ? 'Resume' : 'Start Breach'}</>}
            </button>
            <button 
              className="btn-secondary"
              style={{ padding: '10px 14px' }}
              onClick={handleReset}
              title="Reset simulation"
            >
              <RotateCcw size={14} />
            </button>
          </div>
        </div>

        {/* Live Stats */}
        {progress > 0 && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px', marginBottom: '16px' }}>
            <div style={{ backgroundColor: 'rgba(0,0,0,0.3)', padding: '10px 8px', borderRadius: '6px', textAlign: 'center' }}>
              <div style={{ fontSize: '16px', fontWeight: 700, color: '#38bdf8' }}>{floodedAreaKm2}</div>
              <div style={{ fontSize: '10px', color: '#94a3b8', marginTop: '2px' }}>Area (km²)</div>
            </div>
            <div style={{ backgroundColor: 'rgba(0,0,0,0.3)', padding: '10px 8px', borderRadius: '6px', textAlign: 'center' }}>
              <div style={{ fontSize: '16px', fontWeight: 700, color: '#f59e0b' }}>{maxDepthM}m</div>
              <div style={{ fontSize: '10px', color: '#94a3b8', marginTop: '2px' }}>Max Depth</div>
            </div>
            <div style={{ backgroundColor: 'rgba(0,0,0,0.3)', padding: '10px 8px', borderRadius: '6px', textAlign: 'center' }}>
              <div style={{ fontSize: '16px', fontWeight: 700, color: '#ef4444' }}>{affectedPopulation.toLocaleString()}</div>
              <div style={{ fontSize: '10px', color: '#94a3b8', marginTop: '2px' }}>At Risk</div>
            </div>
          </div>
        )}

        <button 
          className="btn-secondary" 
          style={{ width: '100%', justifyContent: 'center', marginBottom: '12px' }}
          onClick={fetchSatelliteData}
          disabled={loadingSat}
        >
          <CloudRain size={16} /> {loadingSat ? 'Extracting...' : 'Live Satellite Analysis'}
        </button>

        {satResult && (
          <div style={{ backgroundColor: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '6px', fontSize: '13px' }}>
            <div style={{ color: '#22c55e', fontWeight: 600, marginBottom: '8px' }}>{satResult.message}</div>
            <div>Water Pixels: {satResult.outputs?.water_pixels?.toLocaleString()}</div>
            <div style={{ color: '#94a3b8', marginTop: '4px' }}>Satellite: {satResult.metadata?.satellite}</div>
          </div>
        )}

        <div style={{ marginTop: '16px', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '12px' }}>
          <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '1px' }}>Controls</div>
          <div style={{ fontSize: '12px', color: '#94a3b8' }}>• <b>Drag</b> to pan • <b>Ctrl+Drag</b> to rotate</div>
          <div style={{ fontSize: '12px', color: '#94a3b8' }}>• <b>Scroll</b> to zoom • <b>Right-click drag</b> to pitch</div>
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

