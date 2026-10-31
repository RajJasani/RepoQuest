export const LANGUAGE_COLORS: Record<string, string> = {
  Python: 'var(--sky)',
  TypeScript: 'var(--amber)',
  JavaScript: 'var(--amber)',
  Go: 'var(--mint)',
  Rust: 'var(--flame)',
  HTML: 'var(--rose)',
  CSS: 'var(--brand-2)',
  Markdown: 'var(--brand)',
  Shell: 'var(--mint)',
  C: 'var(--sky)',
  'C++': 'var(--sky)',
  Java: 'var(--flame)',
  Kotlin: 'var(--brand)',
  Ruby: 'var(--rose)',
  Swift: 'var(--flame)',
  JSON: 'var(--text-muted)',
  YAML: 'var(--brand-2)',
  Dockerfile: 'var(--sky)',
  SQL: 'var(--mint)',
};

export function getLanguageColor(language?: string | null): string {
  if (!language) return 'var(--brand)';
  return LANGUAGE_COLORS[language] || 'var(--brand)';
}

