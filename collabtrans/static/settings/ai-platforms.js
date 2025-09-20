// AI Platform Settings Module
// AI平台设置模块

let platformConfigs = {};

// Load platform information from configuration file
async function loadPlatformConfigs() {
  try {
    const resp = await fetch('/auth/app-config');
    if (!resp.ok) return;
    const cfg = await resp.json();
    
    // Read new ai_platforms structure
    const aiPlatforms = cfg.ai_platforms || {};
    
    // Build platform configuration object
    platformConfigs = {};
    for (const [key, platform] of Object.entries(aiPlatforms)) {
      platformConfigs[key] = {
        name: platform.name || '',
        url: platform.url || '',
        model: platform.model || '',
        maxTokens: platform.max_tokens || 4096,
        temperature: platform.temperature || 0.7
      };
    }
    
    // Update platform selection dropdown
    updatePlatformSelect();
  } catch (e) {
    console.error('Load platform configs error:', e);
  }
}

// Update platform selection dropdown
function updatePlatformSelect() {
  const select = document.getElementById('platformSelect');
  if (!select) return;
  
  // Clear existing options
  select.innerHTML = '';
  
  // Add options
  for (const [key, config] of Object.entries(platformConfigs)) {
    const option = document.createElement('option');
    option.value = key;
    option.textContent = config.name;
    select.appendChild(option);
  }
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
    const apiKey = secrets.platform_api_keys?.[platform];
    
    if (apiKey) {
      // If API Key exists, display masked version
      const maskedKey = apiKey.substring(0, 8) + '***';
      apiKeyInput.value = maskedKey;
      apiKeyInput.placeholder = window.SettingsCore ? window.SettingsCore.getText('savedApiKeyPlaceholder') : '已保存的API Key';
      // Ensure input type is password so masked display works properly
      apiKeyInput.type = 'password';
      
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
    }
  } catch (e) {
    console.error('Load API key error:', e);
    const apiKeyInput = document.getElementById('platformApiKey');
    apiKeyInput.value = '';
    apiKeyInput.placeholder = window.SettingsCore ? window.SettingsCore.getText('apiKeyPlaceholder') : 'sk-...';
    apiKeyInput.type = 'password';
  }
}

// Update platform fields
function updatePlatformFields() {
  const platform = document.getElementById('platformSelect').value;
  const config = platformConfigs[platform];
  if (!config) return;
  
  document.getElementById('platformName').value = config.name;
  document.getElementById('platformUrl').value = config.url;
  document.getElementById('modelName').value = config.model;
  document.getElementById('maxTokens').value = config.maxTokens;
  document.getElementById('temperature').value = config.temperature;
  
  // Reload current platform API Key
  loadApiKey(platform);
}

// Save AI platform configuration
async function saveAiPlatformConfig() {
  try {
    const platformType = document.getElementById('platformSelect').value;
    const platformName = document.getElementById('platformName').value;
    const platformUrl = document.getElementById('platformUrl').value;
    const apiKey = document.getElementById('platformApiKey').value;
    const modelName = document.getElementById('modelName').value;
    const maxTokens = parseInt(document.getElementById('maxTokens').value);
    const temperature = parseFloat(document.getElementById('temperature').value);

    // Build configuration structure (excluding API Key)
    const config = {
      ai_platforms: {
        [platformType]: {
          name: platformName,
          url: platformUrl,
          model: modelName,
          max_tokens: maxTokens,
          temperature: temperature
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
    if (apiKey && !apiKey.endsWith('***')) {
      const resp2 = await fetch('/auth/app-config/setting', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          key: 'platform_api_keys', 
          value: { [platformType]: apiKey } 
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
document.addEventListener('DOMContentLoaded', () => {
  // Load platform configurations
  loadPlatformConfigs();
  
  // Setup event listeners
  const platformSelect = document.getElementById('platformSelect');
  if (platformSelect) {
    platformSelect.addEventListener('change', updatePlatformFields);
  }
  
  const saveBtn = document.getElementById('saveAiPlatformBtn');
  if (saveBtn) {
    saveBtn.addEventListener('click', saveAiPlatformConfig);
  }
  
  const testBtn = document.getElementById('testAiPlatformBtn');
  if (testBtn) {
    testBtn.addEventListener('click', testAiPlatform);
  }
  
  // Initialize password toggle buttons
  if (window.SettingsCore) {
    window.SettingsCore.initTogglePasswordButtons();
  }
});

// Export functions for global access
window.saveAiPlatformConfig = saveAiPlatformConfig;
