// Users settings module
(function(){
  let superAdminUsername = 'admin';

  async function fetchUsers(){
    try {
      const resp = await fetch('/auth/local-users', {credentials:'include'});
      if(!resp.ok) {
        if(resp.status === 401 || resp.status === 403 || resp.status === 302){
          // Not authenticated or no permission
          console.warn('[Users] Authentication required or no permission');
          return {};
        }
        throw new Error(`Failed to load users: ${resp.status} ${resp.statusText}`);
      }
      const data = await resp.json();
      // Convert object of users to array
      if(data && data.users){
        if(Array.isArray(data.users)){
          return data.users;
        }
        // If users is an object, convert to array
        return Object.entries(data.users).map(([username, info]) => ({
          username,
          ...info
        }));
      }
      return [];
    } catch(e) {
      console.error('[Users] fetchUsers error:', e);
      throw e;
    }
  }

  async function fetchAppConfig(){
    try{
      const resp = await fetch('/auth/app-config', {credentials:'include'});
      if(!resp.ok) return null;
      return await resp.json();
    }catch(_){ return null; }
  }

  function renderUsers(users){
    const tbody = document.getElementById('usersTableBody');
    if(!tbody) return;
    tbody.innerHTML = '';
    
    // Handle both array and object formats
    const userEntries = Array.isArray(users) 
      ? users.map(user => [user.username, user])
      : Object.entries(users);
    
    userEntries.forEach(([username, info])=>{
      const tr = document.createElement('tr');
      const isSuperAdmin = username === superAdminUsername;
      tr.innerHTML = `
        <td>${username}</td>
        <td>${info.display_name||''}</td>
        <td>${info.email||''}</td>
        <td><span data-i18n="userRole${info.role?.replace('_', '') || 'User'}" data-role="${info.role||'user'}">${info.role||'user'}</span></td>
        <td>
          <div class="btn-group btn-group-sm">
            <button class="btn btn-outline-primary" data-action="edit" data-user="${username}"><i class="bi bi-pencil-square"></i></button>
            <button class="btn btn-outline-warning" data-action="reset" data-user="${username}" ${isSuperAdmin?'disabled':''}><i class="bi bi-key"></i></button>
            <button class="btn btn-outline-danger" data-action="delete" data-user="${username}" ${isSuperAdmin?'disabled':''}><i class="bi bi-trash3"></i></button>
          </div>
        </td>`;
      tbody.appendChild(tr);
    });
  }

  function openEditModal(mode, username, info){
    const modalEl = document.getElementById('userEditModal');
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    const title = modalEl.querySelector('.modal-title');
    const usernameInput = document.getElementById('editUsername');
    const displayNameInput = document.getElementById('editDisplayName');
    const emailInput = document.getElementById('editEmail');
    const roleSelect = document.getElementById('editRole');
    const pwdGroup = document.getElementById('editPasswordGroup');
    const pwdInput = document.getElementById('editPassword');

    if(mode==='create'){
      title.textContent = (window.SettingsCore?.getText('createUser','Create User'));
      usernameInput.value = '';
      usernameInput.disabled = false;
      displayNameInput.value='';
      emailInput.value='';
      roleSelect.value='user';
      pwdGroup.style.display='';
      pwdInput.value='';
    }else{
      title.textContent = (window.SettingsCore?.getText('editUser','Edit User'));
      usernameInput.value = username;
      usernameInput.disabled = true;
      displayNameInput.value = info?.display_name||'';
      emailInput.value = info?.email||'';
      roleSelect.value = info?.role||'user';
      pwdGroup.style.display='none';
      pwdInput.value='';
    }

    modal.show();
  }

  async function bindEvents(){
    const createBtn = document.getElementById('createUserBtn');
    createBtn?.addEventListener('click', (e)=> { e.preventDefault(); openEditModal('create'); });

    const tbody = document.getElementById('usersTableBody');
    tbody?.addEventListener('click', async (e)=>{
      const target = e.target.closest('button');
      if(!target) return;
      const action = target.getAttribute('data-action');
      const username = target.getAttribute('data-user');
      if(action==='edit'){
        // Load row info
        const row = target.closest('tr');
        const roleSpan = row.children[3].querySelector('[data-role]');
        const info = {
          display_name: row.children[1].textContent,
          email: row.children[2].textContent,
          role: roleSpan ? roleSpan.getAttribute('data-role') : 'user'
        };
        openEditModal('edit', username, info);
      }else if(action==='reset'){
        const label = (window.SettingsCore?.getText('newPassword','New password'));
        const newPwd = prompt(label);
        if(!newPwd) return;
        if(newPwd.length < 6){ window.SettingsCore?.showNotification(window.SettingsCore.getText('passwordTooShort','Password too short (>=6)'), 'warning'); return; }
        const resp = await fetch(`/auth/local-users/${encodeURIComponent(username)}/reset-password`,{
          method:'POST', credentials:'include', headers:{'Content-Type':'application/json'}, body: JSON.stringify({password:newPwd})
        });
        if(resp.ok){ window.SettingsCore?.showNotification(window.SettingsCore.getText('passwordResetOk','Password reset'), 'success'); }
        else { window.SettingsCore?.showNotification(window.SettingsCore.getText('passwordResetFail','Failed to reset password'), 'error'); }
        if(resp.ok) await initUsersModule(true);
      }else if(action==='delete'){
        const msg = (window.SettingsCore?.getText('confirmDeleteUser','Delete this user?'));
        if(!confirm(msg)) return;
        const resp = await fetch(`/auth/local-users/${encodeURIComponent(username)}`,{method:'DELETE', credentials:'include'});
        if(resp.ok){ window.SettingsCore?.showNotification(window.SettingsCore.getText('deleted','Deleted'), 'success'); }
        else { window.SettingsCore?.showNotification(window.SettingsCore.getText('deleteFailed','Delete failed'), 'error'); }
        if(resp.ok) await initUsersModule(true);
      }
    });

    const saveBtn = document.getElementById('saveUserBtn');
    saveBtn?.addEventListener('click', async ()=>{
      const username = document.getElementById('editUsername').value.trim();
      const display_name = document.getElementById('editDisplayName').value.trim();
      const email = document.getElementById('editEmail').value.trim();
      const role = document.getElementById('editRole').value;
      const pwd = document.getElementById('editPassword').value;
      const modalEl = document.getElementById('userEditModal');
      const title = modalEl.querySelector('.modal-title').textContent;
      if(title.includes('Create') || title.includes('New')){
        if(!username || !pwd){ window.SettingsCore?.showNotification(window.SettingsCore.getText('usernamePasswordRequired','Username and password required'), 'warning'); return; }
        if(pwd.length < 6){ window.SettingsCore?.showNotification(window.SettingsCore.getText('passwordTooShort','Password too short (>=6)'), 'warning'); return; }
        const resp = await fetch('/auth/local-users',{method:'POST', credentials:'include', headers:{'Content-Type':'application/json'}, body: JSON.stringify({username, password:pwd, role, display_name, email})});
        if(resp.ok){ window.SettingsCore?.showNotification(window.SettingsCore.getText('created','Created'), 'success'); }
        else { const t = await resp.text(); window.SettingsCore?.showNotification(window.SettingsCore.getText('createFailed','Create failed')+': '+t, 'error'); }
      }else{
        if(!username){ return; }
        const resp = await fetch(`/auth/local-users/${encodeURIComponent(username)}`,{method:'PUT', credentials:'include', headers:{'Content-Type':'application/json'}, body: JSON.stringify({role, display_name, email})});
        if(resp.ok){ window.SettingsCore?.showNotification(window.SettingsCore.getText('saved','Saved'), 'success'); }
        else { const t = await resp.text(); window.SettingsCore?.showNotification(window.SettingsCore.getText('saveFailed','Save failed')+': '+t, 'error'); }
      }
      bootstrap.Modal.getInstance(modalEl)?.hide();
      await initUsersModule(true);
    });
  }

  async function initUsersModule(silent){
    try{
      const htmlResp = await fetch(`/static/settings/users.html?v=${Date.now()}`, {cache:'no-store'});
      if(!htmlResp.ok) throw new Error('Failed to load users module');
      document.getElementById('users-content').innerHTML = await htmlResp.text();
      
      // Apply i18n to newly loaded content
      if(window.SettingsCore && window.SettingsCore.i18n){
        window.SettingsCore.i18n.applyTranslations();
      }
      
      // Load config for super admin username
      const cfg = await fetchAppConfig();
      if(cfg && cfg.default_username){ superAdminUsername = cfg.default_username; }
      const users = await fetchUsers();
      renderUsers(users);
      await bindEvents();
      if(!silent && window.SettingsCore){ 
        if(users && (Array.isArray(users) ? users.length : Object.keys(users).length) > 0){
          window.SettingsCore.showNotification(window.SettingsCore.getText('usersLoaded','Users loaded'),'success'); 
        }
      }
    }catch(e){
      console.error('[Users] init failed:', e);
      const c = document.getElementById('users-content');
      if(c){ 
        // Check if this is an authentication error
        if(e.message.includes('401') || e.message.includes('403') || e.message.includes('302')){
          c.innerHTML = `<div class="alert alert-warning">
            <i class="bi bi-exclamation-triangle me-2"></i>
            Authentication required. Please log in to manage users.
          </div>`;
        } else {
          c.innerHTML = `<div class="alert alert-danger">
            <i class="bi bi-exclamation-triangle me-2"></i>
            ${e.message}
          </div>`; 
        }
      }
    }
  }

  window.initUsersModule = initUsersModule;
})();
