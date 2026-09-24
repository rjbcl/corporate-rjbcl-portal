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

const SUMMARY_DISPLAY_COLUMNS = [
    { key: 'PolicyNo', label: 'Policy No' },
    { key: 'Name', label: 'Name' },
    { key: 'SA', label: 'Sum Assured' },
    { key: 'Premium', label: 'Premium' },
    { key: 'Term', label: 'Term' },
    { key: 'DOC', label: 'Date of Commencement' },
    { key: 'NextDueDate', label: 'Next Due Date' },
    { key: 'PolicyStatus', label: 'Policy Status' },
];

// Track which reports have been generated (shared across both script blocks below)
const generatedReports = {
    nb: false,
    rb: false,
    summary: false,
};

function hideAllReportTables() {
    document.getElementById('nb-report-results').style.display = 'none';
    document.getElementById('rb-report-results').style.display = 'none';
    document.getElementById('summary-report-results').style.display = 'none';
}

document.addEventListener('DOMContentLoaded', function () {

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

                hideAllReportTables();
                reportResults.style.display = 'block';   // show first
                populateTable(flagKey, data);            // then init
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
        const tableId = `${flagKey}-report-table`;
        const tbody = document.getElementById(`${flagKey}-report-tbody`);

        // Destroy existing DataTable FIRST (before touching the DOM)
        if ($.fn.DataTable.isDataTable(`#${tableId}`)) {
            $(`#${tableId}`).DataTable().destroy();
        }

        // Now clear tbody
        tbody.innerHTML = '';

        if (!data || data.length === 0) {
            const colspan = DISPLAY_COLUMNS.length;
            tbody.innerHTML = `<tr><td colspan="${colspan}" class="text-center">No data found</td></tr>`;
            return;
        }

        // Initialize DataTable with data as a JS array (NOT pre-rendered DOM rows).
        // deferRender: true only creates <tr> elements for the current page (10 rows),
        // not all 82K. This is what prevents the browser from crashing.
        $(`#${tableId}`).DataTable({
            data: data,
            columns: [
                { data: 'PolicyNo', defaultContent: '-' },
                { data: 'Name', defaultContent: '-' },
                { data: 'SA', defaultContent: 0, render: (d) => formatCurrency(d ?? 0) },
                { data: 'Premium', defaultContent: 0, render: (d) => formatCurrency(parseFloat(d) || 0) },
                { data: 'Term', defaultContent: '-' },
                { data: 'DOB', defaultContent: '-' },
                { data: 'NextDueDate', defaultContent: '-' },
                { data: 'MaturityDate', defaultContent: '-' },
                { data: 'Status', defaultContent: '-' },
            ],
            deferRender: true,
            autoWidth: true,
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
            const flagKey = targetId.replace('#', '');                   // 'nb', 'rb', or 'summary'

            hideAllReportTables();

            if (generatedReports[flagKey]) {
                document.getElementById(`${flagKey}-report-results`).style.display = 'block';
            }
        });
    });
});

