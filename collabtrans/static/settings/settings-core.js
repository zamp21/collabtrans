// Settings Core JavaScript
// 核心设置管理功能

// 全局变量 - 与主页保持一致的国际化实现
let i18nData = {
  zh: {
    init_i18n_failed_alert: '加载界面翻译资源失败，请检查网络连接或联系管理员。',
    init_failed_alert: '初始化失败，无法连接到后端服务。请检查服务是否运行或刷新页面。'
  },
  en: {
    init_i18n_failed_alert: 'Failed to load interface translations. Please check your network connection or contact an administrator.',
    init_failed_alert: 'Initialization failed, could not connect to the backend service. Please ensure the service is running and refresh the page.'
  }
};

let currentLang = 'zh';
let loadedModules = new Set();

// --- Theme Helper Functions ---
function setTheme(theme) {
  try {
    if (theme === 'auto') {
      const isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
      document.documentElement.setAttribute('data-bs-theme', isDark ? 'dark' : 'light');
    } else if (theme === 'dark' || theme === 'light') {
      document.documentElement.setAttribute('data-bs-theme', theme);
    } else {
      document.documentElement.setAttribute('data-bs-theme', 'auto');
    }
  } catch (_) {}
}

// --- I18N Helper Functions ---
const getText = (key, fallback = '') => {
  const translations = i18nData[currentLang] || i18nData.zh;
  return translations[key] || fallback || key;
};

function setLanguage(lang) {
  if (!i18nData[lang]) return;
  console.log('[I18N][settings] setLanguage called with:', lang);
  currentLang = lang;
  const translations = i18nData[lang];
  document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';

  // 与主页保持一致的国际化更新机制
  const i18nTargets = {
    'data-i18n': (el, text) => el.innerHTML = text,
    'data-i18n-placeholder': (el, text) => el.placeholder = text,
    'data-i18n-title': (el, text) => {
      if (el.tagName === 'TITLE') {
        el.textContent = text;
      } else {
        el.title = text;
        const tooltipInstance = bootstrap.Tooltip.getInstance(el);
        if (tooltipInstance) {
          tooltipInstance.setContent({'.tooltip-inner': text});
        }
      }
    }
  };

  Object.entries(i18nTargets).forEach(([attribute, updater]) => {
    document.querySelectorAll(`[${attribute}]`).forEach(el => {
      const key = el.getAttribute(attribute);
      if (translations[key] !== undefined) {
        updater(el, translations[key]);
      }
    });
  });

  // Debug: verify specific titles after applying i18n
  try {
    const petEls = document.querySelectorAll('[data-i18n="parsingEngineTitle"]');
    console.log('[I18N][settings][debug] parsingEngineTitle count =', petEls.length);
    petEls.forEach((el, idx) => {
      console.log('[I18N][settings][debug] parsingEngineTitle #' + idx, {
        expected: translations['parsingEngineTitle'],
        actual: el.textContent
      });
    });
    const genEls = document.querySelectorAll('[data-i18n="generalTitle"]');
    console.log('[I18N][settings][debug] generalTitle count =', genEls.length);
    genEls.forEach((el, idx) => {
      console.log('[I18N][settings][debug] generalTitle #' + idx, {
        expected: translations['generalTitle'],
        actual: el.textContent
      });
    });
  } catch (e) {}

  // 更新语言切换按钮状态
  document.querySelectorAll('.dropdown-menu a[data-lang]').forEach(a => {
    a.classList.remove('active');
    if (a.dataset.lang === lang) {
      a.classList.add('active');
    }
  });

  // 与主页保持一致的存储机制
  localStorage.setItem('ui_language', lang);
  
  // 同时保存到后端配置（与主页一致）
  if (typeof saveToConfig === 'function') {
    saveToConfig('ui_language', lang);
  }
}

async function initI18n() {
  // 与主页保持一致的语言检测机制
  let savedLang = localStorage.getItem('ui_language');
  console.log('[I18N][settings] localStorage.ui_language =', savedLang);
  
  if (!savedLang) {
    try {
      const resp = await fetch('/auth/app-config', { credentials: 'include' });
      if (resp.ok) {
        const cfg = await resp.json();
        console.log('[I18N][settings] backend default_language =', cfg.default_language);
        savedLang = cfg.default_language || 'en';
      }
    } catch (e) {
      console.warn('Failed to load language from backend config:', e);
    }
  }
  
  if (!savedLang) {
    const browserLang = (navigator.language || navigator.userLanguage || 'en').toLowerCase();
    savedLang = browserLang.startsWith('en') ? 'en' : 'zh';
    console.log('[I18N][settings] using browser fallback =', browserLang, '=>', savedLang);
  }
  
  console.log('[I18N][settings] final resolved language =', savedLang);
  setLanguage(savedLang);
  // Sync theme from home page
  try {
    const savedTheme = localStorage.getItem('theme') || 'auto';
    setTheme(savedTheme);
  } catch (e) {}
}

