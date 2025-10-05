// Glossary Settings JavaScript
// Glossary management function

// Global variables
let glossariesData = null;
let updateCheckInterval = null;
let lastVersions = {};

// Initialize glossary settings module
async function initGlossaryModule() {
    console.log('[Glossary] Initializing glossary module...');
    
    try {
        // Set up event listeners
        setupEventListeners();
        
        // Load glossary data
        await loadGlossaries();
        
        // Render glossary list
        updateGlossariesUI();
        
        // Start update check
        startUpdateCheck();
        
        console.log('[Glossary] Glossary module initialized successfully');
    } catch (error) {
        console.error('[Glossary] Failed to initialize glossary module:', error);
        showError('Failed to initialize glossary module');
    }
}

// Set up event listeners
function setupEventListeners() {
    // Upload global glossary form
    const uploadGlobalForm = document.getElementById('uploadGlobalGlossaryForm');
    if (uploadGlobalForm) {
        uploadGlobalForm.addEventListener('submit', (e) => {
            e.preventDefault();
            uploadGlobalGlossary();
        });
    }
}

// Start update check
function startUpdateCheck() {
    // Check for updates every 30 seconds
    updateCheckInterval = setInterval(() => {
        checkForUpdates();
    }, 30000);
}

// Check for updates
async function checkForUpdates() {
    try {
        const response = await fetch('/auth/glossaries/check-updates', {
            method: 'GET',
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.has_updates) {
                await loadGlossaries();
                updateGlossariesUI();
                showUpdateNotification();
            }
        }
    } catch (error) {
        console.warn('Failed to check glossary updates:', error);
    }
}

// Load glossary data
async function loadGlossaries() {
    try {
        const response = await fetch('/auth/glossaries', {
            method: 'GET',
            credentials: 'include'
        });
        
        if (response.ok) {
            glossariesData = await response.json();
            lastVersions = glossariesData.versions;
            console.log('[Glossary] Loaded glossaries:', glossariesData);
        } else {
            console.error('[Glossary] Failed to load glossaries');
            glossariesData = null;
        }
    } catch (error) {
        console.error('[Glossary] Failed to load glossaries:', error);
        glossariesData = null;
    }
}

// Update glossary UI
function updateGlossariesUI() {
    const container = document.getElementById('globalGlossariesList');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (!glossariesData || !glossariesData.global_glossaries || glossariesData.global_glossaries.length === 0) {
        container.innerHTML = '<p class="text-muted mb-0" data-i18n="noGlobalGlossariesAvailable">No global glossaries available</p>';
        return;
    }
    
    glossariesData.global_glossaries.forEach(glossary => {
        const div = document.createElement('div');
        div.className = 'd-flex justify-content-between align-items-center mb-2 p-2 border rounded';
        div.innerHTML = `
            <div class="form-check">
                <input class="form-check-input" type="checkbox" value="${glossary.id}" id="glossary_${glossary.id}">
                <label class="form-check-label" for="glossary_${glossary.id}">
                    <strong>${glossary.name}</strong>
                    ${glossary.description ? `<br><small class="text-muted">${glossary.description}</small>` : ''}
                </label>
            </div>
            <div class="btn-group btn-group-sm">
                <button type="button" class="btn btn-outline-info" onclick="downloadGlossary('${glossary.id}')" title="Download">
                    <i class="bi bi-download"></i>
                </button>
                <button type="button" class="btn btn-outline-danger" onclick="deleteGlossary('${glossary.id}')" title="Delete">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        `;
        container.appendChild(div);
    });
    
    // Set selected state
    if (glossariesData.user_selection && glossariesData.user_selection.selected_global_glossaries) {
        glossariesData.user_selection.selected_global_glossaries.forEach(glossaryId => {
            const checkbox = document.getElementById(`glossary_${glossaryId}`);
            if (checkbox) {
                checkbox.checked = true;
            }
        });
    }
    
    // Show/hide admin area
    const adminSection = document.getElementById('adminGlossarySection');
    if (adminSection) {
        // Here you can decide whether to show admin area based on user permissions
        // Temporarily show, should actually be determined by user role
        adminSection.style.display = 'block';
    }
}

