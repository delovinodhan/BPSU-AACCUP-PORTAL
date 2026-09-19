import os
import csv
import io
import json
import sqlite3
import uuid
import secrets
import zipfile
import re
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import (
    Flask, render_template, request, redirect, url_for, flash, session,
    send_from_directory, send_file, abort, Response, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get('BPSU_PORTAL_DATA_DIR', os.environ.get('BPSU_DMS_DATA_DIR', str(BASE_DIR / 'data')))).resolve()
DB_PATH = Path(os.environ.get('BPSU_PORTAL_DB_PATH', os.environ.get('BPSU_DMS_DB_PATH', str(DATA_DIR / 'portal.sqlite3')))).resolve()
UPLOAD_DIR = Path(os.environ.get('BPSU_PORTAL_UPLOAD_DIR', os.environ.get('BPSU_DMS_UPLOAD_DIR', str(DATA_DIR / 'uploads')))).resolve()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {
    'pdf','doc','docx','xls','xlsx','ppt','pptx','csv','txt','jpg','jpeg','png','webp'
}
MAX_FILE_SIZE_MB = int(os.environ.get('BPSU_MAX_FILE_SIZE_MB', '50'))

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
app.secret_key = os.environ.get('BPSU_PORTAL_SECRET', os.environ.get('BPSU_DMS_SECRET', 'local-development-only-change-me'))
app.config.update(
    MAX_CONTENT_LENGTH=MAX_FILE_SIZE_MB * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.environ.get('BPSU_SECURE_COOKIE', os.environ.get('BPSU_DMS_SECURE_COOKIE', '0')) == '1',
    SESSION_COOKIE_NAME='bpsu_portal_session',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=int(os.environ.get('BPSU_SESSION_HOURS', '8'))),
)

PROGRAMS = {
    'BSA': 'Bachelor of Science in Accountancy',
    'BSBA': 'Bachelor of Science in Business Administration',
}
AREA_TITLES = {
    'Area I': 'RESEARCH',
    'Area II': 'PERFORMANCE OF GRADUATES',
    'Area III': 'EXTENSION',
    'Area IV': 'INTERNATIONALIZATION',
    'Area V': 'PLANNING PROCESS',
}
ROLES = [
    'College Dean', 'Accreditation Chair', 'Area Head',
    'Faculty Member', 'Support Staff', 'Accreditor / Visitor'
]
AREAS = list(AREA_TITLES)
STATUSES = ['Submitted','For Review','For Revision','Approved','Archived','Superseded']
DOC_TYPES = [
    'Policy / Guideline', 'Report', 'Minutes / Memorandum', 'Research Output',
    'Certificate / Recognition', 'Photo Documentation', 'Matrix / Summary',
    'Data / Spreadsheet', 'Presentation', 'Other'
]


def now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def db():
    # One connection per operation/request. WAL + busy_timeout improves safe concurrent
    # access for a small departmental deployment while keeping administration simple.
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA journal_mode = WAL')
    conn.execute('PRAGMA synchronous = NORMAL')
    conn.execute('PRAGMA busy_timeout = 30000')
    return conn


