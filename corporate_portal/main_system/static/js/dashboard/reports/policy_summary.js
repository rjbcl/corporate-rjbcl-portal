// policy-summary-report.js

$(document).ready(function() {
    let policySummaryData = null;
    let policyDetailsTable = null;

    $('#policy-summary-report-form').on('submit', function(e) {
        e.preventDefault();
        
        const policyNumber = $('#policy-number').val().trim();
        
        // Validate policy number
        if (!policyNumber) {
            alert('Please enter a policy number');
            return;
        }
        
        // Disable button and show loading state
        const $generateBtn = $('#generate-btn');
        const originalBtnText = $generateBtn.html();
        $generateBtn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-2"></span>Loading...');
        
        // Hide previous results and disable download button
        $('#policy-summary-container').hide();
        $('#download-policy-summary-btn').prop('disabled', true);
        
        // Make API request
        $.ajax({
            url: '/api/corporate/reports/policy-summary/',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            data: JSON.stringify({
                policy_no: policyNumber
            }),
            success: function(response) {
                policySummaryData = response;
                console.log('Policy Summary Data:', policySummaryData);
                
                if (policySummaryData && policySummaryData.length > 0) {
                    displayPolicySummary(policySummaryData);
                    // Enable download button
                    $('#download-policy-summary-btn').prop('disabled', false);
                } else {
                    alert('No policy found with the given policy number.');
                }
            },
            error: function(xhr) {
                console.error('Error:', xhr);
                
                let errorMessage = 'Failed to fetch policy summary';
                
                if (xhr.responseJSON && xhr.responseJSON.error) {
                    errorMessage = xhr.responseJSON.error;
                }
                
                alert(errorMessage);
            },
            complete: function() {
                // Re-enable button and restore original text
                $generateBtn.prop('disabled', false).html(originalBtnText);
            }
        });
    });
    
    // Handle download button click
    $('#download-policy-summary-btn').on('click', function() {
        if (!policySummaryData || policySummaryData.length === 0) {
            alert('No data to download. Please generate a report first.');
            return;
        }
        
        const policyNumber = $('#policy-number').val().trim();
        const timestamp = new Date().toISOString().slice(0, 10);
        const filename = `policy_summary_${policyNumber}_${timestamp}.csv`;
        
        downloadCSV(policySummaryData, filename);
    });
    
    function displayPolicySummary(dataArray) {
        // Use first record for basic information (should be same across all records)
        const firstRecord = dataArray[0];
        
        // Display basic information
        $('#display-policy-no').text(firstRecord.PolicyNo || '-');
        $('#display-branch').text(firstRecord.Branch || '-');
        $('#display-group-id').text(firstRecord.GroupId || '-');
        $('#display-name').text(firstRecord.Name || '-');
        $('#display-nep-name').text(firstRecord.NepName || '-');
        $('#display-dob').text(formatDate(firstRecord.DOB) || '-');
        $('#display-gender').text(firstRecord.Gender || '-');
        $('#display-occupation').text(firstRecord.Occupation || '-');
        $('#display-mobile').text(firstRecord.Mobile || '-');
        $('#display-email').text(firstRecord.Email || '-');
        $('#display-address').text(firstRecord.Address || '-');
        $('#display-district-id').text(firstRecord.DistrictID || '-');
        $('#display-ward-no').text(firstRecord.WardNo || '-');
        
        // Display family and nominee information
        $('#display-father-name').text(firstRecord.FatherName || '-');
        $('#display-mother-name').text(firstRecord.MotherName || '-');
        $('#display-nominee-name').text(firstRecord.NomineeName || '-');
        $('#display-nominee-relationship').text(firstRecord.NomineeRelationship || '-');
        $('#display-nominee-phone').text(firstRecord.NomineePhone || '-');
        $('#display-nominee-address').text(firstRecord.NomineeAddress || '-');
        
        // Display claim information if exists
        if (firstRecord.ClaimDate) {
            $('#display-claim-date').text(formatDate(firstRecord.ClaimDate));
            $('#claim-info-section').show();
        } else {
            $('#claim-info-section').hide();
        }
        
        // Display all policy details in table
        displayPolicyDetailsTable(dataArray);
        
        // Show the container first
        $('#policy-summary-container').show();
        
        // Scroll to results after showing the container
        setTimeout(function() {
            const container = $('#policy-summary-container');
            if (container.length) {
                $('html, body').animate({
                    scrollTop: container.offset().top - 100
                }, 500);
            }
        }, 100);
    }
    
    function displayPolicyDetailsTable(dataArray) {
        // Destroy existing DataTable if it exists
        if (policyDetailsTable) {
            policyDetailsTable.destroy();
        }
        
        // Clear existing table body
        $('#policy-details-tbody').empty();
        
        // Create table rows for all records
        let rows = '';
        dataArray.forEach(function(data) {
            rows += `
                <tr>
                    <td>${formatCurrency(data.Sumassured)}</td>
                    <td>${formatDate(data.DOC)}</td>
                    <td>${formatDate(data.PaidDate)}</td>
                    <td>${formatDate(data.FUP)}</td>
                    <td>${data.Term || '-'}</td>
                    <td>${formatCurrency(data.Premium)}</td>
                    <td>${data.Instalment || '-'}</td>
                    <td>${formatCurrency(data.PaidAmount)}</td>
                    <td>${formatDate(data.maturitydate)}</td>
                    <td>${getStatusBadge(data.PolicyStatus)}</td>
                    <td>${data.PolicyType || '-'}</td>
                </tr>
            `;
        });
        
        $('#policy-details-tbody').html(rows);
        
        // Initialize DataTable with proper configuration
        policyDetailsTable = $('#policy-details-table').DataTable({
            dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>' +
                 '<"row"<"col-sm-12"B>>' +
                 '<"row"<"col-sm-12"tr>>' +
                 '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
            buttons: [
                'copy', 'csv', 'excel', 'pdf', 'print'
            ],
            pageLength: 10,
            lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "All"]],
            responsive: true,
            order: [],
            language: {
                lengthMenu: "Show _MENU_ entries",
                info: "Showing _START_ to _END_ of _TOTAL_ entries",
                infoEmpty: "Showing 0 to 0 of 0 entries",
                infoFiltered: "(filtered from _MAX_ total entries)",
                search: "Search:",
                paginate: {
                    first: "First",
                    last: "Last",
                    next: "Next",
                    previous: "Previous"
                }
            }
        });
    }
    
    function downloadCSV(data, filename) {
        if (!data || data.length === 0) {
            alert('No data to download');
            return;
        }
        
        // Get all keys from the first object
        const headers = Object.keys(data[0]);
        
        // Create CSV header row
        let csv = headers.join(',') + '\n';
        
        // Add data rows
        data.forEach(row => {
            const values = headers.map(header => {
                const value = row[header];
                
                // Handle null/undefined
                if (value === null || value === undefined) {
                    return '';
                }
                
                // Convert to string and escape quotes
                const stringValue = String(value).replace(/"/g, '""');
                
                // Wrap in quotes if contains comma, newline, or quote
                if (stringValue.includes(',') || stringValue.includes('\n') || stringValue.includes('"')) {
                    return `"${stringValue}"`;
                }
                
                return stringValue;
            });
            
            csv += values.join(',') + '\n';
        });
        
        // Create blob and download
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        
        if (navigator.msSaveBlob) { // IE 10+
            navigator.msSaveBlob(blob, filename);
        } else {
            link.href = URL.createObjectURL(blob);
            link.download = filename;
            link.style.display = 'none';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    }
    
    function formatDate(dateString) {
        if (!dateString) return '-';
        
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-GB', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric'
            });
        } catch (e) {
            return dateString;
        }
    }
    
    function formatCurrency(amount) {
        if (!amount && amount !== 0) return '-';
        
        return new Intl.NumberFormat('en-NP', {
            style: 'currency',
            currency: 'NPR',
            minimumFractionDigits: 2
        }).format(amount);
    }
    
    function getStatusBadge(status) {
        if (!status) return '<span class="badge badge-secondary">Unknown</span>';
        
        const statusLower = status.toLowerCase();
        
        if (statusLower === 'a' || statusLower === 'i' || statusLower === 'h' ) {
            return `<span class="badge badge-success">${status}</span>`;
        } else if (statusLower === 'm') {
            return `<span class="badge badge-info">${status}</span>`;
        } else if (statusLower === 'c' || statusLower === 'cancel' || statusLower === 'u') {
            return `<span class="badge badge-danger">${status}</span>`;
        } else if (statusLower === 's' || statusLower === 't'|| statusLower === 'd') {
            return `<span class="badge badge-warning">${status}</span>`;
        } else {
            return `<span class="badge badge-secondary">${status}</span>`;
        }
    }
    
    // Helper function to get CSRF token
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
});