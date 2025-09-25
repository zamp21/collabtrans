// Glossary Settings JavaScript
// 术语表管理功能

// 全局变量
let glossariesData = null;
let updateCheckInterval = null;
let lastVersions = {};

// 初始化术语表设置模块
async function initGlossaryModule() {
    console.log('[Glossary] Initializing glossary module...');
    
    try {
        // 设置事件监听器
        setupEventListeners();
        
        // 加载术语表数据
        await loadGlossaries();
        
        // 渲染术语表列表
        updateGlossariesUI();
        
        // 开始更新检查
        startUpdateCheck();
        
        console.log('[Glossary] Glossary module initialized successfully');
    } catch (error) {
        console.error('[Glossary] Failed to initialize glossary module:', error);
        showError('Failed to initialize glossary module');
    }
}

// 设置事件监听器
function setupEventListeners() {
    // 上传全局术语表表单
    const uploadGlobalForm = document.getElementById('uploadGlobalGlossaryForm');
    if (uploadGlobalForm) {
        uploadGlobalForm.addEventListener('submit', (e) => {
            e.preventDefault();
            uploadGlobalGlossary();
        });
    }
}

// 开始更新检查
function startUpdateCheck() {
    // 每30秒检查一次更新
    updateCheckInterval = setInterval(() => {
        checkForUpdates();
    }, 30000);
}

// 检查更新
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
        console.warn('检查术语表更新失败:', error);
    }
}

// 加载术语表数据
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

// 更新术语表UI
function updateGlossariesUI() {
    const container = document.getElementById('globalGlossariesList');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (!glossariesData || !glossariesData.global_glossaries || glossariesData.global_glossaries.length === 0) {
        container.innerHTML = '<p class="text-muted mb-0" data-i18n="noGlobalGlossariesAvailable">暂无可用全局术语表</p>';
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
                <button type="button" class="btn btn-outline-info" onclick="downloadGlossary('${glossary.id}')" title="下载">
                    <i class="bi bi-download"></i>
                </button>
                <button type="button" class="btn btn-outline-danger" onclick="deleteGlossary('${glossary.id}')" title="删除">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        `;
        container.appendChild(div);
    });
    
    // 设置选中状态
    if (glossariesData.user_selection && glossariesData.user_selection.global_glossaries) {
        glossariesData.user_selection.global_glossaries.forEach(glossaryId => {
            const checkbox = document.getElementById(`glossary_${glossaryId}`);
            if (checkbox) {
                checkbox.checked = true;
            }
        });
    }
    
    // 显示/隐藏管理员区域
    const adminSection = document.getElementById('adminGlossarySection');
    if (adminSection) {
        // 这里可以根据用户权限来决定是否显示管理员区域
        // 暂时显示，实际应该根据用户角色判断
        adminSection.style.display = 'block';
    }
}

// 术语表管理功能已直接集成到页面中，不再需要模态框


// 保存术语表选择
async function saveGlossarySelection() {
    try {
        // 获取选中的术语表
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
            showSuccess(result.message || '术语表选择已保存');
            
            // 重新加载数据
            await loadGlossaries();
            updateGlossariesUI();
        } else {
            const error = await response.json();
            showError(error.detail || '保存术语表选择失败');
        }
    } catch (error) {
        console.error('保存术语表选择失败:', error);
        showError('保存术语表选择失败');
    }
}

// 上传全局术语表
async function uploadGlobalGlossary() {
    const name = document.getElementById('globalGlossaryName').value.trim();
    const file = document.getElementById('globalGlossaryFile').files[0];
    const description = document.getElementById('globalGlossaryDescription').value.trim();
    
    if (!name || !file) {
        showError('请填写术语表名称并选择文件');
        return;
    }
    
    const formData = new FormData();
    formData.append('name', name);
    formData.append('file', file);
    formData.append('is_global', 'true'); // 标记为全局术语表
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
            showSuccess(result.message || '术语表上传成功');
            
            // 清空表单
            document.getElementById('uploadGlobalGlossaryForm').reset();
            
            // 重新加载数据
            await loadGlossaries();
            updateGlossariesUI();
        } else {
            const error = await response.json();
            showError(error.detail || '术语表上传失败');
        }
    } catch (error) {
        console.error('上传术语表失败:', error);
        showError('上传术语表失败');
    }
}


// 下载术语表
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
            showError(error.detail || '下载术语表失败');
        }
    } catch (error) {
        console.error('下载术语表失败:', error);
        showError('下载术语表失败');
    }
}

// 删除术语表
async function deleteGlossary(glossaryId) {
    if (!confirm('确定要删除这个术语表吗？')) {
        return;
    }
    
    try {
        const response = await fetch(`/auth/glossaries/${glossaryId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (response.ok) {
            const result = await response.json();
            showSuccess(result.message || '术语表删除成功');
            
            // 重新加载数据
            await loadGlossaries();
            updateGlossariesUI();
        } else {
            const error = await response.json();
            showError(error.detail || '删除术语表失败');
        }
    } catch (error) {
        console.error('删除术语表失败:', error);
        showError('删除术语表失败');
    }
}

// 显示更新通知
function showUpdateNotification() {
    const notification = document.createElement('div');
    notification.className = 'alert alert-info alert-dismissible fade show position-fixed';
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999;';
    notification.innerHTML = `
        <i class="bi bi-info-circle me-2"></i>
        术语表已更新，页面将自动刷新
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// 显示成功消息
function showSuccess(message) {
    if (typeof showNotification === 'function') {
        showNotification(message, 'success');
    } else {
        alert(message);
    }
}

// 显示错误消息
function showError(message) {
    if (typeof showNotification === 'function') {
        showNotification(message, 'error');
    } else {
        alert(message);
    }
}

// 导出函数供全局使用
window.initGlossaryModule = initGlossaryModule;
window.saveGlossarySelection = saveGlossarySelection;
window.uploadGlobalGlossary = uploadGlobalGlossary;
window.downloadGlossary = downloadGlossary;
window.deleteGlossary = deleteGlossary;
