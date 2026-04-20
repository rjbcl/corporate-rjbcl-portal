function getStatusBadge(status) {
    const badges = {
        'A': '<span class="badge badge-success">Active</span>',
        'L': '<span class="badge badge-warning">Lapsed</span>'
    };
    return badges[status] || '<span class="badge badge-secondary">Inactive</span>';
}

function updateStatistics(summary) {
    try {
        document.getElementById('total-policies').textContent = summary.totalPolicies || 0;
        document.getElementById('active-policies').textContent = summary.activePolicies || 0;
        document.getElementById('total-premium').textContent = formatCurrency(summary.totalPremium || 0);
    } catch (error) {
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Error updating statistics. Please try again or contact support'
        });
    }
}

function populatePoliciesTable(policies) {
    const tbody = document.getElementById('policies-tbody');

    if (!tbody) {
        Swal.fire({
            icon: 'error',
            title: 'Oops...',
            text: 'Policies table body not found'
        });
        return;
    }

    tbody.innerHTML = '';

    if (!policies || policies.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">No policies found</td></tr>';
        return;
    }

    policies.forEach(policy => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${policy.policyNo || '-'}</td>
            <td>${policy.Name || '-'}</td>
            <td>${policy.sumassured || '-'}</td>
            <td>${policy.premium || '-'}</td>
            <td>${policy.DOC || '-'}</td>
            <td>${policy.maturitydate || '-'}</td>
        `;
        tbody.appendChild(row);
    });
}

function showErrorState(message) {
    const tbody = document.getElementById('policies-tbody');
    if (tbody) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">${message}</td></tr>`;
    }
    ['total-policies', 'active-policies', 'total-premium'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = 'Error';
    });
}

function setLoadingState(isLoading) {
    const tbody = document.getElementById('policies-tbody');
    if (tbody && isLoading) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">Loading policies...</td></tr>';
    }

    const timeline = document.getElementById('fup-timeline');  // <-- add this
    if (timeline && isLoading) {
        timeline.innerHTML = '<li><div class="timeline-panel text-muted"><span>Loading payment schedule...</span></div></li>';
    }
}

async function fetchPolicies(companyId) {
    const response = await fetch(`/api/corporate/endowments/by_company/?company_id=${companyId}`);

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
}

async function initializeDashboard() {
    const companyIdElement = document.querySelector('[data-company-id]');

    if (!companyIdElement) {
        showErrorState('Company ID not found in page');
        return;
    }

    const companyId = companyIdElement.getAttribute('data-company-id');

    if (!companyId || companyId === 'None' || companyId === '') {
        showErrorState('Invalid company ID');
        return;
    }

    setLoadingState(true);

    try {
        const data = await fetchPolicies(companyId);
        updateStatistics(data.summary);
        populatePoliciesTable(data.latest_policies);
        populateFupTimeline(data.fup_data);
        initializeFupScrollbar();
    } catch (error) {
        showErrorState('Error loading policies: ' + error.message);
    }
}

function initializeTodoScrollbar() {
    const todoElement = document.querySelector('.widget-todo2');
    if (!todoElement) return;

    if (typeof PerfectScrollbar !== 'undefined') {
        new PerfectScrollbar('.widget-todo2');
    }
}

function initializeAll() {
    initializeDashboard();
    initializeTodoScrollbar();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeAll);
} else {
    initializeAll();
}



function populateFupTimeline(fupData) {
    const timeline = document.getElementById('fup-timeline');

    if (!timeline) {
        Swal.fire({
            icon: 'error',
            title: 'Oops...',
            text: 'FUP timeline element not found'
        });
        return;
    }

    if (!fupData || fupData.length === 0) {
        timeline.innerHTML = '<li><div class="timeline-panel text-muted"><span>No upcoming premium payments found</span></div></li>';
        return;
    }

    // Sort soonest first
    const sorted = [...fupData].sort((a, b) => a.DaysUntilFUP - b.DaysUntilFUP);

    timeline.innerHTML = sorted.map(item => {
        // Urgency badge color
        let badgeClass = 'success';
        if (item.DaysUntilFUP < 7) badgeClass = 'danger';
        else if (item.DaysUntilFUP < 30) badgeClass = 'warning';

        // Format the FUP date
        const fupDate = item.fup ? new Date(item.fup).toLocaleDateString() : '-';

        return `
            <li>
                <div class="timeline-badge ${badgeClass}"></div>
                <a class="timeline-panel text-muted" href="#">
                    <span>${item.DaysUntilFUP} day(s) left &mdash; Due: ${fupDate}</span>
                    <h6 class="m-t-5">${item.Name || '-'}</h6>
                    <p class="mb-0 text-muted" style="font-size:0.85em;">${item.policyNo || '-'}</p>
                </a>
            </li>
        `;
    }).join('');
}


function initializeFupScrollbar() {
    const el = document.getElementById('fup-timeline-scroll');
    if (!el) return;

    if (typeof PerfectScrollbar !== 'undefined') {
        new PerfectScrollbar('#fup-timeline-scroll');
    }
}