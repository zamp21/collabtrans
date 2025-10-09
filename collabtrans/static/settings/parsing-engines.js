// Parsing Engine Settings Module
// Parsing engine settings module

let engineConfigs = {};

// Load engine configurations
async function loadEngineConfigs() {
  try {
    const resp = await fetch('/auth/app-config');
    if (!resp.ok) {
      return;
    }
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
      // Ensure MinerU settings are displayed by default
      if (select.value === 'mineru') {
        updateEngineFields();
      }
    }

    updateEngineFields();
    // Load MinerU API Key (masked display from sensitive configuration)
    await loadMineruApiKey();
    
    // Force display MinerU settings to ensure users can see API Key configuration
    const mineruApiKeyRow = document.getElementById('mineruApiKeyRow');
    if (mineruApiKeyRow) {
      mineruApiKeyRow.style.display = 'block';
    } else {
    }
  } catch (e) { 
    console.error('Load engine configs error:', e); 
  }
}

// Update engine fields
function updateEngineFields() {
  const select = document.getElementById('engineSelect');
  const key = select ? select.value || 'mineru' : 'mineru';
  const cfg = engineConfigs[key] || {};
  
  
  const engineNameEl = document.getElementById('engineName');
  if (engineNameEl) {
    engineNameEl.value = cfg.name || '';
  }
  
  const engineApiUrlEl = document.getElementById('engineApiUrl');
  if (engineApiUrlEl) {
    engineApiUrlEl.value = cfg.api_url || '';
  }

  // MinerU specific fields
  const mineruVisible = key === 'mineru';
  const mineruModelRow = document.getElementById('mineruModelRow');
  const mineruApiKeyRow = document.getElementById('mineruApiKeyRow');
  
  if (mineruModelRow) {
    mineruModelRow.style.display = mineruVisible ? 'block' : 'none';
  }
  
  if (mineruApiKeyRow) {
    mineruApiKeyRow.style.display = mineruVisible ? 'block' : 'none';
  }
  
  if (mineruVisible) {
    const modelVersionEl = document.getElementById('mineruModelVersion');
    if (modelVersionEl) {
      modelVersionEl.value = cfg.model_version || (window.appConfig?.translator_settings?.mineru_model_version) || '';
    }
    const testBtn = document.getElementById('testMineruBtn');
    const statusBadge = document.getElementById('mineruConnStatus');
    if (testBtn) testBtn.style.display = 'inline-block';
    if (statusBadge) statusBadge.style.display = 'inline-block';
  }

  // Whether to show api_url row: MinerU or configuration already contains api_url
  const showApi = mineruVisible || !!cfg.api_url;
  const apiUrlRow = document.getElementById('engineApiUrlRow');
  if (apiUrlRow) {
    apiUrlRow.style.display = showApi ? 'block' : 'none';
  }
}

