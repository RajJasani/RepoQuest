'use client';
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';

const CalmCtx = createContext<{ calm: boolean; setCalm: (v: boolean) => void }>({
  calm: false,
  setCalm: () => {},
});

export function CalmProvider({ children }: { children: ReactNode }) {
  const [calm, setCalmState] = useState(false);
  useEffect(() => {
    let stored = false;
    try { stored = localStorage.getItem('rq-calm') === '1'; } catch {}
    setCalmState(stored);
    document.documentElement.dataset.calm = stored ? '1' : '0';
  }, []);
  const setCalm = (v: boolean) => {
    setCalmState(v);
    document.documentElement.dataset.calm = v ? '1' : '0';
    try { localStorage.setItem('rq-calm', v ? '1' : '0'); } catch {}
  };
  return <CalmCtx.Provider value={{ calm, setCalm }}>{children}</CalmCtx.Provider>;
}

export const useCalmMode = () => useContext(CalmCtx);
