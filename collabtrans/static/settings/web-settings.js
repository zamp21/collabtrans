// Web Settings Module
// Web settings module

// Load app configuration
async function loadAppConfig() {
  try {
    const resp = await fetch(apiUrl('/auth/app-config'));
    if (!resp.ok) return null;
    const cfg = await resp.json();
    
    // Update current certificate and key display
    try {
      const certPath = cfg.https?.cert_file;
      const keyPath = cfg.https?.key_file;
      document.getElementById('currentCertName').textContent = certPath ? (certPath.split('/').pop()) : '-';
      document.getElementById('currentKeyName').textContent = keyPath ? (keyPath.split('/').pop()) : '-';

      // Fetch validity for current certificate
      const certName = certPath ? (certPath.split('/').pop()) : null;
      if (certName) {
        try {
          const lresp = await fetch(apiUrl('/auth/certificate-list'), { credentials: 'include' });
          if (lresp.ok) {
            const list = await lresp.json();
            const cert = (list.certificates || []).find(c => c.type === 'cert' && c.name === certName);
            if (cert && cert.valid_until) {
              const validityText = `${cert.days_left || ''}${cert.days_left ? ' - ' : ''}${cert.valid_until}`;
              const el = document.getElementById('currentCertValidity');
              if (el) el.textContent = validityText || '-';
            } else {
              const el = document.getElementById('currentCertValidity');
              if (el) el.textContent = '-';
            }
          }
        } catch (_) {}
      } else {
        const el = document.getElementById('currentCertValidity');
        if (el) el.textContent = '-';
      }
    } catch(_) {}
    
    return cfg;
  } catch (_) { 
    return null; 
  }
}

// Save app configuration
async function saveAppConfig(patch) {
  const resp = await fetch(apiUrl('/auth/app-config'), {
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
  const resp = await fetch(apiUrl('/auth/web/upload-cert'), { method: 'POST', body: fd });
  return resp.ok;
}

// Internal helper: upload if user selected files
async function maybeUploadSelectedFiles() {
  const cert = document.getElementById('certFile').files[0];
  const key = document.getElementById('keyFile').files[0];
  if (cert || key) {
    const ok = await uploadCertAndKey(cert, key);
    return ok;
  }
  return true;
}

// Save web settings (auto-upload selected files first)
async function saveWebSettings() {
  try {
    const uploadOk = await maybeUploadSelectedFiles();
    if (!uploadOk) {
      if (window.SettingsCore) {
        window.SettingsCore.showNotification(window.SettingsCore.getText('certUploadFailed'), 'error');
      }
      return false;
    }

    const patch = {
      https: {
        enabled: document.getElementById('httpsEnabled').checked,
        force_redirect: document.getElementById('httpsForceRedirect').checked
      },
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

// Initialize web settings module (called by SettingsCore after HTML injected)
async function initWebSettingsModule() {
  // Check if required elements exist
  const httpsEnabledEl = document.getElementById('httpsEnabled');
  const httpsForceRedirectEl = document.getElementById('httpsForceRedirect');
  
  if (!httpsEnabledEl) {
    console.error('HTTPS enabled element not found');
    return;
  }
  
  if (!httpsForceRedirectEl) {
    console.error('HTTPS force redirect element not found');
    return;
  }

  // Set default HTTPS disabled, and disable modification until tested
  httpsEnabledEl.checked = false;
  httpsEnabledEl.disabled = true;
  httpsForceRedirectEl.checked = false;
  httpsForceRedirectEl.disabled = true;

  const cfg = await loadAppConfig();
  if (cfg && cfg.https) {
    if (typeof cfg.https.enabled !== 'undefined') {
      httpsEnabledEl.checked = !!cfg.https.enabled;
      // If HTTPS is already enabled, allow modification of force redirect
      if (cfg.https.enabled) {
        httpsEnabledEl.disabled = false;
        httpsForceRedirectEl.disabled = false;
      }
    }
    if (typeof cfg.https.force_redirect !== 'undefined') {
      httpsForceRedirectEl.checked = !!cfg.https.force_redirect;
    }
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

  // removed openGenerateCertBtn (now implemented in embedded section below)

  // Test HTTPS button (auto-upload before test)
  const testHttpsBtn = document.getElementById('testHttpsBtn');
  if (testHttpsBtn) {
    testHttpsBtn.addEventListener('click', async () => {
      try {
        // If password is entered, save first for server to read
        const pwd = document.getElementById('keyPassword').value;
        if (pwd) {
          await saveAppConfig({ https_key_password: pwd });
        }
        
        // Auto upload selected files before test
        const upOk = await maybeUploadSelectedFiles();
        if (!upOk) {
          if (window.SettingsCore) {
            window.SettingsCore.showNotification(window.SettingsCore.getText('certUploadFailedTestCancelled'), 'error');
          }
          return;
        }
        // Refresh display after upload
        await loadAppConfig();
        
        const resp = await fetch(apiUrl('/auth/web/test-https'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({})
        });
        
        const data = await resp.json();
        if (resp.ok && data.ok) {
          if (window.SettingsCore) {
            window.SettingsCore.showNotification(window.SettingsCore.getText('httpsTestSuccess'), 'success');
          }
          // After passing test, allow switching to enable HTTPS and force redirect
          document.getElementById('httpsEnabled').disabled = false;
          document.getElementById('httpsForceRedirect').disabled = false;
        } else {
          if (window.SettingsCore) {
            window.SettingsCore.showNotification(window.SettingsCore.getText('httpsTestFailed') + ': ' + JSON.stringify(data), 'error');
          }
          // Test failed, still keep disabled
          document.getElementById('httpsEnabled').disabled = true;
          document.getElementById('httpsForceRedirect').disabled = true;
        }
      } catch (e) {
        if (window.SettingsCore) {
          window.SettingsCore.showNotification(window.SettingsCore.getText('httpsTestException') + ': ' + e.message, 'error');
        }
        document.getElementById('httpsEnabled').disabled = true;
        document.getElementById('httpsForceRedirect').disabled = true;
      }
    });
  }

  // Load and initialize embedded certificate module
  try {
    const container = document.getElementById('embedded-certificate-content');
    if (container) {
      const resp = await fetch(apiUrl('/static/settings/certificate-settings.html'), { cache: 'no-store' });
      if (resp.ok) {
        const html = await resp.text();
        container.innerHTML = html;
        try { if (window.SettingsCore) window.SettingsCore.setLanguage && window.SettingsCore.setLanguage(localStorage.getItem('ui_language') || 'zh'); } catch (_) {}

        // Load JS for certificate module (once)
        if (!window.__certificateModuleLoaded) {
          const script = document.createElement('script');
          script.src = '/static/settings/certificate-settings.js?v=' + Date.now();
          script.onload = () => {
            window.__certificateModuleLoaded = true;
            if (window.initCertificateSettingsModule) {
              window.initCertificateSettingsModule();
            }
          };
          document.head.appendChild(script);
        } else if (window.initCertificateSettingsModule) {
          // If already loaded, just init again to bind events
          window.initCertificateSettingsModule();
        }
      } else if (window.SettingsCore) {
        window.SettingsCore.showNotification('Failed to load embedded certificate settings', 'error');
      }
    }
  } catch (e) {
    console.error('Failed to initialize embedded certificate settings:', e);
  }
}

// Export functions for global access
window.saveWebSettings = saveWebSettings;
window.initWebSettingsModule = initWebSettingsModule;
