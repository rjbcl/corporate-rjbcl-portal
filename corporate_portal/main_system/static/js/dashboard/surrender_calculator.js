$(document).ready(function () {

    // Helper function to get CSRF token
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

    function formatCurrency(amount) {
        if (!amount && amount !== 0) return '-';
        return new Intl.NumberFormat('en-NP', {
            style: 'currency',
            currency: 'NPR',
            minimumFractionDigits: 2
        }).format(amount);
    }

    function formatTodayDate() {
        return new Date().toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }

    // ── Form Submit ──────────────────────────────────────────────────────────

    $('#policy-summary-report-form').on('submit', function (e) {
        e.preventDefault();

        const policyNumber = $('#policy-number').val().trim();

        if (!policyNumber) {
            Swal.fire({
                icon: 'warning',
                title: 'Required',
                text: 'Please enter a policy number.',
            });
            return;
        }

        const $generateBtn = $('#generate-btn');
        const originalBtnText = $generateBtn.html();
        $generateBtn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-2"></span>Calculating...');

        // Hide previous results
        $('#surrender-calculator-container').hide();

        $.ajax({
            url: '/api/corporate/surrender-calculator/',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            data: JSON.stringify({
                policy_no: policyNumber,
                claim_date: $('#claim-date').val() || null
            }),
            success: function (response) {
                if (!response) {
                    Swal.fire({
                        icon: 'warning',
                        title: 'Not Found',
                        text: 'No policy found with the given policy number.',
                    });
                    return;
                }
                displaySurrenderCalculator(response);
            },
            error: function (xhr) {
                let errorMessage = 'Failed to calculate surrender value.';
                if (xhr.responseJSON && xhr.responseJSON.error) {
                    errorMessage = xhr.responseJSON.error;
                }
                Swal.fire({
                    icon: 'error',
                    title: 'Error',
                    text: errorMessage,
                });
            },
            complete: function () {
                $generateBtn.prop('disabled', false).html(originalBtnText);
            }
        });
    });

    // ── Display Results ──────────────────────────────────────────────────────

    function displaySurrenderCalculator(data) {
        console.log('Surrender Calculator Data:', data);
        const today = formatTodayDate();

        const grossSurrender = parseFloat(data.GrossSurrenderValue) || 0;
        const netSurrender = parseFloat(data.NetSurrenderValue) || 0;
        const tax = parseFloat(data.Tax) || 0;
        const loanDeducted = parseFloat(data.LoanDeducted) || 0;
        const loanInterest = parseFloat(data.LoanInterest) || 0;
        const hasActiveLoan = loanDeducted > 0 || loanInterest > 0;
        const loanEligible = grossSurrender * 0.9;

        // Surrender card
        $('#surrender-value').text(formatCurrency(netSurrender));
        $('#surrender-date').text(today);

        const subtitlePolicyNumber = data.policyNO || $('#policy-number').val().trim();
        if (subtitlePolicyNumber) {
            $('#surrender-calculator-policy-number').text(subtitlePolicyNumber);
        }

        // Loan card
        if (hasActiveLoan) {
            $('#loan-value-text').html(
                'Active loan exists. Go to <b>Policy Summary</b> for further details.'
            );
            $('#loan-value').closest('p').hide();
        } else {
            $('#loan-value').closest('p').show();
            $('#loan-value').text(formatCurrency(loanEligible));
            $('#loan-date').text(today);
        }

        $('#surrender-calculator-container').show();
    }

    // ── Policy Search Dropdown ───────────────────────────────────────────────

    let searchTimeout = null;

    $('#policy-number').on('input', function () {
        const query = $(this).val().trim();
        const $dropdown = $('#policy-search-dropdown');

        if (query.length < 3) {
            $dropdown.hide().empty();
            return;
        }

        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(function () {

            $dropdown.empty().append('<div class="dropdown-item-muted">Searching...</div>').show();

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
                        $dropdown.append('<div class="dropdown-item-muted">No results found</div>');
                    } else {
                        results.forEach(function (item) {
                            const $item = $(`<a class="dropdown-item" href="#">${item.policyNo} | ${item.name} | ${item.employeeid || '-'}</a>`);
                            $item.on('click', function (e) {
                                e.preventDefault();
                                $('#policy-number').val(item.policyNo);
                                $dropdown.hide().empty();
                            });
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

    // Hide dropdown when clicking outside
    $(document).on('click', function (e) {
        if (!$(e.target).closest('#policy-number, #policy-search-dropdown').length) {
            $('#policy-search-dropdown').hide().empty();
        }
    });

});