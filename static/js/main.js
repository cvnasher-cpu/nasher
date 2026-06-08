/* ===========================
   ناشر — Frontend JS
   =========================== */

/* ===== Tracking (home page) ===== */

function toggleTracking() {
  const card   = document.getElementById('tracking-card');
  const btn    = document.getElementById('track-toggle');
  const hidden = card.classList.toggle('hidden');
  btn.textContent = hidden ? 'تتبع حالة طلبك' : 'إخفاء';
  if (!hidden) document.getElementById('track-code').focus();
}

function trackJob() {
  const input  = document.getElementById('track-code');
  const msg    = document.getElementById('track-msg');
  const btn    = document.getElementById('track-btn');
  const result = document.getElementById('track-result');
  const wrap   = document.getElementById('track-input-wrap');

  const code = input.value.replace(/\D/g, '').slice(0, 6);
  input.value = code;

  clearMsg(msg);
  result.classList.add('hidden');
  result.innerHTML = '';
  wrap.classList.remove('error', 'success');

  if (code.length !== 6) {
    showMsg(msg, 'أدخل رمزاً مكوّناً من 6 أرقام', 'error');
    shake(input);
    return;
  }

  setLoading(btn, true);

  fetch('/api/status/' + code)
    .then(r => r.json())
    .then(data => {
      setLoading(btn, false);
      if (!data.found) {
        wrap.classList.add('error');
        showMsg(msg, data.message || 'الرمز غير موجود', 'error');
        shake(input);
      } else {
        wrap.classList.add('success');
        clearMsg(msg);
        renderTrackResult(data);
      }
    })
    .catch(() => {
      setLoading(btn, false);
      showMsg(msg, 'خطأ في الاتصال بالخادم', 'error');
    });
}

function renderTrackResult(data) {
  const el = document.getElementById('track-result');

  const statusMap = {
    pending:   { bg: 'rgba(251,191,36,.1)',  color: '#fbbf24', border: 'rgba(251,191,36,.3)',  label: 'في الانتظار' },
    running:   { bg: 'rgba(56,189,248,.1)',  color: '#38bdf8', border: 'rgba(56,189,248,.3)',  label: 'جاري الإرسال' },
    completed: { bg: 'rgba(74,222,128,.15)', color: '#4ade80', border: 'rgba(74,222,128,.3)',  label: 'مكتمل ✓' },
  };
  const s = statusMap[data.status] || statusMap.pending;
  const pct = data.percent || 0;

  el.innerHTML = `
    <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:.75rem;margin-bottom:1.25rem">
      <div>
        <div style="font-weight:700;font-size:1.05rem">${data.name}</div>
        <div style="color:var(--text-muted);font-size:.85rem">${data.job_title}</div>
      </div>
      <span style="padding:.3rem .9rem;border-radius:20px;font-size:.8rem;font-weight:600;
                   background:${s.bg};color:${s.color};border:1px solid ${s.border}">${s.label}</span>
    </div>
    <div class="progress-bar-wrap" style="margin-bottom:1.25rem">
      <div class="progress-bar-track">
        <div class="progress-bar-fill" style="width:${pct}%"></div>
      </div>
      <span class="progress-pct">${pct}%</span>
    </div>
    <div class="stats-row" style="margin-bottom:1rem">
      <div class="stat stat-success">
        <div class="stat-val">${data.sent}</div>
        <div class="stat-label">تم الإرسال</div>
      </div>
      <div class="stat stat-remain">
        <div class="stat-val">${data.remaining}</div>
        <div class="stat-label">متبقي</div>
      </div>
      <div class="stat">
        <div class="stat-val">${data.total}</div>
        <div class="stat-label">الإجمالي</div>
      </div>
    </div>
    ${data.completion_date
      ? `<div style="text-align:center;font-size:.85rem;color:var(--text-muted)">
           التاريخ المتوقع للاكتمال:
           <strong style="color:var(--primary)">${data.completion_date}</strong>
         </div>`
      : (data.status === 'completed'
          ? `<div style="text-align:center;font-size:.85rem;color:#4ade80">اكتمل الإرسال بالكامل ✓</div>`
          : '')}
  `;
  el.classList.remove('hidden');
}

/* Auto-filter track-code input to digits only */
const trackInput = document.getElementById('track-code');
if (trackInput) {
  trackInput.addEventListener('input', function () {
    this.value = this.value.replace(/\D/g, '').slice(0, 6);
    document.getElementById('track-input-wrap').classList.remove('error', 'success');
    clearMsg(document.getElementById('track-msg'));
    document.getElementById('track-result').classList.add('hidden');
  });
  trackInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') trackJob();
  });
}

/* ===== Activation Page ===== */

