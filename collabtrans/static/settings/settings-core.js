// Settings Core JavaScript
// 核心设置管理功能

// 全局变量
let i18nData = null;
let currentLang = 'zh';
let loadedModules = new Set();
let settingsUserPermissions = null; // cached permissions for settings page
let isInitialized = false; // 防止重复初始化

// --- I18N System ---
class I18nManager {
  constructor() {
    this.data = null;
    this.currentLang = 'zh';
    this.isLoaded = false;
  }

  async load() {
    try {
      console.log('[I18n] Loading i18n data...');
      const response = await fetch('/i18n/i18nData.json', { cache: 'no-store' });
      if (!response.ok) {
        throw new Error(`Failed to load i18n data: ${response.statusText}`);
      }
      this.data = await response.json();
      this.isLoaded = true;
      console.log('[I18n] i18n data loaded successfully');
      console.log('[I18n] Available languages:', Object.keys(this.data));
      return true;
    } catch (error) {
      console.warn('[I18n] Failed to load i18n data:', error);
      this.data = this.getFallbackData();
      this.isLoaded = true;
      return false;
    }
  }

  getFallbackData() {
    return {
      zh: {
        init_i18n_failed_alert: '加载界面翻译资源失败，请检查网络连接或联系管理员。',
        init_failed_alert: '初始化失败，无法连接到后端服务。请检查服务是否运行或刷新页面。'
      },
      en: {
        init_i18n_failed_alert: 'Failed to load interface translations. Please check your network connection or contact an administrator.',
        init_failed_alert: 'Initialization failed, could not connect to the backend service. Please ensure the service is running and refresh the page.'
      }
    };
  }

  getText(key, fallback = '') {
    if (!this.isLoaded || !this.data) {
      return fallback || key;
    }
    const translations = this.data[this.currentLang] || this.data.zh;
    return translations[key] || fallback || key;
  }

  setLanguage(lang) {
    console.log('[I18n] Setting language to:', lang);
    
    if (!this.isLoaded || !this.data) {
      console.warn('[I18n] i18n data not loaded yet');
      return false;
    }

    if (!this.data[lang]) {
      console.warn(`[I18n] Language ${lang} not available`);
      console.warn('[I18n] Available languages:', Object.keys(this.data));
      return false;
    }

    this.currentLang = lang;
    document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
    
    this.applyTranslations();
    console.log(`[I18n] Language set to ${lang}`);
    return true;
  }

  applyTranslations() {
    if (!this.isLoaded || !this.data) return;

    const translations = this.data[this.currentLang];
    
    // Apply translations to data-i18n attributes
    document.querySelectorAll('[data-i18n]').forEach(element => {
      const key = element.getAttribute('data-i18n');
      if (translations[key]) {
        element.textContent = translations[key];
      }
    });

    // Apply translations to data-i18n-placeholder attributes
    document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
      const key = element.getAttribute('data-i18n-placeholder');
      if (translations[key]) {
        element.placeholder = translations[key];
      }
    });

    // Apply translations to data-i18n-title attributes
    document.querySelectorAll('[data-i18n-title]').forEach(element => {
      const key = element.getAttribute('data-i18n-title');
      if (translations[key]) {
        element.title = translations[key];
      }
    });
  }

  getCurrentLanguage() {
    return this.currentLang;
  }

  isLanguageAvailable(lang) {
    return this.isLoaded && this.data && this.data[lang];
  }
}

// 创建全局i18n管理器实例
const i18n = new I18nManager();

// 兼容性函数
const getText = (key, fallback = '') => i18n.getText(key, fallback);

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

// --- Notification System ---
function showNotification(message, type = 'info') {
  const alertClass = type === 'success' ? 'alert-success' : 
                   type === 'error' ? 'alert-danger' : 'alert-info';
  
  const notification = document.createElement('div');
  notification.className = `alert ${alertClass} alert-dismissible fade show position-fixed`;
  notification.style.cssText = 'top: 20px; left: 50%; transform: translateX(-50%); z-index: 9999;';
  notification.innerHTML = `
    ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
  `;
  document.body.appendChild(notification);
  
  setTimeout(() => {
    notification.remove();
  }, 3000);
}

// --- Password Toggle System ---
function initTogglePasswordButtons() {
  document.querySelectorAll('.toggle-password').forEach(button => {
    button.addEventListener('click', function() {
      const targetId = this.getAttribute('data-target');
      const targetInput = document.getElementById(targetId);
      const icon = this.querySelector('i');
      
      if (targetInput && icon) {
        if (targetInput.type === 'password') {
          targetInput.type = 'text';
          icon.className = 'bi bi-eye';
        } else {
          targetInput.type = 'password';
          icon.className = 'bi bi-eye-slash';
        }
      }
    });
  });
}

// --- Settings Navigation ---
function initSettingsNavigation() {
  const navLinks = document.querySelectorAll('.nav-link[data-section]');
  const contentSections = document.querySelectorAll('.settings-section');
  
  console.log('[Settings] Found navigation links:', navLinks.length);
  console.log('[Settings] Found content sections:', contentSections.length);
  
  navLinks.forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      console.log('[Settings] Navigation link clicked:', link.getAttribute('data-section'));
      
      // Remove active class from all links
      navLinks.forEach(l => l.classList.remove('active'));
      
      // Add active class to clicked link
      link.classList.add('active');
      
      // Hide all content sections
      contentSections.forEach(section => {
        section.classList.remove('active');
        section.style.display = 'none';
      });
      
      // Show target content section
      const sectionName = link.getAttribute('data-section');
      const targetSection = document.getElementById(`${sectionName}-section`);
      if (targetSection) {
        targetSection.classList.add('active');
        targetSection.style.display = 'block';
        console.log('[Settings] Showing section:', sectionName);
        
        // Load module content if needed
        loadModuleContent(sectionName);
      } else {
        console.warn('[Settings] Target section not found:', sectionName);
      }
    });
  });
}

