// Preview module: support original (left) and translated (right) preview
// Supports: text/code, html, pdf, docx (via /preview/docx), xlsx (via /preview/xlsx)

(function(){
  function setPreviewDisplayMode(mode){
    try{
      const originalPreviewContainer = document.getElementById('originalPreviewContainer');
      const translatedPreviewContainer = document.getElementById('translatedPreviewContainer');
      const previewOffcanvasLabel = document.getElementById('previewOffcanvasLabel');
      if (!originalPreviewContainer || !translatedPreviewContainer) return;
      const isMobileView = window.innerWidth < 992;
      const splitContainer = document.querySelector('.preview-split-container');
      if (!splitContainer) return;
      originalPreviewContainer.style.display = 'flex';
      translatedPreviewContainer.style.display = 'flex';
      [originalPreviewContainer, translatedPreviewContainer].forEach(el => { el.style.width = ''; el.style.height=''; });
      splitContainer.style.flexDirection = isMobileView ? 'column' : 'row';
      if (mode === 'translatedOnly'){
        if (previewOffcanvasLabel) previewOffcanvasLabel.textContent = 'Translation Only';
        originalPreviewContainer.style.display = 'none';
        if (isMobileView) translatedPreviewContainer.style.height = '100%'; else translatedPreviewContainer.style.width = '100%';
      } else {
        if (previewOffcanvasLabel) previewOffcanvasLabel.textContent = 'Bilingual';
      }
    }catch(_){/* no-op */}
  }

  async function renderOriginal(file){
    const originalPane = document.getElementById('originalPreviewPane');
    if (!originalPane){ return; }
    const existing = originalPane.querySelector('iframe, pre, p');
    if (existing) existing.remove();
    if (!file){
      const p = document.createElement('p');
      p.className = 'p-3 text-muted';
      p.textContent = 'No original file cached';
      originalPane.appendChild(p);
      return;
    }
    try{
      const type = file.type || '';
      const ext = (file.name.split('.').pop()||'').toLowerCase();
      const textLike = ['md','json','xml','log','py','js','css','java','c','cpp','h','hpp','cs','rb','php','swift','kt','go','rs','ts','txt','srt'];
      if (type.startsWith('text/') || textLike.includes(ext)){
        const pre = document.createElement('pre');
        const text = await file.text();
        pre.textContent = text;
        originalPane.appendChild(pre);
        return;
      }
      if (type === 'text/html' || ['html','htm'].includes(ext) || type === 'application/pdf' || ext === 'pdf'){
        const iframe = document.createElement('iframe');
        iframe.src = URL.createObjectURL(file);
        originalPane.appendChild(iframe);
        return;
      }
      if (type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' || ext === 'docx'){
        const html = await uploadAndGetHtml('/preview/docx', file);
        const iframe = document.createElement('iframe');
        iframe.srcdoc = html;
        originalPane.appendChild(iframe);
        return;
      }
      if (type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' || ext === 'xlsx' || ext === 'csv'){
        const html = await uploadAndGetHtml('/preview/xlsx', file);
        const iframe = document.createElement('iframe');
        iframe.srcdoc = html;
        originalPane.appendChild(iframe);
        return;
      }
      const p = document.createElement('p');
      p.className = 'p-3 text-muted';
      p.textContent = `Cannot preview this file type (${type || 'unknown: ' + ext}).`;
      originalPane.appendChild(p);
    }catch(e){
      const p = document.createElement('p');
      p.className = 'p-3 text-muted';
      p.textContent = 'Preview failed: ' + (e?.message || e);
      originalPane.appendChild(p);
    }
  }

  async function renderTranslated(htmlUrl){
    const frame = document.getElementById('translatedPreviewFrame');
    if (!frame || !htmlUrl) return;
    frame.src = 'about:blank';
    frame.srcdoc = 'Loading...';
    try{
      const resp = await fetch(htmlUrl);
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      const html = await resp.text();
      frame.srcdoc = html;
    }catch(e){
      frame.srcdoc = 'Failed to load translated HTML: ' + (e?.message || e);
    }
  }

  async function uploadAndGetHtml(url, file){
    const fd = new FormData();
    fd.append('file', file);
    const resp = await fetch(url, { method:'POST', body: fd });
    if (resp.status === 503){
      const text = await resp.text();
      return `<div class='p-3 text-danger'>Preview dependency missing: ${text}</div>`;
    }
    if (!resp.ok){
      const t = await resp.text();
      throw new Error(t || ('HTTP ' + resp.status));
    }
    return await resp.text();
  }

  function openPreview({ file, htmlUrl }){
    try{
      const offcanvasEl = document.getElementById('previewOffcanvas');
      if (!offcanvasEl) return;
      const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
      setPreviewDisplayMode('bilingual');
      offcanvas.show();
      const menu = document.getElementById('previewDownloadMenu');
      // menu population remains in index.html context via existing function
      renderOriginal(file);
      renderTranslated(htmlUrl);
    }catch(e){ console.error('openPreview error', e); }
  }

  window.Preview = { openPreview, setPreviewDisplayMode };
})();


