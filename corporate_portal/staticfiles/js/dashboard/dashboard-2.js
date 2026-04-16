/**
 * Company Dashboard JavaScript
 * Handles data loading, statistics display, and chart rendering
 */

/**
 * Get status badge HTML based on policy status
 */
function getStatusBadge(status) {
    const badges = {
        'A': '<span class="badge badge-success">Active</span>',
        'L': '<span class="badge badge-warning">Lapsed</span>'
    };
    return badges[status] || '<span class="badge badge-secondary">Inactive</span>';
}

/**
 * Update statistics cards
 */
function updateStatistics(data) {
    try {
        // Total Policies
        document.getElementById('total-policies').textContent = data.count || 0;

        // Active Policies
        const activePolicies = data.endowments.filter(p => p.policy_status === 'A').length;
        document.getElementById('active-policies').textContent = activePolicies;

        // Total Premium
        const totalPremium = data.endowments.reduce((sum, p) => sum + parseFloat(p.premium || 0), 0);
        document.getElementById('total-premium').textContent = formatCurrency(totalPremium);
        
        console.log('Statistics updated successfully');
    } catch (error) {
        console.error('Error updating statistics:', error);
    }
}

/**
 * Populate policies table
 */
function populatePoliciesTable(policies) {
    const tbody = document.getElementById('policies-tbody');
    
    if (!tbody) {
        console.error('Policies table body not found');
        return;
    }
    
    tbody.innerHTML = '';

    if (!policies || policies.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">No policies found</td></tr>';
        return;
    }

    // Show first 10 policies
    policies.slice(0, 10).forEach(policy => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${policy.policy_no || '-'}</td>
            <td>${policy.name || '-'}</td>
            <td>${formatCurrency(policy.sum_assured)}</td>
            <td>${formatCurrency(policy.premium)}</td>
            <td>${policy.maturity_date || '-'}</td>
            <td>${getStatusBadge(policy.policy_status)}</td>
        `;
        tbody.appendChild(row);
    });
    
    console.log(`Populated table with ${Math.min(policies.length, 10)} policies`);
}

/**
 * Show error state in UI
 */
function showErrorState(message) {
    const tbody = document.getElementById('policies-tbody');
    if (tbody) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">${message}</td></tr>`;
    }
    
    // Set statistics to error state
    const errorText = 'Error';
    const elements = ['total-policies', 'active-policies', 'total-premium'];
    elements.forEach(id => {
        const element = document.getElementById(id);
        if (element) element.textContent = errorText;
    });
}

/**
 * Set loading state
 */
function setLoadingState(isLoading) {
    const tbody = document.getElementById('policies-tbody');
    if (tbody && isLoading) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">Loading policies...</td></tr>';
    }
}

// ================================
// DATA FETCHING
// ================================

/**
 * Fetch policies from API
 */
async function fetchPolicies(companyId) {
    const apiUrl = `/api/corporate/endowments/by_company/?company_id=${companyId}`;
    console.log('Fetching from API:', apiUrl);
    
    try {
        const response = await fetch(apiUrl);
        console.log('API Response Status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('API Response Data:', data);
        console.log('Number of endowments:', data.endowments ? data.endowments.length : 0);
        
        // Validate data structure
        if (!data.endowments || !Array.isArray(data.endowments)) {
            throw new Error('Invalid API response structure');
        }
        
        return data;
    } catch (error) {
        console.error('ERROR fetching policies:', error);
        throw error;
    }
}

/**
 * Initialize dashboard data
 */
async function initializeDashboard() {
    console.log('Initializing dashboard...');
    
    // Get company ID from data attribute
    const companyIdElement = document.querySelector('[data-company-id]');
    console.log('Company ID Element:', companyIdElement);
    
    if (!companyIdElement) {
        console.error('ERROR: Company ID element not found in DOM');
        showErrorState('Company ID not found in page');
        return;
    }
    
    const companyId = companyIdElement.getAttribute('data-company-id');
    console.log('Company ID:', companyId);
    
    if (!companyId || companyId === 'None' || companyId === '') {
        console.error('ERROR: Invalid company ID:', companyId);
        showErrorState('Invalid company ID');
        return;
    }
    
    // Set loading state
    setLoadingState(true);
    
    try {
        // Fetch data
        const data = await fetchPolicies(companyId);
        
        // Update UI
        updateStatistics(data);
        populatePoliciesTable(data.endowments);
        
        console.log('Dashboard initialized successfully');
    } catch (error) {
        console.error('Failed to initialize dashboard:', error);
        showErrorState('Error loading policies: ' + error.message);
    }
}


/**
 * Initialize perfect scrollbar for todo widget
 */
function initializeTodoScrollbar() {
    const todoElement = document.querySelector('.widget-todo2');
    if (!todoElement) {
        console.log('Todo widget element not found, skipping scrollbar');
        return;
    }
    
    if (typeof PerfectScrollbar !== 'undefined') {
        const wt2 = new PerfectScrollbar('.widget-todo2');
        console.log('Todo scrollbar initialized');
    } else {
        console.warn('PerfectScrollbar library not loaded, skipping todo scrollbar');
    }
}

// ================================
// MAIN INITIALIZATION
// ================================

/**
 * Initialize all dashboard components
 */
function initializeAll() {
    console.log('Dashboard script loaded');
    
    // Initialize data (main priority)
    initializeDashboard();
    
    // Initialize charts and widgets (secondary)
    // initializePieChart();
    // initializeBarChart();
    // initializeCalendar();
    initializeTodoScrollbar();
}

// Run initialization when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeAll);
} else {
    initializeAll();
}