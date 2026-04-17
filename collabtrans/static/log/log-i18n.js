/**
 * Log message internationalization for frontend
 * Handles log message translation and display
 */

class LogI18n {
    constructor() {
        this.logMessages = {};
        this.currentLanguage = 'en';
        this.initialized = false;
    }

    /**
     * Initialize log i18n system
     */
    async init() {
        try {
            // Get log messages from backend
            const response = await fetch(apiUrl('/api/log-messages'));
            if (response.ok) {
                this.logMessages = await response.json();
                this.initialized = true;
                console.log('Log i18n initialized successfully');
            } else {
                console.warn('Failed to load log messages, using fallback');
            }
        } catch (error) {
            console.warn('Error initializing log i18n:', error);
        }
    }

    /**
     * Set current language for log messages (always English)
     * @param {string} language - Language code (ignored, always English)
     */
    async setLanguage(language) {
        // Logs are always in English
        this.currentLanguage = 'en';
        console.log('Log language is always English');
    }

    /**
     * Get localized log message
     * @param {string} key - Message key (e.g., 'app.startup.completed')
     * @param {Object} params - Parameters for message formatting
     * @returns {string} Localized message
     */
    getMessage(key, params = {}) {
        if (!this.initialized) {
            return key; // Fallback to key if not initialized
        }

        // Try current language first
        if (this.currentLanguage in this.logMessages) {
            const message = this.getMessageFromPath(key, this.logMessages[this.currentLanguage]);
            if (message) {
                return this.formatMessage(message, params);
            }
        }

        // Fallback to English
        if ('en' in this.logMessages) {
            const message = this.getMessageFromPath(key, this.logMessages['en']);
            if (message) {
                return this.formatMessage(message, params);
            }
        }

        // If not found, return the key
        return key;
    }

    /**
     * Get message from nested object path
     * @param {string} path - Dot-separated path (e.g., 'app.startup.completed')
     * @param {Object} obj - Object to search in
     * @returns {string|null} Message or null if not found
     */
    getMessageFromPath(path, obj) {
        const keys = path.split('.');
        let current = obj;
        
        for (const key of keys) {
            if (current && typeof current === 'object' && key in current) {
                current = current[key];
            } else {
                return null;
            }
        }
        
        return typeof current === 'string' ? current : null;
    }

    /**
     * Format message with parameters
     * @param {string} message - Message template
     * @param {Object} params - Parameters to substitute
     * @returns {string} Formatted message
     */
    formatMessage(message, params) {
        if (!params || Object.keys(params).length === 0) {
            return message;
        }

        return message.replace(/\{(\w+)\}/g, (match, key) => {
            return params[key] !== undefined ? params[key] : match;
        });
    }

    /**
     * Get available languages (always English)
     * @returns {Array} Array of available language codes
     */
    getAvailableLanguages() {
        return ['en'];
    }

    /**
     * Check if a message key exists
     * @param {string} key - Message key to check
     * @returns {boolean} True if key exists
     */
    hasMessage(key) {
        if (!this.initialized) return false;
        
        // Check current language
        if (this.currentLanguage in this.logMessages) {
            if (this.getMessageFromPath(key, this.logMessages[this.currentLanguage])) {
                return true;
            }
        }
        
        // Check English fallback
        if ('en' in this.logMessages) {
            return this.getMessageFromPath(key, this.logMessages['en']) !== null;
        }
        
        return false;
    }
}

// Global instance
window.logI18n = new LogI18n();

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.logI18n.init();
    // Logs are always in English, no need to listen for language changes
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = LogI18n;
}