// Load i18n data from settings directory
async function loadI18nData() {
  try {
    // Change to load from settings directory
    const response = await fetch('/i18n/i18nSettings.json', { cache: 'no-store' });
    if (!response.ok) throw new Error('Failed to load i18n data');
    i18nData = await response.json();
    console.log('[I18N][settings] i18nSettings.json loaded. Languages:', Object.keys(i18nData));
    await initI18n();
  } catch (error) {
    console.error('Failed to load i18n data:', error);
    await initI18n();
    alert(getText('init_i18n_failed_alert'));
  }
}

// --- Settings Navigation ---
function initSettingsNavigation() {
  const navLinks = document.querySelectorAll('.settings-nav .nav-link');
  const sections = document.querySelectorAll('.settings-section');

  navLinks.forEach(link => {
    link.addEventListener('click', async (e) => {
      e.preventDefault();
      
      // Remove active class from all links and sections
      navLinks.forEach(l => l.classList.remove('active'));
      sections.forEach(s => s.classList.remove('active'));
      
      // Add active class to clicked link
      link.classList.add('active');
      
      // Show corresponding section
      const sectionId = link.getAttribute('data-section');
      const targetSection = document.getElementById(`${sectionId}-section`);
      if (targetSection) {
        targetSection.classList.add('active');
        
        // Load module content if not already loaded
        await loadModuleContent(sectionId);
      }
    });
  });
}

// --- Module Loading ---
async function loadModuleContent(moduleName) {
  if (loadedModules.has(moduleName)) {
    return; // Already loaded
  }

  const contentDiv = document.getElementById(`${moduleName}-content`);
  if (!contentDiv) return;

  try {
    const response = await fetch(`/static/settings/${moduleName}.html`, { cache: 'no-store' });
    if (!response.ok) {
      throw new Error(`Failed to load ${moduleName} module`);
    }
    
    const html = await response.text();
    contentDiv.innerHTML = html;
    // Apply i18n to newly injected content
    try { setLanguage(currentLang); } catch (_) {}
    
    // Load corresponding JavaScript module
    const script = document.createElement('script');
    const ts = Date.now();
    script.src = `/static/settings/${moduleName}.js?v=${ts}`;
    script.onload = () => {
      loadedModules.add(moduleName);
      console.log(`Module ${moduleName} loaded successfully`);
      
      // Call module-specific initialization if available with a small delay
      setTimeout(() => {
        try { setLanguage(currentLang); } catch (_) {}
        if (moduleName === 'ai-platforms' && window.initAiPlatformModule) {
          console.log(`Calling ${moduleName} initialization`);
          window.initAiPlatformModule();
        } else if (moduleName === 'general' && window.initGeneralModule) {
          console.log(`Calling ${moduleName} initialization`);
          window.initGeneralModule();
        } else if (moduleName === 'login-settings' && window.initLoginSettingsModule) {
          console.log(`Calling ${moduleName} initialization`);
          window.initLoginSettingsModule();
        } else if (moduleName === 'message-settings' && window.initMessageSettingsModule) {
          console.log(`Calling ${moduleName} initialization`);
          window.initMessageSettingsModule();
        } else if (moduleName === 'parsing-engines' && window.initParsingEnginesModule) {
          console.log(`Calling ${moduleName} initialization`);
          window.initParsingEnginesModule();
        } else if (moduleName === 'web-settings' && window.initWebSettingsModule) {
          console.log(`Calling ${moduleName} initialization`);
          window.initWebSettingsModule();
        } else if (moduleName === 'certificate-settings' && window.initCertificateSettingsModule) {
          console.log(`Calling ${moduleName} initialization`);
          window.initCertificateSettingsModule();
        } else if (moduleName === 'prompts' && window.initPromptsModule) {
          console.log(`Calling ${moduleName} initialization`);
          window.initPromptsModule();
        } else if (moduleName === 'glossary' && window.initGlossaryModule) {
          console.log(`Calling ${moduleName} initialization`);
          window.initGlossaryModule();
        }
      }, 50);
    };
    script.onerror = () => {
      console.error(`Failed to load JavaScript for module ${moduleName}`);
    };
    document.head.appendChild(script);
    
  } catch (error) {
    console.error(`Error loading module ${moduleName}:`, error);
    const failText = getText('moduleLoadFailed', 'Failed to load module');
    contentDiv.innerHTML = `
      <div class="alert alert-danger">
        <i class="bi bi-exclamation-triangle me-2"></i>
        ${failText}: ${error.message}
      </div>
    `;
  }
}

