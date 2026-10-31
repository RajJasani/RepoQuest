'use client';

import React, { useState, useMemo, useCallback } from 'react';
import {
  ReactFlow,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
  Node,
  Edge,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { ArchitectureNode, ArchitectureEdge } from '@/lib/schemas';
import { ModuleNodeComponent, ModuleNodeData } from './ModuleNode';
import { ModuleEdgeComponent, ModuleEdgeData } from './ModuleEdge';
import { Search, Compass } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ModuleGraphProps {
  nodes: ArchitectureNode[];
  edges: ArchitectureEdge[];
  selectedNodeId?: string | null;
  onSelectNode?: (nodeId: string) => void;
  highlightedNodeIds?: string[];
  className?: string;
}

const nodeTypes = {
  module: ModuleNodeComponent,
};

const edgeTypes = {
  moduleEdge: ModuleEdgeComponent,
};

export function ModuleGraphInternal({
  nodes: rawNodes,
  edges: rawEdges,
  selectedNodeId,
  onSelectNode,
  highlightedNodeIds = [],
  className,
}: ModuleGraphProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

  // Compute graph topology (in-degrees, adjacency, distance from entry)
  const { adjacency, distanceMap } = useMemo(() => {
    const adj: Record<string, string[]> = {};
    const inDeg: Record<string, number> = {};

    rawNodes.forEach((n) => {
      adj[n.id] = [];
      inDeg[n.id] = 0;
    });

    rawEdges.forEach((e) => {
      if (adj[e.source]) adj[e.source].push(e.target);
      if (inDeg[e.target] !== undefined) inDeg[e.target] = (inDeg[e.target] || 0) + 1;
    });

    // BFS from root/entry nodes to determine distance
    const dist: Record<string, number> = {};
    const queue: string[] = [];

    rawNodes.forEach((n) => {
      const isEntry = (n.entry_points && n.entry_points.length > 0) || inDeg[n.id] === 0;
      if (isEntry) {
        dist[n.id] = 0;
        queue.push(n.id);
      }
    });

    // Fallback if no clean entry
    if (queue.length === 0 && rawNodes.length > 0) {
      dist[rawNodes[0].id] = 0;
      queue.push(rawNodes[0].id);
    }

    while (queue.length > 0) {
      const curr = queue.shift()!;
      const d = dist[curr];
      (adj[curr] || []).forEach((nxt) => {
        if (dist[nxt] === undefined) {
          dist[nxt] = d + 1;
          queue.push(nxt);
        }
      });
    }

    return { adjacency: adj, distanceMap: dist };
  }, [rawNodes, rawEdges]);

  // Compute Layout (Layered hierarchy by distance or grid)
  const layoutPositions = useMemo(() => {
    const layers: Record<number, ArchitectureNode[]> = {};

    rawNodes.forEach((node) => {
      const dist = distanceMap[node.id] ?? 0;
      if (!layers[dist]) layers[dist] = [];
      layers[dist].push(node);
    });

    const positions: Record<string, { x: number; y: number }> = {};
    const layerKeys = Object.keys(layers)
      .map(Number)
      .sort((a, b) => a - b);

    layerKeys.forEach((layerIndex) => {
      const layerNodes = layers[layerIndex];
      const count = layerNodes.length;
      const spacingX = 220;
      const totalWidth = (count - 1) * spacingX;

      layerNodes.forEach((node, colIndex) => {
        const x = colIndex * spacingX - totalWidth / 2 + 250;
        const y = layerIndex * 150 + 60;
        positions[node.id] = { x, y };
      });
    });

    return positions;
  }, [rawNodes, distanceMap]);

  // Compute neighbor set for active hover
  const activeNeighbors = useMemo(() => {
    if (!hoveredNodeId) return new Set<string>();
    const neighbors = new Set<string>();
    neighbors.add(hoveredNodeId);

    // Direct outgoing neighbors
    (adjacency[hoveredNodeId] || []).forEach((id) => neighbors.add(id));

    // Direct incoming neighbors
    rawEdges.forEach((e) => {
      if (e.target === hoveredNodeId) neighbors.add(e.source);
    });

    return neighbors;
  }, [hoveredNodeId, adjacency, rawEdges]);

  // Transform raw nodes to ReactFlow nodes
  const flowNodes: Node<ModuleNodeData>[] = useMemo(() => {
    return rawNodes.map((n) => {
      const isSelected = selectedNodeId === n.id;
      const isHovered = hoveredNodeId === n.id;
      const isNeighbor = activeNeighbors.has(n.id);
      const isDimmed = Boolean(hoveredNodeId && !isNeighbor);
      const isHighlighted =
        highlightedNodeIds.includes(n.id) ||
        (searchQuery.trim().length > 0 &&
          (n.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            n.path.toLowerCase().includes(searchQuery.toLowerCase())));

      const pos = layoutPositions[n.id] || { x: 0, y: 0 };

      return {
        id: n.id,
        type: 'module',
        position: pos,
        data: {
          id: n.id,
          name: n.name,
          path: n.path,
          fileCount: n.file_count,
          entryPoints: n.entry_points,
          distanceFromEntry: distanceMap[n.id] ?? 0,
          isHovered,
          isNeighbor,
          isDimmed,
          isHighlighted,
        },
        selected: isSelected,
      };
    });
  }, [
    rawNodes,
    selectedNodeId,
    hoveredNodeId,
    activeNeighbors,
    highlightedNodeIds,
    searchQuery,
    layoutPositions,
    distanceMap,
  ]);

  // Transform raw edges to ReactFlow edges
  const flowEdges: Edge<ModuleEdgeData>[] = useMemo(() => {
    return rawEdges.map((e, idx) => {
      const isConnectedToHover =
        hoveredNodeId !== null &&
        (e.source === hoveredNodeId || e.target === hoveredNodeId);
      const isDimmed = hoveredNodeId !== null && !isConnectedToHover;
      const isHighlighted = isConnectedToHover;

      return {
        id: `e-${e.source}-${e.target}-${idx}`,
        source: e.source,
        target: e.target,
        type: 'moduleEdge',
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isHighlighted ? 'var(--amber)' : 'var(--brand)',
          width: 14,
          height: 14,
        },
        data: {
          weight: e.weight,
          isDimmed,
          isHighlighted,
        },
      };
    });
  }, [rawEdges, hoveredNodeId]);

  // Node selection callback
  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      if (onSelectNode) {
        onSelectNode(node.id);
      }
    },
    [onSelectNode]
  );

  const handleNodeMouseEnter = useCallback((_: React.MouseEvent, node: Node) => {
    setHoveredNodeId(node.id);
  }, []);

  const handleNodeMouseLeave = useCallback(() => {
    setHoveredNodeId(null);
  }, []);

  return (
    <div className={cn('relative w-full h-full bg-[#0A0D1A] overflow-hidden', className)}>
      {/* Search Bar Overlay */}
      <div className="absolute top-4 left-4 z-20 flex items-center gap-2">
        <div className="relative flex items-center">
          <Search className="w-3.5 h-3.5 text-text-muted absolute left-3 pointer-events-none" />
          <input
            type="text"
            placeholder="Search modules..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-48 sm:w-64 pl-8 pr-3 py-1.5 text-xs font-mono bg-surface-1/90 backdrop-blur-md border border-border rounded-xl text-text placeholder:text-text-muted/60 focus:outline-none focus:ring-1 focus:ring-brand shadow-sm"
          />
        </div>

        {/* Node stats pill */}
        <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 bg-surface-1/90 backdrop-blur-md border border-border rounded-xl font-mono text-xs text-text-muted">
          <Compass className="w-3.5 h-3.5 text-brand" />
          <span>
            {rawNodes.length} modules · {rawEdges.length} edges
          </span>
        </div>
      </div>

      {/* ReactFlow Canvas */}
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodeClick={handleNodeClick}
        onNodeMouseEnter={handleNodeMouseEnter}
        onNodeMouseLeave={handleNodeMouseLeave}
        fitView
        fitViewOptions={{ padding: 0.25 }}
        minZoom={0.2}
        maxZoom={1.8}
        proOptions={{ hideAttribution: true }}
      >
        {/* Background Dots */}
        <Background
          variant={BackgroundVariant.Dots}
          gap={18}
          size={1}
          color="rgba(42, 53, 96, 0.6)"
        />

        {/* Viewport Zoom Controls */}
        <Controls
          showInteractive={false}
          className="!bg-surface-1 !border-border !rounded-xl !shadow-md [&>button]:!border-border [&>button]:!bg-surface-1 [&>button]:hover:!bg-surface-2 [&>button]:!text-text"
        />

        {/* MiniMap */}
        <MiniMap
          nodeColor={(n) => {
            if (n.id === selectedNodeId) return 'var(--brand)';
            return 'var(--surface-3)';
          }}
          maskColor="rgba(10, 13, 26, 0.7)"
          className="!bg-surface-1/80 !border-border !rounded-xl !shadow-sm overflow-hidden hidden sm:block"
        />
      </ReactFlow>
    </div>
  );
}

export default ModuleGraphInternal;