def init_db():
    conn = db()
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        area_access TEXT DEFAULT 'All',
        active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_code TEXT NOT NULL,
        version INTEGER NOT NULL DEFAULT 1,
        program_code TEXT NOT NULL DEFAULT 'BSA',
        title TEXT NOT NULL,
        description TEXT,
        area TEXT NOT NULL,
        criterion TEXT NOT NULL,
        requirement_id INTEGER,
        doc_type TEXT NOT NULL,
        academic_year TEXT,
        tags TEXT,
        original_filename TEXT NOT NULL,
        stored_filename TEXT NOT NULL,
        mime_type TEXT,
        file_size INTEGER DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'Submitted',
        owner_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        parent_id INTEGER,
        locked INTEGER DEFAULT 0,
        review_note TEXT,
        FOREIGN KEY(owner_id) REFERENCES users(id),
        FOREIGN KEY(parent_id) REFERENCES documents(id),
        FOREIGN KEY(requirement_id) REFERENCES requirements(id)
    );
    CREATE TABLE IF NOT EXISTS requirements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        program_code TEXT NOT NULL DEFAULT 'BSA',
        area TEXT NOT NULL,
        criterion TEXT NOT NULL,
        title TEXT NOT NULL,
        active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER NOT NULL,
        reviewer_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        note TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(document_id) REFERENCES documents(id),
        FOREIGN KEY(reviewer_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        document_id INTEGER,
        details TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(document_id) REFERENCES documents(id)
    );
    CREATE TABLE IF NOT EXISTS publications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER NOT NULL UNIQUE,
        publication_status TEXT NOT NULL DEFAULT 'Not Ready',
        privacy_reviewed INTEGER DEFAULT 0,
        publication_note TEXT,
        ready_by INTEGER,
        ready_at TEXT,
        published_by INTEGER,
        published_at TEXT,
        portal_file_name TEXT,
        portal_url TEXT,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(document_id) REFERENCES documents(id),
        FOREIGN KEY(ready_by) REFERENCES users(id),
        FOREIGN KEY(published_by) REFERENCES users(id)
    );
    ''')
    # Forward-compatible migration for installations created by the earlier DMS build.
    document_columns = {row['name'] for row in conn.execute('PRAGMA table_info(documents)')}
    if 'program_code' not in document_columns:
        conn.execute("ALTER TABLE documents ADD COLUMN program_code TEXT NOT NULL DEFAULT 'BSA'")
    requirement_columns = {row['name'] for row in conn.execute('PRAGMA table_info(requirements)')}
    if 'program_code' not in requirement_columns:
        conn.execute("ALTER TABLE requirements ADD COLUMN program_code TEXT NOT NULL DEFAULT 'BSA'")
    conn.execute('CREATE INDEX IF NOT EXISTS idx_documents_public ON documents(status,program_code,area)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_documents_owner ON documents(owner_id,updated_at)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_publications_status ON publications(publication_status,document_id)')
    conn.execute("UPDATE requirements SET active=0 WHERE area NOT IN ('Area I','Area II','Area III','Area IV','Area V')")
    user_count = conn.execute('SELECT COUNT(*) c FROM users').fetchone()['c']
    if user_count == 0:
        admin_email = os.environ.get('BPSU_ADMIN_EMAIL', '').strip().lower()
        admin_password = os.environ.get('BPSU_ADMIN_PASSWORD', '')
        admin_name = os.environ.get('BPSU_ADMIN_NAME', 'College Dean').strip() or 'College Dean'
        if admin_email and admin_password:
            conn.execute(
                'INSERT INTO users (name,email,password_hash,role,created_at) VALUES (?,?,?,?,?)',
                (admin_name, admin_email, generate_password_hash(admin_password), 'College Dean', now())
            )
        elif os.environ.get('BPSU_ENABLE_DEMO_ACCOUNTS', '0') == '1':
            demo_users = [
                ('College Dean', 'dean@bpsu.demo', 'dean123', 'College Dean'),
                ('Accreditation Chair', 'chair@bpsu.demo', 'chair123', 'Accreditation Chair'),
                ('Area Head', 'areahead@bpsu.demo', 'area123', 'Area Head'),
                ('Faculty Member', 'faculty@bpsu.demo', 'faculty123', 'Faculty Member'),
                ('Support Staff', 'support@bpsu.demo', 'support123', 'Support Staff'),
                ('Accreditor / Visitor', 'accreditor@bpsu.demo', 'view123', 'Accreditor / Visitor'),
            ]
            for name, email, password, role in demo_users:
                conn.execute(
                    'INSERT INTO users (name,email,password_hash,role,created_at) VALUES (?,?,?,?,?)',
                    (name,email,generate_password_hash(password),role,now())
                )
    # Every program/Area starts with the two sections requested for the portal.
    for program_code in PROGRAMS:
        for area in AREAS:
            for criterion, title in [('NP', 'Narrative Profile'), ('EC', 'Extent of Compliance')]:
                exists = conn.execute(
                    '''SELECT 1 FROM requirements
                       WHERE program_code=? AND area=? AND criterion=? AND active=1 LIMIT 1''',
                    (program_code, area, criterion)
                ).fetchone()
                if not exists:
                    conn.execute(
                        '''INSERT INTO requirements
                           (program_code,area,criterion,title,created_at) VALUES (?,?,?,?,?)''',
                        (program_code, area, criterion, title, now())
                    )
    conn.commit()
    conn.close()


def log_action(action, document_id=None, details=''):
    conn = db()
    conn.execute(
        'INSERT INTO audit_logs (user_id,action,document_id,details,created_at) VALUES (?,?,?,?,?)',
        (session.get('user_id'), action, document_id, details, now())
    )
    conn.commit(); conn.close()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS


def current_user():
    uid = session.get('user_id')
    if not uid:
        return None
    conn = db(); user = conn.execute('SELECT * FROM users WHERE id=? AND active=1',(uid,)).fetchone(); conn.close()
    return user


def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not current_user():
            return redirect(url_for('login', next=request.path))
        return fn(*args, **kwargs)
    return wrapped


def roles_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            u=current_user()
            if not u:
                return redirect(url_for('login'))
            if u['role'] not in roles:
                flash('You do not have permission to perform that action.', 'error')
                return redirect(url_for('dashboard'))
            return fn(*args, **kwargs)
        return wrapped
    return deco


def visible_document_clause(user):
    if user['role'] == 'Accreditor / Visitor':
        return "d.status='Approved' AND EXISTS (SELECT 1 FROM publications p WHERE p.document_id=d.id AND p.publication_status='Published')"
    if user['role'] == 'Faculty Member':
        return "(d.owner_id=? OR (d.status='Approved' AND EXISTS (SELECT 1 FROM publications p WHERE p.document_id=d.id AND p.publication_status='Published')))"
    return '1=1'


def can_edit_document(user, doc):
    if user['role'] in ['College Dean','Accreditation Chair']:
        return True
    if user['role'] in ['Area Head','Support Staff'] and doc['status'] not in ['Approved','Archived']:
        return True
    return user['role']=='Faculty Member' and doc['owner_id']==user['id'] and doc['status'] in ['Submitted','For Revision']


def can_review(user):
    return user['role'] in ['College Dean','Accreditation Chair','Area Head']


def document_is_published(conn, doc_id):
    return conn.execute(
        "SELECT 1 FROM publications WHERE document_id=? AND publication_status='Published'",
        (doc_id,)
    ).fetchone() is not None


def generate_doc_code(conn, program_code, area):
    roman = area.replace('Area ','').replace(' ','')
    prefix = f'BPSU-CBA-{program_code}-L4-A{roman}'
    count = conn.execute('SELECT COUNT(DISTINCT doc_code) c FROM documents WHERE doc_code LIKE ?', (prefix+'-%',)).fetchone()['c'] + 1
    return f'{prefix}-{count:04d}'


def portal_filename(doc):
    original = doc['original_filename'] or 'evidence.bin'
    ext = original.rsplit('.', 1)[1].lower() if '.' in original else 'bin'
    return f"{doc['doc_code']}-v{doc['version']}.{ext}"


def portal_record(doc, published_date=None):
    program_code = doc['program_code'] or 'BSA'
    return {
        'id': f"{doc['doc_code']}-v{doc['version']}",
        'docCode': doc['doc_code'],
        'version': doc['version'],
        'title': doc['title'],
        'description': doc['description'] or '',
        'program': PROGRAMS.get(program_code, program_code),
        'programCode': program_code,
        'area': doc['area'],
        'areaTitle': AREA_TITLES.get(doc['area'], ''),
        'criterion': doc['criterion'],
        'docType': doc['doc_type'],
        'academicYear': doc['academic_year'] or '',
        'tags': [t.strip() for t in (doc['tags'] or '').split(',') if t.strip()],
        'publishedDate': published_date or datetime.now().strftime('%Y-%m-%d'),
        'owner': doc['owner_name'] if 'owner_name' in doc.keys() else 'College of Business and Accountancy',
        'fileUrl': url_for('public_document_file', doc_id=doc['id'], _external=True)
    }


def user_count():
    conn = db()
    count = conn.execute('SELECT COUNT(*) c FROM users').fetchone()['c']
    conn.close()
    return count


def safe_next_url(value):
    """Allow only local paths after login; never redirect to an external host."""
    if value and value.startswith('/') and not value.startswith('//'):
        return value
    return url_for('dashboard')


def csrf_token():
    token = session.get('_csrf_token')
    if not token:
        token = secrets.token_urlsafe(32)
        session['_csrf_token'] = token
    return token

@app.before_request
def verify_csrf():
    if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
        supplied = request.form.get('_csrf_token') or request.headers.get('X-CSRF-Token')
        expected = session.get('_csrf_token')
        if not expected or not supplied or not secrets.compare_digest(str(expected), str(supplied)):
            abort(400, description='Invalid or missing CSRF token.')

@app.after_request
def add_security_headers(response):
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
    response.headers.setdefault('Content-Security-Policy', "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self' 'unsafe-inline'; frame-ancestors 'self'")
    if request.is_secure:
        response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
    if request.path == '/api/public/evidence':
        allowed_origin = os.environ.get('BPSU_PUBLIC_PORTAL_ORIGIN', 'https://delovinodhan.github.io')
        origin = request.headers.get('Origin')
        if origin == allowed_origin:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Vary'] = 'Origin'
        response.headers['Cache-Control'] = 'no-store'
    return response

@app.context_processor
def inject_globals():
    return {
        'current_user': current_user(), 'ROLES': ROLES, 'AREAS': AREAS,
        'PROGRAMS': PROGRAMS, 'AREA_TITLES': AREA_TITLES,
        'STATUSES': STATUSES, 'DOC_TYPES': DOC_TYPES, 'csrf_token': csrf_token
    }


@app.route('/')
def public_portal():
    return send_file(BASE_DIR / 'index.html')


@app.route('/assets/<path:filename>')
def portal_asset(filename):
    return send_from_directory(BASE_DIR / 'assets', filename)


@app.route('/legacy/<path:filename>')
def legacy_document(filename):
    # Legacy files are limited to a safe root-level filename referenced by the
    # checked-in evidence manifest. Newly uploaded files use /public/files/<id>.
    safe_name = secure_filename(filename)
    if not safe_name or safe_name != filename or not allowed_file(safe_name):
        abort(404)
    return send_from_directory(BASE_DIR, safe_name, as_attachment=False)


@app.route('/api/public/evidence')
def public_evidence_api():
    records = []
    manifest_path = BASE_DIR / 'assets' / 'data' / 'evidence.json'
    if manifest_path.exists():
        try:
            legacy_records = json.loads(manifest_path.read_text(encoding='utf-8'))
            for item in legacy_records if isinstance(legacy_records, list) else []:
                item = dict(item)
                file_url = str(item.get('fileUrl') or '')
                if file_url.startswith('/'):
                    item['fileUrl'] = request.url_root.rstrip('/') + file_url
                records.append(item)
        except (OSError, ValueError, TypeError):
            app.logger.exception('Could not read the legacy evidence manifest.')

    conn = db()
    rows = conn.execute('''SELECT d.*,u.name owner_name,p.published_at
        FROM documents d
        JOIN users u ON u.id=d.owner_id
        JOIN publications p ON p.document_id=d.id
        WHERE d.status='Approved' AND p.publication_status='Published'
        ORDER BY d.program_code,d.area,d.criterion,d.title''').fetchall()
    conn.close()
    dynamic_records = [portal_record(row, (row['published_at'] or now())[:10]) for row in rows]
    merged = {str(item.get('id') or item.get('docCode')): item for item in records}
    for item in dynamic_records:
        merged[str(item['id'])] = item
    return jsonify(list(merged.values()))


@app.route('/public/files/<int:doc_id>')
def public_document_file(doc_id):
    conn = db()
    doc = conn.execute('''SELECT d.* FROM documents d
        JOIN publications p ON p.document_id=d.id
        WHERE d.id=? AND d.status='Approved' AND p.publication_status='Published' ''',
        (doc_id,)).fetchone()
    conn.close()
    if not doc:
        abort(404)
    path = UPLOAD_DIR / doc['stored_filename']
    if not path.is_file():
        abort(404, description='The published evidence file could not be found.')
    return send_from_directory(
        UPLOAD_DIR,
        doc['stored_filename'],
        as_attachment=request.args.get('download') == '1',
        download_name=doc['original_filename'],
        mimetype=doc['mime_type'] or None,
    )


@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if user_count() > 0:
        flash('The portal administrator has already been configured.', 'success')
        return redirect(url_for('login'))
    configured_token = os.environ.get('BPSU_SETUP_TOKEN', '')
    if not configured_token:
        abort(503, description='Initial setup is disabled until BPSU_SETUP_TOKEN is configured.')
    if request.method == 'POST':
        supplied_token = request.form.get('setup_token', '')
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if not secrets.compare_digest(supplied_token, configured_token):
            flash('The setup token is incorrect.', 'error')
        elif not name or not email or len(password) < 12:
            flash('Enter your name, email address, and a password of at least 12 characters.', 'error')
        elif not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email):
            flash('Enter a valid email address.', 'error')
        else:
            conn = db()
            try:
                conn.execute(
                    'INSERT INTO users (name,email,password_hash,role,created_at) VALUES (?,?,?,?,?)',
                    (name, email, generate_password_hash(password), 'College Dean', now())
                )
                conn.commit()
            except sqlite3.IntegrityError:
                conn.rollback()
                flash('That email address is already registered.', 'error')
            else:
                flash('Administrator account created. You can now sign in.', 'success')
                conn.close()
                return redirect(url_for('login'))
            conn.close()
    return render_template('setup.html')


@app.route('/login', methods=['GET','POST'])
def login():
    if current_user():
        return redirect(url_for('dashboard'))
    if user_count() == 0:
        return redirect(url_for('setup'))
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        conn=db(); user=conn.execute('SELECT * FROM users WHERE lower(email)=? AND active=1',(email,)).fetchone(); conn.close()
        if user and check_password_hash(user['password_hash'],password):
            session.clear(); session['user_id']=user['id']; session.permanent=True
            log_action('LOGIN', details=f"{user['name']} signed in")
            return redirect(safe_next_url(request.args.get('next')))
        flash('Invalid email or password.', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    if session.get('user_id'):
        log_action('LOGOUT')
    session.clear()
    return redirect(url_for('login'))


@app.route('/workspace')
@login_required
def dashboard():
    u=current_user(); conn=db()
    params=[]; clause=visible_document_clause(u)
    if '?' in clause: params.append(u['id'])
    metrics={}
    for status in ['Submitted','For Review','For Revision','Approved']:
        q=f'SELECT COUNT(*) c FROM documents d WHERE {clause} AND d.status=?'
        metrics[status]=conn.execute(q,params+[status]).fetchone()['c']
    metrics['All']=conn.execute(f'SELECT COUNT(*) c FROM documents d WHERE {clause}',params).fetchone()['c']
    metrics['Requirements']=conn.execute('SELECT COUNT(*) c FROM requirements WHERE active=1').fetchone()['c']
    recent=conn.execute(f'''SELECT d.*,u.name owner_name FROM documents d JOIN users u ON u.id=d.owner_id
        WHERE {clause} ORDER BY d.updated_at DESC LIMIT 8''',params).fetchall()
    # approval / coverage by area based on configured requirement rows
    area_stats=[]
    for program_code in PROGRAMS:
        for area in AREAS:
            required=conn.execute('''SELECT COUNT(*) c FROM requirements
                WHERE program_code=? AND area=? AND active=1''',(program_code,area)).fetchone()['c']
            approved=conn.execute('''SELECT COUNT(DISTINCT requirement_id) c FROM documents
                WHERE program_code=? AND area=? AND status='Approved' AND requirement_id IS NOT NULL''',
                (program_code,area)).fetchone()['c']
            pct=round((approved/required*100) if required else 0)
            area_stats.append({'program':program_code,'area':area,'required':required,'approved':approved,'pct':pct})
    conn.close()
    return render_template('dashboard.html', metrics=metrics, recent=recent, area_stats=area_stats)


@app.route('/documents')
@login_required
def documents():
    u=current_user(); conn=db()
    where=[visible_document_clause(u)]; params=[]
    if '?' in where[0]: params.append(u['id'])
    q=request.args.get('q','').strip(); program_code=request.args.get('program_code',''); area=request.args.get('area',''); status=request.args.get('status',''); doc_type=request.args.get('doc_type','')
    if q:
        where.append('(d.title LIKE ? OR d.doc_code LIKE ? OR d.tags LIKE ? OR d.criterion LIKE ?)')
        like=f'%{q}%'; params += [like,like,like,like]
    if program_code in PROGRAMS: where.append('d.program_code=?'); params.append(program_code)
    if area: where.append('d.area=?'); params.append(area)
    if status: where.append('d.status=?'); params.append(status)
    if doc_type: where.append('d.doc_type=?'); params.append(doc_type)
    rows=conn.execute(f'''SELECT d.*,u.name owner_name,r.title requirement_title FROM documents d
        JOIN users u ON u.id=d.owner_id LEFT JOIN requirements r ON r.id=d.requirement_id
        WHERE {' AND '.join(where)} ORDER BY d.updated_at DESC''',params).fetchall()
    conn.close()
    return render_template('documents.html', documents=rows, filters={'q':q,'program_code':program_code,'area':area,'status':status,'doc_type':doc_type})


@app.route('/upload', methods=['GET','POST'])
@login_required
def upload():
    u=current_user()
    if u['role']=='Accreditor / Visitor':
        flash('Accreditor accounts are read-only.', 'error'); return redirect(url_for('documents'))
    conn=db()
    requirements=conn.execute('SELECT * FROM requirements WHERE active=1 ORDER BY program_code,area,criterion').fetchall()
    existing=conn.execute("SELECT id,doc_code,program_code,title,version FROM documents WHERE status NOT IN ('Superseded') ORDER BY updated_at DESC").fetchall()
    if request.method=='POST':
        f=request.files.get('file')
        if not f or not f.filename:
            flash('Please choose a document to upload.', 'error'); conn.close(); return render_template('upload.html',requirements=requirements,existing=existing)
        if not allowed_file(f.filename):
            flash('This file type is not allowed.', 'error'); conn.close(); return render_template('upload.html',requirements=requirements,existing=existing)
        title=request.form.get('title','').strip(); program_code=request.form.get('program_code',''); area=request.form.get('area',''); criterion=request.form.get('criterion','').strip()
        if not title or program_code not in PROGRAMS or area not in AREAS or not criterion:
            flash('Program, title, Area, and Criterion / Indicator are required.', 'error'); conn.close(); return render_template('upload.html',requirements=requirements,existing=existing)
        parent_id=request.form.get('parent_id') or None
        if parent_id:
            parent=conn.execute('SELECT * FROM documents WHERE id=?',(parent_id,)).fetchone()
            if not parent: abort(400)
            program_code=parent['program_code']; area=parent['area']; criterion=parent['criterion']
            doc_code=parent['doc_code']; version=conn.execute('SELECT MAX(version) v FROM documents WHERE doc_code=?',(doc_code,)).fetchone()['v']+1
            conn.execute("UPDATE documents SET status='Superseded',updated_at=? WHERE doc_code=? AND status!='Archived'",(now(),doc_code))
        else:
            doc_code=generate_doc_code(conn,program_code,area); version=1
        original=secure_filename(f.filename)
        ext=original.rsplit('.',1)[1].lower()
        stored=f'{uuid.uuid4().hex}.{ext}'
        path=UPLOAD_DIR/stored; f.save(path)
        req_id=request.form.get('requirement_id') or None
        if req_id:
            requirement=conn.execute('''SELECT id FROM requirements
                WHERE id=? AND program_code=? AND area=? AND active=1''',(req_id,program_code,area)).fetchone()
            if not requirement:
                path.unlink(missing_ok=True); conn.close(); abort(400, description='The selected evidence requirement does not match the program and Area.')
        cur=conn.execute('''INSERT INTO documents
            (doc_code,version,program_code,title,description,area,criterion,requirement_id,doc_type,academic_year,tags,original_filename,stored_filename,mime_type,file_size,status,owner_id,created_at,updated_at,parent_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(
                doc_code,version,program_code,title,request.form.get('description','').strip(),area,criterion,req_id,
                request.form.get('doc_type','Other'),request.form.get('academic_year','').strip(),request.form.get('tags','').strip(),
                original,stored,f.mimetype,path.stat().st_size,'Submitted',u['id'],now(),now(),parent_id
            ))
        doc_id=cur.lastrowid
        conn.commit(); conn.close()
        log_action('UPLOAD',doc_id,f'{doc_code} v{version}: {title}')
        flash(f'Document uploaded successfully as {doc_code} (Version {version}).','success')
        return redirect(url_for('document_detail',doc_id=doc_id))
    conn.close()
    return render_template('upload.html',requirements=requirements,existing=existing)


