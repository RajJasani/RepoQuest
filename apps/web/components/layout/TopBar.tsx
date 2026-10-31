'use client';

import React, { useState, useEffect } from 'react';
import { useTheme } from 'next-themes';
import { useCalmMode } from '@/lib/calm';
import { useSettings, SupportedLanguage } from '@/lib/settings-context';
import { PrivacyBadge } from './PrivacyBadge';
import { cn } from '@/lib/utils';
import { ChevronDown, Moon, Sun, Sparkles, Globe, GitFork } from 'lucide-react';
import { useRouter } from 'next/navigation';

export function TopBar({ className }: { className?: string }) {
  const { theme, setTheme } = useTheme();
  const { calm, setCalm } = useCalmMode();
  const {
    repos,
    selectedRepoId,
    setSelectedRepoId,
    selectedRepo,
    language,
    setLanguage,
  } = useSettings();
  const router = useRouter();

  // Scroll direction detection (hides on scroll down, returns on scroll up over 200ms)
  const [isVisible, setIsVisible] = useState(true);
  const [lastScrollY, setLastScrollY] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      const currentScrollY = window.scrollY;
      if (currentScrollY > 60) {
        if (currentScrollY > lastScrollY && isVisible) {
          setIsVisible(false); // scrolling down
        } else if (currentScrollY < lastScrollY && !isVisible) {
          setIsVisible(true); // scrolling up
        }
      } else {
        setIsVisible(true);
      }
      setLastScrollY(currentScrollY);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [lastScrollY, isVisible]);

  // Dropdown states
  const [repoDropdownOpen, setRepoDropdownOpen] = useState(false);
  const [langDropdownOpen, setLangDropdownOpen] = useState(false);

  const languages: { code: SupportedLanguage; label: string; script: string }[] = [
    { code: 'en', label: 'English', script: 'English' },
    { code: 'hi', label: 'Hindi', script: 'हिन्दी' },
    { code: 'kn', label: 'Kannada', script: 'ಕನ್ನಡ' },
    { code: 'ta', label: 'Tamil', script: 'தமிழ்' },
  ];

  const handleRepoSelect = (repoId: string) => {
    setSelectedRepoId(repoId);
    setRepoDropdownOpen(false);
    router.push(`/repos/${repoId}`);
  };

  return (
    <header
      className={cn(
        'sticky top-0 z-20 h-14 w-full bg-surface-1/85 backdrop-blur-md border-b border-border px-4 flex items-center justify-between transition-transform duration-200 ease-out select-none',
        !isVisible && '-translate-y-full',
        className
      )}
      aria-label="Application Top Bar"
    >
      {/* Left: Repository Switcher */}
      <div className="relative">
        <button
          type="button"
          onClick={() => setRepoDropdownOpen(!repoDropdownOpen)}
          className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg border border-border bg-surface-2 text-xs font-mono font-medium hover:bg-surface-3 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
          aria-expanded={repoDropdownOpen}
          aria-haspopup="listbox"
        >
          <GitFork className="w-3.5 h-3.5 text-text-muted" />
          <span className="truncate max-w-[140px] sm:max-w-[200px] text-text">
            {selectedRepo ? selectedRepo.full_name : 'Select repository...'}
          </span>
          <ChevronDown className="w-3.5 h-3.5 text-text-muted" />
        </button>

        {repoDropdownOpen && (
          <>
            <div
              className="fixed inset-0 z-30"
              onClick={() => setRepoDropdownOpen(false)}
              aria-hidden="true"
            />
            <div
              role="listbox"
              className="absolute left-0 top-full mt-1.5 z-40 w-64 rounded-xl border border-border bg-surface-2 p-1.5 shadow-xl space-y-0.5"
            >
              <div className="px-2 py-1 text-[11px] font-mono text-text-muted uppercase">
                Repositories
              </div>
              {repos.length === 0 ? (
                <div className="px-2 py-2 text-xs text-text-muted">No repositories yet</div>
              ) : (
                repos.map((repo) => (
                  <button
                    key={repo.id}
                    type="button"
                    onClick={() => handleRepoSelect(repo.id)}
                    className={cn(
                      'w-full text-left px-2.5 py-1.5 rounded-md text-xs font-mono flex items-center justify-between transition-colors',
                      repo.id === selectedRepoId
                        ? 'bg-brand/15 text-brand font-semibold'
                        : 'text-text hover:bg-surface-3'
                    )}
                  >
                    <span className="truncate">{repo.full_name}</span>
                    <span className="text-[10px] text-text-muted capitalize">{repo.status}</span>
                  </button>
                ))
              )}
            </div>
          </>
        )}
      </div>

      {/* Right Controls: Language, Privacy Badge, Theme, Calm */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Language Selector */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setLangDropdownOpen(!langDropdownOpen)}
            className="flex items-center gap-1.5 px-2 py-1 rounded-md border border-border bg-surface-2 text-xs text-text-muted hover:text-text hover:bg-surface-3 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
            title="Select Language"
            aria-expanded={langDropdownOpen}
          >
            <Globe className="w-3.5 h-3.5" />
            <span className="uppercase font-mono text-[11px] hidden sm:inline">
              {language}
            </span>
          </button>

          {langDropdownOpen && (
            <>
              <div
                className="fixed inset-0 z-30"
                onClick={() => setLangDropdownOpen(false)}
                aria-hidden="true"
              />
              <div className="absolute right-0 top-full mt-1.5 z-40 w-36 rounded-lg border border-border bg-surface-2 p-1 shadow-lg space-y-0.5">
                {languages.map((l) => (
                  <button
                    key={l.code}
                    type="button"
                    onClick={() => {
                      setLanguage(l.code);
                      setLangDropdownOpen(false);
                    }}
                    className={cn(
                      'w-full text-left px-2.5 py-1 rounded text-xs flex justify-between items-center transition-colors',
                      language === l.code
                        ? 'bg-brand/15 text-brand font-semibold'
                        : 'text-text hover:bg-surface-3'
                    )}
                  >
                    <span>{l.label}</span>
                    <span className="text-[10px] text-text-muted">{l.script}</span>
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Privacy Badge */}
        <PrivacyBadge />

        {/* Calm Mode Toggle */}
        <button
          type="button"
          onClick={() => setCalm(!calm)}
          className={cn(
            'p-1.5 rounded-lg border text-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand',
            calm
              ? 'bg-mint/15 text-mint border-mint/30'
              : 'bg-surface-2 text-text-muted hover:text-text border-border'
          )}
          title={calm ? 'Calm Mode is ON (animations paused)' : 'Turn ON Calm Mode'}
          aria-label={calm ? 'Calm Mode Active' : 'Calm Mode Inactive'}
        >
          <Sparkles className="w-4 h-4" />
        </button>

        {/* Theme Toggle */}
        <button
          type="button"
          onClick={() => setTheme(theme === 'dusk' ? 'parchment' : 'dusk')}
          className="p-1.5 rounded-lg border border-border bg-surface-2 text-text-muted hover:text-text transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
          title={`Switch to ${theme === 'dusk' ? 'Parchment (Light)' : 'Dusk (Dark)'} theme`}
          aria-label="Toggle Theme"
        >
          {theme === 'dusk' ? (
            <Sun className="w-4 h-4" />
          ) : (
            <Moon className="w-4 h-4" />
          )}
        </button>
      </div>
    </header>
  );
}

export default TopBar;
