'use client';

import React, { useState, useMemo, useEffect, useRef, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import {
  ArchitectureResponse,
  ArchitectureResponseSchema,
  ArchitectureNode,
  ArchitectureEdge,
  RepoDetail,
  TreeNode,
  TreeNodesListSchema,
  ModuleDetailResponse,
  ModuleDetailResponseSchema,
} from '@/lib/schemas';
import { AppShell } from '@/components/layout/AppShell';
import { ModuleGraph } from '@/components/graph/ModuleGraph';
import { CodeViewer } from '@/components/ui/CodeViewer';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/states/EmptyState';
import { Skeleton } from '@/components/ui/Skeleton';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/Dialog';
import { getLanguageColor } from '@/lib/languages';
import {
  Network,
  List,
  MessageSquareCode,
  Terminal,
  FileCode,
  X,
  ArrowRight,
  Sparkles,
  RotateCcw,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { showToast } from '@/components/ui/Toast';

export default function ExplorePage() {
  const params = useParams();
  const router = useRouter();
  const repoId = String(params.id || '');

  // UI States
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [highlightedNodeIds, setHighlightedNodeIds] = useState<string[]>([]);
  const [isListView, setIsListView] = useState(false);
  const [activeCodeFile, setActiveCodeFile] = useState<string | null>(null);
  const [runInstructionsOpen, setRunInstructionsOpen] = useState(false);
  const [focusedListIndex, setFocusedListIndex] = useState(0);

  const listContainerRef = useRef<HTMLDivElement>(null);

  // 1. Fetch Repository Details
  const { data: repo, isLoading: isRepoLoading } = useQuery<RepoDetail>({
    queryKey: ['repo', repoId],
    queryFn: () => api.get<RepoDetail>(`/repos/${repoId}`),
    enabled: Boolean(repoId),
  });

  // 2. Fetch Architecture Module Graph
  const {
    data: architecture,
    isLoading: isArchLoading,
    error: archError,
    refetch: refetchArch,
  } = useQuery<ArchitectureResponse>({
    queryKey: ['architecture', repoId],
    queryFn: async () => {
      const res = await api.get<unknown>(`/repos/${repoId}/architecture`);
      return ArchitectureResponseSchema.parse(res);
    },
    enabled: Boolean(repoId),
  });

  // 3. Fetch Tree for fallback if architecture has no edges or nodes
  const { data: treeNodes } = useQuery<TreeNode[]>({
    queryKey: ['repo-tree', repoId],
    queryFn: async () => {
      const raw = await api.get<unknown>(`/repos/${repoId}/tree`);
      if (Array.isArray(raw)) return TreeNodesListSchema.parse(raw);
      if (typeof raw === 'object' && raw !== null && 'tree' in raw) {
        return TreeNodesListSchema.parse((raw as { tree: unknown }).tree);
      }
      return [];
    },
    enabled: Boolean(repoId),
  });

  // 4. Fetch Active Module Detail if a node is selected
  const { data: moduleDetail } = useQuery<ModuleDetailResponse>({
    queryKey: ['module-detail', repoId, selectedNodeId],
    queryFn: async () => {
      if (!selectedNodeId) throw new Error('No module selected');
      const res = await api.get<unknown>(`/repos/${repoId}/modules/${selectedNodeId}`);
      return ModuleDetailResponseSchema.parse(res);
    },
    enabled: Boolean(repoId && selectedNodeId),
  });

  // Ensure Fallback Graph: if repo has no detected imports, build directory hierarchy tree graph
  const { nodes, edges } = useMemo(() => {
    let resolvedNodes: ArchitectureNode[] = architecture?.nodes || [];
    let resolvedEdges: ArchitectureEdge[] = architecture?.edges || [];

    // If architecture nodes are present but zero edges exist, synthesize hierarchy edges
    if (resolvedNodes.length > 0 && resolvedEdges.length === 0) {
      const synthesizedEdges: ArchitectureEdge[] = [];
      const rootNode = resolvedNodes.find((n) => n.path === '.' || n.name === 'root') || resolvedNodes[0];

      resolvedNodes.forEach((node) => {
        if (node.id !== rootNode.id) {
          // Check if any node is a prefix parent
          const parent = resolvedNodes.find(
            (p) => p.id !== node.id && node.path.startsWith(`${p.path}/`)
          );
          synthesizedEdges.push({
            source: parent ? parent.id : rootNode.id,
            target: node.id,
            weight: 1,
          });
        }
      });
      resolvedEdges = synthesizedEdges;
    }

    // If architecture nodes are completely empty, synthesize from tree
    if (resolvedNodes.length === 0 && treeNodes && treeNodes.length > 0) {
      const dirs = treeNodes.filter((t) => t.type === 'directory');
      const rootId = 'root-dir';
      resolvedNodes = [
        {
          id: rootId,
          name: repo?.name || 'root',
          path: '.',
          summary: 'Root project directory and manifest configurations.',
          key_files: treeNodes.filter((t) => t.type === 'file').slice(0, 3).map((f) => f.path),
          entry_points: [],
          file_count: treeNodes.length,
        },
        ...dirs.map((d) => ({
          id: d.path || d.name,
          name: d.name,
          path: d.path,
          summary: `Directory module for ${d.name}.`,
          key_files: (d.children || []).filter((c) => c.type === 'file').slice(0, 3).map((c) => c.path),
          entry_points: [],
          file_count: d.children?.length || 1,
        })),
      ];

      resolvedEdges = dirs.map((d) => ({
        source: rootId,
        target: d.path || d.name,
        weight: 1,
      }));
    }

    return { nodes: resolvedNodes, edges: resolvedEdges };
  }, [architecture, treeNodes, repo]);

  // Selected node object
  const activeNode = useMemo(() => {
    return nodes.find((n) => n.id === selectedNodeId) || null;
  }, [nodes, selectedNodeId]);

  // Handle "Start Here" action: Highlights the recommended entry modules
  const handleStartHere = useCallback(() => {
    // Find entry point modules or root module
    const entryModules = nodes.filter(
      (n) => (n.entry_points && n.entry_points.length > 0) || n.path === '.' || n.name === 'main'
    );
    const targetIds = entryModules.length > 0 ? entryModules.map((m) => m.id) : [nodes[0]?.id].filter(Boolean);

    setHighlightedNodeIds(targetIds);
    if (targetIds.length > 0) {
      setSelectedNodeId(targetIds[0]);
      showToast.info('Highlighted recommended entry points on the architecture map.');
    }
  }, [nodes]);

  // Handle "Ask about this module"
  const handleAskAboutModule = (moduleName: string) => {
    const question = `Where is ${moduleName} handled and how does it work?`;
    router.push(`/repos/${repoId}/ask?q=${encodeURIComponent(question)}`);
  };

  // Keyboard Navigation for Accessible List View (Arrow Keys + Enter)
  useEffect(() => {
    if (!isListView) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (nodes.length === 0) return;

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setFocusedListIndex((prev) => Math.min(nodes.length - 1, prev + 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setFocusedListIndex((prev) => Math.max(0, prev - 1));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const selected = nodes[focusedListIndex];
        if (selected) {
          setSelectedNodeId(selected.id);
        }
      } else if (e.key === 'Escape') {
        setSelectedNodeId(null);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isListView, nodes, focusedListIndex]);

  // Loading State
  if (isRepoLoading || isArchLoading) {
    return (
      <AppShell>
        <div className="h-[calc(100vh-4rem)] w-full flex flex-col p-6 space-y-4">
          <div className="flex items-center justify-between">
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-8 w-48" />
          </div>
          <Skeleton className="flex-1 w-full rounded-2xl" />
        </div>
      </AppShell>
    );
  }

  // Error State
  if (archError) {
    return (
      <AppShell>
        <div className="max-w-2xl mx-auto py-16 text-center space-y-4">
          <div className="p-3 bg-flame/10 text-flame rounded-full inline-flex border border-flame/30">
            <Network className="w-8 h-8" />
          </div>
          <h2 className="font-display font-bold text-xl text-text">
            Failed to Load Living Codebase Map
          </h2>
          <p className="text-xs text-text-muted">
            {archError instanceof Error ? archError.message : 'Could not retrieve architecture.'}
          </p>
          <Button variant="secondary" onClick={() => refetchArch()} className="gap-2">
            <RotateCcw className="w-4 h-4" />
            <span>Retry</span>
          </Button>
        </div>
      </AppShell>
    );
  }

  // Empty State if no modules indexed
  if (nodes.length === 0) {
    return (
      <AppShell>
        <div className="py-16">
          <EmptyState
            title="No Architectural Modules Detected"
            description="The repository contains no parsable module directories or AST source files yet."
            actionLabel="Return to Overview"
            actionHref={`/repos/${repoId}`}
            pipState="exploring"
          />
        </div>
      </AppShell>
    );
  }

  const techStack = architecture?.tech_stack || repo?.tech_stack || [];
  const runInstructions = architecture?.run_instructions || repo?.run_instructions;
  const entryPoints = architecture?.entry_points || [];

  return (
    <AppShell className="p-0 overflow-hidden flex flex-col h-[calc(100vh-3.5rem)]">
      {/* TOP HEADER CONTROLS BAR */}
      <header className="h-14 border-b border-border bg-surface-1/95 backdrop-blur-md px-4 sm:px-6 flex items-center justify-between gap-4 shrink-0 z-20">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex items-center gap-2">
            <Network className="w-4 h-4 text-brand shrink-0" />
            <span className="font-display font-bold text-sm text-text truncate">
              Architecture Explorer
            </span>
          </div>

          {/* Tech Stack Badges */}
          <div className="hidden md:flex items-center gap-1.5 overflow-x-auto">
            {techStack.map((tech) => (
              <span
                key={tech}
                className="px-2 py-0.5 rounded-md text-[11px] font-mono bg-surface-2 border border-border text-text-muted shrink-0"
              >
                {tech}
              </span>
            ))}
            {entryPoints.length > 0 && (
              <span className="px-2 py-0.5 rounded-md text-[11px] font-mono bg-mint/10 border border-mint/30 text-mint shrink-0">
                {entryPoints.length} {entryPoints.length === 1 ? 'entry point' : 'entry points'}
              </span>
            )}
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2.5 shrink-0">
          {/* Start Here Button */}
          <Button
            variant="secondary"
            onClick={handleStartHere}
            className="gap-1.5 text-xs h-8 border-brand/40 text-brand hover:bg-brand/10"
            title="Highlight recommended modules"
          >
            <Sparkles className="w-3.5 h-3.5 text-brand" />
            <span>Start Here</span>
          </Button>

          {/* How to Run Locally Dialog Button */}
          {runInstructions && (
            <Button
              variant="ghost"
              onClick={() => setRunInstructionsOpen(true)}
              className="gap-1.5 text-xs h-8 font-mono"
            >
              <Terminal className="w-3.5 h-3.5 text-text-muted" />
              <span className="hidden sm:inline">Run Locally</span>
            </Button>
          )}

          {/* Accessible List View / Graph View Toggle */}
          <div className="flex items-center bg-surface-2 border border-border rounded-lg p-0.5">
            <button
              type="button"
              onClick={() => setIsListView(false)}
              className={cn(
                'px-2.5 py-1 rounded-md text-xs font-mono flex items-center gap-1.5 transition-colors cursor-pointer',
                !isListView
                  ? 'bg-surface-1 text-text font-bold shadow-sm'
                  : 'text-text-muted hover:text-text'
              )}
              title="Graph View (M3 Living Map)"
              aria-label="Switch to Graph View"
            >
              <Network className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Graph</span>
            </button>
            <button
              type="button"
              onClick={() => setIsListView(true)}
              className={cn(
                'px-2.5 py-1 rounded-md text-xs font-mono flex items-center gap-1.5 transition-colors cursor-pointer',
                isListView
                  ? 'bg-surface-1 text-text font-bold shadow-sm'
                  : 'text-text-muted hover:text-text'
              )}
              title="Accessible List View (Keyboard operable)"
              aria-label="Switch to Accessible List View"
            >
              <List className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">List</span>
            </button>
          </div>
        </div>
      </header>

      {/* MAIN CONTENT AREA: Graph Canvas or Accessible List View */}
      <div className="relative flex-1 w-full h-full overflow-hidden flex">
        {!isListView ? (
          // Living Module Graph (React Flow)
          <div className="flex-1 h-full w-full relative">
            <ModuleGraph
              nodes={nodes}
              edges={edges}
              selectedNodeId={selectedNodeId}
              onSelectNode={(id) => setSelectedNodeId(id)}
              highlightedNodeIds={highlightedNodeIds}
            />
          </div>
        ) : (
          // ACCESSIBLE LIST VIEW ALTERNATIVE (Keyboard navigable via Arrow Keys & Enter)
          <div
            ref={listContainerRef}
            className="flex-1 h-full overflow-y-auto p-6 max-w-4xl mx-auto space-y-3"
            role="listbox"
            aria-label="Repository Modules"
          >
            <div className="pb-2 border-b border-border text-xs font-mono text-text-muted flex items-center justify-between">
              <span>Navigate modules using [Up / Down] arrows, press [Enter] to inspect.</span>
              <span>{nodes.length} Modules</span>
            </div>

            {nodes.map((node, index) => {
              const isSelected = selectedNodeId === node.id;
              const isFocused = focusedListIndex === index;
              const isHighlighted = highlightedNodeIds.includes(node.id);

              return (
                <div
                  key={node.id}
                  role="option"
                  aria-selected={isSelected}
                  tabIndex={0}
                  onClick={() => {
                    setFocusedListIndex(index);
                    setSelectedNodeId(node.id);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      setSelectedNodeId(node.id);
                    }
                  }}
                  className={cn(
                    'p-4 rounded-xl border transition-all cursor-pointer outline-none',
                    isFocused && 'ring-2 ring-brand bg-surface-2',
                    isSelected && 'bg-brand/10 border-brand shadow-sm',
                    isHighlighted && !isSelected && 'border-amber/60 bg-amber/5',
                    !isFocused && !isSelected && 'bg-surface-1 border-border hover:border-brand/40'
                  )}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span
                          className="w-2.5 h-2.5 rounded-full shrink-0"
                          style={{ backgroundColor: getLanguageColor(node.name) }}
                        />
                        <h4 className="font-display font-bold text-sm text-text">
                          {node.name}
                        </h4>
                        <span className="font-mono text-xs text-text-muted">
                          ({node.path})
                        </span>
                        {node.entry_points && node.entry_points.length > 0 && (
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-mint/15 text-mint border border-mint/30">
                            Entry
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-text-muted line-clamp-2 leading-relaxed">
                        {node.summary || 'Module containing repository components and source logic.'}
                      </p>
                    </div>

                    <div className="text-right font-mono text-xs text-text-muted shrink-0">
                      <span>{node.file_count} files</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* RIGHT DRAWER: Module Summary & Code Inspection */}
        {selectedNodeId && activeNode && (
          <aside
            className={cn(
              'absolute top-0 right-0 bottom-0 w-full sm:w-[420px] bg-surface-1/95 backdrop-blur-xl border-l border-border z-30 shadow-2xl flex flex-col justify-between transition-transform duration-300 ease-out animate-in slide-in-from-right'
            )}
            role="dialog"
            aria-label={`Module details: ${activeNode.name}`}
          >
            {/* Drawer Header */}
            <div className="p-4 border-b border-border flex items-center justify-between">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span
                    className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ backgroundColor: getLanguageColor(activeNode.name) }}
                  />
                  <h3 className="font-display font-bold text-base text-text truncate">
                    {activeNode.name}
                  </h3>
                </div>
                <p className="font-mono text-xs text-text-muted truncate mt-0.5">
                  {activeNode.path}
                </p>
              </div>

              <Button
                variant="ghost"
                onClick={() => setSelectedNodeId(null)}
                className="p-1.5 h-8 text-text-muted hover:text-text"
                title="Close drawer (Esc)"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>

            {/* Drawer Scrollable Content */}
            <div className="flex-1 overflow-y-auto p-5 space-y-6 font-mono text-xs">
              {/* Summary Paragraph */}
              <div className="space-y-1.5">
                <span className="text-[11px] uppercase tracking-wider text-text-muted font-bold block">
                  Module Summary
                </span>
                <p className="font-sans text-xs text-text leading-relaxed p-3 bg-surface-2/60 rounded-xl border border-border/60">
                  {moduleDetail?.summary ||
                    activeNode.summary ||
                    'Architectural module responsible for core application functions and workflows.'}
                </p>
              </div>

              {/* Action Buttons: Ask & Start Here */}
              <div className="grid grid-cols-2 gap-2 pt-1">
                <Button
                  variant="primary"
                  onClick={() => handleAskAboutModule(activeNode.name)}
                  className="gap-2 text-xs justify-center"
                >
                  <MessageSquareCode className="w-3.5 h-3.5" />
                  <span>Ask Module</span>
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => {
                    setHighlightedNodeIds([activeNode.id]);
                    showToast.info(`Module ${activeNode.name} marked as exploration target.`);
                  }}
                  className="gap-2 text-xs justify-center"
                >
                  <Sparkles className="w-3.5 h-3.5 text-brand" />
                  <span>Start Here</span>
                </Button>
              </div>

              {/* Key Files (Open in CodeViewer) */}
              <div className="space-y-2">
                <span className="text-[11px] uppercase tracking-wider text-text-muted font-bold block">
                  Key Files ({activeNode.key_files.length})
                </span>
                <div className="space-y-1.5">
                  {activeNode.key_files.length > 0 ? (
                    activeNode.key_files.map((file) => (
                      <button
                        key={file}
                        type="button"
                        onClick={() => setActiveCodeFile(file)}
                        className="w-full text-left p-2.5 rounded-lg bg-surface-2/40 hover:bg-surface-2 border border-border/60 flex items-center justify-between text-xs transition-colors cursor-pointer group"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <FileCode className="w-3.5 h-3.5 text-brand shrink-0" />
                          <span className="text-text group-hover:text-brand transition-colors truncate">
                            {file}
                          </span>
                        </div>
                        <ArrowRight className="w-3.5 h-3.5 text-text-muted/60 group-hover:text-brand transition-colors shrink-0" />
                      </button>
                    ))
                  ) : (
                    <span className="text-text-muted italic text-[11px]">
                      No prioritized key files listed.
                    </span>
                  )}
                </div>
              </div>

              {/* All Files in Module (if loaded from detail) */}
              {moduleDetail?.files && moduleDetail.files.length > 0 && (
                <div className="space-y-2">
                  <span className="text-[11px] uppercase tracking-wider text-text-muted font-bold block">
                    All Module Files ({moduleDetail.files.length})
                  </span>
                  <div className="max-h-40 overflow-y-auto space-y-1 bg-surface-2/30 p-2 rounded-xl border border-border/40 text-[11px]">
                    {moduleDetail.files.map((f) => (
                      <button
                        key={f}
                        type="button"
                        onClick={() => setActiveCodeFile(f)}
                        className="w-full text-left py-1 px-1.5 rounded hover:bg-surface-2 text-text-muted hover:text-text truncate block cursor-pointer transition-colors"
                      >
                        {f}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Module Dependencies (Incoming & Outgoing) */}
              <div className="space-y-3 pt-2 border-t border-border/60">
                <span className="text-[11px] uppercase tracking-wider text-text-muted font-bold block">
                  Dependencies
                </span>

                <div className="space-y-2">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-text-muted">Imports ({moduleDetail?.neighbors?.outgoing?.length || 0}):</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {(moduleDetail?.neighbors?.outgoing || []).length > 0 ? (
                      moduleDetail!.neighbors.outgoing.map((out) => (
                        <button
                          key={out.id}
                          type="button"
                          onClick={() => setSelectedNodeId(out.id)}
                          className="px-2 py-1 rounded bg-surface-2 border border-border text-[11px] hover:border-brand text-text transition-colors cursor-pointer"
                        >
                          {out.name}
                        </button>
                      ))
                    ) : (
                      <span className="text-text-muted/60 text-[11px]">No outgoing dependencies.</span>
                    )}
                  </div>
                </div>

                <div className="space-y-2 pt-2">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-text-muted">Imported By ({moduleDetail?.neighbors?.incoming?.length || 0}):</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {(moduleDetail?.neighbors?.incoming || []).length > 0 ? (
                      moduleDetail!.neighbors.incoming.map((inc) => (
                        <button
                          key={inc.id}
                          type="button"
                          onClick={() => setSelectedNodeId(inc.id)}
                          className="px-2 py-1 rounded bg-surface-2 border border-border text-[11px] hover:border-brand text-text transition-colors cursor-pointer"
                        >
                          {inc.name}
                        </button>
                      ))
                    ) : (
                      <span className="text-text-muted/60 text-[11px]">No incoming dependents.</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </aside>
        )}
      </div>

      {/* CODE VIEWER MODAL OVERLAY */}
      {activeCodeFile && (
        <div className="fixed inset-0 z-50 bg-bg/80 backdrop-blur-sm flex items-center justify-center p-4 sm:p-8 animate-fadeIn">
          <div className="w-full max-w-4xl h-[80vh] flex flex-col shadow-2xl rounded-2xl overflow-hidden">
            <CodeViewer
              repoId={repoId}
              filePath={activeCodeFile}
              onClose={() => setActiveCodeFile(null)}
              jumpLine={1}
            />
          </div>
        </div>
      )}

      {/* HOW TO RUN LOCALLY DIALOG */}
      <Dialog open={runInstructionsOpen} onOpenChange={setRunInstructionsOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-brand" />
              <span>How to Run Locally</span>
            </DialogTitle>
            <DialogDescription>
              Extracted setup and execution commands from the repository manifests and documentation.
            </DialogDescription>
          </DialogHeader>

          <div className="mt-4 p-4 rounded-xl bg-surface-2 border border-border font-mono text-xs overflow-x-auto whitespace-pre-wrap select-text leading-relaxed">
            {runInstructions || 'No setup instructions detected in manifest files.'}
          </div>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}
