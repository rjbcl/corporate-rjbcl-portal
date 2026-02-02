// ================================
// UTILITY FUNCTIONS
// ================================

/**
 * Format number as Nepali Rupees
 */
function formatCurrency(amount) {
  const num = parseFloat(amount || 0);

  if (num >= 1000000000) {
    return 'Rs. ' + (num / 1_000_000_000).toFixed(1).replace(/\.0$/, '') + 'B';
  }
  if (num >= 1000000) {
    return 'Rs. ' + (num / 1_000_000).toFixed(1).replace(/\.0$/, '') + 'M';
  }
  if (num >= 1000) {
    return 'Rs. ' + (num / 1_000).toFixed(1).replace(/\.0$/, '') + 'k';
  }

  // For smaller numbers, show with locale formatting
  return 'Rs. ' + num.toLocaleString('en-NP', { maximumFractionDigits: 2 });
}