@app.route('/documents/<int:doc_id>')
@login_required
def document_detail(doc_id):
    u=current_user(); conn=db()
    doc=conn.execute('''SELECT d.*,u.name owner_name,u.email owner_email,r.title requirement_title FROM documents d
        JOIN users u ON u.id=d.owner_id LEFT JOIN requirements r ON r.id=d.requirement_id WHERE d.id=?''',(doc_id,)).fetchone()
    if not doc: conn.close(); abort(404)
    published = doc['status']=='Approved' and document_is_published(conn, doc_id)
    if u['role']=='Accreditor / Visitor' and not published: conn.close(); abort(403)
    if u['role']=='Faculty Member' and doc['owner_id']!=u['id'] and not published: conn.close(); abort(403)
    reviews=conn.execute('''SELECT rv.*,u.name reviewer_name FROM reviews rv JOIN users u ON u.id=rv.reviewer_id
        WHERE rv.document_id=? ORDER BY rv.created_at DESC''',(doc_id,)).fetchall()
    versions=conn.execute('SELECT id,version,status,created_at,original_filename FROM documents WHERE doc_code=? ORDER BY version DESC',(doc['doc_code'],)).fetchall()
    publication=conn.execute('''SELECT p.*,ru.name ready_by_name,pu.name published_by_name
        FROM publications p
        LEFT JOIN users ru ON ru.id=p.ready_by
        LEFT JOIN users pu ON pu.id=p.published_by
        WHERE p.document_id=?''',(doc_id,)).fetchone()
    conn.close()
    return render_template('document_detail.html',doc=doc,reviews=reviews,versions=versions,
        publication=publication,can_edit=can_edit_document(u,doc),can_review=can_review(u))


