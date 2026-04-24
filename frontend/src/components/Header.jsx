import React, { useState } from 'react';
import { useMerchant } from '../context/MerchantContext';

export default function Header() {
  const { merchantId, setMerchantId, SEED_MERCHANTS } = useMerchant();
  const current = SEED_MERCHANTS.find(m => m.id === merchantId);
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-white/5"
      style={{ background: 'rgba(15,15,20,0.85)', backdropFilter: 'blur(20px)' }}>
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">

        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)' }}>
              <span className="text-white font-bold text-sm">P</span>
            </div>
            <div className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 bg-emerald-400 rounded-full border-2 border-[#0f0f14] pulse-dot" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-white text-base tracking-tight">Playto Pay</span>
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full text-indigo-300"
                style={{ background: 'rgba(99,102,241,0.15)', border: '1px solid rgba(99,102,241,0.3)' }}>
                BETA
              </span>
            </div>
            <p className="text-xs text-slate-500">Merchant Payout Dashboard</p>
          </div>
        </div>

        {/* Center nav */}
        <nav className="hidden md:flex items-center gap-1">
          {['Overview', 'Payouts', 'Ledger', 'Settings'].map((item, i) => (
            <button key={item}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                i === 0
                  ? 'text-white bg-white/8'
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
              }`}>
              {item}
            </button>
          ))}
        </nav>

        {/* Right: merchant switcher */}
        <div className="flex items-center gap-3">
          {/* Live indicator */}
          <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full"
            style={{ background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.2)' }}>
            <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full pulse-dot" />
            <span className="text-xs font-medium text-emerald-400">Live</span>
          </div>

          {/* Merchant selector */}
          <div className="relative">
            <button onClick={() => setOpen(!open)}
              className="flex items-center gap-2.5 px-3 py-2 rounded-xl transition-all"
              style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}>
              <div className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold text-white"
                style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)' }}>
                {current?.name?.[0]}
              </div>
              <div className="text-left hidden sm:block">
                <p className="text-xs font-semibold text-white leading-tight">{current?.name?.split(' ').slice(0,2).join(' ')}</p>
                <p className="text-[10px] text-slate-500">Merchant Account</p>
              </div>
              <svg className={`w-4 h-4 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`}
                fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {open && (
              <div className="absolute right-0 top-full mt-2 w-64 rounded-xl overflow-hidden z-50 fade-in"
                style={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.08)', boxShadow: '0 20px 60px rgba(0,0,0,0.5)' }}>
                <div className="p-2">
                  <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider px-3 py-2">Switch Merchant</p>
                  {SEED_MERCHANTS.map(m => (
                    <button key={m.id}
                      onClick={() => { setMerchantId(m.id); setOpen(false); }}
                      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-left ${
                        m.id === merchantId ? 'bg-indigo-500/20 text-white' : 'text-slate-300 hover:bg-white/5'
                      }`}>
                      <div className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
                        style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)' }}>
                        {m.name[0]}
                      </div>
                      <div>
                        <p className="text-sm font-medium leading-tight">{m.name}</p>
                        <p className="text-[10px] text-slate-500 font-mono">{m.id.substring(0,8)}...</p>
                      </div>
                      {m.id === merchantId && (
                        <svg className="w-4 h-4 text-indigo-400 ml-auto" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
