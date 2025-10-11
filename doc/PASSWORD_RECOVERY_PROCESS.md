# Password Recovery Process

This document describes the password recovery process for CollabTrans, which allows administrators to reset the admin password to a default value when access is lost.

## Overview

The password recovery feature is designed as a safety mechanism for administrators who have lost access to their admin account. When enabled, it will automatically reset the admin password to `Changeme` (with capital C) on the next application startup.

## Security Considerations

⚠️ **Important Security Notes:**
- This feature should only be used in emergency situations
- The recovery process automatically disables itself after use for security
- The default password `Changeme` should be changed immediately after recovery
- This feature bypasses normal password strength requirements

## Configuration

### Enable Password Recovery

To enable password recovery, you need to modify the `local_config.json` file:

#### Windows Configuration Path
```
C:\Users\Public\collabtrans\local_config.json
```
or for development:
```
collabtrans\local_config.json
```

#### Linux Configuration Path
```
/opt/collabtrans/local_config.json
```
or for development:
```
~/workspace/collabtrans/local_config.json
```

### Configuration Steps

1. **Locate the configuration file** using the appropriate path above
2. **Open `local_config.json`** in a text editor
3. **Find the `security` section** and modify the `password_recovery` setting:

```json
{
  "security": {
    "max_login_attempts": 5,
    "login_attempt_window": 300,
    "rate_limit_window": 300,
    "password_recovery": true
  }
}
```

4. **Save the file**

## Recovery Process

### Step 1: Enable Recovery
1. Set `password_recovery: true` in `local_config.json`
2. Save the configuration file

### Step 2: Restart Application
1. **Windows:**
   - Stop the CollabTrans service: `net stop CollabTrans`
   - Start the service: `net start CollabTrans`
   - Or restart the application manually

2. **Linux:**
   - Stop the service: `sudo systemctl stop collabtrans`
   - Start the service: `sudo systemctl start collabtrans`
   - Or restart the application manually

### Step 3: Login with Default Password
1. Open the CollabTrans web interface
2. Login with the following credentials:
   - **Username:** `admin`
   - **Password:** `Changeme`

### Step 4: Change Password Immediately
1. After successful login, click on the user menu (Administrator dropdown)
2. Select "Change Password"
3. Set a new, strong password
4. The recovery feature is automatically disabled after use

## Verification

### Check Recovery Status
You can verify that password recovery was successful by checking the application logs:

#### Windows Log Location
```
C:\Users\Public\collabtrans\logs\app.log
```

#### Linux Log Location
```
/opt/collabtrans/logs/app.log
```

Look for these log messages:
- `Password recovery is enabled, resetting admin password...`
- `Admin password reset to 'Changeme' successfully.`
- `Password recovery disabled for security.`

### Verify Configuration Reset
After recovery, check that `local_config.json` has been updated:
```json
{
  "security": {
    "password_recovery": false
  }
}
```

## Troubleshooting

### Common Issues

#### 1. Recovery Not Working
- **Check file permissions:** Ensure the application has write access to `local_config.json`
- **Verify configuration:** Ensure `password_recovery: true` is set correctly
- **Check logs:** Look for error messages in the application logs

#### 2. Cannot Access Configuration File
- **Windows:** Run text editor as Administrator
- **Linux:** Use `sudo` to edit the file: `sudo nano /opt/collabtrans/local_config.json`

#### 3. Service Won't Start
- **Windows:** Check Windows Event Viewer for service errors
- **Linux:** Check systemd logs: `sudo journalctl -u collabtrans`

#### 4. Default Password Not Working
- Ensure you're using `Changeme` (capital C, not lowercase)
- Check that the recovery process completed successfully in logs
- Verify you're using the correct username: `admin`

### File Permissions

#### Windows
- The application typically runs with appropriate permissions
- If issues occur, ensure the CollabTrans service account has full control over `C:\Users\Public\collabtrans\`

#### Linux
- Ensure the collabtrans user has read/write access to the configuration directory:
```bash
sudo chown -R collabtrans:collabtrans /opt/collabtrans/
sudo chmod 644 /opt/collabtrans/local_config.json
```

## Alternative Recovery Methods

### Method 1: Direct Database/File Modification
If the recovery process fails, you can manually edit the user database:

#### Windows
```
C:\Users\Public\collabtrans\local_users.json
```

#### Linux
```
/opt/collabtrans/local_users.json
```

1. Stop the application
2. Edit `local_users.json`
3. Find the admin user entry
4. Replace the `password_hash` with a known hash for `Changeme`
5. Restart the application

### Method 2: Reinstall with Default Settings
As a last resort, you can reinstall CollabTrans with default settings, which will create a new admin account with the default password.

## Best Practices

1. **Regular Backups:** Keep backups of your configuration files
2. **Document Access:** Maintain a secure record of admin credentials
3. **Test Recovery:** Periodically test the recovery process in a safe environment
4. **Monitor Logs:** Regularly check application logs for security-related messages
5. **Strong Passwords:** Always use strong, unique passwords after recovery

## Security Recommendations

1. **Disable After Use:** The recovery feature automatically disables itself, but verify this
2. **Change Default Password:** Immediately change the default password after recovery
3. **Audit Access:** Review access logs after recovery to ensure no unauthorized access
4. **Update Documentation:** Keep this recovery process documented and accessible to authorized personnel only

## Support

If you encounter issues with the password recovery process:

1. Check the application logs for detailed error messages
2. Verify file permissions and paths
3. Ensure the application has proper write access to configuration files
4. Contact system administrator for assistance with service management

---

**Note:** This recovery process is designed for emergency access only. Regular password management should be done through the normal web interface after successful login.
