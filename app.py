import os
import json
import time
import random
import smtplib
import socket
import ssl
import atexit
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
import openpyxl
from apscheduler.schedulers.background import BackgroundScheduler

# ── paths ─────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_PATH  = os.environ.get('DATA_PATH', os.path.join(BASE_DIR, 'data'))
DB_PATH    = os.path.join(DATA_PATH, 'nasher.db')
CV_DIR     = os.path.join(DATA_PATH, 'cvs')
LOGS_DIR   = os.path.join(BASE_DIR, 'logs')

# codes.json lives in DATA_PATH so it survives Railway redeploys.
# On first boot, bootstrap from the checked-in seed file.
CODES_FILE  = os.path.join(DATA_PATH, 'codes.json')
_codes_seed = os.path.join(BASE_DIR, 'codes.json')
if not os.path.exists(CODES_FILE) and os.path.exists(_codes_seed):
    import shutil as _shutil
    _shutil.copy(_codes_seed, CODES_FILE)

os.makedirs(DATA_PATH, exist_ok=True)
os.makedirs(CV_DIR,    exist_ok=True)
os.makedirs(LOGS_DIR,  exist_ok=True)


def _companies_path():
    p = os.path.join(DATA_PATH, 'companies.xlsx')
    return p if os.path.exists(p) else os.path.join(BASE_DIR, 'companies.xlsx')


# ── Flask & DB ────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'nasher-secret-key-x9k2p7')
app.config['SQLALCHEMY_DATABASE_URI']        = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH']             = 16 * 1024 * 1024

db = SQLAlchemy(app)


# ── Models ────────────────────────────────────────────────────────────────────
class Job(db.Model):
    __tablename__   = 'jobs'
    id              = db.Column(db.Integer, primary_key=True)
    activation_code = db.Column(db.String(6), unique=True, nullable=False)
    client_email    = db.Column(db.String(200), nullable=False)
    app_password    = db.Column(db.String(200), nullable=False)
    name            = db.Column(db.String(200), nullable=False)
    job_title       = db.Column(db.String(200), nullable=False)
    city            = db.Column(db.String(100))
    phone           = db.Column(db.String(50))
    cv_path         = db.Column(db.String(500), nullable=False)
    package_size    = db.Column(db.Integer, nullable=False)
    email_list      = db.Column(db.Text, nullable=False)   # JSON snapshot
    emails_sent     = db.Column(db.Integer, default=0)
    status          = db.Column(db.String(20), default='pending')
    start_date      = db.Column(db.DateTime, default=datetime.utcnow)
    daily_limit     = db.Column(db.Integer, default=490)
    send_logs       = db.relationship('SendLog', backref='job', lazy=True)


class SendLog(db.Model):
    __tablename__ = 'send_logs'
    id        = db.Column(db.Integer, primary_key=True)
    job_id    = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    email     = db.Column(db.String(200))
    success   = db.Column(db.Boolean)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    error_msg = db.Column(db.Text)


with app.app_context():
    db.create_all()


# ── codes helpers ─────────────────────────────────────────────────────────────
def load_codes():
    if not os.path.exists(CODES_FILE):
        return {}
    with open(CODES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_codes(codes):
    with open(CODES_FILE, 'w', encoding='utf-8') as f:
        json.dump(codes, f, indent=2, ensure_ascii=False)


# ── companies helper ──────────────────────────────────────────────────────────
def get_email_list(package_size):
    """Read emails from companies.xlsx columns A–E (500 per col) up to package_size."""
    path = _companies_path()
    if not os.path.exists(path):
        return []
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb.active
    cols_needed = (package_size + 499) // 500   # ceil(package_size / 500)
    emails = []
    for col_idx in range(1, cols_needed + 1):
        for row in ws.iter_rows(min_col=col_idx, max_col=col_idx, values_only=True):
            val = row[0]
            if val and isinstance(val, str) and '@' in val and '.' in val:
                emails.append(val.strip())
    wb.close()
    return emails[:package_size]


# ── email builder (identical template to original) ────────────────────────────
ALLOWED_EXT = {'pdf', 'doc', 'docx'}


def _test_smtp(gmail, app_password):
    """Verify Gmail credentials via SMTP before saving any data.
    Returns (ok: bool, error_message: str | None)."""
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=12) as smtp:
            smtp.login(gmail, app_password)
        return True, None
    except smtplib.SMTPAuthenticationError:
        return False, 'كلمة مرور التطبيق غير صحيحة. تأكد من إنشاء App Password صحيح من إعدادات Google'
    except smtplib.SMTPConnectError as e:
        return False, f'تعذر الاتصال بـ Gmail (SMTP): {e}'
    except (socket.timeout, TimeoutError):
        return False, 'انتهت مهلة الاتصال بـ Gmail. تحقق من الاتصال بالإنترنت'
    except socket.gaierror:
        return False, 'تعذر الوصول إلى خوادم Gmail. تحقق من الاتصال بالإنترنت'
    except ssl.SSLError as e:
        return False, f'خطأ SSL عند الاتصال بـ Gmail: {e}'
    except Exception as e:
        return False, f'خطأ غير متوقع عند التحقق من Gmail: {e}'


