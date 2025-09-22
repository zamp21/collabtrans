// AI Platform Settings Module
// AI平台设置模块

let platformConfigs = window.platformConfigs || {};

// Load platform information from configuration file
async function loadPlatformConfigs() {
  try {
    console.log('[DEBUG] loadPlatformConfigs - starting to load platform configs');
    const resp = await fetch('/auth/app-config');
    if (!resp.ok) {
      console.error('[DEBUG] loadPlatformConfigs - API response not ok:', resp.status, resp.statusText);
      return;
    }
    const cfg = await resp.json();
    console.log('[DEBUG] loadPlatformConfigs - received config:', cfg);
    
    // Read new ai_platforms structure
    const aiPlatforms = cfg.ai_platforms || {};
    console.log('[DEBUG] loadPlatformConfigs - ai_platforms:', aiPlatforms);
    
    // Build platform configuration object
    platformConfigs = {};
    for (const [key, platform] of Object.entries(aiPlatforms)) {
      platformConfigs[key] = {
        name: platform.name || '',
        url: platform.url || '',
        model: platform.model || '',
        maxTokens: platform.max_tokens || 4096,
        temperature: platform.temperature || 0.7,
        recommendedTokens: platform.recommended_tokens || null,
        performanceNote: platform.performance_note || null
      };
    }
    
    // Store in global scope to prevent re-declaration errors
    window.platformConfigs = platformConfigs;
    
    console.log('[DEBUG] loadPlatformConfigs - built platform configs:', platformConfigs);
    
    // Update platform selection dropdown
    updatePlatformSelect();
  } catch (e) {
    console.error('[DEBUG] loadPlatformConfigs - error:', e);
  }
}

// Update platform selection dropdown
function updatePlatformSelect() {
  console.log('[DEBUG] updatePlatformSelect - starting');
  const select = document.getElementById('platformSelect');
  console.log('[DEBUG] updatePlatformSelect - select element:', select);
  console.log('[DEBUG] updatePlatformSelect - platformConfigs:', platformConfigs);
  
  if (!select) {
    console.error('[DEBUG] updatePlatformSelect - select element not found');
    return;
  }
  
  // Clear existing options
  select.innerHTML = '';
  
  // Add options
  const platformCount = Object.keys(platformConfigs).length;
  console.log('[DEBUG] updatePlatformSelect - adding', platformCount, 'platforms');
  
  for (const [key, config] of Object.entries(platformConfigs)) {
    const option = document.createElement('option');
    option.value = key;
    option.textContent = config.name;
    select.appendChild(option);
    console.log('[DEBUG] updatePlatformSelect - added option:', key, '->', config.name);
  }
  
  console.log('[DEBUG] updatePlatformSelect - completed, total options:', select.options.length);
}

// Load AI platform configuration
async function loadAiPlatformConfig() {
  try {
    const resp = await fetch('/auth/app-config');
    if (!resp.ok) return;
    const cfg = await resp.json();
    
    // Get currently selected platform
    const currentPlatform = document.getElementById('platformSelect').value;
    
    // Load data from new configuration structure
    if (cfg.ai_platforms && cfg.ai_platforms[currentPlatform]) {
      const platformConfig = cfg.ai_platforms[currentPlatform];
      
      // Fill form fields
      document.getElementById('platformName').value = platformConfig.name || '';
      document.getElementById('platformUrl').value = platformConfig.url || '';
      document.getElementById('modelName').value = platformConfig.model || '';
      document.getElementById('maxTokens').value = platformConfig.max_tokens || 4096;
      document.getElementById('temperature').value = platformConfig.temperature || 0.7;
    } else {
      // If no configuration found, use default values
      document.getElementById('platformName').value = '';
      document.getElementById('platformUrl').value = '';
      document.getElementById('modelName').value = '';
      document.getElementById('modelName').placeholder = window.SettingsCore ? window.SettingsCore.getText('modelNamePlaceholder') : 'deepseek-chat';
      document.getElementById('maxTokens').value = 4096;
      document.getElementById('maxTokens').placeholder = window.SettingsCore ? window.SettingsCore.getText('maxTokensPlaceholder') : '4096';
      document.getElementById('temperature').value = 0.7;
      document.getElementById('temperature').placeholder = window.SettingsCore ? window.SettingsCore.getText('temperaturePlaceholder') : '0.7';
    }
    
    // Load API Key separately (from sensitive configuration)
    await loadApiKey(currentPlatform);
    
  } catch (e) {
    console.error('Load AI platform config error:', e);
  }
}

