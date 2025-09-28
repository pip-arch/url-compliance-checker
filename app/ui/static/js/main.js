document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const fileUpload = document.querySelector('.file-upload');
    const fileInput = document.getElementById('file-input');
    const filePlaceholder = document.getElementById('file-placeholder');
    const fileInfo = document.getElementById('file-info');
    const filenameEl = document.getElementById('filename');
    const removeFileBtn = document.getElementById('remove-file');
    const uploadForm = document.getElementById('upload-form');
    const batchListBody = document.getElementById('batch-list-body');
    const reportModal = document.getElementById('report-modal');
    const modalCloseBtns = document.querySelectorAll('.modal-close');
    const downloadReportBtn = document.getElementById('download-report');
    const tabBtns = document.querySelectorAll('.tab-btn');
    
    let currentReportId = null;
    
    // API endpoints
    const API_URL = '/api';
    const URLS_ENDPOINT = `${API_URL}/urls`;
    const REPORTS_ENDPOINT = `${API_URL}/reports`;
    
    // Initialize
    loadBatches();
    
    // File Upload Handling
    fileUpload.addEventListener('click', () => {
        fileInput.click();
    });
    
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            const file = e.target.files[0];
            if (file.type === 'text/csv' || file.name.endsWith('.csv')) {
                showFileInfo(file);
            } else {
                alert('Please select a CSV file.');
                fileInput.value = '';
            }
        }
    });
    
    fileUpload.addEventListener('dragover', (e) => {
        e.preventDefault();
        fileUpload.style.borderColor = 'var(--primary-color)';
    });
    
    fileUpload.addEventListener('dragleave', () => {
        fileUpload.style.borderColor = 'var(--border-color)';
    });
    
    fileUpload.addEventListener('drop', (e) => {
        e.preventDefault();
        fileUpload.style.borderColor = 'var(--border-color)';
        
        if (e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            if (file.type === 'text/csv' || file.name.endsWith('.csv')) {
                fileInput.files = e.dataTransfer.files;
                showFileInfo(file);
            } else {
                alert('Please select a CSV file.');
            }
        }
    });
    
    removeFileBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.value = '';
        hideFileInfo();
    });
    
    // Form Submission
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        if (!fileInput.files.length) {
            alert('Please select a CSV file to upload.');
            return;
        }
        
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        
        const description = document.getElementById('description').value;
        if (description) {
            formData.append('description', description);
        }
        
        try {
            uploadForm.querySelector('button[type="submit"]').disabled = true;
            uploadForm.querySelector('button[type="submit"]').innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading...';
            
            const response = await fetch(`${URLS_ENDPOINT}/upload`, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (response.ok) {
                alert(`Successfully uploaded URLs. Batch ID: ${data.batch_id}`);
                uploadForm.reset();
                hideFileInfo();
                loadBatches();
            } else {
                alert(`Error: ${data.detail || 'Failed to upload file.'}`);
            }
        } catch (error) {
            console.error('Error uploading file:', error);
            alert('An error occurred while uploading the file.');
        } finally {
            uploadForm.querySelector('button[type="submit"]').disabled = false;
            uploadForm.querySelector('button[type="submit"]').innerHTML = '<i class="fas fa-upload"></i> Upload and Process';
        }
    });
    
    // Tab Handling
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.dataset.tab;
            
            // Update active tab button
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Update active tab pane
            document.querySelectorAll('.tab-pane').forEach(pane => {
                pane.classList.remove('active');
            });
            document.getElementById(`${tabName}-tab`).classList.add('active');
        });
    });
    
    // Modal Handling
    modalCloseBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            reportModal.classList.remove('active');
        });
    });
    
    // Load Batches
    async function loadBatches() {
        try {
            const response = await fetch(`${URLS_ENDPOINT}/batches`);
            const data = await response.json();
            
            if (response.ok) {
                renderBatches(data.batches);
            } else {
                console.error('Failed to load batches:', data);
                batchListBody.innerHTML = `
                    <tr class="placeholder-row">
                        <td colspan="6">Failed to load batches. Please try again.</td>
                    </tr>
                `;
            }
        } catch (error) {
            console.error('Error loading batches:', error);
            batchListBody.innerHTML = `
                <tr class="placeholder-row">
                    <td colspan="6">Error loading batches. Please check your connection.</td>
                </tr>
            `;
        }
    }
    
    // Render Batches
    function renderBatches(batches) {
        if (!batches || batches.length === 0) {
            batchListBody.innerHTML = `
                <tr class="placeholder-row">
                    <td colspan="6">No batches found. Upload a CSV file to get started.</td>
                </tr>
            `;
            return;
        }
        
        batchListBody.innerHTML = batches.map(batch => `
            <tr>
                <td>${batch.id.substring(0, 8)}...</td>
                <td>${batch.description || '-'}</td>
                <td>${batch.processed_count}/${batch.url_count}</td>
                <td>
                    <span class="status-badge ${batch.status}">
                        ${batch.status}
                    </span>
                </td>
                <td>${new Date(batch.created_at).toLocaleString()}</td>
                <td>
                    <button class="btn-icon view-urls-btn" data-batch-id="${batch.id}" title="View URLs">
                        <i class="fas fa-link"></i>
                    </button>
                    <button class="btn-icon generate-report-btn" data-batch-id="${batch.id}" title="Generate Report">
                        <i class="fas fa-file-alt"></i>
                    </button>
                    <button class="btn-icon view-report-btn" data-batch-id="${batch.id}" title="View Report">
                        <i class="fas fa-chart-bar"></i>
                    </button>
                    <button class="btn-icon delete-batch-btn" data-batch-id="${batch.id}" title="Delete Batch">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `).join('');
        
        // Add event listeners to batch actions
        document.querySelectorAll('.view-urls-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const batchId = btn.dataset.batchId;
                window.location.href = `${URLS_ENDPOINT}/batches/${batchId}/urls`;
            });
        });
        
        document.querySelectorAll('.generate-report-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const batchId = btn.dataset.batchId;
                await generateReport(batchId);
            });
        });
        
        document.querySelectorAll('.view-report-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const batchId = btn.dataset.batchId;
                const reportId = `report-${batchId}`;
                await loadReport(reportId);
            });
        });
        
        document.querySelectorAll('.delete-batch-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const batchId = btn.dataset.batchId;
                if (confirm(`Are you sure you want to delete batch ${batchId}?`)) {
                    await deleteBatch(batchId);
                }
            });
        });
    }
    
    // Generate Report
    async function generateReport(batchId) {
        try {
            const response = await fetch(`${REPORTS_ENDPOINT}/generate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ batch_id: batchId })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                alert(`Report generation started. Report ID: ${data.report_id}`);
                loadBatches();
            } else {
                alert(`Error: ${data.detail || 'Failed to generate report.'}`);
            }
        } catch (error) {
            console.error('Error generating report:', error);
            alert('An error occurred while generating the report.');
        }
    }
    
    // Load Report
    async function loadReport(reportId) {
        try {
            const response = await fetch(`${REPORTS_ENDPOINT}/${reportId}`);
            
            if (!response.ok) {
                const errorData = await response.json();
                alert(`Error: ${errorData.detail || 'Failed to load report.'}`);
                return;
            }
            
            const reportData = await response.json();
            
            // Store current report ID for download button
            currentReportId = reportId;
            
            // Update summary counts
            document.querySelector('.summary-count.blacklist').textContent = reportData.blacklist_count;
            document.querySelector('.summary-count.whitelist').textContent = reportData.whitelist_count;
            document.querySelector('.summary-count.review').textContent = reportData.review_count;
            
            // Load URL reports for each category
            await Promise.all([
                loadUrlReports(reportId, 'blacklist'),
                loadUrlReports(reportId, 'whitelist'),
                loadUrlReports(reportId, 'review')
            ]);
            
            // Show the modal
            reportModal.classList.add('active');
            
        } catch (error) {
            console.error('Error loading report:', error);
            alert('An error occurred while loading the report.');
        }
    }
    
    // Load URL Reports
    async function loadUrlReports(reportId, category) {
        try {
            const response = await fetch(`${REPORTS_ENDPOINT}/${reportId}/urls?list_type=${category}`);
            
            if (!response.ok) {
                console.error(`Failed to load ${category} URLs`);
                return;
            }
            
            const data = await response.json();
            const urls = data.urls || [];
            
            const tableBody = document.getElementById(`${category}-body`);
            
            if (urls.length === 0) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="4">No URLs in this category.</td>
                    </tr>
                `;
                return;
            }
            
            tableBody.innerHTML = urls.map(url => {
                const confidence = url.ai_analysis ? url.ai_analysis.confidence.toFixed(2) : 'N/A';
                const issues = url.rule_matches.length > 0 ? 
                    url.rule_matches.map(match => match.rule_name).join(', ') : 
                    (url.ai_analysis && url.ai_analysis.compliance_issues.length > 0 ? 
                        url.ai_analysis.compliance_issues.join(', ') : 'None');
                
                if (category === 'whitelist') {
                    return `
                        <tr>
                            <td><a href="${url.url}" target="_blank">${url.url}</a></td>
                            <td>${confidence}</td>
                            <td>
                                <button class="btn-icon view-details-btn" data-url='${JSON.stringify(url)}'>
                                    <i class="fas fa-info-circle"></i>
                                </button>
                            </td>
                        </tr>
                    `;
                } else {
                    return `
                        <tr>
                            <td><a href="${url.url}" target="_blank">${url.url}</a></td>
                            <td>${confidence}</td>
                            <td>${issues}</td>
                            <td>
                                <button class="btn-icon view-details-btn" data-url='${JSON.stringify(url)}'>
                                    <i class="fas fa-info-circle"></i>
                                </button>
                            </td>
                        </tr>
                    `;
                }
            }).join('');
            
            // Add event listeners to detail buttons
            tableBody.querySelectorAll('.view-details-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const urlData = JSON.parse(btn.dataset.url);
                    showUrlDetails(urlData);
                });
            });
            
        } catch (error) {
            console.error(`Error loading ${category} URLs:`, error);
            document.getElementById(`${category}-body`).innerHTML = `
                <tr>
                    <td colspan="4">Error loading data. Please try again.</td>
                </tr>
            `;
        }
    }
    
    // Delete Batch
    async function deleteBatch(batchId) {
        try {
            const response = await fetch(`${URLS_ENDPOINT}/batches/${batchId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (response.ok) {
                alert(`Batch ${batchId} deleted successfully.`);
                loadBatches();
            } else {
                alert(`Error: ${data.detail || 'Failed to delete batch.'}`);
            }
        } catch (error) {
            console.error('Error deleting batch:', error);
            alert('An error occurred while deleting the batch.');
        }
    }
    
    // Download Report
    downloadReportBtn.addEventListener('click', () => {
        if (!currentReportId) {
            alert('No report is currently open.');
            return;
        }
        
        window.location.href = `${REPORTS_ENDPOINT}/download/${currentReportId}?format=csv`;
    });
    
    // Helper Functions
    function showFileInfo(file) {
        filePlaceholder.style.display = 'none';
        fileInfo.style.display = 'flex';
        filenameEl.textContent = file.name;
    }
    
    function hideFileInfo() {
        filePlaceholder.style.display = 'flex';
        fileInfo.style.display = 'none';
    }
    
    function showUrlDetails(url) {
        // This would show a modal with detailed information about the URL
        // For now, we'll just log it
        console.log('URL Details:', url);
        alert(`URL Details for ${url.url}:\n\nCategory: ${url.category}\nRule Matches: ${url.rule_matches.length}\nAI Analysis: ${url.ai_analysis ? url.ai_analysis.explanation : 'None'}`);
    }
    
    // Add CSS for status badges
    const style = document.createElement('style');
    style.textContent = `
        .status-badge {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.75rem;
            font-weight: bold;
            text-transform: uppercase;
        }
        
        .status-badge.pending {
            background-color: #ffeeba;
            color: #856404;
        }
        
        .status-badge.processing {
            background-color: #b8daff;
            color: #004085;
        }
        
        .status-badge.processed {
            background-color: #c3e6cb;
            color: #155724;
        }
        
        .status-badge.failed {
            background-color: #f5c6cb;
            color: #721c24;
        }
        
        .status-badge.skipped {
            background-color: #e2e3e5;
            color: #383d41;
        }
    `;
    document.head.appendChild(style);
}); 