def _build_msg(job, to_email, cv_data, cv_ext):
    safe_name = job.name.replace(' ', '_')
    msg = MIMEMultipart()
    msg['From']    = f'{job.name} <{job.client_email}>'
    msg['To']      = to_email
    msg['Subject'] = f'طلب توظيف - {job.job_title} - {job.name}'

    body = f"""السادة المسؤولين عن التوظيف،

السلام عليكم ورحمة الله وبركاته،

يسعدني أن أتقدم بطلب توظيف إلى مؤسستكم الكريمة للعمل في مجال {job.job_title}.

━━━━━━━━━━━━━━━━━━━━━━
البيانات الشخصية:
━━━━━━━━━━━━━━━━━━━━━━
الاسم الكامل      : {job.name}
المسمى الوظيفي    : {job.job_title}
المدينة           : {job.city or ''}
رقم الجوال        : {job.phone or ''}
البريد الإلكتروني : {job.client_email}
━━━━━━━━━━━━━━━━━━━━━━

مرفق طيه سيرتي الذاتية للاطلاع عليها، وأرجو أن تجدوا في مؤهلاتي وخبراتي ما يتوافق مع متطلبات العمل لديكم.

أتطلع إلى فرصة للتعريف بنفسي وإثبات كفاءتي لخدمة مؤسستكم الكريمة.

وتفضلوا بقبول فائق الاحترام والتقدير،

{job.name}
{job.phone or ''}
{job.client_email}"""

    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    if cv_data:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(cv_data)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{safe_name}_CV.{cv_ext}"')
        msg.attach(part)

    return msg


# ── scheduler / job processor ─────────────────────────────────────────────────
def _process_job(job_id):
    job = Job.query.get(job_id)
    if not job or job.status == 'completed':
        return

    job.status = 'running'
    db.session.commit()

    email_list = json.loads(job.email_list)
    total      = len(email_list)
    start_idx  = job.emails_sent
    end_idx    = min(start_idx + job.daily_limit, total)
    batch      = email_list[start_idx:end_idx]

    if not batch:
        job.status = 'completed'
        db.session.commit()
        return

    cv_data, cv_ext = None, 'pdf'
    if os.path.exists(job.cv_path):
        cv_ext = job.cv_path.rsplit('.', 1)[-1].lower()
        with open(job.cv_path, 'rb') as f:
            cv_data = f.read()

    smtp = None
    try:
        smtp = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=30)
        smtp.login(job.client_email, job.app_password)
    except Exception as e:
        db.session.add(SendLog(job_id=job.id, email='[SMTP LOGIN]', success=False, error_msg=str(e)))
        db.session.commit()
        return

    for to_email in batch:
        try:
            try:
                smtp.noop()
            except Exception:
                smtp = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=30)
                smtp.login(job.client_email, job.app_password)

            smtp.send_message(_build_msg(job, to_email, cv_data, cv_ext))
            db.session.add(SendLog(job_id=job.id, email=to_email, success=True))
            job.emails_sent += 1
            db.session.commit()

        except Exception as e:
            db.session.add(SendLog(job_id=job.id, email=to_email, success=False, error_msg=str(e)))
            db.session.commit()
            smtp = None

        time.sleep(random.uniform(3, 5))

    if smtp:
        try:
            smtp.quit()
        except Exception:
            pass

    if job.emails_sent >= total:
        job.status = 'completed'
        db.session.commit()