// Load API Key
async function loadApiKey(platform) {
  try {
    const resp = await fetch('/auth/app-config/raw-secrets');
    if (!resp.ok) return;
    const secrets = await resp.json();
    
    const apiKeyInput = document.getElementById('platformApiKey');
    const statusBadge = document.getElementById('platformApiKeyStatus');
    const apiKey = secrets.platform_api_keys?.[platform];
    
    if (apiKey) {
      // If API Key exists, display masked version
      const maskedKey = apiKey.substring(0, 8) + '***';
      apiKeyInput.value = maskedKey;
      apiKeyInput.placeholder = window.SettingsCore ? window.SettingsCore.getText('savedApiKeyPlaceholder') : 'Saved API Key';
      // Ensure input type is password so masked display works properly
      apiKeyInput.type = 'password';
      if (statusBadge) {
        statusBadge.classList.remove('bg-secondary');
        statusBadge.classList.add('bg-success');
        statusBadge.textContent = window.SettingsCore ? window.SettingsCore.getText('statusConfigured') : '已配置';
        statusBadge.setAttribute('data-i18n', 'statusConfigured');
      }
      
      // Update eye icon state
      const toggleButton = document.querySelector('[data-target="platformApiKey"]');
      if (toggleButton) {
        const icon = toggleButton.querySelector('i');
        if (icon) {
          icon.classList.remove('bi-eye');
          icon.classList.add('bi-eye-slash');
        }
      }
    } else {
      // If no API Key, clear input box
      apiKeyInput.value = '';
      apiKeyInput.placeholder = window.SettingsCore ? window.SettingsCore.getText('apiKeyPlaceholder') : 'sk-...';
      apiKeyInput.type = 'password';
      if (statusBadge) {
        statusBadge.classList.remove('bg-success');
        statusBadge.classList.add('bg-secondary');
        statusBadge.textContent = window.SettingsCore ? window.SettingsCore.getText('statusNotConfigured') : '未配置';
        statusBadge.setAttribute('data-i18n', 'statusNotConfigured');
      }
    }
  } catch (e) {
    console.error('Load API key error:', e);
    const apiKeyInput = document.getElementById('platformApiKey');
    apiKeyInput.value = '';
    apiKeyInput.placeholder = window.SettingsCore ? window.SettingsCore.getText('apiKeyPlaceholder') : 'sk-...';
    apiKeyInput.type = 'password';
    const statusBadge = document.getElementById('platformApiKeyStatus');
    if (statusBadge) {
      statusBadge.classList.remove('bg-success');
      statusBadge.classList.add('bg-secondary');
      statusBadge.textContent = window.SettingsCore ? window.SettingsCore.getText('statusNotConfigured') : '未配置';
      statusBadge.setAttribute('data-i18n', 'statusNotConfigured');
    }
  }
}

// Update platform fields
function updatePlatformFields() {
  const platformSelect = document.getElementById('platformSelect');
  if (!platformSelect) return;
  
  const platform = platformSelect.value;
  const config = platformConfigs[platform];
  if (!config) return;
  
  const platformNameEl = document.getElementById('platformName');
  const platformUrlEl = document.getElementById('platformUrl');
  const modelNameEl = document.getElementById('modelName');
  const maxTokensEl = document.getElementById('maxTokens');
  const temperatureEl = document.getElementById('temperature');
  const recommendedTokensEl = document.getElementById('recommendedTokens');
  const performanceNoteEl = document.getElementById('performanceNote');
  
  if (platformNameEl) platformNameEl.value = config.name;
  if (platformUrlEl) platformUrlEl.value = config.url;
  if (modelNameEl) modelNameEl.value = config.model;
  if (maxTokensEl) maxTokensEl.value = config.maxTokens;
  if (temperatureEl) temperatureEl.value = config.temperature;
  if (recommendedTokensEl) recommendedTokensEl.value = config.recommendedTokens || '';
  if (performanceNoteEl) performanceNoteEl.value = config.performanceNote || '';
  
  // Reload current platform API Key
  loadApiKey(platform);
}

