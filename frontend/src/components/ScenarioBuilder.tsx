import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { useProject } from '../context/ProjectContext';
import { Sliders, Zap } from 'lucide-react';

const ScenarioBuilder: React.FC = () => {
  const navigate = useNavigate();
  const { activeProject } = useProject();
  const [loading, setLoading] = useState(false);

  // Form states
  const [scenarioName, setScenarioName] = useState('Default Scenario');
  const [scenarioType, setScenarioType] = useState('Catastrophic Dam Break');
  const [engine, setEngine] = useState('SPH');
  const [simDuration, setSimDuration] = useState(12.0);
  const [timestep, setTimestep] = useState(1.0);

  // Dam Break params
  const [initWaterLevel, setInitWaterLevel] = useState(732.0);
  const [reservoirVolume, setReservoirVolume] = useState(1996000000);
  const [breachWidth, setBreachWidth] = useState(150.0);
  const [breachHeight, setBreachHeight] = useState(50.0);
  const [breachElevation, setBreachElevation] = useState(680.0);
  const [breachFormationTime, setBreachFormationTime] = useState(0.5);

  // Water Release params
  const [initialDischarge, setInitialDischarge] = useState(0.0);
  const [peakDischarge, setPeakDischarge] = useState(5000.0);
  const [releaseDuration, setReleaseDuration] = useState(6.0);

  // River Blockage params
  const [blockageHeight, setBlockageHeight] = useState(30.0);
  const [blockageVolume, setBlockageVolume] = useState(500000.0);
  const [failureTime, setFailureTime] = useState(2.0);

  const getParameters = () => {
    if (scenarioType === 'Catastrophic Dam Break') {
      return {
        initial_water_level: initWaterLevel,
        reservoir_volume: reservoirVolume,
        breach_width: breachWidth,
        breach_height: breachHeight,
        breach_elevation: breachElevation,
        breach_formation_time: breachFormationTime,
        initial_downstream_condition: 0.0
      };
    } else if (scenarioType === 'Controlled Water Release') {
      return {
        initial_water_level: initWaterLevel,
        initial_discharge: initialDischarge,
        peak_discharge: peakDischarge,
        release_duration: releaseDuration
      };
    } else {
      return {
        blockage_height: blockageHeight,
        blockage_volume: blockageVolume,
        failure_time: failureTime,
        breach_width: breachWidth,
        breach_formation_time: breachFormationTime
      };
    }
  };

  const handleQueueSimulation = async () => {
    if (!activeProject) return alert("Please select a project first");
    setLoading(true);
    try {
      let mappedScenarioType = "DAM_BREAK";
      if (scenarioType === "Controlled Water Release") mappedScenarioType = "WATER_RELEASE";
      else if (scenarioType === "River Blockage / Landslide") mappedScenarioType = "RIVER_BLOCKAGE";

      const scenarioRes = await api.post(`/projects/${activeProject.id}/scenarios`, {
        name: scenarioName,
        scenario_type: mappedScenarioType,
        description: "Created from UI",
        simulation_duration: simDuration,
        timestep: timestep,
        output_interval: 10.0,
        parameters: getParameters()
      });
      
      const scenarioId = scenarioRes.data.id;

      // START SIMULATION GATE
      try {
        await api.post(`/scenarios/${scenarioId}/validate`);
      } catch (validationErr: any) {
        const msg = validationErr?.response?.data?.detail || "Validation failed";
        alert(`Cannot start simulation. Missing inputs or invalid configuration:\n${msg}`);
        return; // Prevent simulation creation
      }

      await api.post('/simulations', {
        project_id: activeProject.id,
        scenario_id: scenarioId,
        engine: engine
      });
      
      navigate('/jobs');
    } catch (err: any) {
      console.error(err);
      const detail = err?.response?.data?.detail || "Unknown error";
      alert(`Failed to create scenario: ${detail}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <h2>Hydrological Scenario Builder</h2>
        <p style={{ color: 'var(--text-muted)' }}>Configure boundary conditions and failure modes before executing physics simulations.</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        <div className="card">
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
            <Sliders size={18} /> Scenario Parameters
          </h3>
          
          <div className="form-group" style={{ marginBottom: '12px' }}>
            <label className="form-label">Scenario Name</label>
            <input type="text" className="form-input" value={scenarioName} onChange={e => setScenarioName(e.target.value)} />
          </div>
          <div className="form-group" style={{ marginBottom: '16px' }}>
            <label className="form-label">Scenario Type</label>
            <select className="form-select" value={scenarioType} onChange={e => setScenarioType(e.target.value)}>
              <option value="Catastrophic Dam Break">Catastrophic Dam Break</option>
              <option value="Controlled Water Release">Controlled Water Release</option>
              <option value="River Blockage / Landslide">River Blockage / Landslide</option>
            </select>
          </div>
          
          {/* Dam Break Parameters */}
          {scenarioType === 'Catastrophic Dam Break' && (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Initial Reservoir Level (m)</label>
                  <input type="number" className="form-input" value={initWaterLevel} onChange={e => setInitWaterLevel(parseFloat(e.target.value))} />
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Reservoir Volume (m³)</label>
                  <input type="number" className="form-input" value={reservoirVolume} onChange={e => setReservoirVolume(parseFloat(e.target.value))} />
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Breach Width (m)</label>
                  <input type="number" className="form-input" value={breachWidth} onChange={e => setBreachWidth(parseFloat(e.target.value))} />
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Breach Height (m)</label>
                  <input type="number" className="form-input" value={breachHeight} onChange={e => setBreachHeight(parseFloat(e.target.value))} />
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Breach Elevation (m)</label>
                  <input type="number" className="form-input" value={breachElevation} onChange={e => setBreachElevation(parseFloat(e.target.value))} />
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Breach Formation Time (hrs)</label>
                  <input type="number" className="form-input" value={breachFormationTime} onChange={e => setBreachFormationTime(parseFloat(e.target.value))} />
                </div>
              </div>
            </>
          )}

          {/* Water Release Parameters */}
          {scenarioType === 'Controlled Water Release' && (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Initial Water Level (m)</label>
                  <input type="number" className="form-input" value={initWaterLevel} onChange={e => setInitWaterLevel(parseFloat(e.target.value))} />
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Initial Discharge (m³/s)</label>
                  <input type="number" className="form-input" value={initialDischarge} onChange={e => setInitialDischarge(parseFloat(e.target.value))} />
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Peak Discharge (m³/s)</label>
                  <input type="number" className="form-input" value={peakDischarge} onChange={e => setPeakDischarge(parseFloat(e.target.value))} />
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Release Duration (hrs)</label>
                  <input type="number" className="form-input" value={releaseDuration} onChange={e => setReleaseDuration(parseFloat(e.target.value))} />
                </div>
              </div>
            </>
          )}

          {/* River Blockage Parameters */}
          {scenarioType === 'River Blockage / Landslide' && (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Blockage Height (m)</label>
                  <input type="number" className="form-input" value={blockageHeight} onChange={e => setBlockageHeight(parseFloat(e.target.value))} />
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Blockage Volume (m³)</label>
                  <input type="number" className="form-input" value={blockageVolume} onChange={e => setBlockageVolume(parseFloat(e.target.value))} />
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Failure Time (hrs)</label>
                  <input type="number" className="form-input" value={failureTime} onChange={e => setFailureTime(parseFloat(e.target.value))} />
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Breach Width (m)</label>
                  <input type="number" className="form-input" value={breachWidth} onChange={e => setBreachWidth(parseFloat(e.target.value))} />
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Breach Time (hrs)</label>
                  <input type="number" className="form-input" value={breachFormationTime} onChange={e => setBreachFormationTime(parseFloat(e.target.value))} />
                </div>
              </div>
            </>
          )}
        </div>

        <div className="card">
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
            <Zap size={18} /> Execution Configuration
          </h3>
          
          <div className="form-group">
            <label className="form-label">Solver Engine</label>
            <select className="form-select" value={engine} onChange={e => setEngine(e.target.value)}>
              <option value="SPH">SPH (Smooth Particle Hydrodynamics)</option>
              <option value="DELFT3D">Delft3D Flexible Mesh</option>
            </select>
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">Simulation Duration (hrs)</label>
              <input type="number" className="form-input" value={simDuration} onChange={e => setSimDuration(parseFloat(e.target.value))} />
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">Time Step (sec)</label>
              <input type="number" className="form-input" value={timestep} onChange={e => setTimestep(parseFloat(e.target.value))} />
            </div>
          </div>
          
          <div style={{ backgroundColor: '#fffbe6', border: '1px solid #ffe58f', padding: '12px', borderRadius: '4px', fontSize: '13px', color: '#876800', marginBottom: '20px' }}>
            <strong>Notice:</strong> Running Delft3D requires the binary to be installed on the host OS. Otherwise, a test fixture will be returned.
          </div>
          
          <button 
            className="btn-primary" 
            style={{ width: '100%', justifyContent: 'center', padding: '12px' }}
            onClick={handleQueueSimulation}
            disabled={loading}
          >
            {loading ? "Queueing..." : "Queue Simulation Job"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ScenarioBuilder;
