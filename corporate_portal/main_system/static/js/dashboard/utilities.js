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

  return 'Rs. ' + num.toLocaleString('en-NP', { maximumFractionDigits: 2 });
}


// ================================
// CHANGE PASSWORD
// ================================

// ── Password validation helpers ──────────────────────────────────────────────
const PASSWORD_RULES = [
  { test: (v) => v.length >= 8,           msg: 'At least 8 characters'             },
  { test: (v) => /[A-Z]/.test(v),         msg: 'At least one uppercase letter'      },
  { test: (v) => /[a-z]/.test(v),         msg: 'At least one lowercase letter'      },
  { test: (v) => /[0-9]/.test(v),         msg: 'At least one number'                },
  { test: (v) => /[^A-Za-z0-9]/.test(v), msg: 'At least one special character'     },
];

/**
 * Validates a password value against all rules.
 * Returns the first failing rule's message, or null if all pass.
 */
function getPasswordError(value) {
  for (const rule of PASSWORD_RULES) {
    if (!rule.test(value)) return rule.msg;
  }
  return null;
}

/**
 * Shows or clears an error message beneath a given input.
 * Adds/removes an `is-invalid` class on the input for Bootstrap styling.
 */
function setFieldError(input, message) {
  // Find or create the sibling error element
  let errorEl = input.parentElement.querySelector('.field-error');
  if (!errorEl) {
    errorEl = document.createElement('span');
    errorEl.className = 'field-error form-text mt-1';
    errorEl.style.cssText = 'color:#e74c3c; font-size:0.82rem;';
    input.after(errorEl);
  }

  if (message) {
    errorEl.textContent = '⚠ ' + message;
    input.classList.add('is-invalid');
    input.style.borderColor = '#e74c3c';
  } else {
    errorEl.textContent = '';
    input.classList.remove('is-invalid');
    input.style.borderColor = '';
  }
}

// ── Live validation for #newPassword ─────────────────────────────────────────
const newPasswordInput     = document.getElementById('newPassword');
const confirmPasswordInput = document.getElementById('confirmPassword');

function validateNewPassword() {
  const val   = newPasswordInput.value;
  const error = val ? getPasswordError(val) : null;   // silent while still empty
  setFieldError(newPasswordInput, error);

  // Re-run confirm check whenever new-password changes
  validateConfirmPassword();
}

function validateConfirmPassword() {
  const newVal     = newPasswordInput.value;
  const confirmVal = confirmPasswordInput.value;

  if (!confirmVal) {
    setFieldError(confirmPasswordInput, null);   // silent while still empty
    return;
  }

  if (newVal !== confirmVal) {
    setFieldError(confirmPasswordInput, 'Passwords do not match');
  } else {
    setFieldError(confirmPasswordInput, null);
  }
}

if (newPasswordInput) {
  newPasswordInput.addEventListener('input', validateNewPassword);
  newPasswordInput.addEventListener('blur',  validateNewPassword);
}

if (confirmPasswordInput) {
  confirmPasswordInput.addEventListener('input', validateConfirmPassword);
  confirmPasswordInput.addEventListener('blur',  validateConfirmPassword);
}

// ── Submit handler ────────────────────────────────────────────────────────────
const changePasswordForm = document.getElementById('changePasswordForm');