// Save AI platform configuration
async function saveAiPlatformConfig() {
  try {
    console.log('[DEBUG] saveAiPlatformConfig - starting save process');
    
    // Check if all required elements exist
    const platformSelect = document.getElementById('platformSelect');
    const platformName = document.getElementById('platformName');
    const platformUrl = document.getElementById('platformUrl');
    const apiKey = document.getElementById('platformApiKey');
    const modelName = document.getElementById('modelName');
    const maxTokens = document.getElementById('maxTokens');
    const temperature = document.getElementById('temperature');
    const recommendedTokens = document.getElementById('recommendedTokens');
    const performanceNote = document.getElementById('performanceNote');
    
    console.log('[DEBUG] saveAiPlatformConfig - element checks:', {
      platformSelect: !!platformSelect,
      platformName: !!platformName,
      platformUrl: !!platformUrl,
      apiKey: !!apiKey,
      modelName: !!modelName,
      maxTokens: !!maxTokens,
      temperature: !!temperature,
      recommendedTokens: !!recommendedTokens,
      performanceNote: !!performanceNote
    });
    
    if (!platformSelect) {
      throw new Error('Platform select element not found');
    }
    
    const platformType = platformSelect.value;
    const platformNameValue = platformName?.value || '';
    const platformUrlValue = platformUrl?.value || '';
    const apiKeyValue = apiKey?.value || '';
    const modelNameValue = modelName?.value || '';
    const maxTokensValue = parseInt(maxTokens?.value || '4096');
    const temperatureValue = parseFloat(temperature?.value || '0.7');
    const recommendedTokensValue = recommendedTokens?.value ? parseInt(recommendedTokens.value) : null;
    const performanceNoteValue = performanceNote?.value || null;
    
    console.log('[DEBUG] saveAiPlatformConfig - values:', {
      platformType,
      platformNameValue,
      platformUrlValue,
      modelNameValue,
      maxTokensValue,
      temperatureValue,
      recommendedTokensValue,
      performanceNoteValue
    });

    // Get current platform configurations to avoid overwriting other platforms
    let currentPlatforms = {};
    try {
      const resp = await fetch('/auth/app-config');
      if (resp.ok) {
        const config = await resp.json();
        currentPlatforms = config.ai_platforms || {};
        console.log(`[DEBUG] saveAiPlatformConfig - current platforms:`, Object.keys(currentPlatforms));
      }
    } catch (error) {
      console.warn('[DEBUG] saveAiPlatformConfig - failed to get current platforms:', error);
    }

    // Build configuration structure (excluding API Key) - only update current platform
    const config = {
      ai_platforms: {
        ...currentPlatforms,  // Keep existing platforms
        [platformType]: {     // Update only current platform
          name: platformNameValue,
          url: platformUrlValue,
          model: modelNameValue,
          max_tokens: maxTokensValue,
          temperature: temperatureValue,
          recommended_tokens: recommendedTokensValue,
          performance_note: performanceNoteValue
        }
      }
    };

    // Save basic configuration
    const resp1 = await fetch('/auth/app-config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });

    // If there is API Key, save separately to sensitive configuration
    if (apiKeyValue && !apiKeyValue.endsWith('***')) {
      console.log(`[DEBUG] saveAiPlatformConfig - saving API key for platform: ${platformType}`);
      
      // 获取当前的API Keys，确保不覆盖其他平台
      let currentApiKeys = {};
      try {
        const resp = await fetch('/auth/app-config/raw-secrets');
        if (resp.ok) {
          const secrets = await resp.json();
          currentApiKeys = secrets.platform_api_keys || {};
          console.log(`[DEBUG] saveAiPlatformConfig - current API keys:`, Object.keys(currentApiKeys));
        }
      } catch (error) {
        console.warn('[DEBUG] saveAiPlatformConfig - failed to get current API keys:', error);
      }
      
      // 只更新当前平台的API Key，保留其他平台
      currentApiKeys[platformType] = apiKey;
      console.log(`[DEBUG] saveAiPlatformConfig - updated API keys:`, Object.keys(currentApiKeys));
      
      const resp2 = await fetch('/auth/app-config/setting', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          key: 'platform_api_keys', 
          value: currentApiKeys 
        })
      });
      if (!resp2.ok) {
        if (window.SettingsCore) {
          window.SettingsCore.showNotification(window.SettingsCore.getText('saveApiKeyFailed'), 'error');
        }
        return false;
      }
    }

    if (resp1.ok) {
      if (window.SettingsCore) {
        window.SettingsCore.showNotification(window.SettingsCore.getText('aiPlatformSettingsSaved'), 'success');
      }
      // Reload API Key display (masked version)
      await loadApiKey(platformType);
      return true;
    } else {
      const error = await resp1.text();
      if (window.SettingsCore) {
        window.SettingsCore.showNotification(window.SettingsCore.getText('saveFailed') + ': ' + error, 'error');
      }
      return false;
    }
  } catch (e) {
    console.error('Save AI platform config error:', e);
    if (window.SettingsCore) {
      window.SettingsCore.showNotification(window.SettingsCore.getText('saveFailed') + ': ' + e.message, 'error');
    }
    return false;
  }
}

