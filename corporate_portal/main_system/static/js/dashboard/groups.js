// groups.js - Handle group information display

document.addEventListener('DOMContentLoaded', function() {
    loadGroups();
});

/**
 * Load groups from API
 */
function loadGroups() {
    // Show loading state
    showLoading();
    
    // API endpoint
    const apiUrl = '/api/corporate/groups/';
    
    // Fetch groups
    fetch(apiUrl, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        credentials: 'include'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('Groups data:', data);
        
        if (data.count === 0 || !data.results || data.results.length === 0) {
            showEmptyState();
        } else {
            renderGroups(data.results);
            showGroups();
        }
    })
    .catch(error => {
        console.error('Error loading groups:', error);
        showError('Failed to load groups: ' + error.message);
    });
}

/**
 * Render groups into accordion
 */
function renderGroups(groups) {
    const accordion = document.getElementById('groups-accordion');
    accordion.innerHTML = '';
    
    groups.forEach((group, index) => {
        const groupHtml = createGroupAccordion(group, index);
        accordion.innerHTML += groupHtml;
    });
}

/**
 * Create accordion HTML for a single group
 */
function createGroupAccordion(group, index) {
    const collapseId = `group-collapse-${index}`;
    const groupName = group.group_name || 'Unnamed Group';
    const groupNameNepali = group.group_name_nepali || '';
    const groupId = group.group_id || 'N/A';
    const isActive = group.is_active;
    const statusBadge = isActive 
        ? '<span class="status-badge status-active">Active</span>' 
        : '<span class="status-badge status-inactive">Inactive</span>';
    
    // Statistics
    const totalMembers = formatNumber(group.total_members_count || 0);
    const activePolicies = formatNumber(group.total_active_policies || 0);
    const totalPremium = formatCurrency(group.total_premium || 0);
    const totalSA = formatCurrency(group.total_sa || 0);
    
    // Claims
    const deathClaims = formatNumber(group.death_claim || 0);
    const surrenderClaims = formatNumber(group.surrender_claim || 0);
    const maturityClaims = formatNumber(group.maturity_claim || 0);
    const transferClaims = formatNumber(group.transfer_claim || 0);
    const terminateClaims = formatNumber(group.terminate_claim || 0);
    const cancelClaims = formatNumber(group.cancel_claim || 0);
    
    return `
        <div class="accordion__item">
            <div class="accordion__header collapsed" data-toggle="collapse" data-target="#${collapseId}" aria-expanded="false">
                <span class="accordion__header--text">
                    <span class="group-header-title">${groupName}</span>
                    <span class="group-id-badge">ID: ${groupId}</span>
                    ${statusBadge}
                    ${groupNameNepali ? `<br><small class="text-muted">${groupNameNepali}</small>` : ''}
                </span>
                <span class="accordion__header--indicator"></span>
            </div>
            <div id="${collapseId}" class="accordion__body collapse" data-parent="#groups-accordion">
                <div class="accordion__body--text">
                    
                    <!-- Group Statistics -->
                    <h5 class="mb-3">Group Statistics</h5>
                    <div class="row mb-4">
                        <div class="col-md-3 col-sm-6">
                            <div class="stat-card">
                                <div class="stat-label">Total Members</div>
                                <div class="stat-value ">${totalMembers}</div>
                            </div>
                        </div>
                        <div class="col-md-3 col-sm-6">
                            <div class="stat-card">
                                <div class="stat-label">Active Policies</div>
                                <div class="stat-value ">${activePolicies}</div>
                            </div>
                        </div>
                        <div class="col-md-3 col-sm-6">
                            <div class="stat-card">
                                <div class="stat-label">Total Premium</div>
                                <div class="stat-value ">${totalPremium}</div>
                            </div>
                        </div>
                        <div class="col-md-3 col-sm-6">
                            <div class="stat-card">
                                <div class="stat-label">Total Sum Assured</div>
                                <div class="stat-value ">${totalSA}</div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Claims Summary -->
                    <h5 class="mb-3">Claims Summary</h5>
                    <div class="row">
                        <div class="col-md-2 col-sm-4 col-6">
                            <div class="stat-card">
                                <div class="stat-label">Death</div>
                                <div class="stat-value">${deathClaims}</div>
                            </div>
                        </div>
                        <div class="col-md-2 col-sm-4 col-6">
                            <div class="stat-card">
                                <div class="stat-label">Surrender</div>
                                <div class="stat-value ">${surrenderClaims}</div>
                            </div>
                        </div>
                        <div class="col-md-2 col-sm-4 col-6">
                            <div class="stat-card">
                                <div class="stat-label">Maturity</div>
                                <div class="stat-value">${maturityClaims}</div>
                            </div>
                        </div>
                        <div class="col-md-2 col-sm-4 col-6">
                            <div class="stat-card">
                                <div class="stat-label">Transfer</div>
                                <div class="stat-value">${transferClaims}</div>
                            </div>
                        </div>
                        <div class="col-md-2 col-sm-4 col-6">
                            <div class="stat-card">
                                <div class="stat-label">Terminate</div>
                                <div class="stat-value">${terminateClaims}</div>
                            </div>
                        </div>
                        <div class="col-md-2 col-sm-4 col-6">
                            <div class="stat-card">
                                <div class="stat-label">Cancel</div>
                                <div class="stat-value">${cancelClaims}</div>
                            </div>
                        </div>
                    </div>
                    
                </div>
            </div>
        </div>
    `;
}

/**
 * Format number with commas
 */
function formatNumber(num) {
    if (!num || num === 0) return '0';
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

/**
 * Format currency (NPR)
 */
function formatCurrency(amount) {
    if (!amount || amount === 0) return 'NPR 0';
    const formatted = parseFloat(amount).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    return `NPR ${formatted}`;
}

/**
 * Show/Hide states
 */
function showLoading() {
    document.getElementById('loading-state').style.display = 'block';
    document.getElementById('error-state').style.display = 'none';
    document.getElementById('groups-container').style.display = 'none';
}

function showError(message) {
    document.getElementById('error-message').textContent = message;
    document.getElementById('loading-state').style.display = 'none';
    document.getElementById('error-state').style.display = 'block';
    document.getElementById('groups-container').style.display = 'none';
}

function showGroups() {
    document.getElementById('loading-state').style.display = 'none';
    document.getElementById('error-state').style.display = 'none';
    document.getElementById('groups-container').style.display = 'block';
    document.getElementById('empty-state').style.display = 'none';
}

function showEmptyState() {
    document.getElementById('loading-state').style.display = 'none';
    document.getElementById('error-state').style.display = 'none';
    document.getElementById('groups-container').style.display = 'block';
    document.getElementById('empty-state').style.display = 'block';
    document.getElementById('groups-accordion').style.display = 'none';
}

/**
 * Get CSRF token from cookie
 */
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