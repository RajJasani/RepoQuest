'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useReducedMotion } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';
import { useSettings } from '@/lib/settings-context';
import { api, ApiError } from '@/lib/api';
import { HealthResponse, HealthResponseSchema } from '@/lib/schemas';

import { AppShell } from '@/components/layout/AppShell';
import { Pip, PipState } from '@/components/brand/Pip';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { showToast } from '@/components/ui/Toast';
import { Copy, Check, Terminal, ExternalLink, ArrowRight, RotateCcw } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function SetupPage() {
  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStill = Boolean(reduce) || calm;

  const { refetchHealth } = useSettings();

  // Test state
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<HealthResponse | null>(null);
  const [testError, setTestError] = useState<string | null>(null);

  // Copied state per command
  const [copiedCmd, setCopiedCmd] = useState<string | null>(null);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCmd(text);
    showToast.info('Copied command to clipboard');
    setTimeout(() => {
      setCopiedCmd((prev) => (prev === text ? null : prev));
    }, 2000);
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestError(null);
    try {
      const data = await api.get<unknown>('/health');
      const parsed = HealthResponseSchema.parse(data);
      setTestResult(parsed);
      refetchHealth();

      const isAllOk =
        (parsed.database === 'ok' || parsed.db === 'ok') &&
        parsed.ollama === 'ok';

      if (isAllOk) {
        showToast.success('Connection successful! All services online.');
      } else if (parsed.ollama !== 'ok') {
        showToast.warning('Ollama is not responding. Ensure "ollama serve" is running.');
      } else {
        showToast.warning('Database is degraded. Start PostgreSQL on port 5432.');
      }
    } catch (err: unknown) {
      const msg =
        err instanceof ApiError
          ? err.message
          : 'Could not connect to FastAPI server at localhost:8000';
      setTestError(msg);
      showToast.error(msg);
    } finally {
      setTesting(false);
    }
  };

  // Determine Pip state: sleeping initially, turns idle or success when Ollama connection passes (A6)
  const isSetupSuccessful =
    testResult &&
    (testResult.database === 'ok' || testResult.db === 'ok') &&
    testResult.ollama === 'ok';

  let currentPipState: PipState = 'sleeping';
  if (isSetupSuccessful) {
    currentPipState = 'idle';
  } else if (testResult?.ollama === 'down' || testError) {
    currentPipState = 'error';
  } else if (testing) {
    currentPipState = 'thinking';
  }

  const commands = {
    install: 'curl -fsSL https://ollama.com/install.sh | sh',
    chatModel: 'ollama pull gemma3:4b',
    embedModel: 'ollama pull nomic-embed-text',
  };

  return (
    <AppShell showSidebar={false}>
      <div className="max-w-3xl mx-auto py-8 space-y-10">
        {/* Header with Mascot */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-6 p-6 rounded-2xl bg-surface-1 border border-border shadow-card">
          <div className="space-y-2 text-center sm:text-left">
            <span className="font-pixel text-xs text-amber uppercase tracking-wider">
              FIRST-RUN WIZARD
            </span>
            <h1 className="font-display font-bold text-3xl text-text">
              Local AI Setup Checklist
            </h1>
            <p className="text-sm text-text-muted max-w-md leading-relaxed">
              RepoQuest runs 100% locally on your machine with zero external subscriptions. Follow these 3 steps to configure Ollama and local models.
            </p>
          </div>

          <div className="w-28 h-28 flex-shrink-0 flex items-center justify-center bg-surface-2 rounded-xl border border-border p-2">
            <Pip state={currentPipState} size={96} />
          </div>
        </div>

        {/* 3-Step Vertical Checklist */}
        <div className="space-y-6">
          {/* STEP 1: Install Ollama */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-7 h-7 rounded-full bg-brand/15 text-brand font-mono font-bold text-xs flex items-center justify-center">
                    1
                  </div>
                  <CardTitle className="text-base sm:text-lg">
                    Install Ollama
                  </CardTitle>
                </div>
                <a
                  href="https://ollama.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-brand hover:underline"
                >
                  <span>ollama.com</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
              <CardDescription>
                Download and install Ollama for macOS, Linux, or Windows.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between bg-surface-2 rounded-lg border border-border p-2.5 font-mono text-xs">
                <div className="flex items-center gap-2 truncate pr-2">
                  <Terminal className="w-4 h-4 text-text-muted flex-shrink-0" />
                  <span className="truncate text-text">{commands.install}</span>
                </div>
                <button
                  type="button"
                  onClick={() => copyToClipboard(commands.install)}
                  className="p-1.5 rounded-md hover:bg-surface-3 text-text-muted hover:text-text transition-colors flex-shrink-0"
                  title="Copy command"
                >
                  {copiedCmd === commands.install ? (
                    <Check className="w-4 h-4 text-mint" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                </button>
              </div>
            </CardContent>
          </Card>

          {/* STEP 2: Pull Models */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="w-7 h-7 rounded-full bg-brand/15 text-brand font-mono font-bold text-xs flex items-center justify-center">
                  2
                </div>
                <div>
                  <CardTitle className="text-base sm:text-lg">
                    Pull Required Models
                  </CardTitle>
                  <CardDescription>
                    Pull the default fast chat model (Gemma 3 4B) and 768-dim embedding model.
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {/* Chat model command */}
              <div>
                <span className="text-xs font-mono text-text-muted block mb-1">
                  1. Reasoning & Chat Model (Gemma 3 4B)
                </span>
                <div className="flex items-center justify-between bg-surface-2 rounded-lg border border-border p-2.5 font-mono text-xs">
                  <div className="flex items-center gap-2 truncate pr-2">
                    <Terminal className="w-4 h-4 text-text-muted flex-shrink-0" />
                    <span className="truncate text-text">{commands.chatModel}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => copyToClipboard(commands.chatModel)}
                    className="p-1.5 rounded-md hover:bg-surface-3 text-text-muted hover:text-text transition-colors flex-shrink-0"
                    title="Copy command"
                  >
                    {copiedCmd === commands.chatModel ? (
                      <Check className="w-4 h-4 text-mint" />
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>

              {/* Embedding model command */}
              <div>
                <span className="text-xs font-mono text-text-muted block mb-1">
                  2. Code Embedding Model (Nomic Embed Text - 768 dim)
                </span>
                <div className="flex items-center justify-between bg-surface-2 rounded-lg border border-border p-2.5 font-mono text-xs">
                  <div className="flex items-center gap-2 truncate pr-2">
                    <Terminal className="w-4 h-4 text-text-muted flex-shrink-0" />
                    <span className="truncate text-text">{commands.embedModel}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => copyToClipboard(commands.embedModel)}
                    className="p-1.5 rounded-md hover:bg-surface-3 text-text-muted hover:text-text transition-colors flex-shrink-0"
                    title="Copy command"
                  >
                    {copiedCmd === commands.embedModel ? (
                      <Check className="w-4 h-4 text-mint" />
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* STEP 3: Test Connection */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="w-7 h-7 rounded-full bg-brand/15 text-brand font-mono font-bold text-xs flex items-center justify-center">
                  3
                </div>
                <div>
                  <CardTitle className="text-base sm:text-lg">
                    Test Local Connection
                  </CardTitle>
                  <CardDescription>
                    Ping the backend, verify database connection, and ensure Ollama models respond.
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button
                variant="primary"
                loading={testing}
                onClick={handleTestConnection}
                className="w-full sm:w-auto"
              >
                <RotateCcw className="w-4 h-4 mr-2" />
                <span>Test Connection Now</span>
              </Button>

              {/* Live check results with A6 ripple */}
              {testResult && (
                <div className="p-4 rounded-xl bg-surface-2 border border-border space-y-3 pt-4">
                  <h4 className="font-display font-bold text-xs uppercase tracking-wider text-text-muted">
                    Health Check Results
                  </h4>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                    {/* Database check */}
                    <div className="p-2.5 rounded-lg bg-surface-1 border border-border flex items-center justify-between">
                      <span className="text-text-muted">Database:</span>
                      <div className="flex items-center gap-2">
                        <span className="relative flex h-2 w-2">
                          {!isStill &&
                            (testResult.database === 'ok' || testResult.db === 'ok') && (
                              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-mint opacity-75" />
                            )}
                          <span
                            className={cn(
                              'relative inline-flex rounded-full h-2 w-2',
                              testResult.database === 'ok' || testResult.db === 'ok'
                                ? 'bg-mint'
                                : 'bg-flame'
                            )}
                          />
                        </span>
                        <span className="font-mono capitalize font-medium">
                          {testResult.database || testResult.db || 'unknown'}
                        </span>
                      </div>
                    </div>

                    {/* Ollama check */}
                    <div className="p-2.5 rounded-lg bg-surface-1 border border-border flex items-center justify-between">
                      <span className="text-text-muted">Ollama:</span>
                      <div className="flex items-center gap-2">
                        <span className="relative flex h-2 w-2">
                          {!isStill && testResult.ollama === 'ok' && (
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-mint opacity-75" />
                          )}
                          <span
                            className={cn(
                              'relative inline-flex rounded-full h-2 w-2',
                              testResult.ollama === 'ok' ? 'bg-mint' : 'bg-flame'
                            )}
                          />
                        </span>
                        <span className="font-mono capitalize font-medium">
                          {testResult.ollama || 'down'}
                        </span>
                      </div>
                    </div>

                    {/* Overall status */}
                    <div className="p-2.5 rounded-lg bg-surface-1 border border-border flex items-center justify-between">
                      <span className="text-text-muted">Overall:</span>
                      <span
                        className={cn(
                          'font-mono uppercase font-bold text-[11px] px-2 py-0.5 rounded',
                          testResult.status === 'ok'
                            ? 'bg-mint/15 text-mint'
                            : 'bg-amber/15 text-amber'
                        )}
                      >
                        {testResult.status}
                      </span>
                    </div>
                  </div>

                  {testResult.embedding_dimension_warning && (
                    <p className="text-xs text-amber leading-relaxed bg-amber/10 p-2.5 rounded-lg border border-amber/20">
                      Embedding Warning: {testResult.embedding_dimension_warning}
                    </p>
                  )}
                </div>
              )}

              {testError && (
                <div className="p-3 rounded-lg bg-flame/10 border border-flame/30 text-xs text-flame leading-relaxed">
                  {testError}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Completion Banner */}
        {isSetupSuccessful && (
          <div className="p-6 rounded-2xl bg-mint/10 border border-mint/30 flex flex-col sm:flex-row items-center justify-between gap-4 text-center sm:text-left">
            <div>
              <h3 className="font-display font-bold text-lg text-mint">
                Local Setup Complete!
              </h3>
              <p className="text-xs text-text-muted mt-1">
                Ollama and database services are responding. Pip is ready to explore repositories.
              </p>
            </div>
            <Link href="/">
              <Button variant="primary" className="whitespace-nowrap gap-2">
                <span>Start Exploring</span>
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
          </div>
        )}
      </div>
    </AppShell>
  );
}
