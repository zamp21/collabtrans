// Message Settings Module
// 消息设置模块

// Load message configuration
async function loadMessageConfig() {
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

// Save message settings
async function saveMessageSettings(silent = false) {
  const messagePayload = {
    login_banner: document.getElementById('loginBannerInput').value.trim(),
    usage_message: document.getElementById('usageMessageInput').value.trim()
  };
  
  const resp = await fetch('/auth/message-config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(messagePayload)
  });
  
  const success = resp.ok;
  
  if (!silent && window.SettingsCore) {
    if (success) {
      window.SettingsCore.showNotification(window.SettingsCore.getText('messageSettingsSaved'), 'success');
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

// Initialize message settings module (called by settings-core.js)
function initMessageSettingsModule() {
  console.log('Initializing message settings module');
  
  // Load message configuration
  loadMessageConfig();
  
  // Setup event listeners
  const saveMessageBtn = document.getElementById('saveMessageBtn');
  if (saveMessageBtn) {
    saveMessageBtn.addEventListener('click', () => saveMessageSettings(false));
  }
}
