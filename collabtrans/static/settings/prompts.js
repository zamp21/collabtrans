// Prompts Settings JavaScript
// 简化的提示词管理功能

// 全局变量
let promptsData = [];

// 初始化提示词设置模块
async function initPromptsModule() {
    console.log('[Prompts] Initializing prompts module...');
    
    try {
        // 设置事件监听器
        setupEventListeners();
        
        // 加载提示词列表
        await loadPrompts();
        
        // 渲染提示词列表
        renderPromptList();
        
        console.log('[Prompts] Prompts module initialized successfully');
    } catch (error) {
        console.error('[Prompts] Failed to initialize prompts module:', error);
        showError('Failed to initialize prompts module');
    }
}

// 设置事件监听器
function setupEventListeners() {
    // 添加提示词表单事件
    const addPromptForm = document.getElementById('addPromptForm');
    if (addPromptForm) {
        addPromptForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await addPrompt();
        });
    }
}

// 加载提示词列表
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

// 刷新提示词列表
async function refreshPromptList() {
    try {
        // 重新加载提示词数据
        await loadPrompts();
        
        // 渲染提示词列表
        renderPromptList();
    } catch (error) {
        console.error('刷新提示词列表失败:', error);
        showError('Failed to refresh prompts');
    }
}

// 渲染提示词列表
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

// 添加新提示词
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
            
            // 清空表单
            document.getElementById('addPromptForm').reset();
            
            // 刷新提示词列表
            await refreshPromptList();
        } else {
            const error = await response.json();
            showError(error.detail || 'Failed to add prompt');
        }
    } catch (error) {
        console.error('添加提示词失败:', error);
        showError('Failed to add prompt');
    }
}

// 删除提示词
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
            
            // 刷新提示词列表
            await refreshPromptList();
        } else {
            const error = await response.json();
            showError(error.detail || 'Failed to delete prompt');
        }
    } catch (error) {
        console.error('删除提示词失败:', error);
        showError('Failed to delete prompt');
    }
}

// 显示成功消息
function showSuccess(message) {
    // 使用Bootstrap toast或简单的alert
    if (typeof showNotification === 'function') {
        showNotification(message, 'success');
    } else {
        alert(message);
    }
}

// 显示错误消息
function showError(message) {
    // 使用Bootstrap toast或简单的alert
    if (typeof showNotification === 'function') {
        showNotification(message, 'error');
    } else {
        alert(message);
    }
}

// 导出函数供全局使用
window.initPromptsModule = initPromptsModule;
window.addPrompt = addPrompt;
window.deletePrompt = deletePrompt;
window.refreshPromptList = refreshPromptList;
