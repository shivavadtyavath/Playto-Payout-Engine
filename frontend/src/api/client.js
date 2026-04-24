/**
 * API client for the Playto Payout Engine backend.
 * All amounts are in paise (integers). Display conversion happens in components.
 */

const API_BASE = process.env.REACT_APP_API_URL || 'https://playto-backend-y9sc.onrender.com/api/v1';

async function apiFetch(path, options = {}, merchantId) {
  const headers = {
    'Content-Type': 'application/json',
    ...(merchantId ? { 'X-Merchant-ID': merchantId } : {}),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  const data = await response.json();

  if (!response.ok) {
    const error = new Error(data.error || 'Request failed');
    error.code = data.code;
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data;
}

export const api = {
  getMerchantBalance: (merchantId) =>
    apiFetch('/merchants/me/', {}, merchantId),

  getLedger: (merchantId) =>
    apiFetch('/merchants/me/ledger/', {}, merchantId),

  getBankAccounts: (merchantId) =>
    apiFetch('/merchants/me/bank-accounts/', {}, merchantId),

  getPayouts: (merchantId) =>
    apiFetch('/payouts/', {}, merchantId),

  getPayout: (merchantId, payoutId) =>
    apiFetch(`/payouts/${payoutId}/`, {}, merchantId),

  createPayout: (merchantId, { amount_paise, bank_account_id }) => {
    const idempotencyKey = crypto.randomUUID();
    return apiFetch(
      '/payouts/',
      {
        method: 'POST',
        headers: { 'Idempotency-Key': idempotencyKey },
        body: JSON.stringify({ amount_paise, bank_account_id }),
      },
      merchantId
    );
  },
};