@app.route('/documents/<int:doc_id>/file')
@login_required
def document_file(doc_id):
    u=current_user(); conn=db(); doc=conn.execute('SELECT * FROM documents WHERE id=?',(doc_id,)).fetchone()
    if not doc: conn.close(); abort(404)
    published = doc['status']=='Approved' and document_is_published(conn, doc_id)
    conn.close()
    if u['role']=='Accreditor / Visitor' and not published: abort(403)
    if u['role']=='Faculty Member' and doc['owner_id']!=u['id'] and not published: abort(403)
    inline=request.args.get('view')=='1'
    log_action('VIEW_FILE' if inline else 'DOWNLOAD',doc_id,doc['original_filename'])
    return send_from_directory(UPLOAD_DIR,doc['stored_filename'],as_attachment=not inline,download_name=doc['original_filename'])


@app.route('/documents/<int:doc_id>/review', methods=['POST'])
@login_required
@roles_required('College Dean','Accreditation Chair','Area Head')
def review_document(doc_id):
    action=request.form.get('action'); note=request.form.get('note','').strip()
    allowed={'For Review','For Revision','Approved','Archived'}
    if action not in allowed: abort(400)
    u=current_user(); conn=db(); doc=conn.execute('SELECT * FROM documents WHERE id=?',(doc_id,)).fetchone()
    if not doc: conn.close(); abort(404)
    published=conn.execute("SELECT publication_status FROM publications WHERE document_id=?",(doc_id,)).fetchone()
    if action != 'Approved' and published and published['publication_status']=='Published':
        conn.close()
        flash('This evidence is currently published on the Accreditation Evidence Portal. Record it as Unpublished before changing its internal approval status.','error')
        return redirect(url_for('document_detail',doc_id=doc_id))
    locked=1 if action in ['Approved','Archived'] else 0
    conn.execute('UPDATE documents SET status=?,review_note=?,locked=?,updated_at=? WHERE id=?',(action,note,locked,now(),doc_id))
    conn.execute('INSERT INTO reviews (document_id,reviewer_id,action,note,created_at) VALUES (?,?,?,?,?)',(doc_id,u['id'],action,note,now()))
    if action != 'Approved':
        conn.execute("""UPDATE publications SET publication_status='Not Ready',privacy_reviewed=0,
            publication_note='Internal approval was changed; publication clearance reset.',
            ready_by=NULL,ready_at=NULL,updated_at=? WHERE document_id=? AND publication_status!='Published'""",(now(),doc_id))
    conn.commit(); conn.close()
    log_action('REVIEW',doc_id,f'{action}: {note}')
    flash(f'Document status updated to {action}.','success')
    return redirect(url_for('document_detail',doc_id=doc_id))


