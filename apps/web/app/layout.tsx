import type { Metadata } from 'next';
import './globals.css';
import { fontVariables } from '@/lib/fonts';
import { ThemeProvider } from '@/components/theme-provider';
import { CalmProvider } from '@/lib/calm';
import { MotionProvider } from '@/components/motion-provider';
import { QueryProvider } from '@/components/query-provider';
import { SettingsProvider } from '@/lib/settings-context';
import { Toaster } from 'sonner';

export const metadata: Metadata = {
  title: 'RepoQuest',
  description: 'Help maintainers keep up. Help newcomers get started.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning className={fontVariables}>
      <body className="bg-bg text-text antialiased min-h-screen">
        <ThemeProvider
          attribute="data-theme"
          defaultTheme="dusk"
          themes={['dusk', 'parchment']}
          enableSystem={false}
        >
          <QueryProvider>
            <SettingsProvider>
              <CalmProvider>
                <MotionProvider>
                  {children}
                  <Toaster richColors position="bottom-right" />
                </MotionProvider>
              </CalmProvider>
            </SettingsProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}

