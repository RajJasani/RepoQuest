'use client';

import React, { createContext, useContext, useState, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import {
  HealthResponse,
  HealthResponseSchema,
  SettingsResponse,
  SettingsResponseSchema,
  RepoSummary,
  ReposListResponseSchema,
} from '@/lib/schemas';

export type SupportedLanguage = 'en' | 'hi' | 'kn' | 'ta';

interface SettingsContextValue {
  settings: SettingsResponse | null;
  health: HealthResponse | null;
  repos: RepoSummary[];
  selectedRepo: RepoSummary | null;
  selectedRepoId: string | null;
  setSelectedRepoId: (id: string | null) => void;
  language: SupportedLanguage;
  setLanguage: (lang: SupportedLanguage) => void;
  isLocalOnly: boolean;
  isBackendOffline: boolean;
  isOllamaDown: boolean;
  refetchHealth: () => void;
  refetchSettings: () => void;
  refetchRepos: () => void;
}

const SettingsContext = createContext<SettingsContextValue | null>(null);

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const [selectedRepoId, setSelectedRepoId] = useState<string | null>(null);
  const [language, setLanguageState] = useState<SupportedLanguage>('en');

  // Load language preference from localStorage if available
  useEffect(() => {
    try {
      const stored = localStorage.getItem('rq-language') as SupportedLanguage;
      if (stored && ['en', 'hi', 'kn', 'ta'].includes(stored)) {
        setLanguageState(stored);
      }
    } catch {
      // Ignore
    }
  }, []);

  const setLanguage = (lang: SupportedLanguage) => {
    setLanguageState(lang);
    try {
      localStorage.setItem('rq-language', lang);
    } catch {
      // Ignore
    }
  };

  // Health Query (checks every 15s)
  const healthQuery = useQuery({
    queryKey: ['system', 'health'],
    queryFn: async () => {
      const data = await api.get<unknown>('/health');
      return HealthResponseSchema.parse(data);
    },
    refetchInterval: 15000,
  });

  // Settings Query
  const settingsQuery = useQuery({
    queryKey: ['settings'],
    queryFn: async () => {
      const data = await api.get<unknown>('/settings');
      return SettingsResponseSchema.parse(data);
    },
    staleTime: 60000,
  });

  // Repositories Query
  const reposQuery = useQuery({
    queryKey: ['repos'],
    queryFn: async () => {
      const data = await api.get<unknown>('/repos');
      return ReposListResponseSchema.parse(data);
    },
    staleTime: 30000,
  });

  const repos = useMemo(() => reposQuery.data || [], [reposQuery.data]);

  // Default selected repo to first ready or indexed repo if none selected
  useEffect(() => {
    if (!selectedRepoId && repos.length > 0) {
      const readyRepo = repos.find((r) => r.status === 'ready') || repos[0];
      setSelectedRepoId(readyRepo.id);
    }
  }, [repos, selectedRepoId]);

  const selectedRepo = repos.find((r) => r.id === selectedRepoId) || null;

  const settings = settingsQuery.data || null;
  const health = healthQuery.data || null;

  const isBackendOffline = healthQuery.isError;
  const isOllamaDown = Boolean(
    health && (health.ollama === 'down' || health.status === 'degraded')
  );

  // Local-only check: base url has localhost or 127.0.0.1 or offline_mode is true
  const isLocalOnly = Boolean(
    settings?.offline_mode ||
      (settings?.ollama_base_url &&
        (settings.ollama_base_url.includes('localhost') ||
          settings.ollama_base_url.includes('127.0.0.1')))
  );

  return (
    <SettingsContext.Provider
      value={{
        settings,
        health,
        repos,
        selectedRepo,
        selectedRepoId,
        setSelectedRepoId,
        language,
        setLanguage,
        isLocalOnly,
        isBackendOffline,
        isOllamaDown,
        refetchHealth: healthQuery.refetch,
        refetchSettings: settingsQuery.refetch,
        refetchRepos: reposQuery.refetch,
      }}
    >
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  const ctx = useContext(SettingsContext);
  if (!ctx) {
    throw new Error('useSettings must be used within SettingsProvider');
  }
  return ctx;
}
