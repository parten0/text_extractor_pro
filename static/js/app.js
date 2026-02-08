// ===== State Management =====
const state = {
    selectedFiles: [],
    currentJobId: null,
    jobs: [],
    refreshInterval: null
};

// ===== DOM Elements =====
const elements = {
    // Upload elements
    uploadArea: document.getElementById('uploadArea'),
    fileInput: document.getElementById('fileInput'),
    browseBtn: document.getElementById('browseBtn'),
    fileList: document.getElementById('fileList'),
    uploadActions: document.getElementById('uploadActions'),
    uploadBtn: document.getElementById('uploadBtn'),
    clearBtn: document.getElementById('clearBtn'),
    processingStatus: document.getElementById('processingStatus'),
    statusTitle: document.getElementById('statusTitle'),
    statusMessage: document.getElementById('statusMessage'),
    progressFill: document.getElementById('progressFill'),
    progressText: document.getElementById('progressText'),

    // History elements
    historyLoading: document.getElementById('historyLoading'),
    historyEmpty: document.getElementById('historyEmpty'),
    historyList: document.getElementById('historyList')
};

// ===== API Configuration =====
const API_BASE = '/api';
const REFRESH_INTERVAL = 2000;

// ===== Upload Functionality =====
function initUpload() {
    // Browse button
    elements.browseBtn.addEventListener('click', () => {
        elements.fileInput.click();
    });

    // File input change
    elements.fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });

    // Drag and drop
    elements.uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        elements.uploadArea.classList.add('drag-over');
    });

    elements.uploadArea.addEventListener('dragleave', () => {
        elements.uploadArea.classList.remove('drag-over');
    });

    elements.uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        elements.uploadArea.classList.remove('drag-over');
        handleFiles(e.dataTransfer.files);
    });

    // Click to browse
    elements.uploadArea.addEventListener('click', (e) => {
        if (e.target === elements.uploadArea || e.target.closest('.upload-icon, h3, p')) {
            elements.fileInput.click();
        }
    });

    // Upload button
    elements.uploadBtn.addEventListener('click', uploadFiles);

    // Clear button
    elements.clearBtn.addEventListener('click', clearFiles);
}

function handleFiles(files) {
    const pdfFiles = Array.from(files).filter(file => file.name.toLowerCase().endsWith('.pdf'));

    if (pdfFiles.length === 0) {
        alert('Please select PDF files only');
        return;
    }

    state.selectedFiles = pdfFiles;
    renderFileList();
}

function renderFileList() {
    if (state.selectedFiles.length === 0) {
        elements.fileList.classList.add('hidden');
        elements.uploadActions.classList.add('hidden');
        return;
    }

    elements.fileList.classList.remove('hidden');
    elements.uploadActions.classList.remove('hidden');

    elements.fileList.innerHTML = state.selectedFiles.map((file, index) => `
        <div class="file-item fade-in">
            <div class="file-info">
                <div class="file-icon">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" stroke="currentColor" stroke-width="2"/>
                        <path d="M14 2v6h6M10 13h4M10 17h4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                    </svg>
                </div>
                <div class="file-details">
                    <div class="file-name">${file.name}</div>
                    <div class="file-size">${formatFileSize(file.size)}</div>
                </div>
            </div>
            <button class="remove-file" onclick="removeFile(${index})">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <path d="M5 5l10 10M15 5l-10 10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
            </button>
        </div>
    `).join('');
}

function removeFile(index) {
    state.selectedFiles.splice(index, 1);
    renderFileList();
}

function clearFiles() {
    state.selectedFiles = [];
    elements.fileInput.value = '';
    renderFileList();
}

async function uploadFiles() {
    if (state.selectedFiles.length === 0) return;

    const formData = new FormData();
    state.selectedFiles.forEach(file => {
        formData.append('files', file);
    });

    // Hide upload UI, show processing
    elements.uploadArea.classList.add('hidden');
    elements.fileList.classList.add('hidden');
    elements.uploadActions.classList.add('hidden');
    elements.processingStatus.classList.remove('hidden');

    try {
        const response = await fetch(`${API_BASE}/upload`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error('Upload failed');
        }

        const data = await response.json();
        state.currentJobId = data.job_id;

        // Start monitoring this job
        startJobMonitoring();

    } catch (error) {
        console.error('Upload error:', error);
        alert('Upload failed. Please try again.');
        resetUploadUI();
    }
}