@app.route('/review-queue')
@login_required
@roles_required('College Dean','Accreditation Chair','Area Head')
def review_queue():
    conn=db(); rows=conn.execute('''SELECT d.*,u.name owner_name FROM documents d JOIN users u ON u.id=d.owner_id
        WHERE d.status IN ('Submitted','For Review','For Revision') ORDER BY d.updated_at ASC''').fetchall(); conn.close()
    return render_template('review_queue.html',documents=rows)



@app.route('/publication-queue')
@login_required
@roles_required('College Dean','Accreditation Chair','Area Head')
def publication_queue():
    conn=db()
    rows=conn.execute('''SELECT d.*,u.name owner_name,
        COALESCE(p.publication_status,'Not Ready') publication_status,
        p.privacy_reviewed,p.publication_note,p.ready_at,p.published_at,p.portal_file_name,p.portal_url
        FROM documents d JOIN users u ON u.id=d.owner_id
        LEFT JOIN publications p ON p.document_id=d.id
        WHERE d.status='Approved'
        ORDER BY CASE COALESCE(p.publication_status,'Not Ready')
            WHEN 'Ready for Publication' THEN 0 WHEN 'Not Ready' THEN 1 WHEN 'Unpublished' THEN 2 ELSE 3 END,
            d.area,d.criterion,d.updated_at DESC''').fetchall()
    metrics={
        'approved': len(rows),
        'ready': sum(1 for r in rows if r['publication_status']=='Ready for Publication'),
        'published': sum(1 for r in rows if r['publication_status']=='Published'),
        'not_ready': sum(1 for r in rows if r['publication_status'] in ['Not Ready','Unpublished'])
    }
    conn.close()
    return render_template('publication_queue.html',documents=rows,metrics=metrics)