// Glossary management function has been directly integrated into the page, no longer need modal


// Save glossary selection
async function saveGlossarySelection() {
    try {
        // Get selected glossaries
        const selectedGlossaries = [];
        const checkboxes = document.querySelectorAll('#globalGlossariesList input[type="checkbox"]:checked');
        checkboxes.forEach(checkbox => {
            selectedGlossaries.push(checkbox.value);
        });
        
        const response = await fetch('/auth/glossaries/selection', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                global_glossaries: selectedGlossaries,
                personal_glossaries: glossariesData?.user_selection?.personal_glossaries || []
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            showSuccess(result.message || 'Glossary selection saved');
            
            // Reload data
            await loadGlossaries();
            updateGlossariesUI();
        } else {
            const error = await response.json();
            showError(error.detail || 'Failed to save glossary selection');
        }
    } catch (error) {
        console.error('Failed to save glossary selection:', error);
        showError('Failed to save glossary selection');
    }
}

// Upload global glossary
async function uploadGlobalGlossary() {
    const name = document.getElementById('globalGlossaryName').value.trim();
    const file = document.getElementById('globalGlossaryFile').files[0];
    const description = document.getElementById('globalGlossaryDescription').value.trim();
    
    if (!name || !file) {
        showError('Please fill in glossary name and select file');
        return;
    }
    
    const formData = new FormData();
    formData.append('name', name);
    formData.append('file', file);
    formData.append('is_global', 'true'); // Mark as global glossary
    if (description) {
        formData.append('description', description);
    }
    
    try {
        const response = await fetch('/auth/glossaries/upload', {
            method: 'POST',
            credentials: 'include',
            body: formData
        });
        
        if (response.ok) {
            const result = await response.json();
            showSuccess(result.message || 'Glossary uploaded successfully');
            
            // Clear form
            document.getElementById('uploadGlobalGlossaryForm').reset();
            
            // Reload data
            await loadGlossaries();
            updateGlossariesUI();
        } else {
            const error = await response.json();
            showError(error.detail || 'Failed to upload glossary');
        }
    } catch (error) {
        console.error('Failed to upload glossary:', error);
        showError('Failed to upload glossary');
    }
}


// Download glossary
async function downloadGlossary(glossaryId) {
    try {
        const response = await fetch(`/auth/glossaries/${glossaryId}/download`, {
            method: 'GET',
            credentials: 'include'
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `glossary_${glossaryId}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            const error = await response.json();
            showError(error.detail || 'Failed to download glossary');
        }
    } catch (error) {
        console.error('Failed to download glossary:', error);
        showError('Failed to download glossary');
    }
}

// Delete glossary
async function deleteGlossary(glossaryId) {
    if (!confirm('Are you sure you want to delete this glossary?')) {
        return;
    }
    
    try {
        const response = await fetch(`/auth/glossaries/${glossaryId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (response.ok) {
            const result = await response.json();
            showSuccess(result.message || 'Glossary deleted successfully');
            
            // Reload data
            await loadGlossaries();
            updateGlossariesUI();
        } else {
            const error = await response.json();
            showError(error.detail || 'Failed to delete glossary');
        }
    } catch (error) {
        console.error('Failed to delete glossary:', error);
        showError('Failed to delete glossary');
    }
}

// Show update notification
function showUpdateNotification() {
    const notification = document.createElement('div');
    notification.className = 'alert alert-info alert-dismissible fade show position-fixed';
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999;';
    notification.innerHTML = `
        <i class="bi bi-info-circle me-2"></i>
        Glossary has been updated, page will refresh automatically
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Show success message
function showSuccess(message) {
    if (typeof showNotification === 'function') {
        showNotification(message, 'success');
    } else {
        alert(message);
    }
}

// Show error message
function showError(message) {
    if (typeof showNotification === 'function') {
        showNotification(message, 'error');
    } else {
        alert(message);
    }
}

// Export functions for global use
window.initGlossaryModule = initGlossaryModule;
window.saveGlossarySelection = saveGlossarySelection;
window.uploadGlobalGlossary = uploadGlobalGlossary;
window.downloadGlossary = downloadGlossary;
window.deleteGlossary = deleteGlossary;
