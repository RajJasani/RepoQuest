'use client';

import React, { useState, useEffect, useRef, useMemo, useCallback, Suspense } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { motion, useReducedMotion } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';
import { useSettings } from '@/lib/settings-context';
import { api, ApiError } from '@/lib/api';
import { streamSse, SseCitationEvent } from '@/lib/sse';
import {
  RepoDetail,
  ArchitectureResponse,
  ArchitectureResponseSchema,
  ChatCitation,
} from '@/lib/schemas';
import { AppShell } from '@/components/layout/AppShell';
import { Pip } from '@/components/brand/Pip';
import { CodeViewer } from '@/components/ui/CodeViewer';
import { CitationChip } from '@/components/ui/CitationChip';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { showToast } from '@/components/ui/Toast';
import {
  Square,
  ArrowUp,
  RotateCcw,
  Sparkles,
  FileCode2,
  BookOpen,
  AlertCircle,
  MessageSquare,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export interface MessageItem {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: ChatCitation[];
  isStreaming?: boolean;
  isLowConfidence?: boolean;
}

function AskRepoContent() {
  const params = useParams();
  const searchParams = useSearchParams();
  const repoId = String(params.id || '');

  const { language } = useSettings();
  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStill = Boolean(reduce) || calm;

  // Session & Mode States
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [mode, setMode] = useState<'newcomer' | 'expert'>('newcomer');
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isThinking, setIsThinking] = useState(false);

  // Screen reader sentence accumulator for aria-live="polite"
  const [srAnnouncement, setSrAnnouncement] = useState('');

  // Sources Panel Selection (for active CodeViewer preview)
  const [selectedCitation, setSelectedCitation] = useState<ChatCitation | null>(null);

  // References
  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const sentenceBufferRef = useRef<string>('');
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // 1. Fetch Repository Details
  const { data: repo, isLoading: isRepoLoading } = useQuery<RepoDetail>({
    queryKey: ['repo', repoId],
    queryFn: () => api.get<RepoDetail>(`/repos/${repoId}`),
    enabled: Boolean(repoId),
  });

  // 2. Fetch Architecture for entry points and starter chips
  const { data: architecture } = useQuery<ArchitectureResponse>({
    queryKey: ['architecture', repoId],
    queryFn: async () => {
      const res = await api.get<unknown>(`/repos/${repoId}/architecture`);
      return ArchitectureResponseSchema.parse(res);
    },
    enabled: Boolean(repoId),
  });

  // Create or reset chat session
  const initSession = useCallback(
    async (sessionMode = mode) => {
      try {
        const res = await api.post<{ id: string }>(`/repos/${repoId}/chat/sessions`, {
          mode: sessionMode,
          language,
        });
        setSessionId(res.id);
        return res.id;
      } catch (err: unknown) {
        const msg = err instanceof ApiError ? err.message : 'Failed to create chat session';
        showToast.error(msg);
        return null;
      }
    },
    [repoId, mode, language]
  );

  // Initialize session on mount
  useEffect(() => {
    initSession();
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [initSession]);

  // Auto-scroll as messages or tokens arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: isStill ? 'auto' : 'smooth' });
  }, [messages, isGenerating, isThinking, isStill]);

  // Starter Questions derived from repo README and entry points + 2 generic fallbacks
  const starterQuestions = useMemo(() => {
    const list: string[] = [];
    const entryPoints = architecture?.entry_points || [];

    if (entryPoints.length > 0) {
      list.push(`Where does execution enter through ${entryPoints[0]}?`);
    }

    list.push('Where is authentication handled in this codebase?');
    list.push('How do I run and test this project locally?');
    list.push('What are the core modules and key workflows?');
    list.push('How is data persistence or database access structured?');

    return list.slice(0, 4);
  }, [architecture]);

  // Handle prefilled query parameter from Explore screen
  const initialQueryApplied = useRef(false);
  useEffect(() => {
    const queryParam = searchParams?.get('q');
    if (queryParam && !initialQueryApplied.current) {
      initialQueryApplied.current = true;
      setInputValue(queryParam);
    }
  }, [searchParams]);

  // Send Message & Stream Response
  const handleSendMessage = async (textToSend?: string) => {
    const prompt = (textToSend || inputValue).trim();
    if (!prompt || isGenerating) return;
    if (prompt.length > 2000) {
      showToast.error('Message exceeds 2,000 character limit');
      return;
    }

    setInputValue('');

    // Ensure session exists
    let sid = sessionId;
    if (!sid) {
      sid = await initSession();
      if (!sid) return;
    }

    const userMessage: MessageItem = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: prompt,
    };

    const assistantMsgId = `asst-${Date.now()}`;
    const initialAssistantMessage: MessageItem = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      citations: [],
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMessage, initialAssistantMessage]);
    setIsGenerating(true);
    setIsThinking(true);
    sentenceBufferRef.current = '';

    const ac = new AbortController();
    abortControllerRef.current = ac;

    let accumulatedContent = '';
    const collectedCitations: ChatCitation[] = [];

    try {
      await streamSse(`/chat/sessions/${sid}/messages`, {
        method: 'POST',
        body: { content: prompt },
        signal: ac.signal,
        onToken: (token: string) => {
          setIsThinking(false);
          accumulatedContent += token;

          // Screen reader announcement buffer (updates per sentence, not per word)
          sentenceBufferRef.current += token;
          if (/[.!?\n]\s*$/.test(sentenceBufferRef.current)) {
            setSrAnnouncement(sentenceBufferRef.current.trim());
            sentenceBufferRef.current = '';
          }

          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId ? { ...m, content: accumulatedContent } : m
            )
          );
        },
        onCitation: (citation: SseCitationEvent) => {
          const chatCit: ChatCitation = {
            file: citation.file,
            start_line: citation.start_line,
            end_line: citation.end_line,
            source_number: (collectedCitations.length + 1),
          };
          collectedCitations.push(chatCit);

          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId
                ? { ...m, citations: [...collectedCitations] }
                : m
            )
          );

          // Select first citation automatically in Sources panel
          if (!selectedCitation) {
            setSelectedCitation(chatCit);
          }
        },
        onError: (err) => {
          setIsThinking(false);
          setIsGenerating(false);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId
                ? {
                    ...m,
                    content:
                      accumulatedContent ||
                      `Error: ${err.message || 'LLM service is currently unavailable.'}`,
                    isStreaming: false,
                  }
                : m
            )
          );
          showToast.error(err.message || 'Stream encountered an error');
        },
        onDone: () => {
          setIsThinking(false);
          setIsGenerating(false);
          // Flush remaining sentence buffer for screen readers
          if (sentenceBufferRef.current.trim()) {
            setSrAnnouncement(sentenceBufferRef.current.trim());
            sentenceBufferRef.current = '';
          }

          const isLow = accumulatedContent.toLowerCase().includes('could not find this in the repo');
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId
                ? {
                    ...m,
                    content: accumulatedContent,
                    citations: collectedCitations,
                    isStreaming: false,
                    isLowConfidence: isLow,
                  }
                : m
            )
          );
        },
      });
    } catch {
      if (ac.signal.aborted) {
        setIsGenerating(false);
        setIsThinking(false);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  content: accumulatedContent || '(Generation stopped by user)',
                  isStreaming: false,
                }
              : m
          )
        );
        showToast.info('Generation cancelled');
        return;
      }
      setIsThinking(false);
      setIsGenerating(false);
    }
  };

  // Stop Generation Handler
  const handleStopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  // New Chat Handler (Clears history and creates fresh session)
  const handleNewChat = async () => {
    if (isGenerating) {
      handleStopGeneration();
    }
    setMessages([]);
    setSelectedCitation(null);
    setSrAnnouncement('');
    sentenceBufferRef.current = '';
    await initSession(mode);
    showToast.success('Started a new conversation session');
  };

  // Toggle Mode (Newcomer vs Expert)
  const handleToggleMode = async (newMode: 'newcomer' | 'expert') => {
    if (newMode === mode) return;
    setMode(newMode);
    if (messages.length === 0) {
      await initSession(newMode);
    }
  };

  // Aggregate all citations across messages for the Sources Panel
  const allCitations = useMemo(() => {
    const list: ChatCitation[] = [];
    const seen = new Set<string>();

    messages.forEach((msg) => {
      (msg.citations || []).forEach((c) => {
        const key = `${c.file}:${c.start_line}-${c.end_line}`;
        if (!seen.has(key)) {
          seen.add(key);
          list.push(c);
        }
      });
    });

    return list;
  }, [messages]);

  // Loading Skeleton State
  if (isRepoLoading) {
    return (
      <AppShell>
        <div className="max-w-6xl mx-auto py-8 space-y-6">
          <Skeleton className="h-10 w-64" />
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[70vh]">
            <Skeleton className="lg:col-span-7 h-full rounded-2xl" />
            <Skeleton className="lg:col-span-5 h-full rounded-2xl" />
          </div>
        </div>
      </AppShell>
    );
  }

  const hasMessages = messages.length > 0;

  return (
    <AppShell className="h-[calc(100vh-3.5rem)] flex flex-col p-4 sm:p-6 overflow-hidden">
      {/* SCREEN READER ANNOUNCER: aria-live="polite" updating per sentence */}
      <div className="sr-only" aria-live="polite" aria-atomic="true">
        {srAnnouncement}
      </div>

      {/* TOP HEADER CONTROLS */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-border shrink-0">
        <div className="flex items-center gap-2.5">
          <MessageSquare className="w-5 h-5 text-brand" />
          <h1 className="font-display font-bold text-lg text-text">
            Ask the Repo
          </h1>
          <span className="font-mono text-xs text-text-muted hidden sm:inline">
            ({repo?.full_name || 'local context'})
          </span>
        </div>

        <div className="flex items-center gap-3">
          {/* Mode Switcher: Newcomer vs Expert */}
          <div className="flex items-center bg-surface-2 border border-border rounded-lg p-0.5 text-xs font-mono">
            <button
              type="button"
              onClick={() => handleToggleMode('newcomer')}
              className={cn(
                'px-2.5 py-1 rounded-md transition-colors cursor-pointer',
                mode === 'newcomer'
                  ? 'bg-surface-1 text-text font-bold shadow-sm'
                  : 'text-text-muted hover:text-text'
              )}
            >
              Newcomer Mode
            </button>
            <button
              type="button"
              onClick={() => handleToggleMode('expert')}
              className={cn(
                'px-2.5 py-1 rounded-md transition-colors cursor-pointer',
                mode === 'expert'
                  ? 'bg-surface-1 text-text font-bold shadow-sm'
                  : 'text-text-muted hover:text-text'
              )}
            >
              Expert Mode
            </button>
          </div>

          {/* New Chat Button */}
          <Button
            variant="ghost"
            onClick={handleNewChat}
            className="gap-1.5 text-xs font-mono h-8 border border-border"
            title="Start new conversation"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>New Chat</span>
          </Button>
        </div>
      </div>

      {/* MAIN TWO-COLUMN SPLIT (60% Chat, 40% Sources) */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-0 pt-4">
        {/* LEFT COLUMN: 60% Conversation Stream */}
        <section
          className="lg:col-span-7 flex flex-col h-full bg-surface-1/40 border border-border rounded-2xl overflow-hidden relative shadow-sm"
          aria-label="Conversation"
        >
          {/* Messages Scroll Area */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
            {/* INITIAL EMPTY STATE: Starter Chips & Centered Pip */}
            {!hasMessages && (
              <div className="h-full flex flex-col items-center justify-center text-center max-w-lg mx-auto py-8 space-y-6">
                <div className="space-y-2">
                  <h3 className="font-display font-bold text-lg text-text">
                    Ask anything about this repository
                  </h3>
                  <p className="text-xs text-text-muted leading-relaxed font-sans">
                    RepoQuest retrieves relevant AST code chunks from pgvector and streams cited explanations locally through Ollama.
                  </p>
                </div>

                {/* Pip Idle Under Chips */}
                <div className="relative py-2">
                  <Pip state="idle" size={80} />
                </div>

                {/* Starter Question Chips */}
                <div className="w-full space-y-2">
                  <span className="font-mono text-[11px] uppercase tracking-wider text-text-muted font-bold block">
                    Suggested Exploration Quests
                  </span>
                  <div className="flex flex-col gap-2">
                    {starterQuestions.map((q, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => handleSendMessage(q)}
                        className="w-full text-left p-2.5 rounded-xl bg-surface-1 hover:bg-surface-2 border border-border hover:border-brand/40 text-xs text-text font-sans flex items-center justify-between gap-2 transition-all cursor-pointer group shadow-sm"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <Sparkles className="w-3.5 h-3.5 text-brand shrink-0" />
                          <span className="truncate group-hover:text-brand transition-colors">
                            {q}
                          </span>
                        </div>
                        <ArrowUp className="w-3.5 h-3.5 rotate-45 text-text-muted/60 group-hover:text-brand transition-colors shrink-0" />
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* MESSAGE STREAM (User bubbles in surface-3, Assistant answers on page without bubbles) */}
            {messages.map((msg) => {
              if (msg.role === 'user') {
                return (
                  <div key={msg.id} className="flex justify-end">
                    <div className="bg-surface-3 text-text rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-[85%] border border-border/80 text-sm leading-relaxed shadow-sm font-sans">
                      {msg.content}
                    </div>
                  </div>
                );
              }

              // Assistant Response (Rendered on the page without bubbles for readability)
              return (
                <div key={msg.id} className="space-y-3 font-sans text-sm text-text leading-relaxed">
                  {/* Word-by-word fade up (A13) */}
                  <div className="prose prose-invert max-w-none text-text text-sm">
                    {isStill || !msg.isStreaming ? (
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    ) : (
                      <p className="whitespace-pre-wrap">
                        {msg.content.split(' ').map((word, wIdx) => (
                          <motion.span
                            key={wIdx}
                            initial={{ opacity: 0, y: 4 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.12, ease: 'easeOut' }}
                            className="inline"
                          >
                            {word}{' '}
                          </motion.span>
                        ))}
                      </p>
                    )}
                  </div>

                  {/* Low Confidence Callout */}
                  {msg.isLowConfidence && (
                    <div className="p-3 rounded-xl bg-amber/10 border border-amber/30 text-xs text-amber space-y-1.5 font-mono">
                      <div className="flex items-center gap-1.5 font-bold">
                        <AlertCircle className="w-4 h-4" />
                        <span>Low Retrieval Confidence</span>
                      </div>
                      <p className="text-text-muted leading-relaxed font-sans">
                        I could not find exact matching chunks for this query in the indexed embeddings. Try querying specific file names or module concepts from the architecture map.
                      </p>
                    </div>
                  )}

                  {/* Inline Citation Chips (A13: fly to Sources Panel) */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-border/40 font-mono text-xs">
                      <span className="text-[11px] text-text-muted font-bold uppercase tracking-wider">
                        Sources:
                      </span>
                      {msg.citations.map((c, cIdx) => (
                        <CitationChip
                          key={cIdx}
                          path={c.file}
                          lines={`L${c.start_line}-${c.end_line}`}
                          index={c.source_number || cIdx + 1}
                          onClick={() => setSelectedCitation(c)}
                        />
                      ))}
                    </div>
                  )}
                </div>
              );
            })}

            {/* A14: Thinking State with Pip & Shimmer Skeleton */}
            {isThinking && (
              <div className="flex items-start gap-4 py-2 animate-fadeIn">
                <div className="shrink-0 pt-1">
                  <Pip state="thinking" size={48} />
                </div>
                <div className="space-y-2 flex-1 pt-2">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-4 w-1/2" />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* INPUT FORM: 2,000 char counter & morphing Send/Stop button */}
          <div className="p-3 sm:p-4 bg-surface-1 border-t border-border shrink-0">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="relative flex flex-col gap-2"
            >
              <div className="relative flex items-center">
                <textarea
                  ref={inputRef}
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value.slice(0, 2000))}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendMessage();
                    }
                  }}
                  placeholder="Ask a technical question about this repository..."
                  rows={2}
                  maxLength={2000}
                  className="w-full resize-none p-3 pr-14 text-xs font-mono bg-surface-2 border border-border rounded-xl text-text placeholder:text-text-muted/60 focus:outline-none focus:ring-1 focus:ring-brand shadow-inner leading-relaxed"
                />

                {/* Send / Stop Button Morphing */}
                <div className="absolute right-2.5 bottom-3.5">
                  {isGenerating ? (
                    <Button
                      type="button"
                      variant="danger"
                      onClick={handleStopGeneration}
                      className="h-8 w-8 p-0 rounded-lg shadow-sm"
                      title="Stop generating"
                    >
                      <Square className="w-3.5 h-3.5 fill-current" />
                    </Button>
                  ) : (
                    <Button
                      type="submit"
                      variant="primary"
                      disabled={!inputValue.trim()}
                      className="h-8 w-8 p-0 rounded-lg shadow-sm"
                      title="Send message (Enter)"
                    >
                      <ArrowUp className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              </div>

              {/* Input Footer: Mode indicator & Character counter */}
              <div className="flex items-center justify-between px-1 text-[11px] font-mono text-text-muted">
                <span>
                  Mode: <strong className="text-text capitalize">{mode}</strong> · Language:{' '}
                  <strong className="text-text uppercase">{language}</strong>
                </span>
                <span>{inputValue.length}/2000</span>
              </div>
            </form>
          </div>
        </section>

        {/* RIGHT COLUMN: 40% Sources Panel & CodeViewer */}
        <aside
          className="lg:col-span-5 flex flex-col h-full bg-surface-1 border border-border rounded-2xl overflow-hidden shadow-sm"
          aria-label="Sources and Citations"
        >
          {/* Sources Header */}
          <div className="px-4 py-3 border-b border-border bg-surface-2/60 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2">
              <FileCode2 className="w-4 h-4 text-brand" />
              <span className="font-mono text-xs font-bold text-text">
                Sources & Citations
              </span>
              <span className="font-mono text-[11px] text-text-muted">
                ({allCitations.length})
              </span>
            </div>

            {selectedCitation && (
              <span className="font-mono text-[11px] text-brand truncate max-w-[150px]">
                {selectedCitation.file.split('/').pop()}
              </span>
            )}
          </div>

          {/* Sources Content: Citations list + Inline CodeViewer */}
          <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
            {allCitations.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center p-8 text-center space-y-3 font-mono text-xs text-text-muted">
                <BookOpen className="w-8 h-8 opacity-40 text-brand" />
                <p>No citation references yet.</p>
                <p className="text-[11px] text-text-muted/70 max-w-xs font-sans">
                  Ask a question about the repository to retrieve cited code chunks and line ranges from local embeddings.
                </p>
              </div>
            ) : (
              <div className="flex-1 flex flex-col min-h-0">
                {/* Horizontal Citations Strip */}
                <div className="p-3 border-b border-border bg-surface-2/30 flex items-center gap-2 overflow-x-auto shrink-0">
                  {allCitations.map((c, idx) => {
                    const isSelected =
                      selectedCitation?.file === c.file &&
                      selectedCitation?.start_line === c.start_line;

                    return (
                      <CitationChip
                        key={idx}
                        path={c.file}
                        lines={`L${c.start_line}-${c.end_line}`}
                        index={c.source_number || idx + 1}
                        className={cn(
                          isSelected && 'ring-2 ring-brand bg-brand/10 border-brand'
                        )}
                        onClick={() => setSelectedCitation(c)}
                      />
                    );
                  })}
                </div>

                {/* Inline CodeViewer for the Selected Citation */}
                <div className="flex-1 min-h-0">
                  {selectedCitation ? (
                    <CodeViewer
                      repoId={repoId}
                      filePath={selectedCitation.file}
                      startLine={Math.max(1, selectedCitation.start_line - 5)}
                      endLine={selectedCitation.end_line + 5}
                      jumpLine={selectedCitation.start_line}
                      highlightRange={{
                        start: selectedCitation.start_line,
                        end: selectedCitation.end_line,
                      }}
                      className="h-full rounded-none border-0"
                    />
                  ) : (
                    <div className="flex-1 flex items-center justify-center p-6 text-center text-xs font-mono text-text-muted">
                      Select a citation chip above to inspect the source file.
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </aside>
      </div>
    </AppShell>
  );
}

export default function AskRepoPage() {
  return (
    <Suspense
      fallback={
        <AppShell>
          <div className="p-6 space-y-4">
            <Skeleton className="h-10 w-64" />
            <Skeleton className="h-[75vh] w-full rounded-2xl" />
          </div>
        </AppShell>
      }
    >
      <AskRepoContent />
    </Suspense>
  );
}
