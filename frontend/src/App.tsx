import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import AppShell from './components/ui/AppShell';
import { ProjectProvider } from './context/ProjectContext';
import MapViewer from './components/MapViewer';
import Map3DViewer from './components/Map3DViewer';
import Dashboard from './components/Dashboard';
import Projects from './components/Projects';
import ProjectWizard from './components/ProjectWizard';
import DataManagement from './components/DataManagement';
import ScenarioBuilder from './components/ScenarioBuilder';
import SimulationJobs from './components/SimulationJobs';
import Comparison from './components/Comparison';
import Exports from './components/Exports';
import HADRImpact from './components/HADRImpact';
import Satellite from './components/Satellite';
import SystemHealth from './components/SystemHealth';
import AssetAlignment from './components/AssetAlignment';
import './index.css';

function App() {
  return (
    <ProjectProvider>
      <Router>
        <AppShell>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/projects" element={<Projects />} />
            <Route path="/projects/new" element={<ProjectWizard />} />
            <Route path="/data" element={<DataManagement />} />
            <Route path="/scenarios" element={<ScenarioBuilder />} />
            <Route path="/jobs" element={<SimulationJobs />} />
            <Route path="/map" element={<MapViewer />} />
            <Route path="/map3d" element={<Map3DViewer />} />
            <Route path="/comparison" element={<Comparison />} />
            <Route path="/exports" element={<Exports />} />
            <Route path="/hadr" element={<HADRImpact />} />
            <Route path="/satellite" element={<Satellite />} />
            <Route path="/assets/align" element={<AssetAlignment />} />
            <Route path="/health" element={<SystemHealth />} />
          </Routes>
        </AppShell>
      </Router>
    </ProjectProvider>
  );
}

export default App;
