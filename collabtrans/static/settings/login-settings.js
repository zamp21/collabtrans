// Login Settings Module
// Login settings module

// Global variable to track LDAP test validation status
let ldapTestValidated = false;
let ldapInitiallyEnabled = false;

// Load LDAP configuration
async function loadLdapConfig() {
  try {
    const resp = await fetch(apiUrl('/auth/ldap-config'));
    if (!resp.ok) return false;
    const cfg = await resp.json();
    const ldapEnabledEl = document.getElementById('ldapEnabled');
    ldapInitiallyEnabled = !!cfg.ldap_enabled;
    ldapEnabledEl.checked = ldapInitiallyEnabled;
    document.getElementById('ldapProtocol').value = cfg.ldap_protocol || 'ldap';
    document.getElementById('ldapHost').value = cfg.ldap_host || '';
    document.getElementById('ldapPort').value = cfg.ldap_port || 389;
    document.getElementById('ldapBindDnTemplate').value = cfg.ldap_bind_dn_template || '';
    document.getElementById('ldapUserFilter').value = cfg.ldap_user_filter || '';
    // Maintain compatibility with old homepage structure: fill both user and group Base DN
    document.getElementById('ldapBaseDn').value = cfg.ldap_base_dn || '';
    document.getElementById('ldapAdminGroupEnabled').checked = !!cfg.ldap_admin_group_enabled;
    document.getElementById('ldapGlossaryGroupEnabled').checked = !!cfg.ldap_glossary_group_enabled;
    document.getElementById('ldapAdminGroup').value = cfg.ldap_admin_group || '';
    document.getElementById('ldapGlossaryGroup').value = cfg.ldap_glossary_group || '';
    document.getElementById('ldapGroupBaseDn').value = cfg.ldap_group_base_dn || '';
    document.getElementById('ldapTlsVerify').checked = cfg.ldap_tls_verify !== false;
    document.getElementById('ldapTlsCacertfile').value = cfg.ldap_tls_cacertfile || '';

    // Enable/disable toggle based on initial state and test status
    try {
      const hintEl = document.getElementById('ldapEnableHint');
      if (ldapInitiallyEnabled) {
        ldapEnabledEl.disabled = false; // allow disabling any time when already enabled
        if (hintEl) hintEl.style.display = 'none';
      } else {
        ldapEnabledEl.disabled = !ldapTestValidated;
        if (hintEl) hintEl.style.display = ldapTestValidated ? 'none' : '';
      }
    } catch (_) {}

    updateLdapsUi();
    return true;
  } catch (_) { 
    return false; 
  }
}

// Load session and security configuration
async function loadSessionSecurityConfig() {
  try {
    const resp = await fetch(apiUrl('/auth/app-config'));
    if (!resp.ok) return false;
    const cfg = await resp.json();
    
    // Load session settings
    const sessionMaxAgeInput = document.getElementById('sessionMaxAgeInput');
    if (sessionMaxAgeInput) {
      sessionMaxAgeInput.value = cfg.session_max_age || 604800;
    }
    
    // Load security settings
    const maxLoginAttemptsInput = document.getElementById('maxLoginAttemptsInput');
    if (maxLoginAttemptsInput) {
      maxLoginAttemptsInput.value = cfg.max_login_attempts || 5;
    }
    
    const loginAttemptWindowInput = document.getElementById('loginAttemptWindowInput');
    if (loginAttemptWindowInput) {
      loginAttemptWindowInput.value = cfg.login_attempt_window || 300;
    }
    
    return true;
  } catch (_) { 
    return false; 
  }
}

// Update LDAPS UI
function updateLdapsUi() {
  const isLdaps = document.getElementById('ldapProtocol').value === 'ldaps';
  document.getElementById('ldapsConfigContainer').style.display = isLdaps ? '' : 'none';
}