// Test AI platform connection
async function testAiPlatform() {
  // Show test progress
  if (window.SettingsCore) {
    window.SettingsCore.showNotification(window.SettingsCore.getText('testingAiPlatformConnection'), 'info');
  }
  
  try {
    const resp = await fetch('/auth/test-ai-platform', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        platform_type: document.getElementById('platformSelect').value,
        base_url: document.getElementById('platformUrl').value,
        model_name: document.getElementById('modelName').value
      })
    });
    
    if (!resp.ok) {
      const errorText = await resp.text();
      if (window.SettingsCore) {
        window.SettingsCore.showNotification(window.SettingsCore.getText('testFailed') + ': HTTP ' + resp.status + ' - ' + errorText, 'error');
      }
      return;
    }
    
    const data = await resp.json();
    if (data.success) {
      if (window.SettingsCore) {
        window.SettingsCore.showNotification(window.SettingsCore.getText('aiPlatformConnectionTestSuccess'), 'success');
      }
    } else {
      if (window.SettingsCore) {
        window.SettingsCore.showNotification(window.SettingsCore.getText('testFailed') + ': ' + (data.error || window.SettingsCore.getText('unknownError')), 'error');
      }
    }
  } catch (e) {
    if (window.SettingsCore) {
      window.SettingsCore.showNotification(window.SettingsCore.getText('testException') + ': ' + e.message, 'error');
    }
  }
}

// Initialize AI platform settings module
function initAiPlatformModule() {
  console.log('[DEBUG] initAiPlatformModule - starting initialization');
  
  // Wait a bit for DOM elements to be available
  setTimeout(() => {
    // Load platform configurations
    loadPlatformConfigs();
    
    // 修复: 确保在加载平台配置后，主动加载当前选中平台的配置信息
    // 这里添加一个小延迟确保updatePlatformSelect完成后再调用updatePlatformFields
    setTimeout(() => {
      updatePlatformFields();
      console.log('[DEBUG] initAiPlatformModule -主动加载了当前选中平台的配置');
    }, 100);
    
    // Setup event listeners
    const platformSelect = document.getElementById('platformSelect');
    if (platformSelect) {
      platformSelect.addEventListener('change', updatePlatformFields);
      console.log('[DEBUG] initAiPlatformModule - platform select event listener added');
    } else {
      console.error('[DEBUG] initAiPlatformModule - platform select element not found');
    }
    
    const saveBtn = document.getElementById('saveAiPlatformBtn');
    if (saveBtn) {
      saveBtn.addEventListener('click', saveAiPlatformConfig);
      console.log('[DEBUG] initAiPlatformModule - save button event listener added');
    } else {
      console.error('[DEBUG] initAiPlatformModule - save button element not found');
    }
    
    const testBtn = document.getElementById('testAiPlatformBtn');
    if (testBtn) {
      testBtn.addEventListener('click', testAiPlatform);
      console.log('[DEBUG] initAiPlatformModule - test button event listener added');
    } else {
      console.error('[DEBUG] initAiPlatformModule - test button element not found');
    }
    
    // Initialize password toggle buttons after a delay to ensure DOM elements are ready
    setTimeout(() => {
      if (window.SettingsCore) {
        // 先移除可能存在的旧事件监听器
        const toggleButtons = document.querySelectorAll('.toggle-password');
        toggleButtons.forEach(button => {
          const newButton = button.cloneNode(true);
          button.parentNode.replaceChild(newButton, button);
        });
        
        // 重新初始化密码切换按钮
        window.SettingsCore.initTogglePasswordButtons();
        console.log('[DEBUG] initAiPlatformModule - password toggle buttons re-initialized');
        
        // 验证密码切换按钮是否正确初始化
        const newToggleButtons = document.querySelectorAll('.toggle-password');
        console.log('[DEBUG] initAiPlatformModule - found toggle buttons:', newToggleButtons.length);
        newToggleButtons.forEach((button, index) => {
          const targetId = button.getAttribute('data-target');
          const targetElement = document.getElementById(targetId);
          console.log(`[DEBUG] initAiPlatformModule - toggle button ${index}: target=${targetId}, element exists=${!!targetElement}`);
        });
      }
    }, 300);
    
    // 确保AI Platform模块区域可见
    const aiPlatformSection = document.getElementById('ai-platforms-section');
    if (aiPlatformSection) {
      // 移除其他模块的active类
      const allSections = document.querySelectorAll('.settings-section');
      allSections.forEach(section => section.classList.remove('active'));
      
      // 添加active类到AI Platform模块
      aiPlatformSection.classList.add('active');
      
      // 更新导航链接状态
      const allNavLinks = document.querySelectorAll('.settings-nav .nav-link');
      allNavLinks.forEach(link => link.classList.remove('active'));
      
      const aiPlatformNav = document.querySelector('[data-section="ai-platforms"]');
      if (aiPlatformNav) {
        aiPlatformNav.classList.add('active');
      }
      
      console.log('[DEBUG] initAiPlatformModule - AI Platform section made visible');
    }
    
    console.log('[DEBUG] initAiPlatformModule - initialization completed');
  }, 100);
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initAiPlatformModule);

// Also initialize when module is loaded dynamically
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initAiPlatformModule);
} else {
  // DOM is already ready, initialize immediately
  initAiPlatformModule();
}

// Export functions for global access
window.saveAiPlatformConfig = saveAiPlatformConfig;
window.initAiPlatformModule = initAiPlatformModule;