function validateCode() {
  const input = document.getElementById('activation-code');
  const btn   = document.getElementById('validate-btn');
  const msg   = document.getElementById('msg');
  if (!input) return;

  const code = input.value.trim();

  if (!code) {
    showMsg(msg, 'يرجى إدخال رمز التفعيل', 'error');
    shake(input);
    return;
  }

  setLoading(btn, true);
  clearMsg(msg);

  fetch('/validate-code', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code })
  })
    .then(r => r.json())
    .then(data => {
      if (data.valid) {
        showMsg(msg, '✓ ' + data.message, 'success');
        document.getElementById('code-input-wrap').classList.add('success');
        setTimeout(() => { window.location.href = '/main'; }, 900);
      } else {
        showMsg(msg, '✗ ' + data.message, 'error');
        document.getElementById('code-input-wrap').classList.add('error');
        shake(input);
        setLoading(btn, false);
      }
    })
    .catch(() => {
      showMsg(msg, 'خطأ في الاتصال بالخادم', 'error');
      setLoading(btn, false);
    });
}

/* Auto-format code input & enter key */
const codeInput = document.getElementById('activation-code');
if (codeInput) {
  codeInput.addEventListener('input', function () {
    let v = this.value.replace(/[^0-9]/g, '').slice(0, 6);
    this.value = v;
    document.getElementById('code-input-wrap').classList.remove('error', 'success');
    clearMsg(document.getElementById('msg'));
  });

  codeInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') validateCode();
  });
}

/* ===== Main Form Page ===== */

function toggleHelp() {
  const box = document.getElementById('help-box');
  if (box) box.classList.toggle('hidden');
}

function togglePassword() {
  const input = document.getElementById('app_password');
  const icon  = document.getElementById('eye-icon');
  if (!input) return;
  if (input.type === 'password') {
    input.type = 'text';
    icon.innerHTML = '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line>';
  } else {
    input.type = 'password';
    icon.innerHTML = '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle>';
  }
}

function onFileChange(input) {
  const label    = document.getElementById('file-label');
  const dropZone = document.getElementById('file-drop');
  if (input.files && input.files[0]) {
    const file = input.files[0];
    const size = (file.size / 1024).toFixed(0);
    label.textContent = `✓ ${file.name}  (${size} KB)`;
    dropZone.classList.add('has-file');
    dropZone.querySelector('svg').style.color = 'var(--success)';
  }
}

/* Drag & drop */
const dropZone = document.getElementById('file-drop');
if (dropZone) {
  dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
  dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) {
      const cvInput = document.getElementById('cv');
      const dt = new DataTransfer();
      dt.items.add(file);
      cvInput.files = dt.files;
      onFileChange(cvInput);
    }
  });
}

/* Form submit */
const form = document.getElementById('send-form');
if (form) {
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    startSend();
  });
}

function startSend() {
  const errEl   = document.getElementById('form-error');
  const sendBtn = document.getElementById('send-btn');

  clearMsg(errEl);

  const full_name    = field('full_name');
  const job_title    = field('job_title');
  const phone        = field('phone');
  const gmail        = field('gmail');
  const app_password = field('app_password');
  const city         = field('city');
  const cv           = document.getElementById('cv');

  if (!full_name || !job_title || !phone || !gmail || !app_password || !city) {
    showMsg(errEl, 'يرجى تعبئة جميع الحقول المطلوبة', 'error');
    return;
  }

  if (!gmail.endsWith('@gmail.com')) {
    showMsg(errEl, 'يرجى إدخال بريد Gmail صحيح ينتهي بـ @gmail.com', 'error');
    return;
  }

  if (!cv || !cv.files || cv.files.length === 0) {
    showMsg(errEl, 'يرجى رفع ملف السيرة الذاتية', 'error');
    return;
  }

  const formData = new FormData();
  formData.append('full_name',    full_name);
  formData.append('job_title',    job_title);
  formData.append('phone',        phone);
  formData.append('gmail',        gmail);
  formData.append('app_password', app_password);
  formData.append('city',         city);
  formData.append('cv',           cv.files[0]);

  // Show "checking Gmail..." — SMTP test can take up to 12 seconds
  const btnText = document.getElementById('send-btn-text');
  const spinner = document.getElementById('send-spinner');
  sendBtn.disabled = true;
  if (btnText) btnText.textContent = 'جاري التحقق من Gmail...';
  if (spinner) spinner.classList.remove('hidden');

  const _restoreBtn = () => {
    sendBtn.disabled = false;
    if (btnText) { btnText.textContent = 'ابدأ الإرسال'; btnText.classList.remove('hidden'); }
    if (spinner) spinner.classList.add('hidden');
  };

  fetch('/submit', { method: 'POST', body: formData })
    .then(r => r.json())
    .then(data => {
      _restoreBtn();
      if (data.ok) {
        showQueued(data.code, data.total);
      } else {
        showMsg(errEl, data.message || 'حدث خطأ أثناء التسجيل', 'error');
        if (data.smtp_error) {
          shake(document.getElementById('app_password'));
        }
      }
    })
    .catch(() => {
      _restoreBtn();
      showMsg(errEl, 'خطأ في الاتصال بالخادم', 'error');
    });
}

