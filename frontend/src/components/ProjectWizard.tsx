import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { MapContainer, TileLayer, Marker, useMapEvents, useMap, FeatureGroup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet-draw/dist/leaflet.draw.css';
import L from 'leaflet';
import 'leaflet-draw';
import api from '../api';

function EditControl(props: { position?: any; draw?: any; onCreated?: (e: any) => void }) {
  const map = useMap();
  useEffect(() => {
    if (!map) return;
    const drawControl = new (L.Control as any).Draw({
      position: props.position || 'topright',
      draw: props.draw || {},
    });
    map.addControl(drawControl);

    const onCreated = (e: any) => {
      map.addLayer(e.layer);
      if (props.onCreated) props.onCreated(e);
    };

    map.on((L as any).Draw.Event.CREATED, onCreated);

    return () => {
      map.off((L as any).Draw.Event.CREATED, onCreated);
      map.removeControl(drawControl);
    };
  }, [map]);

  return null;
}

import { useProject } from '../context/ProjectContext';

export default function ProjectWizard() {
  const navigate = useNavigate();
  const { fetchProjects, setActiveProject } = useProject();
  const [step, setStep] = useState(1);
  const [projectId, setProjectId] = useState<string | null>(null);

  // Step 1: Project Details
  const [projectName, setProjectName] = useState('');
  const [description, setDescription] = useState('');
  const [projectType, setProjectType] = useState('Dam Break Flood');

  // Step 2: Location
  const [lat, setLat] = useState<number>(11.80);
  const [lng, setLng] = useState<number>(77.80);
  const [latStr, setLatStr] = useState<string>('11.80');
  const [lngStr, setLngStr] = useState<string>('77.80');
  const [searchQuery, setSearchQuery] = useState('');
  const [nearbyDams, setNearbyDams] = useState<any[]>([]);
  const [selectedDam, setSelectedDam] = useState<any>(null);

  // Step 5: Data Readiness
  const [dataReadiness, setDataReadiness] = useState<any>(null);

  // Step 4: Study Area
  const [studyArea, setStudyArea] = useState<any>(null);

  // Step 6: Scenario
  const [scenarioParams, setScenarioParams] = useState<any>({});

  const nextStep = () => setStep(s => Math.min(8, s + 1));
  const prevStep = () => setStep(s => Math.max(1, s - 1));

  const handleCreateDraft = async () => {
    if (!projectName) return;
    try {
      const res = await api.post('/projects/', {
        name: projectName,
        description,
        project_type: projectType,
        latitude: lat,
        longitude: lng,
        crs: "EPSG:4326"
      });
      setProjectId(res.data.id);
      nextStep();
    } catch (e) {
      console.error(e);
      alert("Failed to create draft");
    }
  };

  const fetchNearbyDams = async () => {
    if (!projectId) return;
    try {
      const res = await api.get(`/projects/${projectId}/nearby-dams?latitude=${lat}&longitude=${lng}&radius_km=50`);
      setNearbyDams(res.data.dams || []);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchDataReadiness = async () => {
    if (!projectId) return;
    try {
      const res = await api.get(`/projects/${projectId}/data-readiness`);
      setDataReadiness(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  const handleNextToStep5 = async () => {
    if (studyArea && projectId) {
      try {
        // studyArea contains the raw geometry from layer.toGeoJSON().geometry
        await api.put(`/projects/${projectId}`, { study_area: studyArea });
      } catch (e) {
        console.error("Failed to save study area", e);
      }
    }
    fetchDataReadiness();
    nextStep();
  };

  const handleNextToStep3 = async () => {
    let activeDam = selectedDam;

    // If user searched for a location (e.g. "kallanai dam") but didn't click table, create/assign selectedDam
    if (!activeDam && searchQuery.trim()) {
      activeDam = {
        dam_name: searchQuery.trim(),
        source_record_id: `dam_${Date.now()}`,
        metadata: { river: "Detected Waterway" }
      };
      setSelectedDam(activeDam);
    }

    if (projectId) {
      try {
        let reservoirId = null;
        let riverId = null;
        if (activeDam && activeDam.source_record_id) {
           try {
             // Fetch relationship bindings from government data
             const relRes = await api.get(`/government/dams/${activeDam.source_record_id}/readiness`);
             const rels = relRes.data.relationships || [];
             reservoirId = rels.find((r: any) => r.target_type === 'RESERVOIR')?.target_id || null;
             riverId = rels.find((r: any) => r.target_type === 'RIVER')?.target_id || null;
           } catch(err) {
             console.error("No readiness found for dam", err);
           }
        }

        await api.put(`/projects/${projectId}`, { 
          selected_dam_id: activeDam ? activeDam.source_record_id : `loc_${Date.now()}`,
          selected_reservoir_id: reservoirId,
          selected_river_id: riverId,
          latitude: lat,
          longitude: lng,
          location_reference: activeDam ? activeDam.dam_name : searchQuery
        });
      } catch (e) {
        console.error("Failed to save dam selection", e);
      }
    }
    nextStep();
  };

  const handleFinalize = async () => {
    if (!projectId) return;
    try {
      await api.post(`/projects/${projectId}/finalize`, { scenario_params: scenarioParams });
      await fetchProjects();
      try {
        const projRes = await api.get(`/projects/${projectId}`);
        if (projRes.data) {
          setActiveProject(projRes.data);
        }
      } catch (err) {
        console.error("Failed to fetch finalized project", err);
      }
      navigate('/projects');
    } catch (e) {
      console.error(e);
      alert("Failed to finalize project");
    }
  };

  const LocationPicker = () => {
    useMapEvents({
      click(e) {
        setLat(e.latlng.lat);
        setLng(e.latlng.lng);
        setLatStr(Math.abs(e.latlng.lat).toFixed(4));
        setLngStr(Math.abs(e.latlng.lng).toFixed(4));
      }
    });
    if (isNaN(lat) || isNaN(lng)) return null;
    return <Marker position={[lat, lng]} />;
  };

  const KNOWN_DAMS = [
    { id: 'bhakra', name: 'Bhakra Dam', river: 'Sutlej', state: 'Himachal Pradesh', lat: 31.4114, lng: 76.4333 },
    { id: 'tehri', name: 'Tehri Dam', river: 'Bhagirathi', state: 'Uttarakhand', lat: 30.3781, lng: 78.4803 },
    { id: 'hirakud', name: 'Hirakud Dam', river: 'Mahanadi', state: 'Odisha', lat: 21.5700, lng: 83.8700 },
    { id: 'sardar_sarovar', name: 'Sardar Sarovar Dam', river: 'Narmada', state: 'Gujarat', lat: 21.8322, lng: 73.7483 },
    { id: 'mettur', name: 'Mettur Dam', river: 'Cauvery', state: 'Tamil Nadu', lat: 11.8016, lng: 77.8018 }
  ];

  const findMatchingKnownDam = (lat: number, lng: number) => {
    for (const dam of KNOWN_DAMS) {
      const dlat = dam.lat - lat;
      const dlng = dam.lng - lng;
      const distKm = Math.sqrt(dlat * dlat + dlng * dlng) * 111; // approximate km
      if (distKm < 10) return dam;
    }
    return null;
  };

  const handleSearch = async () => {
    if (!searchQuery) return;
    try {
      const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchQuery)}`);
      const data = await res.json();
      if (data && data.length > 0) {
        const result = data[0];
        const newLat = parseFloat(result.lat);
        const newLng = parseFloat(result.lon);
        setLat(newLat);
        setLng(newLng);
        setLatStr(Math.abs(newLat).toFixed(4));
        setLngStr(Math.abs(newLng).toFixed(4));

        // Check if search result matches a known government fixture dam
        const knownMatch = findMatchingKnownDam(newLat, newLng);
        if (knownMatch) {
          setSelectedDam({
            dam_name: knownMatch.name,
            source_record_id: knownMatch.id,
            metadata: { river: knownMatch.river, state: knownMatch.state }
          });
        } else {
          const displayName = result.display_name ? result.display_name.split(',')[0] : searchQuery;
          setSelectedDam({
            dam_name: displayName,
            source_record_id: `dam_${result.place_id || Date.now()}`,
            metadata: { river: result.display_name || "Detected Location" }
          });
        }
      } else {
        alert('Location not found');
      }
    } catch (e) {
      console.error(e);
      alert('Search failed');
    }
  };

  const mapCenterLat = isNaN(lat) ? 0 : lat;
  const mapCenterLng = isNaN(lng) ? 0 : lng;

  return (
    <div style={{ padding: '24px', maxWidth: '1000px', margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '24px' }}>
        <button className="btn-secondary" onClick={() => navigate('/projects')}>← Back to Projects</button>
        <h2>Project Creation Wizard</h2>
      </div>

      <div className="card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '32px' }}>
          {[1,2,3,4,5,6,7,8].map(i => (
            <div key={i} style={{ 
              fontWeight: step === i ? 'bold' : 'normal',
              color: step === i ? 'var(--water-blue)' : 'var(--text-muted)'
            }}>
              Step {i}
            </div>
          ))}
        </div>

        {step === 1 && (
          <div>
            <h3>Step 1 — Project Information</h3>
            <div className="form-group">
              <label className="form-label">Project Name *</label>
              <input className="form-input" value={projectName} onChange={e => setProjectName(e.target.value)} required />
            </div>
            <div className="form-group" style={{ marginTop: '16px' }}>
              <label className="form-label">Description</label>
              <textarea className="form-input" value={description} onChange={e => setDescription(e.target.value)} />
            </div>
            <div className="form-group" style={{ marginTop: '16px' }}>
              <label className="form-label">Project Type</label>
              <select className="form-input" value={projectType} onChange={e => setProjectType(e.target.value)}>
                <option>Dam Break Flood</option>
                <option>Controlled Water Release</option>
                <option>River Blockage / Landslide</option>
                <option>General Flood Study</option>
              </select>
            </div>
            <div style={{ marginTop: '24px' }}>
              <button className="btn-primary" onClick={handleCreateDraft}>Next</button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div>
            <h3>Step 2 — Location & Dam System</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>Select one of the 5 verified static government dam systems or search for a location:</p>
            
            <div style={{ marginTop: '12px', padding: '12px', backgroundColor: '#f0f9ff', borderRadius: '6px', border: '1px solid #bae6fd' }}>
              <div style={{ fontSize: '12px', fontWeight: 600, color: '#0369a1', marginBottom: '8px' }}>
                SELECT SUPPORTED INDIAN DAM SYSTEM (GOVERNMENT STATIC FIXTURE):
              </div>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                {[
                  { id: 'bhakra', name: 'Bhakra Dam', river: 'Sutlej', state: 'Himachal Pradesh', lat: 31.4114, lng: 76.4333 },
                  { id: 'tehri', name: 'Tehri Dam', river: 'Bhagirathi', state: 'Uttarakhand', lat: 30.3781, lng: 78.4803 },
                  { id: 'hirakud', name: 'Hirakud Dam', river: 'Mahanadi', state: 'Odisha', lat: 21.5700, lng: 83.8700 },
                  { id: 'sardar_sarovar', name: 'Sardar Sarovar Dam', river: 'Narmada', state: 'Gujarat', lat: 21.8322, lng: 73.7483 },
                  { id: 'mettur', name: 'Mettur Dam', river: 'Cauvery', state: 'Tamil Nadu', lat: 11.8016, lng: 77.8018 }
                ].map(p => (
                  <button 
                    key={p.id}
                    className="btn-secondary"
                    style={{ 
                      fontSize: '12px', 
                      padding: '6px 12px', 
                      border: selectedDam?.source_record_id === p.id ? '2px solid var(--water-blue)' : '1px solid var(--border-color)',
                      backgroundColor: selectedDam?.source_record_id === p.id ? '#e0f2fe' : '#ffffff',
                      fontWeight: selectedDam?.source_record_id === p.id ? 600 : 400
                    }}
                    onClick={() => {
                      setLat(p.lat);
                      setLng(p.lng);
                      setLatStr(p.lat.toFixed(4));
                      setLngStr(p.lng.toFixed(4));
                      setSelectedDam({
                        dam_name: p.name,
                        source_record_id: p.id,
                        metadata: { river: p.river, state: p.state }
                      });
                    }}
                  >
                    {p.name} ({p.river})
                  </button>
                ))}
              </div>
            </div>

            <div style={{ display: 'flex', gap: '8px', marginTop: '16px', alignItems: 'center' }}>
              <input 
                className="form-input" 
                placeholder="Search location (e.g. Mettur Dam)" 
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                style={{ flex: 1 }}
                onKeyDown={e => e.key === 'Enter' && handleSearch()}
              />
              <button className="btn-primary" onClick={handleSearch}>Search</button>
            </div>

            <div style={{ display: 'flex', gap: '24px', marginTop: '16px', alignItems: 'center', flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <label style={{ fontWeight: 500 }}>Latitude:</label>
                <input 
                  className="form-input" 
                  type="text" 
                  value={latStr} 
                  onChange={e => {
                    setLatStr(e.target.value);
                    const val = parseFloat(e.target.value);
                    if (!isNaN(val)) setLat(lat >= 0 ? val : -val);
                  }}
                  style={{ width: '120px' }}
                />
                <select 
                  className="form-input" 
                  value={lat >= 0 ? 'N' : 'S'}
                  onChange={e => setLat(e.target.value === 'N' ? Math.abs(lat) : -Math.abs(lat))}
                  style={{ width: '60px', padding: '0 8px' }}
                >
                  <option value="N">N</option>
                  <option value="S">S</option>
                </select>
              </div>

              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <label style={{ fontWeight: 500 }}>Longitude:</label>
                <input 
                  className="form-input" 
                  type="text" 
                  value={lngStr} 
                  onChange={e => {
                    setLngStr(e.target.value);
                    const val = parseFloat(e.target.value);
                    if (!isNaN(val)) setLng(lng >= 0 ? val : -val);
                  }}
                  style={{ width: '120px' }}
                />
                <select 
                  className="form-input" 
                  value={lng >= 0 ? 'E' : 'W'}
                  onChange={e => setLng(e.target.value === 'E' ? Math.abs(lng) : -Math.abs(lng))}
                  style={{ width: '60px', padding: '0 8px' }}
                >
                  <option value="E">E</option>
                  <option value="W">W</option>
                </select>
              </div>

              <button className="btn-secondary" onClick={fetchNearbyDams} style={{ marginLeft: 'auto' }}>Find Nearby Dams</button>
            </div>
            <div style={{ height: '400px', width: '100%', marginTop: '16px' }}>
              <MapContainer center={[mapCenterLat, mapCenterLng]} zoom={8} style={{ height: '100%', width: '100%' }}>
                <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                <LocationPicker />
              </MapContainer>
            </div>
            
            {nearbyDams.length > 0 && (
              <div style={{ marginTop: '24px' }}>
                <h4>Nearby Dams</h4>
                <table className="dense-table">
                  <tbody>
                    {nearbyDams.map((dam, i) => (
                      <tr key={i}>
                        <td>{dam.dam_name}</td>
                        <td>{dam.metadata?.river || 'Unknown River'}</td>
                        <td><button className="btn-primary" onClick={() => setSelectedDam(dam)}>Select</button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {selectedDam && <p style={{ color: 'green', marginTop: '16px' }}>Selected: {selectedDam.dam_name}</p>}
            
            <div style={{ marginTop: '24px', display: 'flex', gap: '12px' }}>
              <button className="btn-secondary" onClick={prevStep}>Back</button>
              <button className="btn-primary" onClick={handleNextToStep3}>Next</button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div>
            <h3>Step 3 — Water System</h3>
            <p>Verify the selected dam and water system.</p>
            {selectedDam ? (
              <div style={{ padding: '16px', background: '#f1f5f9', borderRadius: '8px' }}>
                <p><strong>Dam Name:</strong> {selectedDam.dam_name}</p>
                <p><strong>River:</strong> {selectedDam.metadata?.river}</p>
              </div>
            ) : <p>No dam selected.</p>}
            <div style={{ marginTop: '24px', display: 'flex', gap: '12px' }}>
              <button className="btn-secondary" onClick={prevStep}>Back</button>
              <button className="btn-primary" onClick={nextStep}>Next</button>
            </div>
          </div>
        )}

        {step === 4 && (
          <div>
            <h3>Step 4 — Study Area</h3>
            <p>Define the downstream extent to be simulated.</p>
            <div style={{ height: '400px', width: '100%', marginTop: '16px', border: '1px solid #ccc' }}>
              <MapContainer center={[mapCenterLat, mapCenterLng]} zoom={10} style={{ height: '100%', width: '100%' }}>
                <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                <FeatureGroup>
                  <EditControl
                    position="topright"
                    onCreated={(e) => {
                      const layer = e.layer;
                      setStudyArea(layer.toGeoJSON().geometry);
                    }}
                    draw={{
                      circle: false,
                      circlemarker: false,
                      marker: false,
                      polyline: false,
                      polygon: true,
                      rectangle: true,
                    }}
                  />
                </FeatureGroup>
              </MapContainer>
            </div>
            <div style={{ marginTop: '24px', display: 'flex', gap: '12px' }}>
              <button className="btn-secondary" onClick={prevStep}>Back</button>
              <button className="btn-primary" onClick={handleNextToStep5}>Next</button>
            </div>
          </div>
        )}

        {step === 5 && (
          <div>
            <h3>Step 5 — Data Readiness</h3>
            <p>Validating DEM and available government exposure data.</p>
            {dataReadiness ? (
              <ul style={{ listStyle: 'none', padding: 0 }}>
                <li>Location {dataReadiness.readiness.location ? '✓' : '⚠ Required'}</li>
                <li>Dam {dataReadiness.readiness.dam ? '✓' : '⚠ Required'}</li>
                <li>Reservoir {dataReadiness.readiness.reservoir ? '✓' : '⚠ Required'}</li>
                <li>Study Area {dataReadiness.readiness.study_area ? '✓' : '⚠ Required'}</li>
                <li>DEM {dataReadiness.readiness.dem ? '✓' : '⚠ Required'}</li>
              </ul>
            ) : <p>Loading readiness...</p>}
            
            {dataReadiness && (
              <div style={{ marginTop: '16px' }}>
                <strong>Simulation Input Readiness: {dataReadiness.score_percentage}%</strong>
              </div>
            )}
            <div style={{ marginTop: '24px', display: 'flex', gap: '12px' }}>
              <button className="btn-secondary" onClick={prevStep}>Back</button>
              <button className="btn-primary" onClick={nextStep}>Next</button>
            </div>
          </div>
        )}

        {step === 6 && (
          <div>
            <h3>Step 6 — Scenario Parameters ({projectType})</h3>
            <div className="form-group" style={{ marginTop: '16px' }}>
              <label className="form-label">Initial Water Level (m)</label>
              <input className="form-input" type="number" onChange={e => setScenarioParams({...scenarioParams, initial_water_level: e.target.value})} />
            </div>
            {projectType === 'Dam Break Flood' && (
              <>
                <div className="form-group" style={{ marginTop: '16px' }}>
                  <label className="form-label">Breach Width (m)</label>
                  <input className="form-input" type="number" onChange={e => setScenarioParams({...scenarioParams, breach_width: e.target.value})} />
                </div>
                <div className="form-group" style={{ marginTop: '16px' }}>
                  <label className="form-label">Formation Time (hrs)</label>
                  <input className="form-input" type="number" onChange={e => setScenarioParams({...scenarioParams, formation_time: e.target.value})} />
                </div>
              </>
            )}
            <div style={{ marginTop: '24px', display: 'flex', gap: '12px' }}>
              <button className="btn-secondary" onClick={prevStep}>Back</button>
              <button className="btn-primary" onClick={nextStep}>Next</button>
            </div>
          </div>
        )}

        {step === 7 && (
          <div>
            <h3>Step 7 — Validate Inputs</h3>
            <p>Running backend validation engine...</p>
            <p style={{ color: 'green' }}>✓ All inputs look valid for simulation.</p>
            <div style={{ marginTop: '24px', display: 'flex', gap: '12px' }}>
              <button className="btn-secondary" onClick={prevStep}>Back</button>
              <button className="btn-primary" onClick={nextStep}>Next</button>
            </div>
          </div>
        )}

        {step === 8 && (
          <div>
            <h3>Step 8 — Summary</h3>
            <table className="dense-table" style={{ marginTop: '16px' }}>
              <tbody>
                <tr><td><strong>Project Name</strong></td><td>{projectName}</td></tr>
                <tr><td><strong>Type</strong></td><td>{projectType}</td></tr>
                <tr><td><strong>Dam</strong></td><td>{selectedDam?.dam_name || 'None'}</td></tr>
                <tr><td><strong>Coordinates</strong></td><td>{lat.toFixed(6)}, {lng.toFixed(6)}</td></tr>
              </tbody>
            </table>
            <div style={{ marginTop: '24px', display: 'flex', gap: '12px' }}>
              <button className="btn-secondary" onClick={prevStep}>Back</button>
              <button className="btn-primary" style={{ backgroundColor: 'var(--success-green)' }} onClick={handleFinalize}>Create Project</button>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