def scheduler_tick():
    with app.app_context():
        jobs = Job.query.filter(Job.status.in_(['pending', 'running'])).all()
        for job in jobs:
            _process_job(job.id)


_scheduler = BackgroundScheduler(daemon=True)
_scheduler.add_job(scheduler_tick, 'cron', hour=9, minute=0, misfire_grace_time=3600)
_scheduler.start()
atexit.register(lambda: _scheduler.shutdown(wait=False))


# ── routes ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/validate-code', methods=['POST'])
def validate_code():
    data = request.get_json()
    if not data:
        return jsonify({'valid': False, 'message': 'طلب غير صحيح'}), 400

    code = data.get('code', '').strip()

    if not code.isdigit() or len(code) != 6:
        return jsonify({'valid': False, 'message': 'صيغة الرمز غير صحيحة. الرمز يجب أن يكون 6 أرقام'})

    codes = load_codes()

    if code not in codes:
        return jsonify({'valid': False, 'message': 'الرمز غير صحيح أو غير موجود'})

    code_data = codes[code]

    if code_data.get('used'):
        used_at = code_data.get('used_at', '')
        return jsonify({'valid': False, 'message': f'هذا الرمز مستخدم بالفعل منذ {used_at[:10]}'})

    session['valid_code']   = code
    session['package_size'] = code_data['package']

    return jsonify({
        'valid':   True,
        'package': code_data['package'],
        'message': f'رمز صحيح! باقتك: {code_data["package"]} شركة'
    })


@app.route('/main')
def main_page():
    if 'valid_code' not in session:
        return render_template('index.html')
    return render_template('main.html', package=session.get('package_size', 0))


@app.route('/submit', methods=['POST'])
def submit():
    if 'valid_code' not in session:
        return jsonify({'ok': False, 'message': 'انتهت الجلسة، أعد إدخال رمز التفعيل'}), 403

    code  = session['valid_code']
    codes = load_codes()

    if code not in codes or codes[code].get('used'):
        return jsonify({'ok': False, 'message': 'الرمز غير صالح أو مستخدم بالفعل'}), 400

    if Job.query.filter_by(activation_code=code).first():
        return jsonify({'ok': False, 'message': 'تم تسجيل هذا الرمز مسبقاً'}), 400

    name         = request.form.get('full_name', '').strip()
    job_title    = request.form.get('job_title', '').strip()
    city         = request.form.get('city', '').strip()
    phone        = request.form.get('phone', '').strip()
    gmail        = request.form.get('gmail', '').strip()
    app_password = request.form.get('app_password', '').strip()
    cv_file      = request.files.get('cv')

    if not all([name, job_title, gmail, app_password, cv_file]):
        return jsonify({'ok': False, 'message': 'يرجى ملء جميع الحقول المطلوبة'}), 400

    if not gmail.endswith('@gmail.com'):
        return jsonify({'ok': False, 'message': 'يرجى إدخال بريد Gmail صحيح'}), 400

    ext = cv_file.filename.rsplit('.', 1)[-1].lower() if '.' in cv_file.filename else ''
    if ext not in ALLOWED_EXT:
        return jsonify({'ok': False, 'message': 'يُسمح فقط بملفات PDF أو Word'}), 400

    # ── SMTP VERIFICATION ──────────────────────────────────────────────────────
    # Must succeed BEFORE the CV is saved, the email list is snapshotted,
    # the job is written to the DB, or the activation code is marked used.
    # A failure here leaves the code intact so the client can retry.
    smtp_ok, smtp_err = _test_smtp(gmail, app_password)
    if not smtp_ok:
        return jsonify({'ok': False, 'smtp_error': True, 'message': smtp_err}), 400
    # ──────────────────────────────────────────────────────────────────────────

    cv_name = f"{code}_{int(time.time())}.{ext}"
    cv_path = os.path.join(CV_DIR, cv_name)
    cv_file.save(cv_path)

    package_size = codes[code]['package']
    email_list   = get_email_list(package_size)
    if not email_list:
        os.remove(cv_path)
        return jsonify({'ok': False, 'message': 'لا توجد قائمة شركات. يرجى التواصل مع الدعم'}), 500

    job = Job(
        activation_code = code,
        client_email    = gmail,
        app_password    = app_password,
        name            = name,
        job_title       = job_title,
        city            = city,
        phone           = phone,
        cv_path         = cv_path,
        package_size    = package_size,
        email_list      = json.dumps(email_list, ensure_ascii=False),
        status          = 'pending',
        daily_limit     = 490,
    )
    db.session.add(job)

    codes[code]['used']    = True
    codes[code]['used_at'] = datetime.now().isoformat()
    codes[code]['used_by'] = gmail
    save_codes(codes)

    db.session.commit()

    session.pop('valid_code',   None)
    session.pop('package_size', None)

    return jsonify({'ok': True, 'code': code, 'total': len(email_list)})