// Save login settings
async function saveLoginSettings(silent = false) {
  // Check if trying to enable LDAP without test validation
  const ldapEnabled = document.getElementById('ldapEnabled').checked;
  // Only block enabling LDAP without test, allow disabling anytime
  if (ldapEnabled && !ldapTestValidated && !ldapInitiallyEnabled) {
    if (window.SettingsCore) {
      window.SettingsCore.showNotification('LDAP test must be performed and passed before enabling LDAP. Please test the connection first.', 'warning');
    }
    return false;
  }

  // Save LDAP configuration
  const ldapPayload = {
    ldap_enabled: ldapEnabled,
    ldap_protocol: document.getElementById('ldapProtocol').value,
    ldap_host: document.getElementById('ldapHost').value,
    ldap_port: parseInt(document.getElementById('ldapPort').value || '389'),
    ldap_bind_dn_template: document.getElementById('ldapBindDnTemplate').value,
    ldap_base_dn: document.getElementById('ldapBaseDn').value,
    ldap_user_filter: document.getElementById('ldapUserFilter').value,
    ldap_admin_group_enabled: document.getElementById('ldapAdminGroupEnabled').checked,
    ldap_glossary_group_enabled: document.getElementById('ldapGlossaryGroupEnabled').checked,
    ldap_admin_group: document.getElementById('ldapAdminGroup').value,
    ldap_glossary_group: document.getElementById('ldapGlossaryGroup').value,
    ldap_group_base_dn: document.getElementById('ldapGroupBaseDn').value,
    ldap_tls_verify: document.getElementById('ldapTlsVerify').checked,
    ldap_tls_cacertfile: document.getElementById('ldapTlsCacertfile').value,
    ldap_test_validated: ldapTestValidated
  };
  
  const ldapResp = await fetch(apiUrl('/auth/ldap-config'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(ldapPayload)
  });
  
  // Save session and security configuration
  const sessionSecurityPayload = {
    session_max_age: parseInt(document.getElementById('sessionMaxAgeInput').value || '604800'),
    max_login_attempts: parseInt(document.getElementById('maxLoginAttemptsInput').value || '5'),
    login_attempt_window: parseInt(document.getElementById('loginAttemptWindowInput').value || '300')
  };
  
  const sessionSecurityResp = await fetch(apiUrl('/auth/app-config'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(sessionSecurityPayload)
  });
  
  const success = ldapResp.ok && sessionSecurityResp.ok;
  
  if (!silent && window.SettingsCore) {
    if (success) {
      window.SettingsCore.showNotification(window.SettingsCore.getText('loginSettingsSaved'), 'success');
    } else {
      // Show detailed error information
      let errorMsg = window.SettingsCore.getText('saveFailed');
      if (!ldapResp.ok) {
        try {
          const ldapError = await ldapResp.text();
          errorMsg += ` (LDAP: ${ldapResp.status} - ${ldapError})`;
        } catch (e) {
          errorMsg += ` (LDAP: ${ldapResp.status})`;
        }
      }
      if (!sessionSecurityResp.ok) {
        try {
          const sessionError = await sessionSecurityResp.text();
          errorMsg += ` (Session: ${sessionSecurityResp.status} - ${sessionError})`;
        } catch (e) {
          errorMsg += ` (Session: ${sessionSecurityResp.status})`;
        }
      }
      window.SettingsCore.showNotification(errorMsg, 'error');
    }
  }
  
  return success;
}

