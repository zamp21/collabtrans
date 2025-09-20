// General Settings Module
// 通用设置模块

// Load general settings
async function loadGeneralSettings() {
  try {
    const resp = await fetch('/auth/app-config');
    if (!resp.ok) return;
    const cfg = await resp.json();
    
    // Load default language setting
    const defaultLang = cfg.default_language || 'en';
    const defaultLangSelect = document.getElementById('defaultLanguage');
    if (defaultLangSelect) {
      defaultLangSelect.value = defaultLang;
    }
  } catch (e) {
    console.error('Load general settings error:', e);
  }
}

// Save general settings
async function saveGeneralSettings() {
  try {
    const defaultLang = document.getElementById('defaultLanguage').value;
    
    const payload = {
      default_language: defaultLang
    };

    const resp = await fetch('/auth/app-config/setting', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (resp.ok) {
      if (window.SettingsCore) {
        window.SettingsCore.showNotification(window.SettingsCore.getText('generalSettingsSaved'), 'success');
      }
      // Update current language if it matches the new default
      if (window.currentLang === defaultLang) {
        window.setLanguage(defaultLang);
      }
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

// Initialize general settings module
document.addEventListener('DOMContentLoaded', () => {
  // Load settings
  loadGeneralSettings();
  
  // Setup save button
  const saveGeneralBtn = document.getElementById('saveGeneralBtn');
  if (saveGeneralBtn) {
    saveGeneralBtn.addEventListener('click', saveGeneralSettings);
  }
});

// Export functions for global access
window.saveGeneralSettings = saveGeneralSettings;