@app.route('/documents/<int:doc_id>/publication/ready', methods=['POST'])
@login_required
@roles_required('College Dean','Accreditation Chair','Area Head')
def publication_ready(doc_id):
    u=current_user()
    if request.form.get('privacy_confirmed') != 'yes':
        flash('Confirm the publication/privacy review before marking evidence ready.', 'error')
        return redirect(url_for('document_detail',doc_id=doc_id))
    note=request.form.get('publication_note','').strip()
    conn=db()
    doc=conn.execute('SELECT * FROM documents WHERE id=?',(doc_id,)).fetchone()
    if not doc: conn.close(); abort(404)
    if doc['status']!='Approved':
        conn.close(); flash('Only internally approved evidence can enter the publication queue.','error')
        return redirect(url_for('document_detail',doc_id=doc_id))
    stamp=now()
    conn.execute('''INSERT INTO publications
        (document_id,publication_status,privacy_reviewed,publication_note,ready_by,ready_at,portal_file_name,updated_at)
        VALUES (?,?,?,?,?,?,?,?)
        ON CONFLICT(document_id) DO UPDATE SET
        publication_status='Ready for Publication',privacy_reviewed=1,publication_note=excluded.publication_note,
        ready_by=excluded.ready_by,ready_at=excluded.ready_at,portal_file_name=excluded.portal_file_name,
        published_by=NULL,published_at=NULL,portal_url=NULL,updated_at=excluded.updated_at''',
        (doc_id,'Ready for Publication',1,note,u['id'],stamp,portal_filename(doc),stamp))
    conn.commit(); conn.close()
    log_action('PUBLICATION_READY',doc_id,f'Marked Ready for Publication. {note}')
    flash('Evidence marked Ready for Publication. A Dean or Accreditation Chair can now publish it directly to the portal.','success')
    return redirect(url_for('document_detail',doc_id=doc_id))