// Generate LDAP test command
async function generateLdapTestCmd() {
  const protocol = document.getElementById('ldapProtocol').value || 'ldap';
  const host = document.getElementById('ldapHost').value || '';
  const port = document.getElementById('ldapPort').value || (protocol === 'ldaps' ? '636' : '389');
  const baseDn = document.getElementById('ldapBaseDn').value || '';
  const tlsVerify = document.getElementById('ldapTlsVerify').checked;
  const cacert = document.getElementById('ldapTlsCacertfile').value;
  const username = prompt(window.SettingsCore ? window.SettingsCore.getText('enterTestUsernamePrompt') : 'Enter test username:', '');
  if (username === null) return;
  const template = document.getElementById('ldapBindDnTemplate').value || '';
  const bindDnExample = template.replaceAll('{username}', username);
  const baseCmd = `ldapsearch -H ${protocol}://${host}:${port} -D "${bindDnExample}" -W -b "${baseDn}" -x -LLL`;
  const filter = '"(objectClass=*)"';
  const tlsPart = protocol === 'ldaps' ? (tlsVerify ? '' : ' -o tls_reqcert=never') : '';
  const cacertPart = (protocol === 'ldaps' && tlsVerify && cacert) ? ` LDAPTLS_CACERT=${cacert}` : '';
  const finalCmd = `${cacertPart ? cacertPart + ' ' : ''}${baseCmd}${tlsPart} ${filter}`;
  
  // Show popup for user to copy
  try {
    const modalEl = document.getElementById('ldapCmdModal');
    const output = document.getElementById('ldapCmdOutput');
    const copyBtn = document.getElementById('copyLdapCmdBtn');
    if (modalEl && output && copyBtn) {
      output.value = finalCmd;
      const modal = new bootstrap.Modal(modalEl);
      modal.show();
      const handler = async () => {
        try {
          await navigator.clipboard.writeText(output.value);
          if (window.SettingsCore) {
            window.SettingsCore.showNotification(window.SettingsCore.getText('ldapTestCmdCopied'), 'success');
          }
        } catch (e) {
          if (window.SettingsCore) {
            window.SettingsCore.showNotification(window.SettingsCore.getText('copyFailed'), 'error');
          }
        }
      };
      copyBtn.onclick = handler;
    } else {
      // Fallback: directly try to copy
      await navigator.clipboard.writeText(finalCmd);
      if (window.SettingsCore) {
        window.SettingsCore.showNotification(window.SettingsCore.getText('ldapTestCmdCopied'), 'success');
      }
    }
  } catch (err) {
    if (window.SettingsCore) {
      window.SettingsCore.showNotification(window.SettingsCore.getText('copyFailed'), 'error');
    }
    console.log(finalCmd);
  }
}

