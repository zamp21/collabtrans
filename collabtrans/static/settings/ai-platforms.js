// AI Platform Settings Module
// AI platform settings module

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

  // Also update default platform dropdown with same options
  try {
    const defSel = document.getElementById('defaultPlatformSelect');
    if (defSel) {
      defSel.innerHTML = '';
      for (const [key, config] of Object.entries(platformConfigs)) {
        const option = document.createElement('option');
        option.value = key;
        option.textContent = config.name;
        defSel.appendChild(option);
      }
      // Preselect from config if available
      const respCfg = await fetch('/auth/app-config');
      if (respCfg.ok) {
        const cfg2 = await respCfg.json();
        const def = (cfg2.ai_platforms && cfg2.ai_platforms.default_platform) || cfg2.ai_platforms_default_platform || null;
        if (def && platformConfigs[def]) {
          defSel.value = def;
        } else if (!defSel.value && defSel.options.length > 0) {
          defSel.selectedIndex = 0;
        }
      }
    }
  } catch (e) {
    console.warn('[DEBUG] loadPlatformConfigs - defaultPlatformSelect init failed:', e);
  }
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

  // Ensure a default selection is made to avoid saving with empty platform
  try {
    if (!select.value || select.value === '') {
      // Prefer last used platform from localStorage
      const last = (typeof localStorage !== 'undefined') ? localStorage.getItem('translator_platform_type') : null;
      if (last && platformConfigs[last]) {
        select.value = last;
      } else if (platformConfigs['openai']) {
        // Fallback to openai if exists
        select.value = 'openai';
      } else if (select.options.length > 0) {
        // Fallback to first option
        select.selectedIndex = 0;
      }
    }
  } catch (_) {}

  // After ensuring a selection, update fields
  try { updatePlatformFields(); } catch (e) { console.warn('[DEBUG] updatePlatformSelect - updatePlatformFields failed:', e); }
  // Also bind change listener here to ensure dynamic content attaches even if init timing varies
  try {
    const platformSelect = document.getElementById('platformSelect');
    if (platformSelect && !platformSelect.__bindOnce) {
      platformSelect.addEventListener('change', () => {
        try { updatePlatformFields(); } catch (e) { console.warn('[DEBUG] platformSelect change -> updatePlatformFields failed:', e); }
        try { loadAiPlatformConfig && loadAiPlatformConfig(); } catch (_) {}
        // Rebind password toggle and ensure eye works with masked/real key dataset
        try {
          if (window.SettingsCore) window.SettingsCore.initTogglePasswordButtons();
          const btn = document.querySelector('[data-target="platformApiKey"]');
          const input = document.getElementById('platformApiKey');
          if (btn && input && !btn.__eyeFixBound) {
            btn.addEventListener('click', () => {
              const toShow = input.type === 'password';
              const real = input.dataset && input.dataset.realKey;
              const masked = input.dataset && input.dataset.maskedKey;
              if (toShow && real) {
                input.value = real;
              } else if (!toShow && masked) {
                input.value = masked;
              }
            });
            btn.__eyeFixBound = true;
          }
        } catch (_) {}
      });
      platformSelect.__bindOnce = true;
    }
  } catch (_) {}
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
    const resp = await fetch('/auth/app-config/raw-secrets', { credentials: 'include' });
    if (!resp.ok) return;
    const secrets = await resp.json();
    
    const apiKeyInput = document.getElementById('platformApiKey');
    const statusBadge = document.getElementById('platformApiKeyStatus');
    // Prioritize meta (new structure), fallback to old structure
    const meta = (secrets.platform_api_keys_meta && secrets.platform_api_keys_meta[platform]) || null;
    const apiKey = meta ? meta.key : (secrets.platform_api_keys?.[platform]);
    const isConfigured = meta ? !!meta.configured : !!apiKey;
    
    if (isConfigured && apiKey) {
      // If API Key exists, display masked version
      const maskedKey = apiKey.substring(0, 8) + '***';
      // Store real and masked key for eye-toggle reveal
      try {
        apiKeyInput.dataset.realKey = apiKey;
        apiKeyInput.dataset.maskedKey = maskedKey;
      } catch (_) {}
      apiKeyInput.value = maskedKey;
      apiKeyInput.placeholder = window.SettingsCore ? window.SettingsCore.getText('savedApiKeyPlaceholder') : 'Saved API Key';
      // Ensure input type is password so masked display works properly
      apiKeyInput.type = 'password';
      if (statusBadge) {
        statusBadge.classList.remove('bg-secondary');
        statusBadge.classList.add('bg-success');
        statusBadge.textContent = window.SettingsCore ? window.SettingsCore.getText('statusConfigured') : 'Configured';
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
      try {
        delete apiKeyInput.dataset.realKey;
        delete apiKeyInput.dataset.maskedKey;
      } catch (_) {}
      apiKeyInput.placeholder = window.SettingsCore ? window.SettingsCore.getText('apiKeyPlaceholder') : 'sk-...';
      apiKeyInput.type = 'password';
      if (statusBadge) {
        statusBadge.classList.remove('bg-success');
        statusBadge.classList.add('bg-secondary');
        statusBadge.textContent = window.SettingsCore ? window.SettingsCore.getText('statusNotConfigured') : 'Not configured';
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
      statusBadge.textContent = window.SettingsCore ? window.SettingsCore.getText('statusNotConfigured') : 'Not configured';
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
    
    let platformType = platformSelect.value;
    if (!platformType) {
      // Guard: if no selection, try recover a safe default to avoid wiping configs
      const last = (typeof localStorage !== 'undefined') ? localStorage.getItem('translator_platform_type') : null;
      if (last && platformConfigs[last]) {
        platformType = last;
        platformSelect.value = last;
      } else if (platformConfigs['openai']) {
        platformType = 'openai';
        platformSelect.value = 'openai';
      } else if (Object.keys(platformConfigs).length > 0) {
        platformType = Object.keys(platformConfigs)[0];
        platformSelect.value = platformType;
      } else {
        throw new Error('No AI platforms available to save');
      }
      // Also同步展示字段
      try { updatePlatformFields(); } catch (_) {}
    }
    const platformNameValue = platformName?.value || '';
    const platformUrlValue = platformUrl?.value || '';
    const apiKeyValue = (apiKey?.value || '').trim();
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
      const resp = await fetch('/auth/app-config', { credentials: 'include' });
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
      credentials: 'include',
      body: JSON.stringify(config)
    });

    // If there is API Key, save separately to sensitive configuration
    if (apiKeyValue && !apiKeyValue.endsWith('***')) {
      console.log(`[DEBUG] saveAiPlatformConfig - saving API key for platform: ${platformType}`);
      
      // Get current API Keys, ensure not overwriting other platforms (prioritize new structure with meta)
      let currentApiKeys = {};
      try {
        const resp = await fetch('/auth/app-config/raw-secrets', { credentials: 'include' });
        if (resp.ok) {
          const secrets = await resp.json();
          if (secrets.platform_api_keys_meta && typeof secrets.platform_api_keys_meta === 'object') {
            currentApiKeys = secrets.platform_api_keys_meta;
          } else {
            // Fallback and normalize old structure
            const plain = secrets.platform_api_keys || {};
            currentApiKeys = {};
            Object.entries(plain).forEach(([p, v]) => {
              const keyStr = (typeof v === 'string') ? v : (v?.key || '');
              currentApiKeys[p] = { key: keyStr, configured: !!keyStr };
            });
          }
          console.log(`[DEBUG] saveAiPlatformConfig - current API keys:`, Object.keys(currentApiKeys));
        }
      } catch (error) {
        console.warn('[DEBUG] saveAiPlatformConfig - failed to get current API keys:', error);
      }
      
      // Only update current platform's API Key, preserve other platforms (new structure: {key, configured})
      currentApiKeys[platformType] = { key: apiKeyValue, configured: true };
      console.log(`[DEBUG] saveAiPlatformConfig - updated API keys:`, Object.keys(currentApiKeys));
      
      const resp2 = await fetch('/auth/app-config/setting', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
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
      // Save default platform if control exists
      try {
        const defSel = document.getElementById('defaultPlatformSelect');
        if (defSel && defSel.value) {
          // Prefer single-setting endpoint to avoid overwriting ai_platforms block accidentally
          await fetch('/auth/app-config/setting', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ key: 'ai_platforms_default_platform', value: defSel.value })
          });
        }
      } catch (e) { console.warn('[DEBUG] saveAiPlatformConfig - save default_platform failed:', e); }
      if (window.SettingsCore) {
        window.SettingsCore.showNotification(window.SettingsCore.getText('aiPlatformSettingsSaved'), 'success');
      }
      // Reload API Key display (masked version) and status
      await loadApiKey(platformType);
      // Sync current platform to backend user configuration for homepage reading
      try {
        await fetch('/auth/app-config/setting', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ key: 'translator_platform_type', value: platformType })
        });
        // Sync to local storage for homepage backup reading
        try { localStorage.setItem('translator_platform_type', platformType); } catch (e) {}
      } catch (e) {
        console.warn('[DEBUG] saveAiPlatformConfig - failed to sync translator_platform_type:', e);
      }
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
      credentials: 'include',
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
    
    // Fix: Ensure that after loading platform configuration, actively load the configuration information of the currently selected platform
    // Add a small delay here to ensure updatePlatformSelect completes before calling updatePlatformFields
    setTimeout(() => {
      updatePlatformFields();
      console.log('[DEBUG] initAiPlatformModule - actively loaded configuration of currently selected platform');
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
        // First remove any existing old event listeners
        const toggleButtons = document.querySelectorAll('.toggle-password');
        toggleButtons.forEach(button => {
          const newButton = button.cloneNode(true);
          button.parentNode.replaceChild(newButton, button);
        });
        
        // Re-initialize password toggle buttons
        window.SettingsCore.initTogglePasswordButtons();
        console.log('[DEBUG] initAiPlatformModule - password toggle buttons re-initialized');
        
        // Verify password toggle buttons are correctly initialized
        const newToggleButtons = document.querySelectorAll('.toggle-password');
        console.log('[DEBUG] initAiPlatformModule - found toggle buttons:', newToggleButtons.length);
        newToggleButtons.forEach((button, index) => {
          const targetId = button.getAttribute('data-target');
          const targetElement = document.getElementById(targetId);
          console.log(`[DEBUG] initAiPlatformModule - toggle button ${index}: target=${targetId}, element exists=${!!targetElement}`);
        });
      }
    }, 300);
    
    // Ensure AI Platform module area is visible
    const aiPlatformSection = document.getElementById('ai-platforms-section');
    if (aiPlatformSection) {
      // Remove active class from other modules
      const allSections = document.querySelectorAll('.settings-section');
      allSections.forEach(section => section.classList.remove('active'));
      
      // Add active class to AI Platform module
      aiPlatformSection.classList.add('active');
      
      // Update navigation link status
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

// Initialize AI platform settings module
function initAiPlatformModule() {
  console.log('Initializing AI platform settings module');
  
  // Apply i18n to the module content
  if (window.SettingsCore && window.SettingsCore.setLanguage) {
    try {
      window.SettingsCore.setLanguage(window.SettingsCore.currentLang || 'zh');
    } catch (e) {
      console.warn('[AI Platform][init] Failed to apply i18n:', e);
    }
  }
  
  // Load platform configurations
  loadPlatformConfigs();
  
  // Setup event listeners
  const saveAiPlatformBtn = document.getElementById('saveAiPlatformBtn');
  if (saveAiPlatformBtn) {
    saveAiPlatformBtn.addEventListener('click', () => saveAiPlatformConfig(false));
  }
}

// Export functions for global access
window.saveAiPlatformConfig = saveAiPlatformConfig;
window.initAiPlatformModule = initAiPlatformModule;
