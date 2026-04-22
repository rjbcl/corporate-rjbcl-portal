/**
 * CSV Export Utility
 * Handles downloading data as CSV files
 */

/**
 * Convert array of objects to CSV and trigger download
 * @param {Array} data
 * @param {string} filename 
 */
function downloadCSV(data, filename) {
    console.log("Download CSV called with:", { dataLength: data?.length, filename });
    
    // Validate data
    if (!data || data.length === 0) {
        alert('No data to download');
        return;
    }
    
    const policies = data;
    
    // Get all keys from the first policy object (column names)
    const headers = Object.keys(policies[0]);
    
    // Create CSV header row
    let csvContent = headers.join(',') + '\n';
    
    // Add data rows
    policies.forEach(policy => {
        const row = headers.map(header => {
            let value = policy[header];
            
            // Handle null/undefined
            if (value === null || value === undefined) {
                value = '';
            }
            
            // Convert to string
            value = String(value).trim();
            
            // Escape commas, quotes, and newlines for CSV
            if (value.includes(',') || value.includes('"') || value.includes('\n')) {
                value = '"' + value.replace(/"/g, '""') + '"';
            }
            
            return value;
        });
        
        csvContent += row.join(',') + '\n';
    });
    
    // Create blob and download
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Clean up
    URL.revokeObjectURL(url);
    
    console.log(`CSV downloaded: ${filename}`);
}

