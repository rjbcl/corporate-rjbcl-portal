/**
 * Maturity Forecasting Report JavaScript
 * Handles form submission, date validation, and report generation
 */

// ================================
// GLOBAL STATE
// ================================
let currentDateType = 'ad'; // 'ad' or 'bs'

// ================================
// UTILITY FUNCTIONS
// ================================

/**
 * Format currency as Nepali Rupees
 */
function formatCurrency(amount) {
    return 'Rs. ' + parseFloat(amount || 0).toLocaleString('en-NP', { maximumFractionDigits: 2 });
}

/**
 * Get status badge HTML
 */
function getStatusBadge(status) {
    const badges = {
        'A': '<span class="badge badge-success">Active</span>',
        'L': '<span class="badge badge-warning">Lapsed</span>',
        'M': '<span class="badge badge-info">Matured</span>'
    };
    return badges[status] || '<span class="badge badge-secondary">Inactive</span>';
}

/**
 * Calculate months between two dates
 */
function calculateMonthsDifference(dateString) {
    const maturityDate = new Date(dateString);
    const today = new Date();

    const yearsDiff = maturityDate.getFullYear() - today.getFullYear();
    const monthsDiff = maturityDate.getMonth() - today.getMonth();

    return (yearsDiff * 12) + monthsDiff;
}

/**
 * Format date for display
 */