// Load MinerU API Key (masked display)
async function loadMineruApiKey() {
  try {
    const resp = await fetch('/auth/app-config/raw-secrets', { credentials: 'include' });
    if (!resp.ok) return;
    const secrets = await resp.json();
    // Prioritize new structure meta
    const mineruMeta = secrets.translator_mineru_token_meta || null;
    const key = mineruMeta ? (mineruMeta.key || '') : (secrets.translator_mineru_token || '');
    const isConfigured = mineruMeta ? !!mineruMeta.configured : !!key;
    const el = document.getElementById('mineruApiKey');
    const status = document.getElementById('mineruApiKeyStatus');
    if (!el) return;
    if (isConfigured && key) {
      el.value = key.substring(0, 8) + '***';
      el.type = 'password';
      if (status) {
        status.classList.remove('bg-secondary');
        status.classList.add('bg-success');
        status.textContent = window.SettingsCore ? window.SettingsCore.getText('statusConfigured') : 'Configured';
        status.setAttribute('data-i18n', 'statusConfigured');
      }
    } else {
      el.value = '';
      el.placeholder = window.SettingsCore ? window.SettingsCore.getText('mineruApiKeyPlaceholder') : '';
      el.type = 'password';
      if (status) {
        status.classList.remove('bg-success');
        status.classList.add('bg-secondary');
        status.textContent = window.SettingsCore ? window.SettingsCore.getText('statusNotConfigured') : 'Not configured';
        status.setAttribute('data-i18n', 'statusNotConfigured');
      }
    }
  } catch (e) {
    console.warn('Load MinerU API Key failed', e);
    const status = document.getElementById('mineruApiKeyStatus');
    if (status) {
      status.classList.remove('bg-success');
      status.classList.add('bg-secondary');
      status.textContent = window.SettingsCore ? window.SettingsCore.getText('statusNotConfigured') : 'Not configured';
      status.setAttribute('data-i18n', 'statusNotConfigured');
    }
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
    engineConfigs[key].name = name || getText('mineruPlaceholder');
    if (apiUrl) {
      engineConfigs[key].api_url = apiUrl;
    } else {
      delete engineConfigs[key].api_url;
    }
    if (key === 'mineru') {
      engineConfigs[key].model_version = mineruModelVersion || getText('mineruModelVersionPlaceholder');
    } else {
      delete engineConfigs[key].model_version;
    }

    // Combine translator_settings payload
    const payload = {
      translator_settings: {
        convert_engine: key,
        mineru_model_version: mineruModelVersion || getText('mineruModelVersionPlaceholder'),
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

// Initialize parsing engines settings module
function initParsingEngineModule() {
  console.log('Initializing parsing engines settings module');
  
  // Apply i18n to the module content
  if (window.SettingsCore && window.SettingsCore.setLanguage) {
    try {
      window.SettingsCore.setLanguage(window.SettingsCore.currentLang || 'zh');
    } catch (e) {
      console.warn('[Parsing Engines][init] Failed to apply i18n:', e);
    }
  }
  
  // Load engine configurations
  loadEngineConfigs().then(() => {
    // Delay refresh MinerU Key status again to avoid being overridden by other rendering
    setTimeout(() => { try { loadMineruApiKey(); } catch (e) {} }, 150);
  });
  
  // Setup event listeners
  const sel = document.getElementById('engineSelect');
  if (sel) sel.addEventListener('change', () => updateEngineFields());
  
  const saveBtn = document.getElementById('saveEngineBtn');
  if (saveBtn) saveBtn.addEventListener('click', saveParsingEngineConfig);
  const testBtn = document.getElementById('testMineruBtn');
  if (testBtn) testBtn.addEventListener('click', testMineruConnectionInSettings);
  
  // Initialize password toggle buttons
  if (window.SettingsCore) {
    window.SettingsCore.initTogglePasswordButtons();
  }
}

// Export functions for global access
window.saveParsingEngineConfig = saveParsingEngineConfig;
window.initParsingEnginesModule = initParsingEngineModule;

async function testMineruConnectionInSettings() {
  try {
    const statusBadge = document.getElementById('mineruConnStatus');
    if (statusBadge) {
      statusBadge.className = 'badge bg-warning';
      statusBadge.textContent = 'Testing...';
    }
    // Load current config
    const r = await fetch('/auth/app-config', { credentials: 'include' });
    if (!r.ok) throw new Error('Failed to load config');
    const cfg = await r.json();
    const ts = cfg.translator_settings || {};
    // Only MinerU needs test
    const key = document.getElementById('engineSelect')?.value || 'mineru';
    const engine = (ts.engines && ts.engines[key]) || {};
    const baseUrl = engine.api_url || '';
    const model = engine.model_version || ts.mineru_model_version || '';
    if (!baseUrl || !model) {
      throw new Error('Missing API URL or model_version');
    }
    const resp = await fetch('/auth/mineru/test-connection', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ base_url: baseUrl, model_version: model })
    });
    const data = await resp.json().catch(()=>({}));
    if (resp.ok && data.success) {
      if (statusBadge) {
        statusBadge.className = 'badge bg-success';
        statusBadge.textContent = 'Connected';
      }
    } else {
      const msg = data.message || data.detail || ('HTTP ' + resp.status);
      if (statusBadge) {
        statusBadge.className = 'badge bg-danger';
        statusBadge.textContent = 'Failed';
      }
      if (window.SettingsCore) {
        window.SettingsCore.showNotification('MinerU test failed: ' + msg, 'error');
      }
    }
  } catch (e) {
    const statusBadge = document.getElementById('mineruConnStatus');
    if (statusBadge) {
      statusBadge.className = 'badge bg-danger';
      statusBadge.textContent = 'Failed';
    }
    if (window.SettingsCore) {
      window.SettingsCore.showNotification('MinerU test failed: ' + (e?.message || e), 'error');
    }
  }
}