function showQueued(code, total) {
  document.getElementById('form-section').classList.add('hidden');
  const section = document.getElementById('queued-section');
  section.classList.remove('hidden');

  const codeEl = document.getElementById('queued-code');
  if (codeEl) codeEl.textContent = code;

  const totalEl = document.getElementById('q-total');
  if (totalEl) totalEl.textContent = total;

  const link = document.getElementById('status-link');
  if (link) link.href = '/status/' + code;
}

let _prevSent = 0;

function readSSE(response) {
  const reader  = response.body.getReader();
  const decoder = new TextDecoder();
  let   buffer  = '';

  function pump() {
    return reader.read().then(({ done, value }) => {
      if (done) return;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            handleSSEData(data);
          } catch (_) {}
        }
      }
      return pump();
    });
  }

  return pump();
}

function handleSSEData(data) {
  if (data.error) {
    showError(data.error);
    return;
  }

  if (data.status === 'connecting') {
    updateLog('جاري تسجيل الدخول إلى Gmail...', 'info');
    setCounter(0, data.total);
    return;
  }

  if (data.status === 'sending') {
    updateLog('بدأ الإرسال ✓', 'ok');
    return;
  }

  if (data.done) {
    showDone(data.sent, data.failed, data.total);
    return;
  }

  /* Normal progress tick */
  setCounter(data.current, data.total);
  setBar(data.percent);
  setStats(data.sent, data.failed, data.total - data.current);
  setCurrentEmail(data.current_email);

  /* sent is cumulative; compare to previous to know if this email succeeded */
  const thisOk = data.sent > _prevSent;
  _prevSent = data.sent;
  updateLog(`${thisOk ? '✓' : '✗'} ${data.current_email}`, thisOk ? 'ok' : 'fail');
}

/* ===== UI helpers ===== */


function setCounter(current, total) {
  document.getElementById('p-sent').textContent  = current;
  document.getElementById('p-total').textContent = total;
}

function setBar(pct) {
  document.getElementById('progress-bar').style.width = pct + '%';
  document.getElementById('progress-pct').textContent = pct + '%';
}

function setStats(sent, failed, remain) {
  document.getElementById('stat-sent').textContent   = sent;
  document.getElementById('stat-failed').textContent = failed;
  document.getElementById('stat-remain').textContent = remain >= 0 ? remain : '—';
}

function setCurrentEmail(email) {
  document.getElementById('current-email').textContent = email || '—';
}

function updateLog(text, type) {
  const log  = document.getElementById('progress-log');
  const line = document.createElement('div');
  line.className = 'log-line ' + (type === 'ok' ? 'log-ok' : type === 'fail' ? 'log-fail' : '');
  line.textContent = text;
  log.prepend(line);
  if (log.children.length > 120) log.removeChild(log.lastChild);
}

function showDone(sent, failed, total) {
  document.getElementById('progress-status').className  = 'status-badge status-done';
  document.getElementById('progress-status').textContent = 'اكتمل';

  const doneBox = document.getElementById('done-box');
  document.getElementById('done-summary').textContent =
    `تم إرسال ${sent} سيرة ذاتية بنجاح من أصل ${total} شركة. الفاشل: ${failed}.`;
  doneBox.classList.remove('hidden');

  setBar(100);
  setCounter(total, total);
  setStats(sent, failed, 0);
  setCurrentEmail('');
}

function showError(msg) {
  const errBox = document.getElementById('error-box');
  const errMsg = document.getElementById('error-msg');
  if (errBox && errMsg) {
    errMsg.textContent = msg;
    errBox.classList.remove('hidden');
    document.getElementById('progress-status').className   = 'status-badge msg-error';
    document.getElementById('progress-status').textContent = 'خطأ';
  }
}

function showMsg(el, text, type) {
  if (!el) return;
  el.textContent = text;
  el.className   = `msg msg-${type}`;
  el.classList.remove('hidden');
}

function clearMsg(el) {
  if (!el) return;
  el.textContent = '';
  el.classList.add('hidden');
}

function setLoading(btn, loading) {
  if (!btn) return;
  const txt  = btn.querySelector('#btn-text') || btn.querySelector('[id$="-text"]');
  const spin = btn.querySelector('.spinner');
  btn.disabled = loading;
  if (txt)  txt.classList.toggle('hidden', loading);
  if (spin) spin.classList.toggle('hidden', !loading);
}

function field(id) {
  const el = document.getElementById(id);
  return el ? el.value.trim() : '';
}

function shake(el) {
  el.animate([
    { transform: 'translateX(0)' },
    { transform: 'translateX(-8px)' },
    { transform: 'translateX(8px)' },
    { transform: 'translateX(-6px)' },
    { transform: 'translateX(0)' },
  ], { duration: 350, easing: 'ease-out' });
}