// --- Notification System ---
function showNotification(message, type = 'info') {
  const alertClass = {
    'success': 'alert-success',
    'error': 'alert-danger',
    'warning': 'alert-warning',
    'info': 'alert-info'
  }[type] || 'alert-info';

  const notification = document.createElement('div');
  notification.className = `alert ${alertClass} alert-dismissible fade show position-fixed`;
  notification.style.cssText = 'top: 20px; left: 50%; transform: translateX(-50%); z-index: 9999; min-width: 300px;';
  notification.innerHTML = `
    ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
  `;

  document.body.appendChild(notification);

  // Auto remove after 5 seconds
  setTimeout(() => {
    if (notification.parentNode) {
      notification.remove();
    }
  }, 5000);
}

// --- Password Toggle ---
function initTogglePasswordButtons() {
  console.log('[DEBUG] initTogglePasswordButtons - starting initialization');
  const toggleButtons = document.querySelectorAll('.toggle-password');
  console.log('[DEBUG] initTogglePasswordButtons - found toggle buttons:', toggleButtons.length);
  
  toggleButtons.forEach((button, index) => {
    const targetId = button.getAttribute('data-target');
    const passwordInput = document.getElementById(targetId);
    const icon = button.querySelector('i');

    console.log(`[DEBUG] initTogglePasswordButtons - button ${index}: target=${targetId}, input exists=${!!passwordInput}, icon exists=${!!icon}`);

    if (!passwordInput || !icon) {
      console.warn(`[DEBUG] initTogglePasswordButtons - button ${index} missing target or icon`);
      return;
    }

    button.addEventListener('click', async () => {
      console.log(`[DEBUG] toggle-password button clicked for target: ${targetId}`);
      if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        icon.classList.remove('bi-eye-slash');
        icon.classList.add('bi-eye');
        
        if ((targetId === 'platformApiKey' || targetId === 'mineruApiKey') && passwordInput.value && passwordInput.value.includes('***')) {
          try {
            const resp = await fetch('/auth/app-config/raw-secrets');
            if (resp.ok) {
              const secrets = await resp.json();
              console.log(`[DEBUG] Raw secrets response:`, secrets);
              
              if (targetId === 'platformApiKey') {
                const currentPlatform = document.getElementById('platformSelect').value;
                console.log(`[DEBUG] Detected masked API key, fetching real key for platform: ${currentPlatform}`);
                console.log(`[DEBUG] Current masked value: "${passwordInput.value}"`);
                console.log(`[DEBUG] Input type: ${passwordInput.type}`);
                console.log(`[DEBUG] Available platforms:`, Object.keys(secrets.platform_api_keys || {}));
                
                const apiKey = secrets.platform_api_keys?.[currentPlatform];
                if (apiKey) {
                  console.log(`[DEBUG] Found API key for platform ${currentPlatform}, length: ${apiKey.length}`);
                  passwordInput.value = apiKey;
                  console.log(`[DEBUG] Real API key loaded for platform: ${currentPlatform}`);
                } else {
                  console.log(`[DEBUG] No API key found for platform: ${currentPlatform}`);
                  console.log(`[DEBUG] Available platforms:`, Object.keys(secrets.platform_api_keys || {}));
                }
              } else if (targetId === 'mineruApiKey') {
                console.log(`[DEBUG] Detected masked MinerU API key, fetching real key`);
                console.log(`[DEBUG] Current masked value: "${passwordInput.value}"`);
                
                const mineruToken = secrets.translator_mineru_token;
                if (mineruToken) {
                  console.log(`[DEBUG] Found MinerU token, length: ${mineruToken.length}`);
                  passwordInput.value = mineruToken;
                  console.log(`[DEBUG] Real MinerU token loaded`);
                } else {
                  console.log(`[DEBUG] No MinerU token found`);
                }
              }
            } else {
              console.error(`[DEBUG] Failed to fetch raw secrets: ${resp.status}`);
            }
          } catch (error) {
            console.error('[DEBUG] Error fetching raw API key:', error);
          }
        }
      } else {
        passwordInput.type = 'password';
        icon.classList.remove('bi-eye');
        icon.classList.add('bi-eye-slash');
        
        if ((targetId === 'platformApiKey' || targetId === 'mineruApiKey') && passwordInput.value && !passwordInput.value.includes('***')) {
          const maskedKey = passwordInput.value.substring(0, 8) + '***';
          passwordInput.value = maskedKey;
          if (targetId === 'platformApiKey') {
            console.log(`[DEBUG] API key masked for platform: ${document.getElementById('platformSelect').value}`);
          } else if (targetId === 'mineruApiKey') {
            console.log(`[DEBUG] MinerU API key masked`);
          }
        }
      }
    });
  });
}

