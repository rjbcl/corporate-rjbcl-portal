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


document.getElementById('changePasswordForm').addEventListener('submit', function (e) {
  e.preventDefault();

  const form = this;
  const submitBtn = document.getElementById('submitBtn');
  const alert = document.getElementById('passwordAlert');
  const csrfToken = form.querySelector('[name=csrfmiddlewaretoken]').value;

  // Reset UI
  alert.className = 'alert d-none';
  alert.textContent = '';
  submitBtn.disabled = true;
  submitBtn.textContent = 'Submitting...';

  fetch("/change_password/", {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrfToken,
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams(new FormData(form)),
  })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        alert.className = 'alert alert-success';
        alert.textContent = data.message;
        form.reset();
      } else {
        // Flatten and display all errors
        const messages = Object.values(data.errors).flat().join(' ');
        alert.className = 'alert alert-danger';
        alert.textContent = messages;
      }
    })
    .catch(() => {
      alert.className = 'alert alert-danger';
      alert.textContent = 'A network error occurred. Please try again.';
    })
    .finally(() => {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Submit';
    });
});