@app.route('/documents/<int:doc_id>/publication/package')
@login_required
@roles_required('College Dean','Accreditation Chair')
def publication_package(doc_id):
    conn=db()
    doc=conn.execute('''SELECT d.*,u.name owner_name,p.publication_status,p.ready_at,p.portal_file_name
        FROM documents d JOIN users u ON u.id=d.owner_id
        LEFT JOIN publications p ON p.document_id=d.id WHERE d.id=?''',(doc_id,)).fetchone()
    conn.close()
    if not doc: abort(404)
    if doc['status']!='Approved' or doc['publication_status'] not in ['Ready for Publication','Published']:
        flash('This evidence must be Approved and Ready for Publication before a package can be generated.','error')
        return redirect(url_for('document_detail',doc_id=doc_id))
    source=UPLOAD_DIR/doc['stored_filename']
    if not source.exists(): abort(404, description='The stored evidence file could not be found.')
    file_name=doc['portal_file_name'] or portal_filename(doc)
    record=portal_record(doc, (doc['ready_at'] or now())[:10])
    mem=io.BytesIO()
    with zipfile.ZipFile(mem,'w',zipfile.ZIP_DEFLATED) as z:
        z.write(source,arcname=f'documents/{file_name}')
        z.writestr('portal-record.json',json.dumps(record,ensure_ascii=False,indent=2))
        z.writestr('portal-record.js','window.EVIDENCE_DATA = window.EVIDENCE_DATA || [];\nwindow.EVIDENCE_DATA.push(' + json.dumps(record,ensure_ascii=False,indent=2) + ');\n')
        manifest=io.StringIO()
        writer=csv.writer(manifest)
        writer.writerow(['doc_code','version','title','area','criterion','doc_type','academic_year','portal_file_name','publication_status'])
        writer.writerow([doc['doc_code'],doc['version'],doc['title'],doc['area'],doc['criterion'],doc['doc_type'],doc['academic_year'] or '',file_name,doc['publication_status']])
        z.writestr('publication-manifest.csv',manifest.getvalue())
        z.writestr('PUBLISHING_INSTRUCTIONS.txt',
            'BPSU CBA AACCUP PORTAL PUBLICATION PACKAGE\n\n'
            '1. Review the packaged evidence file one final time.\n'
            '2. Copy the file inside documents/ to the portal repository documents/ folder.\n'
            '3. Add the object in portal-record.json to window.EVIDENCE_DATA in assets/data/portal-data.js.\n'
            '4. Commit/push the portal changes and verify the GitHub Pages site.\n'
            '5. Return to the DMS and mark this evidence Published, recording the portal URL.\n\n'
            'Important: marking Published in the DMS records the publication event; it does not itself upload files to GitHub.\n')
    mem.seek(0)
    log_action('PUBLICATION_PACKAGE',doc_id,f'Generated publication package for {file_name}')
    return send_file(mem,mimetype='application/zip',as_attachment=True,
        download_name=f"{doc['doc_code']}-v{doc['version']}-PORTAL-PACKAGE.zip")


@app.route('/documents/<int:doc_id>/publication/published', methods=['POST'])
@login_required
@roles_required('College Dean','Accreditation Chair')
def publication_published(doc_id):
    if request.form.get('published_confirmed') != 'yes':
        flash('Confirm the final direct-publication step before continuing.','error')
        return redirect(url_for('document_detail',doc_id=doc_id))
    u=current_user(); conn=db()
    row=conn.execute('''SELECT d.status,p.publication_status FROM documents d
        LEFT JOIN publications p ON p.document_id=d.id WHERE d.id=?''',(doc_id,)).fetchone()
    if not row: conn.close(); abort(404)
    if row['status']!='Approved' or row['publication_status']!='Ready for Publication':
        conn.close(); flash('Only evidence that is Approved and Ready for Publication can be marked Published.','error')
        return redirect(url_for('document_detail',doc_id=doc_id))
    stamp=now()
    portal_url=url_for('public_document_file',doc_id=doc_id,_external=True)
    conn.execute('''UPDATE publications SET publication_status='Published',published_by=?,published_at=?,
        portal_url=?,updated_at=? WHERE document_id=?''',(u['id'],stamp,portal_url,stamp,doc_id))
    conn.commit(); conn.close()
    log_action('PUBLISHED_TO_PORTAL',doc_id,f'Direct portal publication completed. {portal_url}')
    flash('Published successfully. The document is now visible in the public Evidence Library and to accreditors.','success')
    return redirect(url_for('document_detail',doc_id=doc_id))


@app.route('/documents/<int:doc_id>/publication/unpublish', methods=['POST'])
@login_required
@roles_required('College Dean','Accreditation Chair')
def publication_unpublish(doc_id):
    note=request.form.get('publication_note','').strip()
    conn=db(); row=conn.execute('SELECT id FROM publications WHERE document_id=?',(doc_id,)).fetchone()
    if not row: conn.close(); abort(404)
    conn.execute("""UPDATE publications SET publication_status='Unpublished',publication_note=?,
        published_by=NULL,published_at=NULL,portal_url=NULL,updated_at=? WHERE document_id=?""",
        (note or 'Publication withdrawn from the public Evidence Library.',now(),doc_id))
    conn.commit(); conn.close()
    log_action('UNPUBLISH_PORTAL',doc_id,note or 'Publication withdrawn')
    flash('The document has been removed from the public Evidence Library. Its controlled file remains in secure storage.','success')
    return redirect(url_for('document_detail',doc_id=doc_id))


@app.route('/evidence-matrix', methods=['GET','POST'])
@login_required
def evidence_matrix():
    u=current_user(); conn=db()
    if request.method=='POST':
        if u['role'] not in ['College Dean','Accreditation Chair']:
            conn.close(); abort(403)
        program_code=request.form.get('program_code'); area=request.form.get('area'); criterion=request.form.get('criterion','').strip(); title=request.form.get('title','').strip()
        if program_code in PROGRAMS and area in AREAS and criterion and title:
            conn.execute('''INSERT INTO requirements
                (program_code,area,criterion,title,created_at) VALUES (?,?,?,?,?)''',
                (program_code,area,criterion,title,now())); conn.commit()
            log_action('ADD_REQUIREMENT',details=f'{program_code} {area} {criterion}: {title}')
            flash('Evidence requirement added.','success')
        return redirect(url_for('evidence_matrix',program_code=program_code or '',area=area or ''))
    program_code=request.args.get('program_code',''); area=request.args.get('area','')
    params=[]; where='WHERE r.active=1'
    if program_code in PROGRAMS: where+=' AND r.program_code=?'; params.append(program_code)
    if area: where+=' AND r.area=?'; params.append(area)
    rows=conn.execute(f'''SELECT r.*,
        (SELECT COUNT(*) FROM documents d WHERE d.requirement_id=r.id) uploaded_count,
        (SELECT COUNT(*) FROM documents d WHERE d.requirement_id=r.id AND d.status='Approved') approved_count,
        (SELECT d.id FROM documents d WHERE d.requirement_id=r.id ORDER BY d.version DESC,d.updated_at DESC LIMIT 1) latest_doc_id,
        (SELECT d.status FROM documents d WHERE d.requirement_id=r.id ORDER BY d.version DESC,d.updated_at DESC LIMIT 1) latest_status
        FROM requirements r {where} ORDER BY r.program_code,r.area,r.criterion''',params).fetchall()
    conn.close()
    return render_template('evidence_matrix.html',requirements=rows,selected_program=program_code,selected_area=area)


