// Parsing Engine Settings Module
// 解析引擎设置模块

let engineConfigs = {};

// Load engine configurations
async function loadEngineConfigs() {
  try {
    const resp = await fetch('/auth/app-config');
    if (!resp.ok) return;
    const cfg = await resp.json();
    const ts = (cfg.translator_settings || {});
    engineConfigs = ts.engines || {};

    // Update selection box: only show engines that need to be managed in settings (currently only mineru)
    const select = document.getElementById('engineSelect');
    if (select) {
      select.innerHTML = '';
      for (const [key, val] of Object.entries(engineConfigs)) {
        if (key !== 'mineru') continue; // Temporarily only open MinerU settings
        const opt = document.createElement('option');
        opt.value = key;
        opt.textContent = val.name || key;
        select.appendChild(opt);
      }
      // Select current global engine
      if (ts.convert_engine && select.querySelector(`option[value="${ts.convert_engine}"]`)) {
        select.value = ts.convert_engine;
      }
      // If current global selection is not mineru, but settings only shows mineru, then default to mineru for editing its configuration
      if (!select.value && select.querySelector('option[value="mineru"]')) {
        select.value = 'mineru';
      }
    }

    updateEngineFields();
    // Load MinerU API Key (masked display from sensitive configuration)
    await loadMineruApiKey();
  } catch (e) { 
    console.error('Load engine configs error:', e); 
  }
}

// Update engine fields
function updateEngineFields() {
  const key = document.getElementById('engineSelect').value || 'mineru';
  const cfg = engineConfigs[key] || {};
  document.getElementById('engineName').value = cfg.name || '';
  document.getElementById('engineApiUrl').value = cfg.api_url || '';

  // MinerU specific fields
  const mineruVisible = key === 'mineru';
  document.getElementById('mineruModelRow').style.display = mineruVisible ? 'block' : 'none';
  document.getElementById('mineruApiKeyRow').style.display = mineruVisible ? 'block' : 'none';
  if (mineruVisible) {
    document.getElementById('mineruModelVersion').value = cfg.model_version || (window.appConfig?.translator_settings?.mineru_model_version) || '';
  }

  // Whether to show api_url row: MinerU or configuration already contains api_url
  const showApi = mineruVisible || !!cfg.api_url;
  document.getElementById('engineApiUrlRow').style.display = showApi ? 'block' : 'none';
}

// Load MinerU API Key (masked display)
async function loadMineruApiKey() {
  try {
    const resp = await fetch('/auth/app-config/raw-secrets', { credentials: 'include' });
    if (!resp.ok) return;
    const secrets = await resp.json();
    const key = secrets.translator_mineru_token || '';
    const el = document.getElementById('mineruApiKey');
    if (!el) return;
    if (key) {
      el.value = key.substring(0, 8) + '***';
      el.type = 'password';
    } else {
      el.value = '';
      el.placeholder = 'sk-...';
      el.type = 'password';
    }
  } catch (e) {
    console.warn('Load MinerU API Key failed', e);
  }
}

// Save parsing engine configuration
async function saveParsingEngineConfig() {
  try {
    const key = document.getElementById('engineSelect').value || 'mineru';
    const name = document.getElementById('engineName').value.trim();
    const apiUrl = document.getElementById('engineApiUrl').value.trim();
    const mineruModelVersion = document.getElementById('mineruModelVersion').value.trim();
    const mineruApiKey = (document.getElementById('mineruApiKey').value || '').trim();

    // Update local engine configuration object
    engineConfigs[key] = engineConfigs[key] || {};
    engineConfigs[key].name = name || key;
    if (apiUrl) {
      engineConfigs[key].api_url = apiUrl;
    } else {
      delete engineConfigs[key].api_url;
    }
    if (key === 'mineru') {
      engineConfigs[key].model_version = mineruModelVersion || 'vlm';
    } else {
      delete engineConfigs[key].model_version;
    }

    // Combine translator_settings payload
    const payload = {
      translator_settings: {
        convert_engine: key,
        mineru_model_version: mineruModelVersion || 'vlm',
        code_ocr: (window.appConfig?.translator_settings?.code_ocr) || false,
        skip_translate: (window.appConfig?.translator_settings?.skip_translate) || false,
        engines: engineConfigs
      }
    };

    // Save non-sensitive configuration
    const resp = await fetch('/auth/app-config', {
      method: 'POST', 
      headers: { 'Content-Type': 'application/json' }, 
      credentials: 'include',
      body: JSON.stringify(payload)
    });
    if (!resp.ok) {
      const t = await resp.text();
      if (window.SettingsCore) {
        window.SettingsCore.showNotification(window.SettingsCore.getText('saveFailed') + ': ' + t, 'error');
      }
      return false;
    }

    // If there's plain text token input (not *** masked), save sensitive configuration separately
    if (mineruApiKey && !mineruApiKey.endsWith('***') && key === 'mineru') {
      const r2 = await fetch('/auth/app-config/setting', {
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        credentials: 'include',
        body: JSON.stringify({ key: 'translator_mineru_token', value: mineruApiKey })
      });
      if (!r2.ok) {
        const t2 = await r2.text();
        if (window.SettingsCore) {
          window.SettingsCore.showNotification(window.SettingsCore.getText('saveMineruApiKeyFailed') + ': ' + t2, 'error');
        }
        return false;
      }
    }

    // Success notification and refresh token display
    if (window.SettingsCore) {
      window.SettingsCore.showNotification(window.SettingsCore.getText('engineSettingsSaved'), 'success');
    }
    await loadEngineConfigs();
    return true;
  } catch (e) {
    console.error('Save parsing engine config error:', e);
    if (window.SettingsCore) {
      window.SettingsCore.showNotification(window.SettingsCore.getText('saveFailed') + ': ' + e.message, 'error');
    }
    return false;
  }
}

// Initialize parsing engine settings module
document.addEventListener('DOMContentLoaded', () => {
  // Load engine configurations
  loadEngineConfigs();
  
  // Setup event listeners
  const sel = document.getElementById('engineSelect');
  if (sel) sel.addEventListener('change', () => updateEngineFields());
  
  const saveBtn = document.getElementById('saveEngineBtn');
  if (saveBtn) saveBtn.addEventListener('click', saveParsingEngineConfig);
  
  // Initialize password toggle buttons
  if (window.SettingsCore) {
    window.SettingsCore.initTogglePasswordButtons();
  }
});

// Export functions for global access
window.saveParsingEngineConfig = saveParsingEngineConfig;
