// ================================
// SECTION NAVIGATION
// ================================
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', function(e) {
        e.preventDefault();
        const section = this.getAttribute('data-section');
        const report = this.getAttribute('data-report');
        
        // Update active states
        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        this.classList.add('active');
        
        // Handle parent menu active state
        const parentLi = this.closest('li').parentElement.closest('li');
        if (parentLi) {
            document.querySelectorAll('.metismenu > li').forEach(li => li.classList.remove('mm-active'));
            parentLi.classList.add('mm-active');
        }
        
        showSection(section, report);
    });
});

function showSection(sectionName, reportType) {
    // Hide all sections
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.remove('active');
        section.classList.add('hidden-section');
    });

    // Show selected section
    const activeSection = document.getElementById(sectionName + '-section');
    if (activeSection) {
        activeSection.classList.remove('hidden-section');
        activeSection.classList.add('active');
    }
    
    // If specific report type, could handle different report views here
    if (reportType) {
        console.log('Loading report type:', reportType);
        // Future: Show specific report based on reportType
    }
}

// Set initial active state
document.addEventListener('DOMContentLoaded', function() {
    const dashboardLink = document.querySelector('[data-section="dashboard"]');
    if (dashboardLink) {
        dashboardLink.classList.add('active');
        const parentLi = dashboardLink.closest('.metismenu > li');
        if (parentLi) parentLi.classList.add('mm-active');
    }
});

// ================================
// MATURITY FORECASTING REPORT
// ================================
// Get company ID from the page
const companyIdElement = document.querySelector('[data-company-id]');
const companyId = companyIdElement ? companyIdElement.getAttribute('data-company-id') : '';

document.addEventListener('DOMContentLoaded', function() {
    const maturityForm = document.getElementById('maturity-report-form');
    if (maturityForm) {
        maturityForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const fromDate = document.getElementById('from-date').value;
            const toDate = document.getElementById('to-date').value;
            const groupId = document.getElementById('group-id').value;

            // Validate dates
            if (new Date(fromDate) > new Date(toDate)) {
                alert('From Date must be before To Date');
                return;
            }

            // For now, just show sample data
            generateSampleReport(fromDate, toDate, groupId);
        });
    }
});

function generateSampleReport(fromDate, toDate, groupId) {
    // Sample data - replace with actual API call later
    const sampleData = [
        {
            policy_no: 'POL-001',
            name: 'John Doe',
            maturity_date: '2025-06-15',
            sum_assured: 500000,
            months_to_maturity: 4
        },
        {
            policy_no: 'POL-002',
            name: 'Jane Smith',
            maturity_date: '2025-07-20',
            sum_assured: 750000,
            months_to_maturity: 5
        },
        {
            policy_no: 'POL-003',
            name: 'Robert Wilson',
            maturity_date: '2025-08-10',
            sum_assured: 600000,
            months_to_maturity: 6
        },
        {
            policy_no: 'POL-004',
            name: 'Maria Garcia',
            maturity_date: '2025-09-05',
            sum_assured: 800000,
            months_to_maturity: 7
        }
    ];

    // Populate table
    const tbody = document.getElementById('report-tbody');
    tbody.innerHTML = '';

    sampleData.forEach(policy => {
        const row = `
            <tr>
                <td>${policy.policy_no}</td>
                <td>${policy.name}</td>
                <td>${policy.maturity_date}</td>
                <td>Rs. ${policy.sum_assured.toLocaleString('en-NP')}</td>
                <td>${policy.months_to_maturity} months</td>
                <td><span class="badge badge-info">Upcoming</span></td>
            </tr>
        `;
        tbody.innerHTML += row;
    });

    // Update summary
    document.getElementById('report-summary').textContent = 
        `Showing ${sampleData.length} policies maturing between ${fromDate} and ${toDate} for Group: ${groupId}`;

    // Show results section
    document.getElementById('report-results').classList.remove('hidden-section');
    document.getElementById('report-results').classList.add('active');

    // Hide form
    document.getElementById('maturity-report-form').closest('.report-form-container').style.display = 'none';
}

function resetReport() {
    // Hide results
    document.getElementById('report-results').classList.add('hidden-section');
    document.getElementById('report-results').classList.remove('active');

    // Show form
    document.getElementById('maturity-report-form').closest('.report-form-container').style.display = 'block';

    // Reset form
    document.getElementById('maturity-report-form').reset();
}

// ================================
// DASHBOARD INITIAL LOAD
// ================================
document.addEventListener('DOMContentLoaded', function() {
    // Get company ID from data attribute
    const companyIdElement = document.querySelector('[data-company-id]');
    if (!companyIdElement) {
        console.error('Company ID not found');
        return;
    }
    
    const companyId = companyIdElement.getAttribute('data-company-id');
    
    // Fetch and display policies
    fetch(`/api/corporate/endowments/by_company/?company_id=${companyId}`)
        .then(response => response.json())
        .then(data => {
            console.log('API Response:', data);

            // Update statistics
            document.getElementById('total-policies').textContent = data.count;

            const activePolicies = data.endowments.filter(p => p.policy_status === 'A').length;
            document.getElementById('active-policies').textContent = activePolicies;

            const totalPremium = data.endowments.reduce((sum, p) => sum + parseFloat(p.premium || 0), 0);
            document.getElementById('total-premium').textContent = 'Rs. ' + totalPremium.toLocaleString('en-NP', { maximumFractionDigits: 2 });

            // Populate table
            const tbody = document.getElementById('policies-tbody');
            tbody.innerHTML = '';

            if (data.endowments.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center">No policies found</td></tr>';
                return;
            }

            // Show first 10 policies
            data.endowments.slice(0, 10).forEach(policy => {
                const statusBadge = policy.policy_status === 'A'
                    ? '<span class="badge badge-success">Active</span>'
                    : policy.policy_status === 'L'
                        ? '<span class="badge badge-warning">Lapsed</span>'
                        : '<span class="badge badge-secondary">Inactive</span>';

                const row = `
                    <tr>
                        <td>${policy.policy_no || '-'}</td>
                        <td>${policy.name || '-'}</td>
                        <td>Rs. ${parseFloat(policy.sum_assured || 0).toLocaleString('en-NP')}</td>
                        <td>Rs. ${parseFloat(policy.premium || 0).toLocaleString('en-NP')}</td>
                        <td>${policy.maturity_date || '-'}</td>
                        <td>${statusBadge}</td>
                    </tr>
                `;
                tbody.innerHTML += row;
            });
        })
        .catch(error => {
            console.error('Error fetching policies:', error);
            document.getElementById('policies-tbody').innerHTML =
                '<tr><td colspan="6" class="text-center text-danger">Error loading policies</td></tr>';
        });
});