// Login Settings Module
// 登录设置模块

// Load LDAP configuration
async function loadLdapConfig() {
  try {
    const resp = await fetch('/auth/ldap-config');
    if (!resp.ok) return false;
    const cfg = await resp.json();
    document.getElementById('ldapEnabled').checked = !!cfg.ldap_enabled;
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

    updateLdapsUi();
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
  const payload = {
    ldap_enabled: document.getElementById('ldapEnabled').checked,
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
    ldap_tls_cacertfile: document.getElementById('ldapTlsCacertfile').value
  };
  
  const resp = await fetch('/auth/ldap-config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  
  if (!silent && window.SettingsCore) {
    if (resp.ok) {
      window.SettingsCore.showNotification(window.SettingsCore.getText('loginSettingsSaved'), 'success');
    } else {
      window.SettingsCore.showNotification(window.SettingsCore.getText('saveFailed'), 'error');
    }
  }
  
  return resp.ok;
}

// Generate LDAP test command
async function generateLdapTestCmd() {
  const protocol = document.getElementById('ldapProtocol').value || 'ldap';
  const host = document.getElementById('ldapHost').value || 'dc.example.com';
  const port = document.getElementById('ldapPort').value || (protocol === 'ldaps' ? '636' : '389');
  const baseDn = document.getElementById('ldapBaseDn').value || 'OU=Users,DC=example,DC=com';
  const tlsVerify = document.getElementById('ldapTlsVerify').checked;
  const cacert = document.getElementById('ldapTlsCacertfile').value;
  const username = prompt(window.SettingsCore ? window.SettingsCore.getText('enterTestUsernamePrompt') : '请输入测试用户名:', 'testuser');
  if (username === null) return;
  const template = document.getElementById('ldapBindDnTemplate').value || '{username}@example.com';
  const bindDnExample = template.replaceAll('{username}', username);
  const baseCmd = `ldapsearch -H ${protocol}://${host}:${port} -D "${bindDnExample}" -W -b "${baseDn}" -x -LLL`;
  const filter = '"(objectClass=*)"';
  const tlsPart = protocol === 'ldaps' ? (tlsVerify ? '' : ' -o tls_reqcert=never') : '';
  const cacertPart = (protocol === 'ldaps' && tlsVerify && cacert) ? ` LDAPTLS_CACERT=${cacert}` : '';
  const finalCmd = `${cacertPart ? cacertPart + ' ' : ''}${baseCmd}${tlsPart} ${filter}`;
  
  try {
    await navigator.clipboard.writeText(finalCmd);
    if (window.SettingsCore) {
      window.SettingsCore.showNotification(window.SettingsCore.getText('ldapTestCmdCopied'), 'success');
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
      
      const resp = await fetch('/auth/test-ldap', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload)
      });
      
      const text = await resp.text();
      modal.hide();
      
      if (window.SettingsCore) {
        if (resp.ok) {
          window.SettingsCore.showNotification(window.SettingsCore.getText('ldapConnectionTestSuccess'), 'success');
        } else {
          window.SettingsCore.showNotification(window.SettingsCore.getText('ldapConnectionTestFailed') + ': ' + text, 'error');
        }
      }
    } catch (e) {
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
document.addEventListener('DOMContentLoaded', () => {
  // Load LDAP configuration
  loadLdapConfig();
  
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
  
  // Initialize password toggle buttons
  if (window.SettingsCore) {
    window.SettingsCore.initTogglePasswordButtons();
  }
});

// Export functions for global access
window.saveLoginSettings = saveLoginSettings;