// Test LDAP connectivity
async function testLdapConnectivity() {
  const modalEl = document.getElementById('ldapTestModal');
  const modal = new bootstrap.Modal(modalEl);
  document.getElementById('ldapTestUsernameInput').value = '';
  document.getElementById('ldapTestPasswordInput').value = '';
  modal.show();

  const confirmBtn = document.getElementById('ldapTestConfirmBtn');
  const onConfirm = async () => {
    confirmBtn.disabled = true;
    try {
      const username = document.getElementById('ldapTestUsernameInput').value.trim();
      const password = document.getElementById('ldapTestPasswordInput').value;
      if (!username || !password) {
        if (window.SettingsCore) {
          window.SettingsCore.showNotification(window.SettingsCore.getText('enterUsernameAndPassword'), 'warning');
        }
        return;
      }
      
      const payload = {
        username,
        password,
        ldap_protocol: document.getElementById('ldapProtocol').value,
        ldap_host: document.getElementById('ldapHost').value,
        ldap_port: document.getElementById('ldapPort').value,
        ldap_bind_dn_template: document.getElementById('ldapBindDnTemplate').value,
        ldap_base_dn: document.getElementById('ldapBaseDn').value,
        ldap_user_filter: document.getElementById('ldapUserFilter').value,
        ldap_admin_group_enabled: document.getElementById('ldapAdminGroupEnabled').checked,
        ldap_glossary_group_enabled: document.getElementById('ldapGlossaryGroupEnabled').checked,
        ldap_admin_group: document.getElementById('ldapAdminGroup').value,
        ldap_glossary_group: document.getElementById('ldapGlossaryGroup').value,
        ldap_group_base_dn: document.getElementById('ldapGroupBaseDn').value,
        ldap_tls_verify: document.getElementById('ldapTlsVerify').checked,
        ldap_tls_cacertfile: document.getElementById('ldapTlsCacertfile').value
      };
      
      console.log('Sending LDAP test request:', payload);
      
      const resp = await fetch(apiUrl('/auth/test-ldap'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload)
      });
      
      console.log('LDAP test response status:', resp.status);
      const text = await resp.text();
      console.log('LDAP test response content:', text);
      
      // Log detailed error information
      if (!resp.ok) {
        console.error('LDAP test failed with status:', resp.status);
        console.error('Response headers:', Object.fromEntries(resp.headers.entries()));
      }
      
      modal.hide();
      
      if (window.SettingsCore) {
        if (resp.ok) {
          const result = JSON.parse(text);
          if (result.test_validated) {
            ldapTestValidated = true;
            // Automatically check "Enable LDAP" and enable switch to avoid false override during subsequent save
            try {
              const ldapEnabledEl = document.getElementById('ldapEnabled');
              const hintEl = document.getElementById('ldapEnableHint');
              if (ldapEnabledEl) {
                ldapEnabledEl.checked = true;
                ldapEnabledEl.disabled = false; // Enable switch
              }
              if (hintEl) {
                hintEl.style.display = 'none'; // Hide hint
              }
            } catch (_) {}
            window.SettingsCore && window.SettingsCore.showNotification(
              window.SettingsCore.getText('ldapConnectionTestSuccess') + ' - LDAP can now be enabled',
              'success'
            );
          } else {
            window.SettingsCore && window.SettingsCore.showNotification(window.SettingsCore.getText('ldapConnectionTestSuccess'), 'success');
          }
        } else {
          ldapTestValidated = false;
          window.SettingsCore.showNotification(window.SettingsCore.getText('ldapConnectionTestFailed') + ': ' + text, 'error');
        }
      }
    } catch (e) {
      ldapTestValidated = false;
      if (window.SettingsCore) {
        window.SettingsCore.showNotification(window.SettingsCore.getText('ldapConnectionTestFailed') + ': ' + e.message, 'error');
      }
    } finally {
      confirmBtn.disabled = false;
      confirmBtn.removeEventListener('click', onConfirm);
    }
  };
  confirmBtn.addEventListener('click', onConfirm);
}

// Initialize login settings module
document.addEventListener('DOMContentLoaded', async () => {
  // Load LDAP configuration first to know initial state
  try { await loadLdapConfig(); } catch(_) {}
  
  // Load session and security configuration
  try { await loadSessionSecurityConfig(); } catch(_) {}
  
  // Setup event listeners
  const ldapProtocol = document.getElementById('ldapProtocol');
  if (ldapProtocol) {
    ldapProtocol.addEventListener('change', updateLdapsUi);
  }
  
  const saveLoginBtn = document.getElementById('saveLoginBtn');
  if (saveLoginBtn) {
    saveLoginBtn.addEventListener('click', () => saveLoginSettings(false));
  }
  
  const genTestCmdBtn = document.getElementById('genLdapTestCmdBtn');
  if (genTestCmdBtn) {
    genTestCmdBtn.addEventListener('click', generateLdapTestCmd);
  }
  
  const testConnectivityBtn = document.getElementById('runLdapConnectivityBtn');
  if (testConnectivityBtn) {
    testConnectivityBtn.addEventListener('click', testLdapConnectivity);
  }
  
  // Initialize password toggle buttons and set internationalized placeholders
  if (window.SettingsCore) {
    window.SettingsCore.initTogglePasswordButtons();
    // Set internationalized placeholders
    const elements = [
      { id: 'ldapBindDnTemplate', attr: 'data-i18n-placeholder' },
      { id: 'ldapUserFilter', attr: 'data-i18n-placeholder' },
      { id: 'ldapTestPasswordInput', attr: 'data-i18n-placeholder' },
      { id: 'ldapTestUsernameInput', attr: 'data-i18n-placeholder' },
      { id: 'sessionMaxAgeInput', attr: 'data-i18n-placeholder' },
      { id: 'maxLoginAttemptsInput', attr: 'data-i18n-placeholder' },
      { id: 'loginAttemptWindowInput', attr: 'data-i18n-placeholder' }
    ];
    
    elements.forEach(({ id, attr }) => {
      const el = document.getElementById(id);
      if (el && el.getAttribute(attr)) {
        el.placeholder = window.SettingsCore.getText(el.getAttribute(attr)) || el.placeholder;
      }
    });
  }
});

