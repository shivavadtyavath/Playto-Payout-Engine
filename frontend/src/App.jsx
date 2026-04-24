import React from 'react';
import { MerchantProvider, useMerchant } from './context/MerchantContext';
import Header from './components/Header';
import BalanceCard from './components/BalanceCard';
import PayoutForm from './components/PayoutForm';
import PayoutHistory from './components/PayoutHistory';
import LedgerTable from './components/LedgerTable';
import { useQuery } from '@tanstack/react-query';
import { api } from './api/client';
import { formatINR } from './utils/formatters';

function MerchantBanner() {
  const { merchantId, SEED_MERCHANTS } = useMerchant();
  const current = SEED_MERCHANTS.find(m => m.id === merchantId);

  const { data: balance } = useQuery({
    queryKey: ['balance', merchantId],
    queryFn: () => api.getMerchantBalance(merchantId),
    refetchInterval: 5000,
    enabled: !!merchantId,
  });

  return (
    <div className="relative overflow-hidden rounded-2xl p-6 mb-6"
      style={{
        background: 'linear-gradient(135deg, rgba(99,102,241,0.15) 0%, rgba(139,92,246,0.1) 50%, rgba(6,182,212,0.08) 100%)',
        border: '1px solid rgba(99,102,241,0.2)',
      }}>
      {/* Background grid */}
      <div className="absolute inset-0 opacity-5"
        style={{
          backgroundImage: 'linear-gradient(rgba(99,102,241,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(99,102,241,0.5) 1px, transparent 1px)',
          backgroundSize: '40px 40px',
        }} />

      {/* Glow orbs */}
      <div className="absolute top-0 right-0 w-64 h-64 rounded-full opacity-10 -translate-y-32 translate-x-32"
        style={{ background: 'radial-gradient(circle, #6366f1, transparent)' }} />
      <div className="absolute bottom-0 left-0 w-48 h-48 rounded-full opacity-10 translate-y-24 -translate-x-24"
        style={{ background: 'radial-gradient(circle, #06b6d4, transparent)' }} />

      <div className="relative flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold text-indigo-300 uppercase tracking-wider">Merchant Account</span>
            <span className="text-[10px] px-2 py-0.5 rounded-full font-medium text-emerald-300"
              style={{ background: 'rgba(16,185,129,0.15)', border: '1px solid rgba(16,185,129,0.25)' }}>
              Active
            </span>
          </div>
          <h1 className="text-2xl font-bold text-white mb-1">{current?.name}</h1>
          <p className="text-xs text-slate-400 font-mono">{merchantId}</p>
        </div>

        <div className="hidden md:flex items-center gap-6">
          <div className="text-right">
            <p className="text-xs text-slate-400 mb-1">Net Balance</p>
            <p className="text-2xl font-bold text-white">
              {balance ? formatINR(balance.available_balance_paise) : '—'}
            </p>
          </div>
          <div className="w-px h-12 bg-white/10" />
          <div className="text-right">
            <p className="text-xs text-slate-400 mb-1">In Transit</p>
            <p className="text-2xl font-bold text-amber-400">
              {balance ? formatINR(balance.held_balance_paise) : '—'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function Dashboard() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      {/* Merchant banner */}
      <MerchantBanner />

      {/* Stats row */}
      <div className="mb-6">
        <BalanceCard />
      </div>

      {/* Main content: form + history */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-6">
        <div className="lg:col-span-4">
          <PayoutForm />
        </div>
        <div className="lg:col-span-8">
          <PayoutHistory />
        </div>
      </div>

      {/* Ledger */}
      <LedgerTable />

      {/* Footer */}
      <div className="mt-8 pt-6 border-t border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)' }}>
            <span className="text-white font-bold text-[10px]">P</span>
          </div>
          <span className="text-xs text-slate-500">Playto Pay · Payout Engine v1.0</span>
        </div>
        <div className="flex items-center gap-4 text-xs text-slate-600">
          <span>All amounts in INR</span>
          <span>·</span>
          <span>Stored as paise (integer)</span>
          <span>·</span>
          <span className="flex items-center gap-1">
            <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full pulse-dot" />
            Live updates every 5s
          </span>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <MerchantProvider>
      <div className="min-h-screen" style={{ background: '#0f0f14' }}>
        <Header />
        <main>
          <Dashboard />
        </main>
      </div>
    </MerchantProvider>
  );
}
