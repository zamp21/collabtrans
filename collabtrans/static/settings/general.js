// General Settings Module
// General settings module

// Load general settings
async function loadGeneralSettings() {
  try {
    const resp = await fetch('/auth/app-config', { credentials: 'include' });
    if (!resp.ok) return;
    const cfg = await resp.json();
    console.log('[General][load] backend default_language =', cfg.default_language, 'ui_language(user)=', cfg.ui_language);
    
    // Load default language setting
    const defaultLang = cfg.default_language || 'en';
    const defaultLangSelect = document.getElementById('defaultLanguage');
    if (defaultLangSelect) {
      defaultLangSelect.value = defaultLang;
      console.log('[General][load] set select#defaultLanguage.value =', defaultLangSelect.value);
    }
    
    // Removed default username from General settings
    
    // Removed super admin password field from General settings
    return cfg;
  } catch (e) {
    console.error('Load general settings error:', e);
  }
}

// Save general settings
async function saveGeneralSettings() {
  try {
    const defaultLang = document.getElementById('defaultLanguage').value;
    const payload = {
      default_language: defaultLang,
    // Only keeping default_language in General; other admin fields removed
    };

    const resp = await fetch('/auth/app-config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(payload)
    });

    if (resp.ok) {
      if (window.SettingsCore) {
        window.SettingsCore.showNotification(window.SettingsCore.getText('generalSettingsSaved'), 'success');
      }
      // Sync default language to user preferences and current page language
      try {
        console.log('[General][save] default_language to set =', defaultLang);
        localStorage.setItem('ui_language', defaultLang);
        if (window.SettingsCore) {
          console.log('[General][save] calling SettingsCore.setLanguage with', defaultLang);
          window.SettingsCore.setLanguage(defaultLang);
        }
        // Notify other pages
        console.log('[General][save] dispatch languageChanged event:', defaultLang);
        window.dispatchEvent(new CustomEvent('languageChanged', { detail: { language: defaultLang } }));
      } catch (_) {}
      return true;
    } else {
      const error = await resp.text();
      if (window.SettingsCore) {
        window.SettingsCore.showNotification(window.SettingsCore.getText('saveFailed') + ': ' + error, 'error');
      }
      return false;
    }
  } catch (e) {
    if (window.SettingsCore) {
      window.SettingsCore.showNotification(window.SettingsCore.getText('saveFailed') + ': ' + e.message, 'error');
    }
    return false;
  }
}

// Initialize general settings module (called by settings-core after dynamic load)
function initGeneralModule() {
  console.log('[General][init] initGeneralModule called');
  // Load settings
  loadGeneralSettings().then(cfg => {
    // Safety: sync select value again after i18n is applied
    try {
      const defaultLangSelect = document.getElementById('defaultLanguage');
      if (defaultLangSelect && cfg && cfg.default_language) {
        defaultLangSelect.value = cfg.default_language;
        console.log('[General][init] re-sync select after load, value =', defaultLangSelect.value);
      }
    } catch (_) {}
  });
  
  // Setup save button
  const saveGeneralBtn = document.getElementById('saveGeneralBtn');
  if (saveGeneralBtn) {
    console.log('[General][init] binding click for #saveGeneralBtn');
    saveGeneralBtn.addEventListener('click', () => {
      console.log('[General][click] saveGeneralBtn clicked');
      saveGeneralSettings();
    });
  } else {
    console.warn('[General][init] #saveGeneralBtn not found');
  }
  
  // Initialize password toggle buttons
  if (window.SettingsCore) {
    window.SettingsCore.initTogglePasswordButtons();
  }
}

// Initialize general settings module
function initGeneralModule() {
  console.log('Initializing general settings module');
  
  // Apply i18n to the module content
  if (window.SettingsCore && window.SettingsCore.setLanguage) {
    try {
      window.SettingsCore.setLanguage(window.SettingsCore.currentLang || 'zh');
    } catch (e) {
      console.warn('[General][init] Failed to apply i18n:', e);
    }
  }
  
  // Load general settings
  loadGeneralSettings();
  
  // Setup event listeners
  const saveGeneralBtn = document.getElementById('saveGeneralBtn');
  if (saveGeneralBtn) {
    saveGeneralBtn.addEventListener('click', () => saveGeneralSettings(false));
  } else {
    console.warn('[General][init] #saveGeneralBtn not found');
  }
  
  // Initialize password toggle buttons
  if (window.SettingsCore) {
    window.SettingsCore.initTogglePasswordButtons();
  }
}

// Export functions for global access
window.saveGeneralSettings = saveGeneralSettings;
window.initGeneralModule = initGeneralModule;