// Group Summary Report Logic
$(document).ready(function () {
    let summaryReportTable = null;
    let summaryReportData = null;

    // Local helper functions so we don't rely on external files
    function formatSummaryDate(dateString) {
        if (!dateString) return '-';
        try {
            const date = new Date(dateString);
            if (isNaN(date.getTime())) return dateString;
            return date.toLocaleDateString('en-GB', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric'
            });
        } catch (e) {
            return dateString;
        }
    }

    function formatSummaryCurrency(amount) {
        if (amount === null || amount === undefined || isNaN(amount)) return '-';
        return new Intl.NumberFormat('en-NP', {
            style: 'currency',
            currency: 'NPR',
            minimumFractionDigits: 2
        }).format(amount);
    }

    $('#summary-report-form').on('submit', function (e) {
        e.preventDefault();

        const group_id = $('#summary-group-id').val();
        if (!group_id) {
            Swal.fire('Error', 'Please select a group.', 'error');
            return;
        }

        const $generateBtn = $('#summary-generate-btn');
        const originalBtnText = $generateBtn.html();
        $generateBtn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-2"></span>Loading...');

        hideAllReportTables();
        $('#summary-download-btn').prop('disabled', true);

        // NOTE: payload now sends a single generic date range (from_date/to_date)
        // plus filter_by ('DOC' or 'FUP') telling the backend which date field
        // that range applies to, instead of separate doc_*/fup_* ranges.
        const payload = {
            group_id: group_id,
            policystatus: $('#summary-status').val(),
            filter_by: $('#summary-filter-by').val(),
            from_date: $('#summary-from-date-ad').val(),
            to_date: $('#summary-to-date-ad').val()
        };

        $.ajax({
            url: '/api/corporate/reports/group-summary/',
            method: 'POST',
            timeout: 120000, // 2 minute timeout for large queries
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            data: JSON.stringify(payload),
            success: function (response) {
                summaryReportData = response;

                if (summaryReportData && summaryReportData.length > 0) {
                    displaySummaryTable(summaryReportData);
                    $('#summary-download-btn').prop('disabled', false);
                    generatedReports.summary = true;
                } else {
                    Swal.fire({
                        icon: 'warning',
                        title: 'No Data',
                        text: 'No records found for the selected filters.',
                    });
                }
            },
            error: function (xhr) {
                let errorMessage = 'Failed to generate report.';
                if (xhr.responseJSON && xhr.responseJSON.error) {
                    errorMessage = xhr.responseJSON.error;
                } else if (xhr.statusText === 'timeout') {
                    errorMessage = 'The request timed out. Try narrowing your date filters.';
                } else {
                    console.error("Summary Report Error:", xhr.responseText);
                }
                Swal.fire({
                    icon: 'error',
                    title: 'Error',
                    text: errorMessage,
                });
            },
            complete: function () {
                $generateBtn.prop('disabled', false).html(originalBtnText);
            }
        });
    });

    function displaySummaryTable(dataArray) {
        if (summaryReportTable) {
            summaryReportTable.destroy();
            $('#summary-report-tbody').empty();
            $('#summary-report-table thead tr').empty();
        }

        if (!dataArray || dataArray.length === 0) return;

        const columns = SUMMARY_DISPLAY_COLUMNS.map(({ key, label }) => {
            let colDef = { data: key, title: label, defaultContent: '-' };

            // Safe string check for formatting
            if (typeof key === 'string' && (key.toLowerCase().includes('date') || key === 'DOC' || key === 'NextDueDate' || key === 'DOB')) {
                colDef.render = function(data) { return formatSummaryDate(data); };
            } else if (key === 'SA' || key === 'Premium') {
                colDef.render = function(data) { return formatSummaryCurrency(data); };
            }

            return colDef;
        });

        // Initialize DataTable using the `data` array directly with `deferRender: true`
        summaryReportTable = $('#summary-report-table').DataTable({
            data: dataArray,
            columns: columns,
            deferRender: true,
            dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>' +
                '<"row"<"col-sm-12"B>>' +
                '<"row"<"col-sm-12"tr>>' +
                '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
            buttons: ['copy', 'csv', 'excel', 'pdf', 'print'],
            pageLength: 10,
            lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "All"]],
            responsive: true,
            order: [],
            language: {
                lengthMenu: "Show _MENU_ entries",
                info: "Showing _START_ to _END_ of _TOTAL_ entries",
                search: "Search:",
                paginate: {
                    first: "First", last: "Last", next: "Next", previous: "Previous"
                }
            }
        });

        $('#summary-report-results').show();

        setTimeout(function () {
            $('html, body').animate({
                scrollTop: $('#summary-report-results').offset().top - 100
            }, 500);
        }, 100);
    }

    // Summary Download Button
    $('#summary-download-btn').on('click', function () {
        if (!summaryReportData || summaryReportData.length === 0) {
            alert('No data to download. Please generate a report first.');
            return;
        }

        const groupId = $('#summary-group-id').val();
        const timestamp = new Date().toISOString().slice(0, 10);
        const filename = `group_summary_${groupId}_${timestamp}.csv`;

        downloadCSV(summaryReportData, filename);
    });
});