@app.route('/api/status/<code>')
def api_status(code):
    job = Job.query.filter_by(activation_code=code).first()
    if not job:
        return jsonify({'found': False, 'message': 'لا يوجد طلب مرتبط بهذا الرمز'})

    email_list = json.loads(job.email_list)
    total      = len(email_list)
    sent       = job.emails_sent
    remaining  = max(0, total - sent)
    percent    = round(sent / total * 100) if total else 0
    days_left  = (remaining + 489) // 490 if remaining > 0 else 0
    completion = (datetime.utcnow() + timedelta(days=days_left)).strftime('%Y-%m-%d') if days_left > 0 else None

    return jsonify({
        'found':           True,
        'name':            job.name,
        'job_title':       job.job_title,
        'status':          job.status,
        'total':           total,
        'sent':            sent,
        'remaining':       remaining,
        'percent':         percent,
        'completion_date': completion,
        'start_date':      job.start_date.strftime('%Y-%m-%d'),
    })


@app.route('/status/<code>')
def status_page(code):
    job = Job.query.filter_by(activation_code=code).first()
    if not job:
        return render_template('status.html', job=None, code=code)

    email_list = json.loads(job.email_list)
    total      = len(email_list)
    sent       = job.emails_sent
    remaining  = max(0, total - sent)
    percent    = round(sent / total * 100) if total else 0
    days_left  = (remaining + 489) // 490 if remaining > 0 else 0
    completion = (datetime.utcnow() + timedelta(days=days_left)).strftime('%Y-%m-%d') if days_left > 0 else None

    return render_template('status.html', job=job, code=code,
                           total=total, sent=sent, remaining=remaining,
                           percent=percent, completion_date=completion)


def _check_admin(provided):
    """Return True only when ADMIN_PASSWORD is set and matches."""
    pw = os.environ.get('ADMIN_PASSWORD', '')
    return pw and provided == pw


@app.route('/admin/upload-codes', methods=['GET', 'POST'])
def upload_codes():
    if request.method == 'GET':
        return render_template('admin.html')

    provided = request.form.get('password', '')
    if not _check_admin(provided):
        return jsonify({'ok': False, 'message': 'كلمة المرور غير صحيحة'}), 403

    f = request.files.get('file')
    if not f or not f.filename.endswith('.json'):
        return jsonify({'ok': False, 'message': 'يرجى رفع ملف JSON'}), 400

    try:
        codes = json.loads(f.read().decode('utf-8'))
        if not isinstance(codes, dict):
            raise ValueError('يجب أن يكون الملف كائن JSON')
    except (json.JSONDecodeError, ValueError) as e:
        return jsonify({'ok': False, 'message': f'ملف JSON غير صحيح: {e}'}), 400

    with open(CODES_FILE, 'w', encoding='utf-8') as out:
        json.dump(codes, out, indent=2, ensure_ascii=False)

    return jsonify({'ok': True, 'message': f'تم رفع codes.json بنجاح ({len(codes)} رمز)'})


@app.route('/admin/upload-companies', methods=['GET', 'POST'])
def upload_companies():
    if request.method == 'GET':
        return render_template('admin.html')

    provided = request.form.get('password', '')
    if not _check_admin(provided):
        return jsonify({'ok': False, 'message': 'كلمة المرور غير صحيحة'}), 403

    f = request.files.get('file')
    if not f or not f.filename.endswith('.xlsx'):
        return jsonify({'ok': False, 'message': 'يرجى رفع ملف xlsx'}), 400

    dest = os.path.join(DATA_PATH, 'companies.xlsx')
    if os.path.exists(dest):
        os.remove(dest)
    f.save(dest)
    return jsonify({'ok': True, 'message': 'تم رفع companies.xlsx بنجاح'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