// --- Module Loading System ---
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
    
    // Apply i18n to newly loaded content
    i18n.applyTranslations();
    
    // Load corresponding JavaScript module
    const script = document.createElement('script');
    const ts = Date.now();
    script.src = `/static/settings/${moduleName}.js?v=${ts}`;
    script.onload = () => {
      loadedModules.add(moduleName);
      console.log(`Module ${moduleName} loaded successfully`);
      
      // Call module-specific initialization if available
      setTimeout(() => {
        if (moduleName === 'users' && window.initUsersModule) {
          window.initUsersModule();
        } else if (moduleName === 'banner-settings' && window.initBannerSettingsModule) {
          window.initBannerSettingsModule();
        } else if (moduleName === 'general' && window.initGeneralModule) {
          window.initGeneralModule();
        } else if (moduleName === 'ai-platforms' && window.initAiPlatformModule) {
          window.initAiPlatformModule();
        } else if (moduleName === 'parsing-engines' && window.initParsingEnginesModule) {
          window.initParsingEnginesModule();
        } else if (moduleName === 'login-settings' && window.initLoginSettingsModule) {
          window.initLoginSettingsModule();
        } else if (moduleName === 'web-settings' && window.initWebSettingsModule) {
          window.initWebSettingsModule();
        }
      }, 50);
    };
    script.onerror = () => {
      console.error(`Failed to load JavaScript for module ${moduleName}`);
    };
    document.head.appendChild(script);
    
  } catch (error) {
    console.error(`Error loading module ${moduleName}:`, error);
    const failText = i18n.getText('moduleLoadFailed', 'Failed to load module');
    contentDiv.innerHTML = `
      <div class="alert alert-danger">
        <i class="bi bi-exclamation-triangle me-2"></i>
        ${failText}: ${error.message}
      </div>
    `;
  }
}

// --- User Permissions ---
async function loadUserPermissionsForSettings() {
  try {
    const response = await fetch('/auth/user-permissions', { credentials: 'include' });
    if (response.ok) {
      settingsUserPermissions = await response.json();
      console.log('[Settings] User permissions loaded:', settingsUserPermissions);
      
      // Control Users tab visibility based on permissions
      const usersTab = document.querySelector('[data-target="users-content"]');
      if (usersTab && settingsUserPermissions) {
        const canManageUsers = settingsUserPermissions.is_admin || 
                              settingsUserPermissions.is_local_admin || 
                              settingsUserPermissions.is_local_app_admin;
        usersTab.style.display = canManageUsers ? 'block' : 'none';
      }
    }
  } catch (error) {
    console.error('[Settings] Failed to load user permissions:', error);
  }
}

// --- Language Change Listeners ---
function setupLanguageChangeListeners() {
  // Listen for language changes from main page via localStorage
  window.addEventListener('storage', (e) => {
    console.log('[Settings] Storage event received:', e.key, e.newValue);
    if (e.key === 'currentLanguage' && e.newValue) {
      console.log('[Settings] Language changed via storage to:', e.newValue);
      i18n.setLanguage(e.newValue);
    }
  });
  
  // Listen for custom language change events
  window.addEventListener('languageChanged', (e) => {
    console.log('[Settings] Language changed via custom event:', e.detail);
    if (e.detail) {
      i18n.setLanguage(e.detail);
    }
  });
}

// --- Main Initialization ---
async function initSettings() {
  if (isInitialized) {
    console.log('[Settings] Already initialized, skipping...');
    return;
  }
  
  try {
    console.log('[Settings] Initializing settings page...');
    isInitialized = true;
    
    // Load i18n data first
    await i18n.load();
    
    // Get current language from localStorage or default to Chinese
    // Check both possible keys for compatibility
    const savedLang = localStorage.getItem('currentLanguage') || 
                     localStorage.getItem('ui_language') || 
                     'zh';
    console.log('[Settings] Current language from localStorage:', savedLang);
    
    // Set initial language
    i18n.setLanguage(savedLang);
    
    // Initialize navigation
    initSettingsNavigation();
    
    // Initialize password toggle buttons
    initTogglePasswordButtons();
  
    // Load permissions and control Users tab visibility
    await loadUserPermissionsForSettings();
    
    // Load default module (general)
    await loadModuleContent('general');
    
    // Setup language change listeners
    setupLanguageChangeListeners();
    
    // Debug: Check current localStorage value
    console.log('[Settings] Current localStorage currentLanguage:', localStorage.getItem('currentLanguage'));
    console.log('[Settings] All localStorage keys:', Object.keys(localStorage));
    
    console.log('[Settings] Settings initialized successfully');
    
  } catch (error) {
    console.error('[Settings] Failed to initialize settings:', error);
    showNotification('初始化设置页面失败', 'error');
  }
}

// Export functions for use by modules
window.SettingsCore = {
  getText,
  setLanguage: (lang) => i18n.setLanguage(lang),
  showNotification,
  initTogglePasswordButtons,
  loadedModules,
  get currentLang() { return i18n.getCurrentLanguage(); }, // Getter for current language
  i18n
};

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initSettings);
} else {
  initSettings();
}