function formatDate(dateString) {
    if (!dateString) return '-';

    // Check if it's already in a valid format
    // Handle formats like "YYYY-MM-DD" or "DD/MM/YYYY"
    let date;

    // If the date contains slashes, it might be DD/MM/YYYY format
    if (dateString.includes('/')) {
        const parts = dateString.split('/');
        if (parts.length === 3) {
            // Assume DD/MM/YYYY format
            date = new Date(parts[2], parts[1] - 1, parts[0]);
        }
    } else if (dateString.includes('-')) {
        // Check if it's YYYY-MM-DD or DD-MM-YYYY
        const parts = dateString.split('-');
        if (parts.length === 3) {
            if (parts[0].length === 4) {
                // YYYY-MM-DD format
                date = new Date(dateString);
            } else {
                // DD-MM-YYYY format
                date = new Date(parts[2], parts[1] - 1, parts[0]);
            }
        }
    } else {
        // Try default parsing
        date = new Date(dateString);
    }

    // Check if date is valid
    if (isNaN(date.getTime())) {
        return '-';
    }

    return date.toLocaleDateString('en-GB', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

/**
 * Show loading state on button
 */
function setButtonLoading(button, isLoading) {
    if (isLoading) {
        button.disabled = true;
        button.dataset.originalText = button.innerHTML;
        button.innerHTML = '<span class="spinner-border spinner-border-sm mr-2"></span> Generating...';
    } else {
        button.disabled = false;
        button.innerHTML = button.dataset.originalText || button.innerHTML;
    }
}

/**
 * Show notification
 */
function showNotification(message, type = 'error') {
    // You can implement a toast notification here
    // For now, using alert
    if (type === 'error') {
        alert('Error: ' + message);
    } else {
        alert(message);
    }
}

// ================================
// FORM VALIDATION
// ================================

/**
 * Validate date range
 */
function validateDateRange(fromDate, toDate) {
    const from = new Date(fromDate);
    const to = new Date(toDate);

    if (from > to) {
        return { valid: false, message: 'From Date must be before To Date' };
    }

    // Check if date range is reasonable (not more than 10 years)
    const yearsDiff = (to - from) / (1000 * 60 * 60 * 24 * 365);
    if (yearsDiff > 10) {
        return { valid: false, message: 'Date range should not exceed 10 years' };
    }

    return { valid: true };
}

/**
 * Validate BS date format (basic validation)
 */
function validateBSDate(dateString) {
    // Basic format check: YYYY-MM-DD
    const pattern = /^\d{4}-\d{2}-\d{2}$/;
    if (!pattern.test(dateString)) {
        return { valid: false, message: 'Invalid BS date format. Use YYYY-MM-DD' };
    }

    const [year, month, day] = dateString.split('-').map(Number);

    // Basic range checks
    if (year < 2000 || year > 2100) {
        return { valid: false, message: 'BS year should be between 2000 and 2100' };
    }
    if (month < 1 || month > 12) {
        return { valid: false, message: 'BS month should be between 1 and 12' };
    }
    if (day < 1 || day > 32) {
        return { valid: false, message: 'BS day should be between 1 and 32' };
    }

    return { valid: true };
}

/**
 * Get form data
 */
function getFormData() {
    const formData = {
        groupId: document.getElementById('group-id').value
    };

    // Get AD dates
    const fromDateAD = document.getElementById('from-date-ad').value;
    const toDateAD = document.getElementById('to-date-ad').value;

    // Get BS dates
    const fromDateBS = document.getElementById('from-date-bs').value;
    const toDateBS = document.getElementById('to-date-bs').value;

    // Determine which date type to use (prefer AD if both are filled)
    if (fromDateAD && toDateAD) {
        formData.dateType = 'ad';
        formData.fromDate = fromDateAD;
        formData.toDate = toDateAD;
    } else if (fromDateBS && toDateBS) {
        formData.dateType = 'bs';
        formData.fromDate = fromDateBS;
        formData.toDate = toDateBS;
    }

    return formData;
}

/**
 * Validate form
 */
function validateForm(formData) {
    // Check group selection
    if (!formData.groupId) {
        return { valid: false, message: 'Please select a group' };
    }

    // Check if at least one date type is filled
    if (!formData.fromDate || !formData.toDate) {
        return { valid: false, message: 'Please enter dates in either AD or BS format' };
    }

    // Validate based on date type
    if (formData.dateType === 'ad') {
        return validateDateRange(formData.fromDate, formData.toDate);
    } else {
        // Validate BS dates
        const fromValidation = validateBSDate(formData.fromDate);
        if (!fromValidation.valid) return fromValidation;

        const toValidation = validateBSDate(formData.toDate);
        if (!toValidation.valid) return toValidation;

        return { valid: true };
    }
}

// ================================
// REPORT GENERATION
// ================================

/**
 * Fetch report data from server
 */
async function fetchReportData(formData) {
    try {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

        const requestData = {
            date_type: formData.dateType,
            from_date: formData.fromDate,
            to_date: formData.toDate,
            group_id: formData.groupId
        };

        const response = await fetch('/api/corporate/reports/maturity-forecasting/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(requestData)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to fetch report data');
        }

        const data = await response.json();

        return {
            policies: data.policies,
            count: data.count,
            formData: formData
        };
    } catch (error) {
        console.error('Error fetching report data:', error);
        throw error;
    }
}

/**
 * Calculate report statistics
 */
function calculateStatistics(policies) {
    const totalPolicies = policies.length;

    // Handle different field names
    const activePolicies = policies.filter(p => {
        const status = p.PolicyStatus || p.policy_status;
        return status === 'A';
    }).length;

    const totalSum = policies.reduce((sum, p) => {
        const sumAssured = p.SumAssured || p.sum_assured || 0;
        return sum + parseFloat(sumAssured);
    }, 0);

    // Calculate average months to maturity
    const monthsArray = policies.map(p => {
        const maturityDate = p.MaturityDate || p.maturity_date;
        return calculateMonthsDifference(maturityDate);
    });
    const avgMonths = monthsArray.length > 0
        ? Math.round(monthsArray.reduce((a, b) => a + b, 0) / monthsArray.length)
        : 0;

    return {
        totalPolicies,
        activePolicies,
        totalSum,
        avgMonths
    };
}

/**
 * Update statistics cards
 */
function updateStatistics(stats) {
    document.getElementById('stat-total-policies').textContent = stats.totalPolicies;
    document.getElementById('stat-active-policies').textContent = stats.activePolicies;
    document.getElementById('stat-total-sum').textContent = formatCurrency(stats.totalSum);
    document.getElementById('stat-avg-months').textContent = stats.avgMonths + ' months';
}

/**
 * Populate report table
 */
function populateReportTable(policies) {
    const tbody = document.getElementById('report-tbody');
    tbody.innerHTML = '';

    if (!policies || policies.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center">No policies found for the selected criteria</td></tr>';
        return false; // Return false to indicate no data
    }

    let hasValidData = false;

    policies.forEach(policy => {
        // Handle different field names from stored procedure
        const policyNo = policy.PolicyNo || policy.policy_no || '';

        // Skip rows without a valid policy number
        if (!policyNo || policyNo === '-' || policyNo.trim() === '') {
            return; // Skip this iteration
        }

        hasValidData = true;

        const name = policy.Name || policy.name || policy.EmployeeName || '-';
        const maturityDate = policy.MaturityDate || policy.maturity_date || '';
        const sumAssured = policy.SumAssured || policy.sum_assured || 0;
        const premium = policy.Premium || policy.premium || 0;
        const policyStatus = policy.PolicyStatus || policy.policy_status || 'A';
        const daysToMaturity = policy.RemainingDayToMature || NULL;
        const row = document.createElement('tr');

        row.innerHTML = `
            <td>${policyNo}</td>
            <td>${name}</td>
            <td>${formatDate(maturityDate)}</td>
            <td>${formatCurrency(sumAssured)}</td>
            <td>${formatCurrency(premium)}</td>
            <td>${daysToMaturity}</td>
            <td>${getStatusBadge(policyStatus)}</td>
        `;

        tbody.appendChild(row);
    });

    // If no valid data was found, show message
    if (!hasValidData) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center">No policies found for the selected criteria</td></tr>';
        return false;
    }

    return true; // Return true to indicate data exists
}
/**
 * Update report summary
 */