function startJobMonitoring() {
    // Fetch jobs immediately to show the new job
    fetchJobs();

    let errorCount = 0;
    const MAX_ERRORS = 3;

    const checkInterval = setInterval(async () => {
        if (!state.currentJobId) {
            clearInterval(checkInterval);
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/jobs/${state.currentJobId}/status`);

            if (!response.ok) {
                if (response.status === 404) {
                    console.error('Job not found, stopping monitoring');
                    clearInterval(checkInterval);
                    resetUploadUI();
                    return;
                }
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const job = await response.json();
            errorCount = 0; // Reset error count on success

            // Update processing status
            elements.statusTitle.textContent = job.status.charAt(0).toUpperCase() + job.status.slice(1);
            elements.statusMessage.textContent = job.message || 'Processing...';
            elements.progressFill.style.width = `${Math.round(job.progress * 100)}%`;
            elements.progressText.textContent = `${Math.round(job.progress * 100)}%`;

            if (job.status === 'completed' || job.status === 'failed') {
                clearInterval(checkInterval);
                setTimeout(resetUploadUI, 2000);
            }
        } catch (error) {
            console.error('Job monitoring error:', error);
            errorCount++;

            if (errorCount >= MAX_ERRORS) {
                console.error('Too many monitoring errors, stopping');
                clearInterval(checkInterval);
                alert('Lost connection to server. Please check processing history for updates.');
                resetUploadUI();
            }
        }
    }, 1000);
}

function resetUploadUI() {
    state.currentJobId = null;
    state.selectedFiles = [];
    elements.fileInput.value = '';

    elements.processingStatus.classList.add('hidden');
    elements.uploadArea.classList.remove('hidden');
    renderFileList();
}

// ===== History Functionality =====
async function fetchJobs() {
    try {
        const response = await fetch(`${API_BASE}/jobs`);

        if (!response.ok) {
            // If we get a 404 or error, show empty state
            showEmptyHistory();
            return;
        }

        const data = await response.json();
        const newJobs = data.jobs || [];

        // Update state and UI
        updateJobsSelectively(newJobs);

    } catch (error) {
        console.error('Error fetching jobs:', error);
        showEmptyHistory();
    }
}

function showEmptyHistory() {
    elements.historyLoading.classList.add('hidden');
    elements.historyEmpty.classList.remove('hidden');
    elements.historyList.classList.add('hidden');
}

function updateJobsSelectively(newJobs) {
    const oldJobs = state.jobs;

    // Hide loading, show appropriate state
    elements.historyLoading.classList.add('hidden');

    if (newJobs.length === 0) {
        showEmptyHistory();
        return;
    }

    elements.historyEmpty.classList.add('hidden');
    elements.historyList.classList.remove('hidden');

    // Check if we need a full re-render
    if (oldJobs.length !== newJobs.length) {
        state.jobs = newJobs;
        renderJobs();
        return;
    }

    // Check for changes in active jobs
    const jobsToUpdate = [];
    for (const newJob of newJobs) {
        const oldJob = oldJobs.find(j => j.job_id === newJob.job_id);

        if (!oldJob) {
            state.jobs = newJobs;
            renderJobs();
            return;
        }

        const isActive = newJob.status === 'pending' ||
            newJob.status === 'uploading' ||
            newJob.status === 'processing';

        if (isActive) {
            if (oldJob.status !== newJob.status ||
                oldJob.progress !== newJob.progress ||
                oldJob.message !== newJob.message) {
                jobsToUpdate.push(newJob);
            }
        } else if (oldJob.status !== newJob.status) {
            jobsToUpdate.push(newJob);
        }
    }

    state.jobs = newJobs;

    if (jobsToUpdate.length > 0) {
        updateSpecificCards(jobsToUpdate);
    }
}

function updateSpecificCards(jobsToUpdate) {
    for (const job of jobsToUpdate) {
        const cardElement = document.querySelector(`[data-job-id="${job.job_id}"]`);
        if (cardElement) {
            const newCardHTML = createJobCardHTML(job);
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = newCardHTML;
            cardElement.replaceWith(tempDiv.firstElementChild);
        } else {
            renderJobs();
            break;
        }
    }
}

function renderJobs() {
    const sortedJobs = [...state.jobs].sort((a, b) => {
        return new Date(b.created_at) - new Date(a.created_at);
    });

    elements.historyList.innerHTML = sortedJobs.map(job => createJobCardHTML(job)).join('');
}

function createJobCardHTML(job) {
    const statusColor = getStatusColor(job.status);
    const statusIcon = getStatusIcon(job.status);
    const canDownload = job.status === 'completed';

    return `
        <div class="history-card fade-in" data-job-id="${job.job_id}">
            <div class="history-header">
                <div class="history-status" style="color: ${statusColor}">
                    ${statusIcon}
                    <span>${job.status}</span>
                </div>
            </div>
            
            <div class="history-details">
                <div class="history-detail">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                        <circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.5"/>
                        <path d="M8 4v4l2 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                    </svg>
                    <span>${formatTimestamp(job.created_at)}</span>
                </div>
                <div class="history-detail">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                        <path d="M4 2h8a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V4a2 2 0 012-2z" stroke="currentColor" stroke-width="1.5"/>
                        <path d="M6 6h4M6 9h4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                    </svg>
                    <span>${job.total_files} file${job.total_files !== 1 ? 's' : ''}</span>
                </div>
            </div>
            
            ${job.status === 'processing' || job.status === 'uploading' ? `
                <div class="history-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${Math.round(job.progress * 100)}%"></div>
                    </div>
                    <span class="progress-text">${Math.round(job.progress * 100)}%</span>
                </div>
            ` : ''}
            
            ${job.message ? `
                <div style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 1rem;">${job.message}</div>
            ` : ''}
            
            <div class="history-actions">
                ${canDownload ? `
                    <button class="btn-download" onclick="downloadCSV('${job.job_id}')">
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                            <path d="M8 2v8M5 7l3 3 3-3M2 12h12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                        <span>Download CSV</span>
                    </button>
                ` : `
                    <button class="btn-download" disabled>
                        <span>Processing...</span>
                    </button>
                `}
            </div>
        </div>
    `;
}

// ===== Utility Functions =====
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function formatTimestamp(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;

    const options = {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    };

    return date.toLocaleString('en-US', options);
}

function getStatusColor(status) {
    const colors = {
        'pending': '#f59e0b',
        'uploading': '#3b82f6',
        'processing': '#8b5cf6',
        'completed': '#22c55e',
        'failed': '#ef4444'
    };
    return colors[status] || '#6b7280';
}

function getStatusIcon(status) {
    const icons = {
        'pending': `<svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="2"/>
            <path d="M8 4v4l2 2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>`,
        'uploading': `<svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M8 2v8M4 6l4-4 4 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>`,
        'processing': `<div class="spinner" style="width: 16px; height: 16px; border-width: 2px;"></div>`,
        'completed': `<svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M3 8l3 3 7-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>`,
        'failed': `<svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>`
    };
    return icons[status] || icons['pending'];
}

function downloadCSV(jobId) {
    window.location.href = `${API_BASE}/jobs/${jobId}/download/csv`;
}

function startAutoRefresh() {
    fetchJobs();
    state.refreshInterval = setInterval(fetchJobs, REFRESH_INTERVAL);
}

function stopAutoRefresh() {
    if (state.refreshInterval) {
        clearInterval(state.refreshInterval);
        state.refreshInterval = null;
    }
}

// ===== Initialization =====
document.addEventListener('DOMContentLoaded', () => {
    initUpload();
    startAutoRefresh();
});

window.addEventListener('beforeunload', () => {
    stopAutoRefresh();
});

// ===== Global Functions =====
window.removeFile = removeFile;
window.downloadCSV = downloadCSV;
