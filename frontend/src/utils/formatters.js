/**
 * Display formatters.
 * All monetary values are stored and transmitted in paise.
 * Conversion to INR happens only at the display layer.
 */

/**
 * Convert paise to INR string for display.
 * @param {number} paise - integer amount in paise
 * @returns {string} formatted INR string e.g. "₹1,234.56"
 */
export function formatINR(paise) {
  const inr = paise / 100;
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
  }).format(inr);
}

/**
 * Format a timestamp for display.
 */
export function formatDate(isoString) {
  return new Date(isoString).toLocaleString('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

/**
 * Truncate a UUID for display (first 8 chars).
 */
export function shortId(uuid) {
  return uuid ? uuid.substring(0, 8) + '...' : '—';
}
