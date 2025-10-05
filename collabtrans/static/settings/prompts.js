// Prompts Settings JavaScript
// Simplified prompt management function

// Global variables
let promptsData = [];

// Initialize prompts settings module
async function initPromptsModule() {
    console.log('[Prompts] Initializing prompts module...');
    
    try {
        // Set up event listeners
        setupEventListeners();
        
        // Load prompts list
        await loadPrompts();
        
        // Render prompts list
        renderPromptList();
        
        console.log('[Prompts] Prompts module initialized successfully');
    } catch (error) {
        console.error('[Prompts] Failed to initialize prompts module:', error);
        showError('Failed to initialize prompts module');
    }
}

// Set up event listeners
function setupEventListeners() {
    // Add prompt form events
    const addPromptForm = document.getElementById('addPromptForm');
    if (addPromptForm) {
        addPromptForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await addPrompt();
        });
    }
}

// Load prompts list
async function loadPrompts() {
    try {
        const response = await fetch('/auth/prompts/simple', {
            method: 'GET',
            credentials: 'include'
        });
        
        if (response.ok) {
            promptsData = await response.json();
            console.log('[Prompts] Loaded prompts:', promptsData);
        } else {
            console.error('[Prompts] Failed to load prompts');
            promptsData = [];
        }
    } catch (error) {
        console.error('[Prompts] Failed to load prompts:', error);
        promptsData = [];
    }
}

// Refresh prompts list
async function refreshPromptList() {
    try {
        // Reload prompts data
        await loadPrompts();
        
        // Render prompts list
        renderPromptList();
    } catch (error) {
        console.error('Failed to refresh prompts list:', error);
        showError('Failed to refresh prompts');
    }
}

// Render prompts list
function renderPromptList() {
    const container = document.getElementById('promptList');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (promptsData.length === 0) {
        container.innerHTML = '<p class="text-muted mb-0" data-i18n="noPromptsAvailable">No prompts available</p>';
        return;
    }
    
    promptsData.forEach((prompt, index) => {
        const div = document.createElement('div');
        div.className = 'd-flex justify-content-between align-items-start mb-3 p-3 border rounded';
        div.innerHTML = `
            <div class="flex-grow-1">
                <h6 class="mb-1">${prompt.name}</h6>
                <p class="mb-0 text-muted small">${prompt.content}</p>
            </div>
            <div class="btn-group btn-group-sm">
                <button type="button" class="btn btn-outline-danger" onclick="deletePrompt(${index})" title="Delete">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        `;
        container.appendChild(div);
    });
}

// Add new prompt
async function addPrompt() {
    const description = document.getElementById('newPromptDescription').value.trim();
    const content = document.getElementById('newPromptText').value.trim();
    
    if (!description || !content) {
        showError('Please fill in both prompt description and text');
        return;
    }
    
    try {
        const response = await fetch('/auth/prompts/simple', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                name: description,
                content: content
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            showSuccess(result.message || 'Prompt added successfully');
            
            // Clear form
            document.getElementById('addPromptForm').reset();
            
            // Refresh prompts list
            await refreshPromptList();
        } else {
            const error = await response.json();
            showError(error.detail || 'Failed to add prompt');
        }
    } catch (error) {
        console.error('Failed to add prompt:', error);
        showError('Failed to add prompt');
    }
}

// Delete prompt
async function deletePrompt(index) {
    if (!confirm('Are you sure you want to delete this prompt?')) {
        return;
    }
    
    const prompt = promptsData[index];
    if (!prompt) {
        showError('Prompt not found');
        return;
    }
    
    try {
        const response = await fetch(`/auth/prompts/simple/${prompt.id}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (response.ok) {
            const result = await response.json();
            showSuccess(result.message || 'Prompt deleted successfully');
            
            // Refresh prompts list
            await refreshPromptList();
        } else {
            const error = await response.json();
            showError(error.detail || 'Failed to delete prompt');
        }
    } catch (error) {
        console.error('Failed to delete prompt:', error);
        showError('Failed to delete prompt');
    }
}

// Show success message
function showSuccess(message) {
    // Use Bootstrap toast or simple alert
    if (typeof showNotification === 'function') {
        showNotification(message, 'success');
    } else {
        alert(message);
    }
}

// Show error message
function showError(message) {
    // Use Bootstrap toast or simple alert
    if (typeof showNotification === 'function') {
        showNotification(message, 'error');
    } else {
        alert(message);
    }
}

// Export functions for global use
window.initPromptsModule = initPromptsModule;
window.addPrompt = addPrompt;
window.deletePrompt = deletePrompt;
window.refreshPromptList = refreshPromptList;
