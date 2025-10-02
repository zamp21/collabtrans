// Certificate Settings Module
let certificateModal = null;

async function loadCertificateList() {
    try {
        const resp = await fetch('/auth/certificate-list', { credentials: 'include' });
        if (!resp.ok) {
            throw new Error(`HTTP ${resp.status}`);
        }
        const data = await resp.json();
        
        const listElement = document.getElementById('certificateList');
        if (data.certificates && data.certificates.length > 0) {
            let html = '<div class="table-responsive"><table class="table table-sm">';
            html += '<thead><tr><th data-i18n="certificateFile">File</th><th data-i18n="certificateType">Type</th><th data-i18n="certificateSize">Size</th><th data-i18n="certificateModified">Modified</th><th data-i18n="certificateValidity">Validity</th></tr></thead>';
            html += '<tbody>';
            
            data.certificates.forEach(cert => {
                let validityCell = '';
                if (cert.type === 'cert' && cert.valid_until) {
                    const badgeClass = cert.is_expired ? 'danger' : 'success';
                    validityCell = `<td>
                        <span class="badge bg-${badgeClass}">${cert.days_left}</span>
                        <br><small class="text-muted">${cert.valid_until}</small>
                    </td>`;
                } else {
                    validityCell = '<td><span class="text-muted">-</span></td>';
                }
                
                html += `<tr>
                    <td><i class="bi bi-file-earmark-${cert.type === 'key' ? 'lock' : 'check'} me-2"></i>${cert.name}</td>
                    <td><span class="badge bg-${cert.type === 'key' ? 'warning' : 'success'}">${cert.type.toUpperCase()}</span></td>
                    <td>${cert.size}</td>
                    <td>${cert.modified}</td>
                    ${validityCell}
                </tr>`;
            });
            
            html += '</tbody></table></div>';
            listElement.innerHTML = html;
        } else {
            listElement.innerHTML = '<div class="text-muted"><i class="bi bi-info-circle me-2"></i><span data-i18n="noCertificatesFound">No certificates found in certs/ directory</span></div>';
        }
    } catch (error) {
        console.error('Failed to load certificate list:', error);
        document.getElementById('certificateList').innerHTML = '<div class="text-danger"><i class="bi bi-exclamation-triangle me-2"></i><span data-i18n="failedToLoadCertificates">Failed to load certificates</span></div>';
    }
}

function showCertificateModal() {
    if (!certificateModal) {
        certificateModal = new bootstrap.Modal(document.getElementById('certificateModal'));
    }
    certificateModal.show();
}

function hideCertificateModal() {
    if (certificateModal) {
        certificateModal.hide();
    }
}

function initCertificateModal() {
    const modal = document.getElementById('certificateModal');
    if (!modal) return;

    // Platform selection handlers
    const platformRadios = document.querySelectorAll('input[name="platform"]');
    const windowsInstructions = document.getElementById('windowsInstructions');
    const linuxInstructions = document.getElementById('linuxInstructions');
    const generateBtn = document.getElementById('generateCertNowBtn');

    platformRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.value === 'windows') {
                windowsInstructions.style.display = 'block';
                linuxInstructions.style.display = 'none';
            } else if (this.value === 'linux') {
                windowsInstructions.style.display = 'none';
                linuxInstructions.style.display = 'block';
            }
            generateBtn.disabled = false;
        });
    });

    // Generate certificate button
    generateBtn.addEventListener('click', async function() {
        const selectedPlatform = document.querySelector('input[name="platform"]:checked');
        if (!selectedPlatform) {
            if (window.SettingsCore) {
                window.SettingsCore.showNotification(window.SettingsCore.getText('pleaseSelectPlatform'), 'warning');
            }
            return;
        }

        try {
            generateBtn.disabled = true;
            generateBtn.innerHTML = '<i class="bi bi-hourglass-split me-2"></i><span data-i18n="generating">Generating...</span>';

            const resp = await fetch('/auth/generate-certificate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ platform: selectedPlatform.value })
            });

            if (resp.ok) {
                const result = await resp.json();
                if (window.SettingsCore) {
                    const successMessage = window.SettingsCore.getText('certificateGeneratedSuccessfully') + 
                        '\n\n' + window.SettingsCore.getText('certificateLocation') + 
                        '\n• ./certs/server.crt - ' + window.SettingsCore.getText('certificateFile') + 
                        '\n• ./certs/server.key - ' + window.SettingsCore.getText('privateKeyFile') +
                        '\n\n' + window.SettingsCore.getText('certificateLocationNote');
                    window.SettingsCore.showNotification(successMessage, 'success');
                }
                hideCertificateModal();
                await loadCertificateList(); // Refresh the certificate list
            } else {
                const error = await resp.text();
                if (window.SettingsCore) {
                    window.SettingsCore.showNotification(window.SettingsCore.getText('failedToGenerateCertificate') + ': ' + error, 'error');
                }
            }
        } catch (error) {
            console.error('Certificate generation error:', error);
            if (window.SettingsCore) {
                window.SettingsCore.showNotification(window.SettingsCore.getText('failedToGenerateCertificate') + ': ' + error.message, 'error');
            }
        } finally {
            generateBtn.disabled = false;
            generateBtn.innerHTML = '<i class="bi bi-download me-2"></i><span data-i18n="generateNow">Generate Certificate</span>';
        }
    });

    // Reset modal when hidden
    modal.addEventListener('hidden.bs.modal', function() {
        // Reset platform selection
        platformRadios.forEach(radio => radio.checked = false);
        windowsInstructions.style.display = 'none';
        linuxInstructions.style.display = 'none';
        generateBtn.disabled = true;
    });
}

function initCertificateSettingsModule() {
    console.log('Initializing certificate settings module');
    
    // Load certificate list
    loadCertificateList();
    
    // Initialize modal
    initCertificateModal();
    
    // Add event listener for generate button
    const generateBtn = document.getElementById('generateCertBtn');
    if (generateBtn) {
        generateBtn.addEventListener('click', showCertificateModal);
    }
}

// Export functions for global access
window.initCertificateSettingsModule = initCertificateSettingsModule;
window.loadCertificateList = loadCertificateList;
