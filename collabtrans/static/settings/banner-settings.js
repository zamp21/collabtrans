// Banner Settings Module
// Banner settings module

// Load banner configuration
async function loadBannerConfig() {
  try {
    const resp = await fetch('/auth/message-config');
    if (!resp.ok) return false;
    const cfg = await resp.json();
    document.getElementById('loginBannerInput').value = cfg.login_banner || 'Welcome to document translation system.';
    document.getElementById('usageMessageInput').value = cfg.usage_message || 'Please drop your file and click Translate.';
    return true;
  } catch (_) { 
    return false; 
  }
}

// Save banner settings
async function saveBannerSettings(silent = false) {
  const bannerPayload = {
    login_banner: document.getElementById('loginBannerInput').value.trim(),
    usage_message: document.getElementById('usageMessageInput').value.trim()
  };
  
  const resp = await fetch('/auth/message-config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(bannerPayload)
  });
  
  const success = resp.ok;
  
  if (!silent && window.SettingsCore) {
    if (success) {
      window.SettingsCore.showNotification(window.SettingsCore.getText('bannerSettingsSaved'), 'success');
    } else {
      // Show detailed error information
      let errorMsg = window.SettingsCore.getText('saveFailed');
      if (!resp.ok) {
        try {
          const error = await resp.text();
          errorMsg += ` (${resp.status} - ${error})`;
        } catch (e) {
          errorMsg += ` (${resp.status})`;
        }
      }
      window.SettingsCore.showNotification(errorMsg, 'error');
    }
  }
  
  return success;
}

// Initialize banner settings module (called by settings-core.js)
function initBannerSettingsModule() {
  console.log('Initializing banner settings module');
  
  // Load banner configuration
  loadBannerConfig();
  
  // Setup event listeners
  const saveBannerBtn = document.getElementById('saveBannerBtn');
  if (saveBannerBtn) {
    saveBannerBtn.addEventListener('click', () => saveBannerSettings(false));
  }
}
