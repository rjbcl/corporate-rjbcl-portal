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

            console.log(`Generating ${claimType} claim report...`);
            console.log('Form Data:', Object.fromEntries(formData));

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

        // Make your API call here
        // Example:
        fetch(`/api/claims/${claimType}/report/`, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        })
        .then(response => response.json())
        .then(data => {
            // Populate the specific table for this claim type
            populateTable(claimType, data);
            
            // Show the specific report table
            reportResults.style.display = 'block';
            
            // Mark this report as generated
            generatedReports[claimType] = true;
            
            // Enable download button for this claim type
            document.getElementById(`${claimType}-download-btn`).disabled = false;

            // Scroll to the report
            setTimeout(() => {
                reportResults.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }, 100);
        })
        .catch(error => {
            console.error('Error:', error);
            alert(`Error generating ${claimType} report`);
        })
        .finally(() => {
            generateBtn.disabled = false;
            generateBtn.innerHTML = originalText;
        });

        // For now, just simulate the process with dummy data
        // Remove this setTimeout when you have real API
        setTimeout(() => {
            const dummyData = generateDummyData(claimType);
            populateTable(claimType, dummyData);
            reportResults.style.display = 'block';
            generatedReports[claimType] = true;
            document.getElementById(`${claimType}-download-btn`).disabled = false;
            generateBtn.disabled = false;
            generateBtn.innerHTML = originalText;

            // Scroll to the report
            setTimeout(() => {
                reportResults.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }, 100);
        }, 1500);
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
                    <td>${item.policy_no || '-'}</td>
                    <td>${item.employee_name || '-'}</td>
                    <td>${item.sum_assured || '-'}</td>
                    <td>${item.premium || '-'}</td>
                    <td>${item.maturity_date || '-'}</td>
                    <td>${item.days_to_maturity || '-'}</td>
                    <td>${item.term || '-'}</td>
                    <td>${item.status || '-'}</td>
                `;
            } else if (claimType === 'surrender') {
                row.innerHTML = `
                    <td>${item.policy_no || '-'}</td>
                    <td>${item.employee_name || '-'}</td>
                    <td>${item.sum_assured || '-'}</td>
                    <td>${item.premium || '-'}</td>
                    <td>${item.surrender_date || '-'}</td>
                    <td>${item.surrender_value || '-'}</td>
                    <td>${item.term || '-'}</td>
                    <td>${item.status || '-'}</td>
                `;
            } else if (claimType === 'death') {
                row.innerHTML = `
                    <td>${item.policy_no || '-'}</td>
                    <td>${item.employee_name || '-'}</td>
                    <td>${item.sum_assured || '-'}</td>
                    <td>${item.premium || '-'}</td>
                    <td>${item.death_date || '-'}</td>
                    <td>${item.claim_amount || '-'}</td>
                    <td>${item.term || '-'}</td>
                    <td>${item.status || '-'}</td>
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
            console.log('DataTables library not loaded');
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
    document.getElementById('maturity-download-btn').addEventListener('click', function() {
        downloadReport('maturity');
    });

    document.getElementById('surrender-download-btn').addEventListener('click', function() {
        downloadReport('surrender');
    });

    document.getElementById('death-download-btn').addEventListener('click', function() {
        downloadReport('death');
    });

    function downloadReport(claimType) {
        // Implement download functionality
        console.log(`Downloading ${claimType} report...`);
        
        // Example: Trigger download via API
        // window.location.href = `/api/claims/${claimType}/download/`;
        
        // Or use the DataTable export functionality
        if (typeof $ !== 'undefined' && typeof $.fn.DataTable !== 'undefined') {
            const table = $(`#${claimType}-report-table`).DataTable();
            if (table.button) {
                table.button('.buttons-excel').trigger();
            }
        }
    }

    // Generate dummy data for testing (REMOVE THIS WHEN YOU HAVE REAL API)
    function generateDummyData(claimType) {
        const dummyData = [];
        
        for (let i = 1; i <= 20; i++) {
            if (claimType === 'maturity') {
                dummyData.push({
                    policy_no: `POL-MAT-${1000 + i}`,
                    employee_name: `Employee ${i}`,
                    sum_assured: `Rs. ${50000 * i}`,
                    premium: `Rs. ${5000 * i}`,
                    maturity_date: `2025-0${Math.min(i, 9)}-15`,
                    days_to_maturity: `${30 * i}`,
                    term: `${10 + i} years`,
                    status: 'Active'
                });
            } else if (claimType === 'surrender') {
                dummyData.push({
                    policy_no: `POL-SUR-${2000 + i}`,
                    employee_name: `Employee ${i}`,
                    sum_assured: `Rs. ${45000 * i}`,
                    premium: `Rs. ${4500 * i}`,
                    surrender_date: `2025-0${Math.min(i, 9)}-20`,
                    surrender_value: `Rs. ${35000 * i}`,
                    term: `${8 + i} years`,
                    status: 'Surrendered'
                });
            } else if (claimType === 'death') {
                dummyData.push({
                    policy_no: `POL-DTH-${3000 + i}`,
                    employee_name: `Employee ${i}`,
                    sum_assured: `Rs. ${100000 * i}`,
                    premium: `Rs. ${10000 * i}`,
                    death_date: `2025-0${Math.min(i, 9)}-10`,
                    claim_amount: `Rs. ${100000 * i}`,
                    term: `${12 + i} years`,
                    status: 'Claimed'
                });
            }
        }
        
        return dummyData;
    }

    // No tab switching logic needed - tables persist within their own tab panes!
    // Each table is now part of its tab content, so Bootstrap handles the visibility automatically
    
    // However, since tables are now outside the main card, we need to show/hide them based on active tab
    const tabButtons = document.querySelectorAll('[data-bs-toggle="tab"]');
    tabButtons.forEach(button => {
        button.addEventListener('shown.bs.tab', function(event) {
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