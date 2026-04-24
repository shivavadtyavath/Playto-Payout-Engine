import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useMerchant } from '../context/MerchantContext';
import { api } from '../api/client';
import { formatINR, formatDate } from '../utils/formatters';

const STATUS_CONFIG = {
  pending:    { label: 'Pending',    color: '#f59e0b', bg: 'rgba(245,158,11,0.12)',    border: 'rgba(245,158,11,0.25)',    dot: 'bg-amber-400',    badge: 'badge-pending',   icon: '⏳' },
  processing: { label: 'Processing', color: '#6366f1', bg: 'rgba(99,102,241,0.12)',   border: 'rgba(99,102,241,0.25)',   dot: 'bg-indigo-400',   badge: 'badge-processing',icon: '⚡' },
  completed:  { label: 'Completed',  color: '#10b981', bg: 'rgba(16,185,129,0.12)',   border: 'rgba(16,185,129,0.25)',   dot: 'bg-emerald-400',  badge: 'badge-completed', icon: '✓' },
  failed:     { label: 'Failed',     color: '#ef4444', bg: 'rgba(239,68,68,0.12)',    border: 'rgba(239,68,68,0.25)',    dot: 'bg-red-400',      badge: 'badge-failed',    icon: '✕' },
};

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${cfg.badge}`}
      style={{ background: cfg.bg, border: `1px solid ${cfg.border}`, color: cfg.color }}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot} ${status === 'processing' ? 'pulse-dot' : ''}`} />
      {cfg.label}
    </span>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-4"
        style={{ background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.2)' }}>
        <svg className="w-8 h-8 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
      </div>
      <p className="text-slate-300 font-semibold mb-1">No payouts yet</p>
      <p className="text-slate-500 text-sm text-center">Request your first payout using the form on the left.</p>
    </div>
  );
}

export default function PayoutHistory() {
  const { merchantId } = useMerchant();
  const [filter, setFilter] = useState('all');

  const { data: payouts, isLoading } = useQuery({
    queryKey: ['payouts', merchantId],
    queryFn: () => api.getPayouts(merchantId),
    refetchInterval: 5000,
    enabled: !!merchantId,
  });

  const filtered = filter === 'all' ? payouts : payouts?.filter(p => p.status === filter);

  const counts = payouts?.reduce((acc, p) => {
    acc[p.status] = (acc[p.status] || 0) + 1;
    return acc;
  }, {}) || {};

  return (
    <div className="glass-card rounded-2xl overflow-hidden flex flex-col">
      {/* Header */}
      <div className="px-6 pt-6 pb-4 border-b border-white/5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center"
              style={{ background: 'rgba(99,102,241,0.15)', border: '1px solid rgba(99,102,241,0.25)' }}>
              <svg className="w-4 h-4 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">Payout History</h2>
              <p className="text-xs text-slate-500">{payouts?.length || 0} total · refreshes every 5s</p>
            </div>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full"
            style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.15)' }}>
            <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full pulse-dot" />
            <span className="text-xs text-emerald-400 font-medium">Live</span>
          </div>
        </div>

        {/* Filter tabs */}
        <div className="flex gap-1 p-1 rounded-xl" style={{ background: 'rgba(255,255,255,0.03)' }}>
          {['all', 'pending', 'processing', 'completed', 'failed'].map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-medium transition-all capitalize ${
                filter === f ? 'text-white' : 'text-slate-500 hover:text-slate-300'
              }`}
              style={filter === f ? { background: 'rgba(99,102,241,0.3)', border: '1px solid rgba(99,102,241,0.4)' } : {}}>
              {f === 'all' ? `All ${payouts?.length ? `(${payouts.length})` : ''}` : (
                <span className="flex items-center justify-center gap-1">
                  {f}
                  {counts[f] ? <span className="text-[10px] opacity-70">({counts[f]})</span> : ''}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        {isLoading ? (
          <div className="p-4 space-y-3">
            {[1,2,3].map(i => (
              <div key={i} className="h-14 rounded-xl shimmer" />
            ))}
          </div>
        ) : !filtered?.length ? (
          <EmptyState />
        ) : (
          <table className="w-full">
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                {['Payout ID', 'Amount', 'Bank Account', 'Status', 'Created'].map(h => (
                  <th key={h} className="px-5 py-3 text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((payout, i) => (
                <tr key={payout.id}
                  className="table-row-hover transition-all cursor-pointer"
                  style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                  <td className="px-5 py-4">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-lg flex items-center justify-center text-xs"
                        style={{ background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.15)' }}>
                        {STATUS_CONFIG[payout.status]?.icon}
                      </div>
                      <span className="font-mono text-xs text-slate-400">
                        {payout.id.substring(0, 8)}...
                      </span>
                    </div>
                  </td>
                  <td className="px-5 py-4">
                    <span className="text-sm font-bold text-white">{formatINR(payout.amount_paise)}</span>
                  </td>
                  <td className="px-5 py-4">
                    <span className="font-mono text-xs text-slate-500">
                      ••••{String(payout.bank_account_id).substring(0, 8)}...
                    </span>
                  </td>
                  <td className="px-5 py-4">
                    <StatusBadge status={payout.status} />
                  </td>
                  <td className="px-5 py-4">
                    <span className="text-xs text-slate-500">{formatDate(payout.created_at)}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