function updateReportSummary(data) {
    const groupSelect = document.getElementById('group-id');
    const groupName = groupSelect.options[groupSelect.selectedIndex].text;

    const dateTypeText = data.formData.dateType === 'ad' ? 'AD' : 'BS';

    const summaryText = `Showing ${data.count} policies maturing between ${data.formData.fromDate} and ${data.formData.toDate} (${dateTypeText}) for Group: ${groupName}`;

    document.getElementById('report-summary').textContent = summaryText;
}

/**
 * Show report results below the form
 */
function showReportResults(data) {
    // Destroy existing DataTable safely
    if ($.fn.DataTable.isDataTable('#report-table')) {
        $('#report-table').DataTable().clear().destroy();
    }

    // Populate table and check if data exists
    const hasData = populateReportTable(data.policies);

    // Show results section
    const resultsSection = document.getElementById('report-results');
    resultsSection.style.display = 'block';

    // Enable download button only if data exists
    const downloadBtn = document.getElementById('download-btn');
    if (downloadBtn) {
        downloadBtn.disabled = !hasData;
    }

    // Do not initialize DataTable if no data
    if (!hasData) return;

    // Initialize DataTable
    $('#report-table').DataTable({
        pageLength: 10,
        ordering: true,
        searching: true,
        info: true,
        responsive: true,
        language: {
            search: "Search:",
            lengthMenu: "Show _MENU_ entries",
            info: "Showing _START_ to _END_ of _TOTAL_ entries",
            paginate: {
                first: "First",
                last: "Last",
                next: "Next",
                previous: "Previous"
            }
        }
    });

    // Scroll to results
    setTimeout(() => {
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
}

// ================================
// FORM HANDLING
// ================================

/**
 * Handle form submission
 */
async function handleFormSubmit(event) {
    event.preventDefault();

    console.log('Form submitted');

    // Get form data
    const formData = getFormData();
    console.log('Form data:', formData);

    // Validate form
    const validation = validateForm(formData);
    if (!validation.valid) {
        showNotification(validation.message, 'error');
        return;
    }

    // Show loading state
    const submitButton = document.getElementById('generate-btn');
    setButtonLoading(submitButton, true);

    try {
        // Fetch report data
        const reportData = await fetchReportData(formData);
        console.log('Report data received:', reportData);
        console.log('Policies:', reportData.policies);
        console.log('Count:', reportData.count);

        // Check if we have valid data
        if (!reportData.policies) {
            throw new Error('No policies data received from server');
        }

        // Show results
        showReportResults(reportData);
    } catch (error) {
        console.error('Error generating report:', error);
        console.error('Error message:', error.message);
        console.error('Error stack:', error.stack);
        showNotification('Failed to generate report: ' + error.message, 'error');
    } finally {
        setButtonLoading(submitButton, false);
    }
}
// ================================
// EVENT LISTENERS
// ================================

/**
 * Initialize all event listeners
 */
function initializeEventListeners() {
    // Form submission
    const form = document.getElementById('maturity-report-form');
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    }

    // Download report button
    const downloadButton = document.getElementById('download-btn');
    if (downloadButton) {
        downloadButton.addEventListener('click', handleDownloadReport);
    }
}
// ================================
// INITIALIZATION
// ================================

/**
 * Initialize the maturity report page
 */
function initialize() {
    console.log('Maturity report script loaded');

    // Initialize event listeners
    initializeEventListeners();

    console.log('Maturity report initialized');
}

// Run initialization when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
} else {
    initialize();
}



/**
 * Handle download report
 */
function handleDownloadReport() {
    // Get current table data
    const table = document.getElementById('report-table');
    const rows = table.querySelectorAll('tbody tr');

    if (rows.length === 0) {
        showNotification('No data to download', 'error');
        return;
    }

    // Create CSV content
    let csvContent = "Policy No,Employee Name,Maturity Date,Sum Assured,Premium,Months to Maturity,Status\n";

    rows.forEach(row => {
        const cells = row.querySelectorAll('td');
        const rowData = Array.from(cells).map(cell => {
            // Remove HTML tags and clean the text
            let text = cell.textContent.trim();
            // Escape commas and quotes
            if (text.includes(',') || text.includes('"')) {
                text = '"' + text.replace(/"/g, '""') + '"';
            }
            return text;
        });
        csvContent += rowData.join(',') + "\n";
    });

    // Create download link
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);

    link.setAttribute('href', url);
    link.setAttribute('download', 'maturity_report_' + new Date().toISOString().slice(0, 10) + '.csv');
    link.style.visibility = 'hidden';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}