# Log Internationalization Guide

## Overview

This guide explains how to use the log internationalization (i18n) system that supports both backend and frontend log message translation.

## Architecture

```
Backend (Python)                    Frontend (JavaScript)
├── LogMessageManager               ├── LogI18n class
├── I18nLogger wrapper              ├── Message translation
├── JSON message files              ├── Real-time log display
└── API endpoints                   └── Language switching
```

## Backend Usage

### 1. Using I18nLogger

```python
from collabtrans.logger.logger import i18n_logger

# Simple message
i18n_logger.info("app.startup.completed")

# Message with parameters
i18n_logger.error("app.startup.cleanup_task_failed", error=str(e))

# Different log levels
i18n_logger.debug("translation.agent.prompt_sent", model="gpt-4")
i18n_logger.warning("performance.issue.detected", issue="slow_response")
i18n_logger.critical("system.critical.error", error="database_down")
```

### 2. Message Key Structure

Message keys follow a hierarchical structure:

```
category.subcategory.specific_message
```

Examples:
- `app.startup.completed` - Application startup completion
- `translation.task.failed` - Translation task failure
- `conversion.pdf2docx.processing` - PDF to DOCX conversion
- `font.selection.applied` - Font selection applied
- `logging.config.level_changed` - Log level configuration change

### 3. Adding New Messages

1. **Add to JSON files**:
   ```json
   // log_i18n_en.json
   {
     "new_category": {
       "new_message": "New message in English"
     }
   }
   
   // log_i18n_zh.json
   {
     "new_category": {
       "new_message": "新消息（中文）"
     }
   }
   ```

2. **Use in code**:
   ```python
   i18n_logger.info("new_category.new_message")
   ```

### 4. Message Parameters

Use `{parameter_name}` syntax for dynamic content:

```json
{
  "app": {
    "startup": {
      "api_docs": "Service API documentation: {url}"
    }
  }
}
```

```python
i18n_logger.info("app.startup.api_docs", url="http://localhost:8000/docs")
```

## Frontend Usage

### 1. Initialize Log I18n

```javascript
// Initialize (automatically done on DOM ready)
await window.logI18n.init();

// Set language
await window.logI18n.setLanguage('zh'); // or 'en', 'ja'
```

### 2. Get Localized Messages

```javascript
// Simple message
const message = window.logI18n.getMessage('app.startup.completed');

// Message with parameters
const message = window.logI18n.getMessage('app.startup.api_docs', {
    url: 'http://localhost:8000/docs'
});

// Check if message exists
if (window.logI18n.hasMessage('app.startup.completed')) {
    // Message exists
}
```

### 3. Real-time Log Display

```javascript
// Example: Display log messages in real-time
function displayLogMessage(logData) {
    const message = window.logI18n.getMessage(logData.key, logData.params);
    const logElement = document.getElementById('log-area');
    logElement.innerHTML += `<div class="log-entry">${message}</div>`;
}

// Listen for log updates
window.addEventListener('logUpdate', (event) => {
    displayLogMessage(event.detail);
});
```

### 4. Language Switching

```javascript
// Switch log language
async function switchLogLanguage(language) {
    await window.logI18n.setLanguage(language);
    
    // Refresh displayed logs
    refreshLogDisplay();
}

// Get available languages
const languages = window.logI18n.getAvailableLanguages();
console.log('Available languages:', languages); // ['en', 'zh', 'ja']
```

## Configuration

### 1. Language Detection

The system automatically detects language from global config:

```python
# In global_config.json
{
  "default_language": "zh"  # Will set log language to Chinese
}
```

### 2. Manual Language Setting

```python
from collabtrans.i18n.log_messages import set_log_language

# Set specific language
set_log_language('en')  # English
set_log_language('zh')  # Chinese
set_log_language('ja')  # Japanese
```

## File Structure

