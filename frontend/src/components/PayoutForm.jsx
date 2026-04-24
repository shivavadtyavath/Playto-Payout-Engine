import React, { useState, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useMerchant } from '../context/MerchantContext';
import { api } from '../api/client';
import { formatINR } from '../utils/formatters';

export default function PayoutForm() {
  const { merchantId } = useMerchant();
  const queryClient = useQueryClient();

  const [amountINR, setAmountINR] = useState('');
  // selectedAccountId tracks what the user has explicitly chosen in the dropdown
  const [selectedAccountId, setSelectedAccountId] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [success, setSuccess] = useState(null);
  const [error, setError] = useState(null);

  const { data: bankAccounts, isLoading: loadingAccounts } = useQuery({
    queryKey: ['bankAccounts', merchantId],
    queryFn: () => api.getBankAccounts(merchantId),
    enabled: !!merchantId,
  });

  const { data: balance } = useQuery({
    queryKey: ['balance', merchantId],
    queryFn: () => api.getMerchantBalance(merchantId),
    enabled: !!merchantId,
  });

  // Derive the effective bank account ID:
  // Use the selected one if it belongs to this merchant, otherwise fall back to first.
  const validIds = bankAccounts?.map(a => a.id) || [];
  const bankAccountId = validIds.includes(selectedAccountId)
    ? selectedAccountId
    : (validIds[0] || '');

  // Reset form when merchant changes
  useEffect(() => {
    setSuccess(null);
    setError(null);
    setAmountINR('');
    setSelectedAccountId('');
  }, [merchantId]);

  const amountPaise = Math.round(parseFloat(amountINR || 0) * 100);
  const availablePaise = balance?.available_balance_paise ?? 0;
  const isOverBalance = amountPaise > availablePaise && amountPaise > 0;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSuccess(null); setError(null);

    if (!amountINR || parseFloat(amountINR) <= 0) {
      setError('Enter a valid amount greater than ₹0.');
      return;
    }
    if (!bankAccountId) {
      setError('No bank account available. Please check your account setup.');
      return;
    }

    setIsSubmitting(true);
    try {
      const payout = await api.createPayout(merchantId, {
        amount_paise: amountPaise,
        bank_account_id: bankAccountId,
      });
      setSuccess(payout);
      setAmountINR('');
      queryClient.invalidateQueries({ queryKey: ['balance', merchantId] });
      queryClient.invalidateQueries({ queryKey: ['payouts', merchantId] });
      queryClient.invalidateQueries({ queryKey: ['ledger', merchantId] });
    } catch (err) {
      setError(err.message || 'Payout request failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="glass-card rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="px-6 pt-6 pb-4 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)' }}>
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </div>
          <div>
            <h2 className="text-base font-semibold text-white">Request Payout</h2>
            <p className="text-xs text-slate-500">Transfer funds to your bank</p>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-5">
        {/* Available balance hint */}
        {balance && (
          <div className="flex items-center justify-between px-4 py-3 rounded-xl"
            style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.15)' }}>
            <span className="text-xs text-slate-400">Available to withdraw</span>
            <span className="text-sm font-bold text-emerald-400">
              {formatINR(availablePaise)}
            </span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Amount input */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Amount (INR)
            </label>
            <div className="relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 font-semibold text-lg">₹</span>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={amountINR}
                onChange={e => setAmountINR(e.target.value)}
                placeholder="0.00"
                className={`w-full pl-10 pr-4 py-3.5 rounded-xl text-white text-lg font-semibold outline-none transition-all input-glow ${
                  isOverBalance ? 'border-red-500/50' : 'border-white/8'
                }`}
                style={{ background: 'rgba(255,255,255,0.04)', border: `1px solid ${isOverBalance ? 'rgba(239,68,68,0.4)' : 'rgba(255,255,255,0.08)'}` }}
              />
            </div>
            {amountINR && (
              <div className="flex items-center justify-between mt-2">
                <p className="text-xs text-slate-500 font-mono">{amountPaise.toLocaleString('en-IN')} paise</p>
                {isOverBalance && (
                  <p className="text-xs text-red-400 font-medium">Exceeds available balance</p>
                )}
              </div>
            )}
          </div>

          {/* Quick amount buttons */}
          <div className="flex gap-2">
            {[500, 1000, 5000].map(amt => (
              <button key={amt} type="button"
                onClick={() => setAmountINR(String(amt))}
                className="flex-1 py-2 rounded-lg text-xs font-medium text-slate-400 transition-all hover:text-white"
                style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)' }}>
                ₹{amt.toLocaleString('en-IN')}
              </button>
            ))}
            <button type="button"
              onClick={() => setAmountINR(String((availablePaise / 100).toFixed(2)))}
              className="flex-1 py-2 rounded-lg text-xs font-medium text-indigo-400 transition-all hover:text-indigo-300"
              style={{ background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)' }}>
              Max
            </button>
          </div>

          {/* Bank account */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Bank Account
            </label>
            {loadingAccounts ? (
              <div className="h-12 rounded-xl shimmer" />
            ) : (
              <div className="relative">
                <select
                  value={bankAccountId}
                  onChange={e => setSelectedAccountId(e.target.value)}
                  className="w-full px-4 py-3.5 rounded-xl text-white text-sm font-medium outline-none appearance-none transition-all input-glow"
                  style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}>
                  {bankAccounts?.map(acc => (
                    <option key={acc.id} value={acc.id} style={{ background: '#1a1a2e' }}>
                      {acc.account_holder} · ••••{acc.account_number.slice(-4)} · {acc.ifsc_code}
                    </option>
                  ))}
                </select>
                <svg className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none"
                  fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            )}
          </div>

          {/* Error */}
          {error && (
            <div className="flex items-start gap-3 px-4 py-3 rounded-xl fade-in"
              style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)' }}>
              <span className="text-red-400 mt-0.5">⚠</span>
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          {/* Success */}
          {success && (
            <div className="px-4 py-4 rounded-xl fade-in"
              style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)' }}>
              <div className="flex items-center gap-2 mb-2">
                <div className="w-5 h-5 rounded-full bg-emerald-400 flex items-center justify-center">
                  <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                </div>
                <p className="text-sm font-semibold text-emerald-400">Payout Initiated!</p>
              </div>
              <p className="text-xs text-slate-400 font-mono mb-1">ID: {success.id}</p>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">Status:</span>
                <span className="text-xs font-semibold text-amber-400 capitalize">{success.status}</span>
              </div>
            </div>
          )}

          {/* Submit */}
          <button type="submit" disabled={isSubmitting || loadingAccounts || isOverBalance}
            className="btn-primary w-full py-3.5 rounded-xl text-white font-semibold text-sm flex items-center justify-center gap-2">
            {isSubmitting ? (
              <>
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Processing...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
                Request Payout
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
