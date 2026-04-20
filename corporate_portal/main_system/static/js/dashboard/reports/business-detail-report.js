let nbReportData = [];
let nbMetaData = {};

let rbReportData = [];
let rbMetaData = {};

// Columns to display in the table (same for both NB and RB)
const DISPLAY_COLUMNS = [
    { key: 'PolicyNo', label: 'Policy No' },
    { key: 'Name', label: 'Name' },
    { key: 'SA', label: 'Sum Assured' },
    { key: 'Premium', label: 'Premium' },
    { key: 'Term', label: 'Term' },
    { key: 'DOB', label: 'Date of Birth' },
    { key: 'NextDueDate', label: 'Next Due Date' },
    { key: 'MaturityDate', label: 'Maturity Date' },
    { key: 'Status', label: 'Status' },
];

document.addEventListener('DOMContentLoaded', function () {

    // Track which reports have been generated
    const generatedReports = {
        nb: false,
        rb: false,
    };

    // Inject static headers into both tables on page load
    ['nb', 'rb'].forEach(flag => {
        const thead = document.querySelector(`#${flag}-report-table thead tr`);
        if (thead) {
            thead.innerHTML = DISPLAY_COLUMNS.map(col => `<th>${col.label}</th>`).join('');
        }
    });

    // Attach submit handlers to both forms
    const forms = document.querySelectorAll('.business-form');
    forms.forEach(form => {
        form.addEventListener('submit', function (e) {
            e.preventDefault();

            const flag = this.getAttribute('data-flag');         // 'NB' or 'RB'
            const flagKey = flag.toLowerCase();                  // 'nb' or 'rb'
            const formData = new FormData(this);

            generateReport(flag, flagKey, formData);
        });
    });

    // -------------------------------------------------------------------------
    // Core fetch + render
    // -------------------------------------------------------------------------
    function generateReport(flag, flagKey, formData) {
        const generateBtn = document.getElementById(`${flagKey}-generate-btn`);
        const originalText = generateBtn.innerHTML;
        generateBtn.disabled = true;
        generateBtn.innerHTML = '<span class="spinner"></span> Generating...';

        const reportResults = document.getElementById(`${flagKey}-report-results`);

        const requestData = {
            group_id: formData.get('group_id'),
            flag: flag,
            filter_by: formData.get('filter_by'),
            from_date: formData.get('from_date_ad'),
            to_date: formData.get('to_date_ad'),
        };

        fetch('/api/corporate/reports/group-business-detail/', {
            method: 'POST',
            body: JSON.stringify(requestData),
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
            },
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {

                // Store full response for download
                if (flagKey === 'nb') {
                    nbReportData = data;
                    nbMetaData = {
                        from_date: requestData.from_date,
                        to_date: requestData.to_date,
                        group_id: requestData.group_id,
                        filter_by: requestData.filter_by,
                    };
                } else {
                    rbReportData = data;
                    rbMetaData = {
                        from_date: requestData.from_date,
                        to_date: requestData.to_date,
                        group_id: requestData.group_id,
                        filter_by: requestData.filter_by,
                    };
                }

                populateTable(flagKey, data);

                reportResults.style.display = 'block';
                generatedReports[flagKey] = true;

                document.getElementById(`${flagKey}-download-btn`).disabled = false;

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

                alert(`Error generating ${flag} report: ${error.message}`);
            })
            .finally(() => {
                generateBtn.disabled = false;
                generateBtn.innerHTML = originalText;
            });
    }

    // -------------------------------------------------------------------------
    // Table population — hardcoded 9 columns
    // -------------------------------------------------------------------------
    function populateTable(flagKey, data) {
        const tbody = document.getElementById(`${flagKey}-report-tbody`);
        tbody.innerHTML = '';

        if (!data || data.length === 0) {
            const colspan = DISPLAY_COLUMNS.length;
            tbody.innerHTML = `<tr><td colspan="${colspan}" class="text-center">No data found</td></tr>`;
            return;
        }

        data.forEach(item => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${item.PolicyNo || '-'}</td>
                <td>${item.Name || '-'}</td>
                <td>${formatCurrency(item.SA ?? 0)}</td>
                <td>${formatCurrency(parseFloat(item.Premium) || 0)}</td>
                <td>${item.Term ?? '-'}</td>
                <td>${item.DOB || '-'}</td>
                <td>${item.NextDueDate || '-'}</td>
                <td>${item.MaturityDate || '-'}</td>
                <td>${item.Status || '-'}</td>
            `;
            tbody.appendChild(row);
        });

        initializeDataTable(flagKey);
    }

    // -------------------------------------------------------------------------
    // DataTable initialisation
    // -------------------------------------------------------------------------
    function initializeDataTable(flagKey) {
        const tableId = `${flagKey}-report-table`;

        if (typeof $ === 'undefined' || typeof $.fn.DataTable === 'undefined') {
            return;
        }

        if ($.fn.DataTable.isDataTable(`#${tableId}`)) {
            $(`#${tableId}`).DataTable().destroy();
        }

        $(`#${tableId}`).DataTable({
            responsive: true,
            pageLength: 10,
            lengthMenu: [[10, 25, 50, -1], [10, 25, 50, 'All']],
            dom:
                '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>' +
                '<"row"<"col-sm-12"tr>>' +
                '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
            language: {
                lengthMenu: 'Show _MENU_ entries',
                search: 'Search:',
                info: 'Showing _START_ to _END_ of _TOTAL_ entries',
                paginate: {
                    first: 'First',
                    last: 'Last',
                    next: 'Next',
                    previous: 'Previous',
                },
            },
        });
    }

    // -------------------------------------------------------------------------
    // Download handlers — dumps full API response as CSV
    // -------------------------------------------------------------------------
    document.getElementById('nb-download-btn').addEventListener('click', function () {
        const meta = nbMetaData;
        const filename = `nb_business_report_${meta.group_id}_${meta.from_date}_to_${meta.to_date}.csv`;
        downloadCSV(nbReportData, filename);
    });

    document.getElementById('rb-download-btn').addEventListener('click', function () {
        const meta = rbMetaData;
        const filename = `rb_business_report_${meta.group_id}_${meta.from_date}_to_${meta.to_date}.csv`;
        downloadCSV(rbReportData, filename);
    });

    // -------------------------------------------------------------------------
    // Tab switching — show/hide result tables outside the main card
    // -------------------------------------------------------------------------
    const tabButtons = document.querySelectorAll('[data-bs-toggle="tab"]');
    tabButtons.forEach(button => {
        button.addEventListener('shown.bs.tab', function (event) {
            const targetId = event.target.getAttribute('data-bs-target'); // e.g. '#nb'
            const flagKey = targetId.replace('#', '');                   // 'nb' or 'rb'

            hideAllReportTables();

            if (generatedReports[flagKey]) {
                document.getElementById(`${flagKey}-report-results`).style.display = 'block';
            }
        });
    });

    function hideAllReportTables() {
        document.getElementById('nb-report-results').style.display = 'none';
        document.getElementById('rb-report-results').style.display = 'none';
    }
});