@app.route('/requirements/<int:req_id>/archive', methods=['POST'])
@login_required
@roles_required('College Dean','Accreditation Chair')
def archive_requirement(req_id):
    conn=db(); conn.execute('UPDATE requirements SET active=0 WHERE id=?',(req_id,)); conn.commit(); conn.close(); log_action('ARCHIVE_REQUIREMENT',details=f'Requirement {req_id}')
    flash('Requirement archived.','success'); return redirect(url_for('evidence_matrix'))


@app.route('/audit')
@login_required
@roles_required('College Dean','Accreditation Chair','Area Head')
def audit():
    conn=db(); rows=conn.execute('''SELECT a.*,u.name user_name,d.doc_code FROM audit_logs a
        LEFT JOIN users u ON u.id=a.user_id LEFT JOIN documents d ON d.id=a.document_id
        ORDER BY a.id DESC LIMIT 500''').fetchall(); conn.close()
    return render_template('audit.html',logs=rows)


@app.route('/users', methods=['GET','POST'])
@login_required
@roles_required('College Dean','Accreditation Chair')
def users():
    conn=db()
    if request.method=='POST':
        name=request.form.get('name','').strip(); email=request.form.get('email','').strip().lower(); password=request.form.get('password',''); role=request.form.get('role')
        if name and email and len(password) >= 12 and role in ROLES:
            try:
                conn.execute('INSERT INTO users (name,email,password_hash,role,created_at) VALUES (?,?,?,?,?)',(name,email,generate_password_hash(password),role,now())); conn.commit()
                log_action('CREATE_USER',details=f'{email} - {role}'); flash('User account created.','success')
            except sqlite3.IntegrityError:
                flash('That email address already exists.','error')
        else:
            flash('Name, valid email, role, and a temporary password of at least 12 characters are required.','error')
        return redirect(url_for('users'))
    rows=conn.execute('SELECT * FROM users ORDER BY active DESC,role,name').fetchall(); conn.close()
    return render_template('users.html',users=rows)


@app.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@roles_required('College Dean','Accreditation Chair')
def toggle_user(user_id):
    if user_id==session.get('user_id'):
        flash('You cannot disable your own account while signed in.','error'); return redirect(url_for('users'))
    conn=db(); row=conn.execute('SELECT active,email FROM users WHERE id=?',(user_id,)).fetchone()
    if row:
        conn.execute('UPDATE users SET active=? WHERE id=?',(0 if row['active'] else 1,user_id)); conn.commit(); log_action('TOGGLE_USER',details=row['email'])
    conn.close(); return redirect(url_for('users'))


@app.route('/reports/export.csv')
@login_required
def export_csv():
    u=current_user(); conn=db(); clause=visible_document_clause(u); params=[]
    if '?' in clause: params.append(u['id'])
    rows=conn.execute(f'''SELECT d.doc_code,d.version,d.program_code,d.title,d.area,d.criterion,d.doc_type,d.academic_year,d.tags,d.status,
        COALESCE(p.publication_status,'Not Ready') publication_status,p.published_at,p.portal_url,
        u.name owner,d.created_at,d.updated_at
        FROM documents d JOIN users u ON u.id=d.owner_id
        LEFT JOIN publications p ON p.document_id=d.id
        WHERE {clause} ORDER BY d.area,d.doc_code,d.version''',params).fetchall(); conn.close()
    output=io.StringIO(); w=csv.writer(output); w.writerow(rows[0].keys() if rows else ['doc_code','version','program_code','title','area','criterion','doc_type','academic_year','tags','status','publication_status','published_at','portal_url','owner','created_at','updated_at'])
    for r in rows: w.writerow(list(r))
    log_action('EXPORT_CSV',details=f'{len(rows)} documents')
    return Response(output.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=BPSU_AACCUP_Evidence_Register.csv'})


@app.route('/help')
@login_required
def help_page():
    return render_template('help.html')


@app.route('/health')
def health():
    try:
        conn=db(); conn.execute('SELECT 1').fetchone(); conn.close()
        storage_ready = UPLOAD_DIR.is_dir() and os.access(UPLOAD_DIR, os.W_OK)
    except sqlite3.Error:
        return jsonify({'status':'error','database':'unavailable'}), 503
    return jsonify({'status':'ok','system':'BPSU CBA AACCUP Evidence Portal','storage':'ready' if storage_ready else 'read-only'}), (200 if storage_ready else 503)


@app.errorhandler(413)
def too_large(e):
    flash(f'File is too large. Maximum upload size is {MAX_FILE_SIZE_MB} MB.','error')
    return redirect(url_for('upload'))


# Initialize schema for both local execution and WSGI/Gunicorn deployment.
init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '5000')), debug=False)
