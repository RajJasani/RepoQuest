import Link from 'next/link';

export default function HomePage() {
  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-8 text-center">
      <div className="max-w-md w-full p-8 rounded-lg bg-surface-1 border border-border quest-card shadow-card">
        <h1 className="font-display font-bold text-3xl mb-4 text-text">RepoQuest</h1>
        <p className="text-text-muted mb-6">
          Help maintainers keep up. Help newcomers get started.
        </p>
        <Link
          href="/design"
          className="inline-flex items-center justify-center px-4 py-2 font-medium rounded-md bg-brand text-bg hover:opacity-90 transition-opacity"
        >
          View Design System (/design)
        </Link>
      </div>
    </main>
  );
}
