// ================================
// GLOBAL STATE
// ================================
let currentDateType = 'ad'; // 'ad' or 'bs'
var groupTransferData; // Global variable to store report data

// ================================
// UTILITY FUNCTIONS
// ================================

/**
 * Format currency values
 */
function formatCurrency(value) {
    if (value === null || value === undefined || value === '') return '-';
    const num = parseFloat(value);
    if (isNaN(num)) return '-';
    return num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/**
 * Format date for display
 */
function formatDate(dateString) {
    if (!dateString) return '-';

    let date;

    if (dateString.includes('/')) {
        const parts = dateString.split('/');
        if (parts.length === 3) {
            // Assume DD/MM/YYYY format
            date = new Date(parts[2], parts[1] - 1, parts[0]);
        }
    } else if (dateString.includes('-')) {
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
        date = new Date(dateString);
    }

    if (isNaN(date.getTime())) {
        return dateString; // Return original string if parsing fails
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
    const pattern = /^\d{4}-\d{2}-\d{2}$/;
    if (!pattern.test(dateString)) {
        return { valid: false, message: 'Invalid BS date format. Use YYYY-MM-DD' };
    }

    const [year, month, day] = dateString.split('-').map(Number);

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

    const fromDateAD = document.getElementById('from-date-ad').value;
    const toDateAD = document.getElementById('to-date-ad').value;

    const fromDateBS = document.getElementById('from-date-bs').value;
    const toDateBS = document.getElementById('to-date-bs').value;

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
    if (!formData.groupId) {
        return { valid: false, message: 'Please select a group' };
    }

    if (!formData.fromDate || !formData.toDate) {
        return { valid: false, message: 'Please enter dates in either AD or BS format' };
    }

    if (formData.dateType === 'ad') {
        return validateDateRange(formData.fromDate, formData.toDate);
    } else {
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
            transfer_date_from: formData.fromDate,
            transfer_date_to: formData.toDate,
            group_id: formData.groupId
        };

        const response = await fetch('/api/corporate/reports/group-transfer/', {
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
            transfers: data.transfers,
            count: data.count,
            formData: formData
        };
    } catch (error) {
        console.error('Error fetching report data:', error);
        throw error;
    }
}

/**
 * Populate report table
 */
function populateReportTable(transfers) {
    const tbody = document.getElementById('report-tbody');
    tbody.innerHTML = '';

    if (!transfers || transfers.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center">No transfers found for the selected criteria</td></tr>';
        return false;
    }

    let hasValidData = false;

    transfers.forEach(transfer => {
        const policyNo = transfer.PolicyNo || transfer.policy_no || '';

        // Skip rows without a valid policy number
        if (!policyNo || policyNo === '-' || policyNo.trim() === '') {
            return;
        }

        hasValidData = true;

        const name = transfer.Name || '-';
        const transferDate = transfer.TransferDate || '';
        const sumAssured = transfer.SA || transfer.SumAssured || 0;
        const premium = transfer.Premium || transfer.BasicPremium || 0;
        const paidAmount = transfer.PaidAmount || 0;
        const instalment = transfer.Instalment || transfer.Installment || '-';

        const row = document.createElement('tr');

        row.innerHTML = `
            <td>${policyNo}</td>
            <td>${name}</td>
            <td>${formatDate(transferDate)}</td>
            <td>${formatCurrency(sumAssured)}</td>
            <td>${formatCurrency(premium)}</td>
            <td>${formatCurrency(paidAmount)}</td>
            <td>${instalment}</td>
        `;

        tbody.appendChild(row);
    });

    if (!hasValidData) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center">No transfers found.</td></tr>';
        return false;
    }

    return true;
}

/**
 * Update report summary
 */
function updateReportSummary(data) {
    const summaryEl = document.getElementById('report-summary');
    if (!summaryEl) return; // Guard against missing element
 
    const groupSelect = document.getElementById('group-id');
    const groupName = groupSelect.options[groupSelect.selectedIndex].text;
 
    const dateTypeText = data.formData.dateType === 'ad' ? 'AD' : 'BS';
 
    summaryEl.textContent = `Showing ${data.count} transfers between ${data.formData.fromDate} and ${data.formData.toDate} (${dateTypeText}) for Group: ${groupName}`;
}

/**
 * Show report results below the form
 */
function showReportResults(data) {
    // Destroy existing DataTable first if it exists
    if ($.fn.DataTable.isDataTable('#report-table')) {
        $('#report-table').DataTable().destroy();
    }

    // Populate table
    const hasData = populateReportTable(data.transfers);

    // Update summary
    updateReportSummary(data);

    // Show results section
    const resultsSection = document.getElementById('report-results');
    resultsSection.style.display = 'block';

    if (!hasData) {
        const downloadBtn = document.getElementById('download-btn');
        if (downloadBtn) downloadBtn.disabled = true;

        showNotification('No transfers found for the selected criteria', 'info');

        setTimeout(() => {
            resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);

        return;
    }

    const downloadBtn = document.getElementById('download-btn');
    if (downloadBtn) downloadBtn.disabled = false;

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

    const formData = getFormData();
    console.log('Form data:', formData);

    const validation = validateForm(formData);
    if (!validation.valid) {
        showNotification(validation.message, 'error');
        return;
    }

    const submitButton = document.getElementById('generate-btn');
    setButtonLoading(submitButton, true);

    try {
        const reportData = await fetchReportData(formData);
        console.log('Report data received:', reportData);
        console.log('Transfers:', reportData.transfers);
        console.log('Count:', reportData.count);

        if (!reportData.transfers) {
            throw new Error('No transfer data received from server');
        }

        groupTransferData = reportData.transfers; // Store globally for download

        showReportResults(reportData);
    } catch (error) {
        console.error('Error generating report:', error);
        showNotification('Failed to generate report: ' + error.message, 'error');
    } finally {
        setButtonLoading(submitButton, false);
    }
}

// ================================
// DOWNLOAD HANDLING
// ================================

/**
 * Handle download report
 */
function handleDownloadReport() {
    console.log("Global data:", groupTransferData);

    if (!groupTransferData || groupTransferData.length === 0) {
        showNotification('No data to download. Please generate a report first.', 'error');
        return;
    }

    const groupSelect = document.getElementById('group-id');
    const groupId = groupSelect.value;

    const userInfoDiv = document.getElementById('user-info');
    const userName = userInfoDiv ? userInfoDiv.dataset.username : 'user';

    const today = new Date().toISOString().slice(0, 10);

    const filename = `group_transfer_report_${groupId}_${userName}_${today}.csv`;

    downloadCSV(groupTransferData, filename);
}

// ================================
// EVENT LISTENERS
// ================================

/**
 * Initialize all event listeners
 */
function initializeEventListeners() {
    const form = document.getElementById('transfer-report-form');
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    }

    const downloadButton = document.getElementById('download-btn');
    if (downloadButton) {
        downloadButton.addEventListener('click', handleDownloadReport);
    }
}

// ================================
// INITIALIZATION
// ================================

/**
 * Initialize the group transfer report page
 */
function initialize() {
    console.log('Group transfer report script loaded');
    initializeEventListeners();
    console.log('Group transfer report initialized');
}

// Run initialization when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
} else {
    initialize();
}