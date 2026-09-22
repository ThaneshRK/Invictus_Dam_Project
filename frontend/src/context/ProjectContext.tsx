import React, { createContext, useState, useContext, useEffect } from 'react';
import type { ReactNode } from 'react';
import api from '../api';

export interface Project {
  id: string;
  name: string;
  description: string;
  latitude?: number;
  longitude?: number;
  study_area: any;
  crs: string;
  created_at: string;
  updated_at: string;
}

interface ProjectContextType {
  projects: Project[];
  activeProject: Project | null;
  setActiveProject: (project: Project | null) => void;
  fetchProjects: () => Promise<void>;
  createProject: (name: string, description: string, lat?: number, lng?: number) => Promise<Project>;
  loading: boolean;
  error: string | null;
}

const ProjectContext = createContext<ProjectContextType | undefined>(undefined);

export const ProjectProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProjects = async () => {
    setLoading(true);
    try {
      const res = await api.get('/projects/'); 
      setProjects(res.data);
      if (res.data.length > 0 && !activeProject) {
        setActiveProject(res.data[0]);
      }
      setError(null);
    } catch (err) {
      console.error(err);
      setError('Failed to fetch projects.');
    } finally {
      setLoading(false);
    }
  };

  const createProject = async (name: string, description: string, lat?: number, lng?: number) => {
    try {
      const payload: any = { name, description };
      if (lat !== undefined) payload.latitude = lat;
      if (lng !== undefined) payload.longitude = lng;
      
      const res = await api.post('/projects/', payload); 
      await fetchProjects();
      setActiveProject(res.data);
      return res.data;
    } catch (err) {
      console.error(err);
      throw new Error('Failed to create project');
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  return (
    <ProjectContext.Provider value={{ projects, activeProject, setActiveProject, fetchProjects, createProject, loading, error }}>
      {children}
    </ProjectContext.Provider>
  );
};

export const useProject = () => {
  const context = useContext(ProjectContext);
  if (context === undefined) {
    throw new Error('useProject must be used within a ProjectProvider');
  }
  return context;
};
