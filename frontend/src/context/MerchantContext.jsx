import React, { createContext, useContext, useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const MerchantContext = createContext(null);

// Seeded merchant IDs from seed_data.py
const SEED_MERCHANTS = [
  { id: '11111111-1111-1111-1111-111111111111', name: 'Arjun Sharma Design Studio' },
  { id: '22222222-2222-2222-2222-222222222222', name: 'Priya Nair Freelance Dev' },
  { id: '33333333-3333-3333-3333-333333333333', name: 'Rahul Mehta Content Agency' },
];

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 2000,
    },
  },
});

export function MerchantProvider({ children }) {
  const [merchantId, setMerchantId] = useState(
    () => localStorage.getItem('merchantId') || SEED_MERCHANTS[0].id
  );

  const handleMerchantChange = (id) => {
    setMerchantId(id);
    localStorage.setItem('merchantId', id);
    // Invalidate all queries when switching merchants
    queryClient.invalidateQueries();
  };

  return (
    <QueryClientProvider client={queryClient}>
      <MerchantContext.Provider value={{ merchantId, setMerchantId: handleMerchantChange, SEED_MERCHANTS }}>
        {children}
      </MerchantContext.Provider>
    </QueryClientProvider>
  );
}

export function useMerchant() {
  const ctx = useContext(MerchantContext);
  if (!ctx) throw new Error('useMerchant must be used within MerchantProvider');
  return ctx;
}

export { queryClient };
