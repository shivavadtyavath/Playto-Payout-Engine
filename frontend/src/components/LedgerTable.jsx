import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useMerchant } from '../context/MerchantContext';
import { api } from '../api/client';
import { formatINR, formatDate } from '../utils/formatters';

export default function LedgerTable() {
  const { merchantId } = useMerchant();

  const { data: entries, isLoading } = useQuery({
    queryKey: ['ledger', merchantId],
    queryFn: () => api.getLedger(merchantId),
    refetchInterval: 5000,
    enabled: !!merchantId,
  });

  const totalCredits = entries?.filter(e => e.entry_type === 'credit').reduce((s, e) => s + e.amount_paise, 0) || 0;
  const totalDebits  = entries?.filter(e => e.entry_type === 'debit').reduce((s, e) => s + e.amount_paise, 0) || 0;

  return (
    <div className="glass-card rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="px-6 pt-6 pb-4 border-b border-white/5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center"
              style={{ background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.2)' }}>
              <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">Ledger</h2>
              <p className="text-xs text-slate-500">Append-only · immutable audit trail</p>
            </div>
          </div>

          {/* Summary pills */}
          <div className="hidden sm:flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full"
              style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.15)' }}>
              <span className="text-xs text-emerald-400 font-medium">↑ {formatINR(totalCredits)}</span>
            </div>
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full"
              style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.15)' }}>
              <span className="text-xs text-red-400 font-medium">↓ {formatINR(totalDebits)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        {isLoading ? (
          <div className="p-4 space-y-3">
            {[1,2,3,4].map(i => <div key={i} className="h-12 rounded-xl shimmer" />)}
          </div>
        ) : !entries?.length ? (
          <div className="py-12 text-center text-slate-500 text-sm">No ledger entries.</div>
        ) : (
          <table className="w-full">
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                {['Type', 'Amount', 'Description', 'Date'].map(h => (
                  <th key={h} className="px-5 py-3 text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {entries.map(entry => (
                <tr key={entry.id}
                  className="table-row-hover transition-all"
                  style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                  <td className="px-5 py-3.5">
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${
                      entry.entry_type === 'credit'
                        ? 'text-emerald-400'
                        : 'text-red-400'
                    }`}
                      style={{
                        background: entry.entry_type === 'credit' ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
                        border: `1px solid ${entry.entry_type === 'credit' ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'}`,
                      }}>
                      {entry.entry_type === 'credit' ? '↑ Credit' : '↓ Debit'}
                    </span>
                  </td>
                  <td className="px-5 py-3.5">
                    <span className={`text-sm font-bold ${entry.entry_type === 'credit' ? 'text-emerald-400' : 'text-red-400'}`}>
                      {entry.entry_type === 'credit' ? '+' : '-'}{formatINR(entry.amount_paise)}
                    </span>
                  </td>
                  <td className="px-5 py-3.5">
                    <span className="text-xs text-slate-400 max-w-xs truncate block">{entry.description || '—'}</span>
                  </td>
                  <td className="px-5 py-3.5">
                    <span className="text-xs text-slate-500">{formatDate(entry.created_at)}</span>
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
