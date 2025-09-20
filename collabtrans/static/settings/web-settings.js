// Web Settings Module
// Web设置模块

// Load app configuration
async function loadAppConfig() {
  try {
    const resp = await fetch('/auth/app-config');
    if (!resp.ok) return null;
    const cfg = await resp.json();
    
    // Update current certificate and key display
    try {
      const certPath = cfg.https_cert_file;
      const keyPath = cfg.https_key_file;
      document.getElementById('currentCertName').textContent = certPath ? (certPath.split('/').pop()) : '-';
      document.getElementById('currentKeyName').textContent = keyPath ? (keyPath.split('/').pop()) : '-';
    } catch(_) {}
    
    return cfg;
  } catch (_) { 
    return null; 
  }
}

// Save app configuration
async function saveAppConfig(patch) {
  const resp = await fetch('/auth/app-config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch)
  });
  return resp.ok;
}

// Upload certificate and key
async function uploadCertAndKey(certFile, keyFile) {
  const fd = new FormData();
  if (certFile) fd.append('cert', certFile);
  if (keyFile) fd.append('key', keyFile);
  const resp = await fetch('/auth/web/upload-cert', { method: 'POST', body: fd });
  return resp.ok;
}

// Save web settings
async function saveWebSettings() {
  try {
    const patch = {
      https_enabled: document.getElementById('httpsEnabled').checked,
      https_key_password: document.getElementById('keyPassword').value || null
    };
    
    const ok = await saveAppConfig(patch);
    if (ok) {
      if (window.SettingsCore) {
        window.SettingsCore.showNotification(window.SettingsCore.getText('webSettingsSaved'), 'success');
      }
      return true;
    } else {
      if (window.SettingsCore) {
        window.SettingsCore.showNotification(window.SettingsCore.getText('webSettingsSaveFailed'), 'error');
      }
      return false;
    }
  } catch (error) {
    console.error('Save web settings error:', error);
    if (window.SettingsCore) {
      window.SettingsCore.showNotification(window.SettingsCore.getText('webSettingsSaveFailed') + ': ' + error.message, 'error');
    }
    return false;
  }
}

// Initialize web settings module
document.addEventListener('DOMContentLoaded', async () => {
  // Set default HTTPS disabled, and disable modification until tested
  document.getElementById('httpsEnabled').checked = false;
  document.getElementById('httpsEnabled').disabled = true;

  const cfg = await loadAppConfig();
  if (cfg && typeof cfg.https_enabled !== 'undefined') {
    document.getElementById('httpsEnabled').checked = !!cfg.https_enabled;
  }

  // Set internationalized placeholders
  if (window.SettingsCore) {
    const keyPassword = document.getElementById('keyPassword');
    if (keyPassword && keyPassword.getAttribute('data-i18n-placeholder')) {
      keyPassword.placeholder = window.SettingsCore.getText(keyPassword.getAttribute('data-i18n-placeholder')) || keyPassword.placeholder;
    }
    
    const certFile = document.getElementById('certFile');
    if (certFile && certFile.getAttribute('data-i18n-accept')) {
      certFile.setAttribute('accept', window.SettingsCore.getText(certFile.getAttribute('data-i18n-accept')) || certFile.getAttribute('accept'));
    }
    
    const keyFile = document.getElementById('keyFile');
    if (keyFile && keyFile.getAttribute('data-i18n-accept')) {
      keyFile.setAttribute('accept', window.SettingsCore.getText(keyFile.getAttribute('data-i18n-accept')) || keyFile.getAttribute('accept'));
    }
  }

  // Save web settings button
  const saveWebBtn = document.getElementById('saveWebBtn');
  if (saveWebBtn) {
    saveWebBtn.addEventListener('click', saveWebSettings);
  }

  // Upload certificate and key button
  const uploadCertBtn = document.getElementById('uploadCertBtn');
  if (uploadCertBtn) {
    uploadCertBtn.addEventListener('click', async () => {
      const cert = document.getElementById('certFile').files[0];
      const key = document.getElementById('keyFile').files[0];
      const ok = await uploadCertAndKey(cert, key);
      if (ok) {
        // Reload to update current file name display
        await loadAppConfig();
        if (window.SettingsCore) {
          window.SettingsCore.showNotification(window.SettingsCore.getText('certUploadSuccess'), 'success');
        }
      } else {
        if (window.SettingsCore) {
          window.SettingsCore.showNotification(window.SettingsCore.getText('certUploadFailed'), 'error');
        }
      }
    });
  }

  // Test HTTPS button
  const testHttpsBtn = document.getElementById('testHttpsBtn');
  if (testHttpsBtn) {
    testHttpsBtn.addEventListener('click', async () => {
      try {
        // If password is entered, save first for server to read
        const pwd = document.getElementById('keyPassword').value;
        if (pwd) {
          await saveAppConfig({ https_key_password: pwd });
        }
        
        // If user selected new file, upload first, then test with new certificate
        const certSel = document.getElementById('certFile').files[0];
        const keySel = document.getElementById('keyFile').files[0];
        if (certSel || keySel) {
          const upOk = await uploadCertAndKey(certSel, keySel);
          if (!upOk) {
            if (window.SettingsCore) {
              window.SettingsCore.showNotification(window.SettingsCore.getText('certUploadFailedTestCancelled'), 'error');
            }
            return;
          }
          // Refresh display after upload
          await loadAppConfig();
        }
        
        const resp = await fetch('/auth/web/test-https', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({})
        });
        
        const data = await resp.json();
        if (resp.ok && data.ok) {
          if (window.SettingsCore) {
            window.SettingsCore.showNotification(window.SettingsCore.getText('httpsTestSuccess'), 'success');
          }
          // After passing test, allow switching to enable HTTPS
          document.getElementById('httpsEnabled').disabled = false;
        } else {
          if (window.SettingsCore) {
            window.SettingsCore.showNotification(window.SettingsCore.getText('httpsTestFailed') + ': ' + JSON.stringify(data), 'error');
          }
          // Test failed, still keep disabled
          document.getElementById('httpsEnabled').disabled = true;
        }
      } catch (e) {
        if (window.SettingsCore) {
          window.SettingsCore.showNotification(window.SettingsCore.getText('httpsTestException') + ': ' + e.message, 'error');
        }
        document.getElementById('httpsEnabled').disabled = true;
      }
    });
  }
});

// Export functions for global access
window.saveWebSettings = saveWebSettings;