// Initialize login settings module (called by settings-core.js)
async function initLoginSettingsModule() {
  console.log('Initializing login settings module');
  
  // Load LDAP configuration first to know initial state
  try { 
    await loadLdapConfig(); 
  } catch(_) {}
  
  // Load session and security configuration
  try { 
    await loadSessionSecurityConfig(); 
  } catch(_) {}
  
  // Setup event listeners
  const ldapProtocol = document.getElementById('ldapProtocol');
  if (ldapProtocol) {
    ldapProtocol.addEventListener('change', updateLdapsUi);
  }
  
  const saveLoginBtn = document.getElementById('saveLoginBtn');
  if (saveLoginBtn) {
    saveLoginBtn.addEventListener('click', () => saveLoginSettings(false));
  }
  
  const genTestCmdBtn = document.getElementById('genLdapTestCmdBtn');
  if (genTestCmdBtn) {
    genTestCmdBtn.addEventListener('click', generateLdapTestCmd);
  }
  
  const testConnectivityBtn = document.getElementById('runLdapConnectivityBtn');
  if (testConnectivityBtn) {
    testConnectivityBtn.addEventListener('click', testLdapConnectivity);
    console.log('LDAP test button event listener added');
  } else {
    console.error('LDAP test button not found!');
  }
  
  // LDAP enable/disable rule:
  // - If initially enabled -> allow disabling anytime
  // - If initially disabled -> require test to enable
  const ldapEnabledCheckbox = document.getElementById('ldapEnabled');
  if (ldapEnabledCheckbox) {
    if (ldapInitiallyEnabled) {
      ldapEnabledCheckbox.disabled = false; // allow disabling immediately
      console.log('LDAP initially enabled, allowing immediate disable');
    } else {
      ldapEnabledCheckbox.disabled = !ldapTestValidated;
      console.log('LDAP initially disabled, test validated:', ldapTestValidated);
      ldapEnabledCheckbox.addEventListener('click', function(e) {
        if (!ldapTestValidated) {
          e.preventDefault();
          console.log('Prevented LDAP enable without test validation');
        }
      });
    }
  }
  
  // Initialize password toggle buttons and set internationalized placeholders
  if (window.SettingsCore) {
    window.SettingsCore.initTogglePasswordButtons();
    // Set internationalized placeholders
    const elements = [
      { id: 'ldapBindDnTemplate', attr: 'data-i18n-placeholder' },
      { id: 'ldapUserFilter', attr: 'data-i18n-placeholder' },
      { id: 'ldapTestPasswordInput', attr: 'data-i18n-placeholder' },
      { id: 'ldapTestUsernameInput', attr: 'data-i18n-placeholder' },
      { id: 'sessionMaxAgeInput', attr: 'data-i18n-placeholder' },
      { id: 'maxLoginAttemptsInput', attr: 'data-i18n-placeholder' },
      { id: 'loginAttemptWindowInput', attr: 'data-i18n-placeholder' }
    ];
    
    elements.forEach(({ id, attr }) => {
      const el = document.getElementById(id);
      if (el && el.getAttribute(attr)) {
        el.placeholder = window.SettingsCore.getText(el.getAttribute(attr)) || el.placeholder;
      }
    });
  }
}

// Export functions for global access
window.saveLoginSettings = saveLoginSettings;
window.initLoginSettingsModule = initLoginSettingsModule;
