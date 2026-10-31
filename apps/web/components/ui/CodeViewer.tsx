'use client';

import React, { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { FileContentResponse, FileContentResponseSchema } from '@/lib/schemas';
import { cn } from '@/lib/utils';
import { Copy, Check, X, ArrowDown, FileCode, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { showToast } from '@/components/ui/Toast';

export interface CodeViewerProps {
  repoId?: string;
  filePath?: string;
  content?: string;
  startLine?: number;
  endLine?: number;
  jumpLine?: number;
  highlightRange?: { start: number; end: number };
  language?: string;
  className?: string;
  onClose?: () => void;
}

export function CodeViewer({
  repoId,
  filePath,
  content: directContent,
  startLine,
  endLine,
  jumpLine,
  highlightRange,
  className,
  onClose,
}: CodeViewerProps) {
  const [copied, setCopied] = useState(false);
  const [targetLineInput, setTargetLineInput] = useState<string>('');
  const [activeFlashLine, setActiveFlashLine] = useState<number | null>(jumpLine || null);
  const [flashKey, setFlashKey] = useState<number>(0);

  const containerRef = useRef<HTMLDivElement>(null);
  const lineRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  // Query file content from backend if repoId and filePath are provided and direct content is absent
  const { data: fileData, isLoading, error } = useQuery<FileContentResponse>({
    queryKey: ['file-content', repoId, filePath, startLine, endLine],
    queryFn: async () => {
      if (!repoId || !filePath) throw new Error('Missing repoId or filePath');
      const params = new URLSearchParams({ path: filePath });
      if (startLine) params.set('start', String(startLine));
      if (endLine) params.set('end', String(endLine));
      const res = await api.get<unknown>(`/repos/${repoId}/files?${params.toString()}`);
      return FileContentResponseSchema.parse(res);
    },
    enabled: Boolean(repoId && filePath && directContent === undefined),
    staleTime: 60 * 1000,
  });

  const rawContent = directContent !== undefined ? directContent : fileData?.content || '';
  const baseStartLine = startLine || fileData?.start_line || 1;

  // Split lines
  const lines = useMemo(() => {
    return rawContent.split(/\r?\n/);
  }, [rawContent]);

  // Jump to specific line with Amber flash
  const performJumpToLine = useCallback(
    (lineNum: number) => {
      if (lineNum < baseStartLine || lineNum >= baseStartLine + lines.length) {
        showToast.error(`Line ${lineNum} is out of bounds (1 - ${lines.length})`);
        return;
      }

      const lineElement = lineRefs.current.get(lineNum);
      if (lineElement) {
        lineElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
        setActiveFlashLine(lineNum);
        setFlashKey((k) => k + 1);
      }
    },
    [baseStartLine, lines.length]
  );

  // Jump on mount or when jumpLine prop changes
  useEffect(() => {
    if (jumpLine) {
      const timer = setTimeout(() => {
        performJumpToLine(jumpLine);
      }, 150);
      return () => clearTimeout(timer);
    }
  }, [jumpLine, performJumpToLine]);

  const handleCopy = () => {
    navigator.clipboard.writeText(rawContent);
    setCopied(true);
    showToast.success('File content copied to clipboard');
    setTimeout(() => setCopied(false), 2000);
  };

  // Lightweight token coloring for syntax display (Dusk: Sky, Amber, Rose, Mint on ink)
  const renderHighlightedLine = (text: string) => {
    if (!text) return <span>&nbsp;</span>;

    // Detect comment
    if (/^\s*(#|\/\/|\/\*).*/.test(text)) {
      return <span className="text-text-muted/70 italic">{text}</span>;
    }

    // Split on string literals first
    const parts = text.split(/(".*?"|'.*?'|`.*?`)/g);

    return parts.map((part, i) => {
      // String literal -> Mint
      if (/^(".*?"|'.*?'|`.*?`)$/.test(part)) {
        return (
          <span key={i} className="text-mint">
            {part}
          </span>
        );
      }

      // Tokenize words
      const words = part.split(/(\b[A-Za-z0-9_]+\b|[^\w\s]+|\s+)/g);
      return words.map((w, j) => {
        // Keywords -> Rose / Flame
        if (
          /^(def|function|class|return|import|from|export|const|let|var|if|else|elif|for|while|try|except|catch|finally|async|await|with|as|type|interface|enum|yield)$/.test(
            w
          )
        ) {
          return (
            <span key={j} className="text-rose font-medium">
              {w}
            </span>
          );
        }
        // Types / Capitalized classes -> Sky
        if (/^[A-Z][A-Za-z0-9_]*$/.test(w)) {
          return (
            <span key={j} className="text-sky font-semibold">
              {w}
            </span>
          );
        }
        // Numbers / Boolean -> Amber
        if (/^(\d+(\.\d+)?|true|false|None|null|undefined)$/.test(w)) {
          return (
            <span key={j} className="text-amber">
              {w}
            </span>
          );
        }
        // Method calls / Functions -> Brand-2
        if (/^[a-z_][a-z0-9_]*$/.test(w) && part[part.indexOf(w) + w.length] === '(') {
          return (
            <span key={j} className="text-brand-2">
              {w}
            </span>
          );
        }

        return <span key={j}>{w}</span>;
      });
    });
  };

  return (
    <div
      className={cn(
        'flex flex-col h-full w-full rounded-2xl border border-border bg-[#0B0F19] text-[#EDF1FF] overflow-hidden shadow-lg isolate',
        className
      )}
    >
      {/* Header Bar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-surface-1 border-b border-border/70 select-none">
        <div className="flex items-center gap-2 min-w-0">
          <FileCode className="w-4 h-4 text-brand shrink-0" />
          <span className="font-mono text-xs font-bold text-text truncate">
            {filePath || 'Source Viewer'}
          </span>
          <span className="font-mono text-[11px] text-text-muted shrink-0">
            ({lines.length} lines)
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Jump to Line Form */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const num = parseInt(targetLineInput, 10);
              if (!isNaN(num)) performJumpToLine(num);
            }}
            className="hidden sm:flex items-center gap-1.5"
          >
            <input
              type="number"
              placeholder="Line #"
              value={targetLineInput}
              onChange={(e) => setTargetLineInput(e.target.value)}
              className="w-16 px-2 py-1 text-xs font-mono bg-surface-2 border border-border rounded text-text placeholder:text-text-muted/60 focus:outline-none focus:ring-1 focus:ring-brand"
            />
            <Button
              type="submit"
              variant="ghost"
              className="p-1 h-7 text-xs font-mono text-text-muted hover:text-text"
              title="Jump to line"
            >
              <ArrowDown className="w-3.5 h-3.5" />
            </Button>
          </form>

          {/* Copy Button */}
          <Button
            variant="ghost"
            onClick={handleCopy}
            className="p-1.5 h-8 text-text-muted hover:text-text"
            title="Copy code"
          >
            {copied ? <Check className="w-4 h-4 text-mint" /> : <Copy className="w-4 h-4" />}
          </Button>

          {/* Close Button if modal/drawer context */}
          {onClose && (
            <Button
              variant="ghost"
              onClick={onClose}
              className="p-1.5 h-8 text-text-muted hover:text-rose hover:bg-rose/10"
              title="Close viewer"
            >
              <X className="w-4 h-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex-1 flex items-center justify-center py-16 gap-3 text-text-muted font-mono text-xs">
          <Loader2 className="w-4 h-4 animate-spin text-brand" />
          <span>Retrieving file content from disk...</span>
        </div>
      )}

      {/* Error State */}
      {error && !isLoading && (
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-center space-y-2">
          <p className="text-xs font-mono text-flame">
            Failed to read file: {error instanceof Error ? error.message : 'Not found'}
          </p>
        </div>
      )}

      {/* Code Text Container */}
      {!isLoading && !error && (
        <div
          ref={containerRef}
          className="flex-1 overflow-auto font-mono text-[13px] leading-5 select-text py-2 scroll-smooth"
        >
          {lines.map((lineText, idx) => {
            const currentLineNum = baseStartLine + idx;
            const isFlash = activeFlashLine === currentLineNum;
            const isRange =
              highlightRange &&
              currentLineNum >= highlightRange.start &&
              currentLineNum <= highlightRange.end;

            return (
              <div
                key={`${currentLineNum}-${flashKey}`}
                ref={(el) => {
                  if (el) lineRefs.current.set(currentLineNum, el);
                  else lineRefs.current.delete(currentLineNum);
                }}
                className={cn(
                  'flex items-stretch px-3 transition-colors',
                  isFlash && 'animate-amber-flash border-l-2 border-amber',
                  isRange && !isFlash && 'bg-brand/10 border-l-2 border-brand',
                  !isFlash && !isRange && 'hover:bg-surface-2/30'
                )}
              >
                {/* Line Number Gutter */}
                <span className="w-10 shrink-0 text-right pr-4 text-text-muted/40 select-none font-mono text-xs">
                  {currentLineNum}
                </span>

                {/* Code Content */}
                <pre className="flex-1 overflow-x-auto whitespace-pre font-mono font-normal">
                  {renderHighlightedLine(lineText)}
                </pre>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