// --- Save All Settings ---
async function saveAllSettings() {
  const saveAllBtn = document.getElementById('saveAllBtn');
  if (saveAllBtn) {
    saveAllBtn.disabled = true;
    saveAllBtn.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>保存中...';
  }

  try {
    // Call save functions from loaded modules
    const savePromises = [];
    
    if (loadedModules.has('general') && window.saveGeneralSettings) {
      savePromises.push(window.saveGeneralSettings());
    }
    
    if (loadedModules.has('ai-platforms') && window.saveAiPlatformConfig) {
      savePromises.push(window.saveAiPlatformConfig());
    }
    
    if (loadedModules.has('parsing-engines') && window.saveParsingEngineConfig) {
      savePromises.push(window.saveParsingEngineConfig());
    }
    
    if (loadedModules.has('login-settings') && window.saveLoginSettings) {
      savePromises.push(window.saveLoginSettings(true));
    }
    
    if (loadedModules.has('message-settings') && window.saveMessageSettings) {
      savePromises.push(window.saveMessageSettings(true));
    }
    
    if (loadedModules.has('web-settings') && window.saveWebSettings) {
      savePromises.push(window.saveWebSettings());
    }
    
    if (loadedModules.has('certificate-settings') && window.saveCertificateSettings) {
      savePromises.push(window.saveCertificateSettings());
    }

    const results = await Promise.allSettled(savePromises);
    const successCount = results.filter(r => r.status === 'fulfilled' && r.value).length;
    const totalCount = results.length;

    if (successCount === totalCount) {
      showNotification(getText('saveAllSuccess', 'All settings saved successfully!'), 'success');
    } else {
      const msgTpl = getText('saveAllPartial', 'Partially saved ({success}/{total})');
      const msg = msgTpl.replace('{success}', successCount).replace('{total}', totalCount);
      showNotification(msg, 'warning');
    }

  } catch (error) {
    console.error('Error saving settings:', error);
    showNotification(getText('saveAllError', 'Error occurred while saving settings'), 'error');
  } finally {
    if (saveAllBtn) {
      saveAllBtn.disabled = false;
      const label = getText('saveAllBtn', 'Save All Settings');
      saveAllBtn.innerHTML = `<i class="bi bi-check-circle me-2"></i>${label}`;
    }
  }
}

// 语言切换功能已移除，因为settings页面不再需要独立的语言切换按钮

// --- Language Synchronization ---
function initLanguageSync() {
  // 监听主页的语言切换事件
  window.addEventListener('languageChanged', (e) => {
    const newLang = e.detail.language;
    if (newLang && newLang !== currentLang && i18nData[newLang]) {
      console.log('Language changed via custom event:', currentLang, '->', newLang);
      currentLang = newLang;
      setLanguage(newLang);
    }
  });
  
  // 监听localStorage变化（跨标签页/窗口同步）
  window.addEventListener('storage', (e) => {
    if (e.key === 'ui_language' && e.newValue !== e.oldValue) {
      console.log('Language changed via storage event:', e.oldValue, '->', e.newValue);
      if (e.newValue && e.newValue !== currentLang && i18nData[e.newValue]) {
        currentLang = e.newValue;
        setLanguage(e.newValue);
      }
    }
  });
  
  // 定期检查语言变化（作为备用机制）
  setInterval(() => {
    const storedLang = localStorage.getItem('ui_language');
    if (storedLang && storedLang !== currentLang && i18nData[storedLang]) {
      console.log('Language sync detected via polling:', currentLang, '->', storedLang);
      currentLang = storedLang;
      setLanguage(storedLang);
    }
  }, 2000);
}

// --- Main Initialization ---
async function initSettings() {
  try {
    // Load i18n data first
    await loadI18nData();
    
    // Initialize language synchronization
    initLanguageSync();
    
    // Initialize navigation
    initSettingsNavigation();
    
    // Initialize password toggle buttons
    initTogglePasswordButtons();
    
    // Load default module (general)
    await loadModuleContent('general');
    
    // Setup save all button - 已注释，因为每个子模块都有独立的保存按钮
    /*
    const saveAllBtn = document.getElementById('saveAllBtn');
    if (saveAllBtn) {
      saveAllBtn.addEventListener('click', saveAllSettings);
    }
    */
    
    console.log('Settings initialized successfully');
    
  } catch (error) {
    console.error('Failed to initialize settings:', error);
    showNotification('初始化设置页面失败', 'error');
  }
}

// Export functions for use by modules
window.SettingsCore = {
  getText,
  setLanguage,
  showNotification,
  initTogglePasswordButtons,
  loadedModules
};
