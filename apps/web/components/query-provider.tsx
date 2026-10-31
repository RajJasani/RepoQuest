'use client';

import React, { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ApiError } from '@/lib/api';

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // Retry max 2 times on network errors only
            retry: (failureCount, error) => {
              if (failureCount >= 2) return false;
              if (error instanceof ApiError && error.code === 'network_error') {
                return true;
              }
              if (error instanceof TypeError && error.message.includes('fetch')) {
                return true;
              }
              return false;
            },
            staleTime: 30000,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

export default QueryProvider;
