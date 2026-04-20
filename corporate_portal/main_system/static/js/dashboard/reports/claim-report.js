let deathReportData = [];
let deathMetaData = {};


let maturityReportData = [];
let maturityMetaData = {};

let surrenderReportData = [];
let surrenderMetaData = {};


// Handle form submissions for all three claim types
document.addEventListener('DOMContentLoaded', function () {
    // Track which reports have been generated
    const generatedReports = {
        maturity: false,
        surrender: false,
        death: false
    };

    // Get all claim forms
    const forms = document.querySelectorAll('.claim-form');

    forms.forEach(form => {
        form.addEventListener('submit', function (e) {
            e.preventDefault();

            const claimType = this.getAttribute('data-claim-type');
            const formData = new FormData(this);


            // Generate report for the specific claim type
            generateReport(claimType, formData);
        });
    });

    function generateReport(claimType, formData) {
        // Disable generate button and show loading
        const generateBtn = document.getElementById(`${claimType}-generate-btn`);
        const originalText = generateBtn.innerHTML;
        generateBtn.disabled = true;
        generateBtn.innerHTML = '<span class="spinner"></span> Generating...';

        // Get the report results div for this specific claim type
        const reportResults = document.getElementById(`${claimType}-report-results`);

        // Only death claim is implemented
        const requestData = {
            group_id: formData.get('group_id'),
            from_date: formData.get('from_date_ad'),
            to_date: formData.get('to_date_ad')
        };
        if (claimType === 'death') {
            fetch('/api/corporate/reports/death-claim/', {
                method: 'POST',
                body: JSON.stringify(requestData),
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                }
            })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {

                    deathReportData = data;
                    deathMetaData = {
                        from_date: requestData.from_date,
                        to_date: requestData.to_date,
                        group_id: requestData.group_id
                    };

                    // Populate the table
                    populateTable(claimType, data);

                    // Show the report table
                    reportResults.style.display = 'block';

                    // Mark this report as generated
                    generatedReports[claimType] = true;

                    // Enable download button
                    document.getElementById(`${claimType}-download-btn`).disabled = false;

                    // Scroll to the report
                    setTimeout(() => {
                        reportResults.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                    }, 100);
                })
                .catch(error => {
                    Swal.fire({
                        icon: 'error',
                        title: 'Oops...',
                        text: 'Error: Please try again or contact support if the issue persists.',
                    });
                    alert(`Error generating ${claimType} report: ${error.message}`);
                })
                .finally(() => {
                    generateBtn.disabled = false;
                    generateBtn.innerHTML = originalText;
                });
        }

        if (claimType === 'maturity') {
            fetch('/api/corporate/reports/maturity-claim/', {
                method: 'POST',
                body: JSON.stringify(requestData),
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                }
            })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {

                    maturityReportData = data;
                    maturityMetaData = {
                        from_date: requestData.from_date,
                        to_date: requestData.to_date,
                        group_id: requestData.group_id
                    };

                    // Populate the table
                    populateTable(claimType, data);

                    // Show the report table
                    reportResults.style.display = 'block';

                    // Mark this report as generated
                    generatedReports[claimType] = true;

                    // Enable download button
                    document.getElementById(`${claimType}-download-btn`).disabled = false;

                    // Scroll to the report
                    setTimeout(() => {
                        reportResults.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                    }, 100);
                })
                .catch(error => {
                    Swal.fire({
                        icon: 'error',
                        title: 'Oops...',
                        text: 'Error: Please try again or contact support if the issue persists.',
                    });
                    alert(`Error generating ${claimType} report: ${error.message}`);
                })
                .finally(() => {
                    generateBtn.disabled = false;
                    generateBtn.innerHTML = originalText;
                });
        }
        if (claimType === 'surrender') {
            fetch('/api/corporate/reports/surrender-claim/', {
                method: 'POST',
                body: JSON.stringify(requestData),
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                }
            })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {

                    surrenderReportData = data;
                    surrenderMetaData = {
                        from_date: requestData.from_date,
                        to_date: requestData.to_date,
                        group_id: requestData.group_id
                    };

                    // Populate the table
                    populateTable(claimType, data);

                    // Show the report table
                    reportResults.style.display = 'block';

                    // Mark this report as generated
                    generatedReports[claimType] = true;

                    // Enable download button
                    document.getElementById(`${claimType}-download-btn`).disabled = false;

                    // Scroll to the report
                    setTimeout(() => {
                        reportResults.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                    }, 100);
                })
                .catch(error => {
                    Swal.fire({
                        icon: 'error',
                        title: 'Oops...',
                        text: 'Error: Please try again or contact support if the issue persists.',
                    });
                    alert(`Error generating ${claimType} report: ${error.message}`);
                })
                .finally(() => {
                    generateBtn.disabled = false;
                    generateBtn.innerHTML = originalText;
                });
        }
    }
    // Populate table with data for specific claim type
    function populateTable(claimType, data) {
        const tbody = document.getElementById(`${claimType}-report-tbody`);
        tbody.innerHTML = ''; // Clear existing data

        if (!data || data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center">No data found</td></tr>';
            return;
        }

        data.forEach(item => {
            const row = document.createElement('tr');

            if (claimType === 'maturity') {
                row.innerHTML = `
                    <td>${item.PolicyNo || '-'}</td>
                    <td>${item.Name || '-'}</td>
                    <td>${formatCurrency(item.SA || 0)}</td>
                    <td>${formatCurrency(item.Premium || 0)}</td>
                    <td>${item.MaturityDate || '-'}</td>
                    <td>${item.ClaimAmount || '-'}</td>
                    <td>${item.ClaimDate || '-'}</td>
                    <td>${item.Bonus || '-'}</td>
                `;
            } else if (claimType === 'surrender') {
                row.innerHTML = `
                    <td>${item.PolicyNo || '-'}</td>
                    <td>${item.Name || item.NepName || '-'}</td>
                    <td>${formatCurrency(item.SA || 0)}</td>
                    <td>${formatCurrency(item.Premium || 0)}</td>
                    <td>${item.SurrenderDate || '-'}</td>
                    <td>${formatCurrency(item.SurrenderAmount || 0)}</td>
                    <td>${formatCurrency(item.LoanAmount) || '-'}</td>
                    <td>${item.Term || '-'}</td>
                `;
            } else if (claimType === 'death') {
                row.innerHTML = `
                    <td>${item.PolicyNo || '-'}</td>
                    <td>${item.Name || item.NepName || '-'}</td>
                    <td>${formatCurrency(item.SA || 0)}</td>
                    <td>${formatCurrency(item.Premium || 0)}</td>
                    <td>${item.DeathDate || '-'}</td>
                    <td>${formatCurrency(item.NetClaimAmount || 0)}</td>
                    <td>${item.Instalment || '-'}</td>
                    <td>${item.Bonus || '-'}</td>
                `;
            }

            tbody.appendChild(row);
        });

        // Initialize DataTable if you're using it
        initializeDataTable(claimType);
    }

    // Initialize DataTable (if using DataTables library)
    function initializeDataTable(claimType) {
        const tableId = `${claimType}-report-table`;

        // Check if jQuery and DataTables are available
        if (typeof $ === 'undefined' || typeof $.fn.DataTable === 'undefined') {
            return;
        }

        // Destroy existing DataTable if it exists
        if ($.fn.DataTable.isDataTable(`#${tableId}`)) {
            $(`#${tableId}`).DataTable().destroy();
        }

        // Initialize new DataTable
        $(`#${tableId}`).DataTable({
            responsive: true,
            pageLength: 10,
            lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "All"]],
            // DOM layout: l = length, f = filter, r = processing, t = table, i = info, p = pagination, B = buttons
            dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>' +
                '<"row"<"col-sm-12"tr>>' +
                '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
            buttons: [
                'copy', 'csv', 'excel', 'pdf', 'print'
            ],
            language: {
                lengthMenu: "Show _MENU_ entries",
                search: "Search:",
                info: "Showing _START_ to _END_ of _TOTAL_ entries",
                paginate: {
                    first: "First",
                    last: "Last",
                    next: "Next",
                    previous: "Previous"
                }
            }
        });
    }

    // Handle download button clicks
    document.getElementById('maturity-download-btn').addEventListener('click', function () {
        downloadReport('maturity_claim_report', maturityReportData);
    });

    document.getElementById('surrender-download-btn').addEventListener('click', function () {
        downloadReport('surrender_claim_report', surrenderReportData);
    });

    document.getElementById('death-download-btn').addEventListener('click', function () {
        downloadReport('death_claim_report', deathReportData);
    });

    function downloadReport(claimType, data) {

        if (!claimType) {
            alert('No data to download. Please generate a report first.');
            return;
        }

        // Get group name from the select dropdown
        const groupSelect = document.querySelector(`#${claimType} select[name="group_id"]`);
        const groupId = groupSelect ? groupSelect.value : deathMetaData.group_id;

        // Get user from data attribute (if available)
        const userInfoDiv = document.getElementById('user-info');
        const userName = userInfoDiv ? userInfoDiv.dataset.username : 'user';

        // Create filename with group ID and user
        const filename = `${claimType}_${groupId}_${userName}_${deathMetaData.from_date}_to_${deathMetaData.to_date}.csv`;

        // Call the downloadCSV function from report.js
        // downloadCSV(deathReportData, filename);
        downloadCSV(data, filename);

    }
    // No tab switching logic needed - tables persist within their own tab panes!
    // Each table is now part of its tab content, so Bootstrap handles the visibility automatically

    // However, since tables are now outside the main card, we need to show/hide them based on active tab
    const tabButtons = document.querySelectorAll('[data-bs-toggle="tab"]');
    tabButtons.forEach(button => {
        button.addEventListener('shown.bs.tab', function (event) {
            // Get the claim type from the tab target
            const targetId = event.target.getAttribute('data-bs-target');
            const claimType = targetId.replace('#', ''); // e.g., 'maturity', 'surrender', 'death'

            // Hide all report tables first
            hideAllReportTables();

            // Show the report table for the active tab if it was generated
            if (generatedReports[claimType]) {
                document.getElementById(`${claimType}-report-results`).style.display = 'block';
            }
        });
    });

    // Function to hide all report tables
    function hideAllReportTables() {
        document.getElementById('maturity-report-results').style.display = 'none';
        document.getElementById('surrender-report-results').style.display = 'none';
        document.getElementById('death-report-results').style.display = 'none';
    }
});