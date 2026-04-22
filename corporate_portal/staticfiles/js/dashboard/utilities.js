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

const changePasswordForm = document.getElementById('changePasswordForm');
if (changePasswordForm) {
  changePasswordForm.addEventListener('submit', function (e) {
    e.preventDefault();

    const form = this;
    const submitBtn = document.getElementById('submitBtn');
    const alert = document.getElementById('passwordAlert');
    const csrfToken = form.querySelector('[name=csrfmiddlewaretoken]').value;

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
    document.getElementById('search-panel').style.display = 'none';
  }
});