```
collabtrans/
├── i18n/
│   ├── __init__.py
│   ├── log_messages.py          # Core i18n manager
│   ├── log_i18n_en.json        # English messages
│   ├── log_i18n_zh.json        # Chinese messages
│   └── log_i18n_ja.json        # Japanese messages (optional)
├── logger/
│   └── logger.py               # I18nLogger class
└── static/
    └── js/
        └── log-i18n.js         # Frontend i18n support
```

## API Endpoints

### GET /api/log-messages
Returns all log messages in all available languages.

**Response:**
```json
{
  "en": {
    "app": {
      "startup": {
        "completed": "Application startup completed..."
      }
    }
  },
  "zh": {
    "app": {
      "startup": {
        "completed": "应用启动完成..."
      }
    }
  }
}
```

### POST /api/log-language
Sets the log language for the current session.

**Request:**
```json
"zh"
```

**Response:**
```json
{
  "status": "success",
  "language": "zh"
}
```

## Best Practices

### 1. Message Key Naming
- Use descriptive, hierarchical names
- Follow the pattern: `category.subcategory.specific`
- Use lowercase with dots as separators

### 2. Message Content
- Keep messages concise but informative
- Use parameters for dynamic content
- Avoid technical jargon in user-facing messages

### 3. Error Handling
- Always provide fallback messages
- Use English as the default fallback
- Log i18n errors separately from application errors

### 4. Performance
- Initialize i18n system early
- Cache frequently used messages
- Use lazy loading for large message sets

## Troubleshooting

### Common Issues

1. **Message not found**
   - Check if the key exists in JSON files
   - Verify the key path is correct
   - Ensure the language file is loaded

2. **Parameters not substituted**
   - Check parameter names match `{name}` in message
   - Verify parameters are passed correctly
   - Ensure parameter values are not undefined

3. **Language not switching**
   - Check if language is supported
   - Verify API endpoint is accessible
   - Ensure frontend and backend are synchronized

### Debug Mode

Enable debug logging to troubleshoot i18n issues:

```python
import logging
logging.getLogger('collabtrans.i18n').setLevel(logging.DEBUG)
```

## Migration Guide

### From Hardcoded Messages

**Before:**
```python
print("Application startup completed")
logger.info("Translation task failed: " + str(error))
```

**After:**
```python
i18n_logger.info("app.startup.completed")
i18n_logger.error("translation.task.failed", error=str(error))
```

### Adding New Languages

1. Create new JSON file: `log_i18n_[lang].json`
2. Add language to `LogMessageManager._load_log_messages()`
3. Update frontend language selector
4. Test with new language

## Examples

### Complete Backend Example

```python
from collabtrans.logger.logger import i18n_logger

class TranslationService:
    def __init__(self):
        self.logger = i18n_logger
    
    def translate_document(self, document):
        try:
            self.logger.info("translation.task.started")
            
            # Translation logic here
            result = self.perform_translation(document)
            
            self.logger.info("translation.task.completed")
            return result
            
        except Exception as e:
            self.logger.error("translation.task.failed", error=str(e))
            raise
```

### Complete Frontend Example

```javascript
class LogDisplay {
    constructor() {
        this.logContainer = document.getElementById('log-container');
        this.init();
    }
    
    async init() {
        await window.logI18n.init();
        this.setupLogListener();
    }
    
    setupLogListener() {
        // Listen for real-time log updates
        window.addEventListener('logUpdate', (event) => {
            this.addLogEntry(event.detail);
        });
    }
    
    addLogEntry(logData) {
        const message = window.logI18n.getMessage(logData.key, logData.params);
        const timestamp = new Date().toLocaleTimeString();
        
        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry';
        logEntry.innerHTML = `
            <span class="timestamp">${timestamp}</span>
            <span class="level">${logData.level}</span>
            <span class="message">${message}</span>
        `;
        
        this.logContainer.appendChild(logEntry);
        this.logContainer.scrollTop = this.logContainer.scrollHeight;
    }
}

// Initialize log display
new LogDisplay();
```