if (changePasswordForm) {
  changePasswordForm.addEventListener('submit', function (e) {
    e.preventDefault();

    const form      = this;
    const submitBtn = document.getElementById('submitBtn');
    const alertEl   = document.getElementById('passwordAlert');
    const csrfToken = form.querySelector('[name=csrfmiddlewaretoken]').value;

    // ── Client-side guard: run all validations before hitting the server ──
    const newVal     = newPasswordInput.value;
    const confirmVal = confirmPasswordInput.value;

    const passwordError = getPasswordError(newVal);
    if (passwordError) {
      setFieldError(newPasswordInput, passwordError);
      newPasswordInput.focus();
      return;                         // block submit
    }

    if (newVal !== confirmVal) {
      setFieldError(confirmPasswordInput, 'Passwords do not match');
      confirmPasswordInput.focus();
      return;                         // block submit
    }

    // ── All good — proceed with fetch ─────────────────────────────────────
    alertEl.className   = 'alert d-none';
    alertEl.textContent = '';
    submitBtn.disabled    = true;
    submitBtn.textContent = 'Submitting…';

    fetch('/change_password/', {
      method:  'POST',
      headers: {
        'X-CSRFToken':   csrfToken,
        'Content-Type':  'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams(new FormData(form)),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.success) {
          alertEl.className   = 'alert alert-success';
          alertEl.textContent = data.message;
          form.reset();
          // Clear any lingering error states after reset
          [newPasswordInput, confirmPasswordInput].forEach((el) => setFieldError(el, null));
        } else {
          const messages      = Object.values(data.errors).flat().join(' ');
          alertEl.className   = 'alert alert-danger';
          alertEl.textContent = messages;
        }
      })
      .catch(() => {
        alertEl.className   = 'alert alert-danger';
        alertEl.textContent = 'A network error occurred. Please try again.';
      })
      .finally(() => {
        submitBtn.disabled    = false;
        submitBtn.textContent = 'Submit';
      });
  });
}

// ================================
// CSRF HELPER
// ================================

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}


// ================================
// NAVBAR SEARCH
// ================================

let navSearchTimeout = null;

$('#nav-policy-search').on('input', function () {
  const query = $(this).val().trim();
  const $dropdown = $('#nav-policy-search-dropdown');

  if (query.length < 3) {
    $dropdown.hide().empty();
    return;
  }

  clearTimeout(navSearchTimeout);
  navSearchTimeout = setTimeout(function () {

    $dropdown.empty().append('<div class="dropdown-item-muted px-3 py-2">Searching...</div>').show();

    $.ajax({
      url: '/api/corporate/policy-search/',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
      },
      data: JSON.stringify({ q: query }),
      success: function (results) {
        $dropdown.empty();

        if (!results || results.length === 0) {
          $dropdown.append('<div class="dropdown-item-muted px-3 py-2">No results found</div>');
        } else {
          results.forEach(function (item) {
            // data-policy-no is required for the redirect click handler below
            const $item = $(
              `<a class="dropdown-item px-3 py-2" href="#" data-policy-no="${item.policyNo}">
                ${item.policyNo} | ${item.name} | ${item.employeeid || '-'}
              </a>`
            );
            $dropdown.append($item);
          });
        }

        $dropdown.show();
      },
      error: function () {
        $dropdown.hide().empty();
        Swal.fire({
          icon: 'error',
          title: 'Search Failed',
          text: 'Could not search for policies. Please try again.',
        });
      }
    });

  }, 300);
});

// Single delegated click handler for navbar search results — redirects to policy summary
$(document).on('click', '#nav-policy-search-dropdown .dropdown-item[data-policy-no]', function (e) {
  e.preventDefault();
  e.stopPropagation();
  const policyNo = $(this).data('policy-no');
  window.location.href = `/company/reports/summary/?policy_number=${encodeURIComponent(policyNo)}`;
});

// Hide results when clicking outside the navbar search bar
$(document).on('click', function (e) {
  if (!$(e.target).closest('.search_bar').length) {
    $('#nav-policy-search-dropdown').hide().empty();
    $('#nav-policy-search').val('');
  }
});


// ================================
// SEARCH PANEL TOGGLE
// ================================
const searchToggle = document.getElementById('search-toggle');
if (searchToggle) {
  searchToggle.addEventListener('click', function () {
    const panel = document.getElementById('search-panel');
    const isVisible = panel.style.display === 'block';
    panel.style.display = isVisible ? 'none' : 'block';
    if (!isVisible) {
      document.getElementById('nav-policy-search').focus();
    }
  });
}

// Close search panel when clicking outside
document.addEventListener('click', function (e) {
  if (!e.target.closest('.search_bar')) {
    const panel = document.getElementById('search-panel');
    if (panel) panel.style.display = 'none';
  }
});