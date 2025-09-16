// Test script to debug LDAP UI issues
console.log("Testing LDAP UI functionality...");

// Simulate the loadAuthConfig function
async function testLoadAuthConfig() {
    try {
        const response = await fetch('/auth/config', {
            method: 'GET',
            credentials: 'include'
        });
        
        if (response.ok) {
            const config = await response.json();
            console.log("LDAP Config loaded:", config);
            
            // Test if elements exist
            const ldapEnabledSwitch = document.getElementById('ldapEnabledSwitch');
            const ldapConfigGroup = document.getElementById('ldapConfigGroup');
            const defaultUserConfigGroup = document.getElementById('defaultUserConfigGroup');
            
            console.log("ldapEnabledSwitch:", ldapEnabledSwitch);
            console.log("ldapConfigGroup:", ldapConfigGroup);
            console.log("defaultUserConfigGroup:", defaultUserConfigGroup);
            
            if (ldapEnabledSwitch && ldapConfigGroup && defaultUserConfigGroup) {
                console.log("All required elements found");
                
                // Test UI update
                ldapEnabledSwitch.checked = config.ldap_enabled || false;
                
                if (ldapEnabledSwitch.checked) {
                    ldapConfigGroup.style.display = 'block';
                    defaultUserConfigGroup.style.display = 'none';
                    console.log("LDAP config should be visible");
                } else {
                    ldapConfigGroup.style.display = 'none';
                    defaultUserConfigGroup.style.display = 'block';
                    console.log("Default user config should be visible");
                }
            } else {
                console.error("Missing required elements");
            }
        } else {
            console.error("Failed to load config:", response.status, response.statusText);
        }
    } catch (error) {
        console.error("Error loading config:", error);
    }
}

// Run test
testLoadAuthConfig();
