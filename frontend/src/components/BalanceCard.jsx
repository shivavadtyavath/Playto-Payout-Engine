import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useMerchant } from '../context/MerchantContext';
import { api } from '../api/client';
import { formatINR } from '../utils/formatters';

function StatCard({ label, value, paise, icon, color, glowClass, trend }) {
  return (
    <div className={`stat-card glass-card rounded-2xl p-6 ${glowClass} relative overflow-hidden`}>
      {/* Background decoration */}
      <div className="absolute top-0 right-0 w-32 h-32 rounded-full opacity-5 -translate-y-8 translate-x-8"
        style={{ background: color }} />

      <div className="relative">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center text-base"
              style={{ background: `${color}20`, border: `1px solid ${color}30` }}>
              {icon}
            </div>
            <span className="text-sm font-medium text-slate-400">{label}</span>
          </div>
          {trend && (
            <span className="text-xs font-medium px-2 py-1 rounded-full"
              style={{ background: 'rgba(16,185,129,0.1)', color: '#10b981' }}>
              {trend}
            </span>
          )}
        </div>

        <div className="count-up">
          <p className="text-3xl font-bold text-white tracking-tight mb-1">{value}</p>
          <p className="text-xs text-slate-500 font-mono">{paise?.toLocaleString('en-IN')} paise</p>
        </div>
      </div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="glass-card rounded-2xl p-6">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-8 h-8 rounded-lg shimmer" />
        <div className="h-4 w-28 rounded shimmer" />
      </div>
      <div className="h-8 w-40 rounded shimmer mb-2" />
      <div className="h-3 w-24 rounded shimmer" />
    </div>
  );
}

export default function BalanceCard() {
  const { merchantId } = useMerchant();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['balance', merchantId],
    queryFn: () => api.getMerchantBalance(merchantId),
    refetchInterval: 5000,
    enabled: !!merchantId,
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[1,2,3,4].map(i => <SkeletonCard key={i} />)}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="glass-card rounded-2xl p-4 border border-red-500/20 text-red-400 text-sm">
        Failed to load balance data. Retrying...
      </div>
    );
  }

  const available = data?.available_balance_paise ?? 0;
  const held = data?.held_balance_paise ?? 0;
  const total = available + held;
  const utilization = total > 0 ? Math.round((held / total) * 100) : 0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard
        label="Available Balance"
        value={formatINR(available)}
        paise={available}
        icon="💰"
        color="#10b981"
        glowClass="glow-green"
        trend="Active"
      />
      <StatCard
        label="Held Balance"
        value={formatINR(held)}
        paise={held}
        icon="⏳"
        color="#f59e0b"
        glowClass="glow-amber"
      />
      <StatCard
        label="Total Credited"
        value={formatINR(total)}
        paise={total}
        icon="📈"
        color="#6366f1"
        glowClass="glow-blue"
      />
      {/* Utilization card */}
      <div className="stat-card glass-card rounded-2xl p-6 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-32 h-32 rounded-full opacity-5 -translate-y-8 translate-x-8"
          style={{ background: '#06b6d4' }} />
        <div className="relative">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center text-base"
              style={{ background: 'rgba(6,182,212,0.1)', border: '1px solid rgba(6,182,212,0.2)' }}>
              📊
            </div>
            <span className="text-sm font-medium text-slate-400">Funds Utilization</span>
          </div>
          <p className="text-3xl font-bold text-white tracking-tight mb-3">{utilization}%</p>
          <div className="w-full h-1.5 rounded-full bg-slate-700/50">
            <div className="h-full rounded-full transition-all duration-700"
              style={{
                width: `${utilization}%`,
                background: 'linear-gradient(90deg, #6366f1, #06b6d4)'
              }} />
          </div>
          <p className="text-xs text-slate-500 mt-2">of balance in payouts</p>
        </div>
      </div>
    </div>
  );
}
