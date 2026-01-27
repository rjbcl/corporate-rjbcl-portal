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
    const date = new Date(dateString);
    return date.toLocaleDateString('en-NP', { year: 'numeric', month: 'short', day: 'numeric' });
}

/**
 * Show loading state on button
 */
function setButtonLoading(button, isLoading) {
    if (isLoading) {
        button.disabled = true;
        button.dataset.originalText = button.innerHTML;
        button.innerHTML = '<span class="spinner"></span> Generating...';
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
// DATE TYPE SWITCHING
// ================================

/**
 * Initialize date type tabs
 */
function initializeDateTypeTabs() {
    const tabs = document.querySelectorAll('.date-type-tab');

    tabs.forEach(tab => {
        tab.addEventListener('click', function () {
            const dateType = this.dataset.dateType;
            switchDateType(dateType);
        });
    });
}

/**
 * Switch between AD and BS date types
 */
function switchDateType(dateType) {
    currentDateType = dateType;

    // Update active tab
    document.querySelectorAll('.date-type-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelector(`[data-date-type="${dateType}"]`).classList.add('active');

    // Show/hide date fields
    document.querySelectorAll('.date-fields').forEach(field => {
        field.classList.remove('active');
    });
    document.getElementById(`${dateType}-date-fields`).classList.add('active');

    // Update required fields
    updateRequiredFields(dateType);
}

/**
 * Update which fields are required based on date type
 */
function updateRequiredFields(dateType) {
    // Remove all required attributes first
    document.getElementById('from-date-ad').removeAttribute('required');
    document.getElementById('to-date-ad').removeAttribute('required');
    document.getElementById('from-date-bs').removeAttribute('required');
    document.getElementById('to-date-bs').removeAttribute('required');

    // Add required to active date type
    if (dateType === 'ad') {
        document.getElementById('from-date-ad').setAttribute('required', 'required');
        document.getElementById('to-date-ad').setAttribute('required', 'required');
    } else {
        document.getElementById('from-date-bs').setAttribute('required', 'required');
        document.getElementById('to-date-bs').setAttribute('required', 'required');
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
 * Get form data based on current date type
 */
function getFormData() {
    const formData = {
        dateType: currentDateType,
        groupId: document.getElementById('group-id').value
    };

    if (currentDateType === 'ad') {
        formData.fromDate = document.getElementById('from-date-ad').value;
        formData.toDate = document.getElementById('to-date-ad').value;
    } else {
        formData.fromDate = document.getElementById('from-date-bs').value;
        formData.toDate = document.getElementById('to-date-bs').value;
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

    // Check dates
    if (!formData.fromDate || !formData.toDate) {
        return { valid: false, message: 'Please enter both from and to dates' };
    }

    // Validate based on date type
    if (currentDateType === 'ad') {
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
 * Generate sample report data (replace with actual API call)
 */
function generateSampleData(formData) {
    // This is sample data - replace with actual API call
    const samplePolicies = [
        {
            policy_no: 'POL-001',
            name: 'John Doe',
            maturity_date: '2025-06-15',
            sum_assured: 500000,
            premium: 25000,
            policy_status: 'A'
        },
        {
            policy_no: 'POL-002',
            name: 'Jane Smith',
            maturity_date: '2025-07-20',
            sum_assured: 750000,
            premium: 37500,
            policy_status: 'A'
        },
        {
            policy_no: 'POL-003',
            name: 'Robert Wilson',
            maturity_date: '2025-08-10',
            sum_assured: 600000,
            premium: 30000,
            policy_status: 'A'
        },
        {
            policy_no: 'POL-004',
            name: 'Maria Garcia',
            maturity_date: '2025-09-05',
            sum_assured: 800000,
            premium: 40000,
            policy_status: 'L'
        },
        {
            policy_no: 'POL-005',
            name: 'Ahmed Khan',
            maturity_date: '2025-10-12',
            sum_assured: 550000,
            premium: 27500,
            policy_status: 'A'
        }
    ];

    return {
        policies: samplePolicies,
        count: samplePolicies.length,
        formData: formData
    };
}

/**
 * Fetch report data from API
 */
async function fetchReportData(formData) {
    try {
        // Get CSRF token
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

        const response = await fetch('/api/corporate/reports/maturity-forecasting/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            credentials: 'same-origin',  // Include cookies for session auth
            body: JSON.stringify({
                group_id: formData.groupId,
                from_date: formData.fromDate,
                to_date: formData.toDate,
                date_type: formData.dateType
            })
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
        return;
    }

    policies.forEach(policy => {
        // Handle different field names from stored procedure
        // Adjust these field names based on your stored procedure output
        const policyNo = policy.PolicyNo || policy.policy_no || '-';
        const name = policy.Name || policy.name || policy.EmployeeName || '-';
        const maturityDate = policy.MaturityDate || policy.maturity_date || '-';
        const sumAssured = policy.SumAssured || policy.sum_assured || 0;
        const premium = policy.Premium || policy.premium || 0;
        const policyStatus = policy.PolicyStatus || policy.policy_status || 'A';

        const monthsToMaturity = calculateMonthsDifference(maturityDate);
        const row = document.createElement('tr');

        row.innerHTML = `
            <td>${policyNo}</td>
            <td>${name}</td>
            <td>${formatDate(maturityDate)}</td>
            <td>${formatCurrency(sumAssured)}</td>
            <td>${formatCurrency(premium)}</td>
            <td>${monthsToMaturity > 0 ? monthsToMaturity + ' months' : 'Matured'}</td>
            <td>${getStatusBadge(policyStatus)}</td>
        `;

        tbody.appendChild(row);
    });
}
/**
 * Update report summary
 */
function updateReportSummary(data) {
    const groupSelect = document.getElementById('group-id');
    const groupName = groupSelect.options[groupSelect.selectedIndex].text;

    const dateTypeText = currentDateType === 'ad' ? 'AD' : 'BS';

    const summaryText = `Showing ${data.count} policies maturing between ${data.formData.fromDate} and ${data.formData.toDate} (${dateTypeText}) for Group: ${groupName}`;

    document.getElementById('report-summary').textContent = summaryText;
}

/**
 * Show report results
 */
function showReportResults(data) {
    // Calculate statistics
    const stats = calculateStatistics(data.policies);

    // Update UI
    updateStatistics(stats);
    updateReportSummary(data);
    populateReportTable(data.policies);

    // Hide form, show results
    document.querySelector('.report-container').style.display = 'none';
    document.getElementById('report-results').classList.add('active');

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

/**
 * Hide report results and show form
 */
function hideReportResults() {
    document.getElementById('report-results').classList.remove('active');
    document.querySelector('.report-container').style.display = 'block';

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
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
        console.log('Report data:', reportData);

        // Show results
        showReportResults(reportData);
    } catch (error) {
        console.error('Error generating report:', error);
        showNotification('Failed to generate report. Please try again.', 'error');
    } finally {
        setButtonLoading(submitButton, false);
    }
}

/**
 * Handle form reset
 */
function handleFormReset() {
    // Reset to AD date type
    switchDateType('ad');

    // Clear all fields
    document.getElementById('from-date-ad').value = '';
    document.getElementById('to-date-ad').value = '';
    document.getElementById('from-date-bs').value = '';
    document.getElementById('to-date-bs').value = '';
    document.getElementById('group-id').value = '';
}

/**
 * Handle export report
 */
function handleExportReport() {
    // TODO: Implement export functionality (Excel, PDF, etc.)
    console.log('Exporting report...');
    showNotification('Export functionality coming soon!', 'info');
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
        form.addEventListener('reset', handleFormReset);
    }

    // Back to form button
    const backButton = document.getElementById('back-to-form-btn');
    if (backButton) {
        backButton.addEventListener('click', hideReportResults);
    }

    // Export report button
    const exportButton = document.getElementById('export-report-btn');
    if (exportButton) {
        exportButton.addEventListener('click', handleExportReport);
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

    // Initialize date type tabs
    initializeDateTypeTabs();

    // Initialize event listeners
    initializeEventListeners();

    // Set default date type
    switchDateType('ad');

    console.log('Maturity report initialized');
}

// Run initialization when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
} else {
    initialize();
}