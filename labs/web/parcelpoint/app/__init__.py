"""ParcelPoint's isolated educational dispatch API."""
from pathlib import Path
from datetime import datetime, timezone
import json
import hashlib
import os
import re
import secrets
import sqlite3
import time
from flask import Flask, abort, jsonify, render_template, request
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash
from .db import close_db, get_db


def body_fields(*fields):
    data = request.get_json()
    if not isinstance(data, dict) or set(data) != set(fields):
        abort(400)
    return data


def valid_email(value):
    if not isinstance(value, str) or len(value) > 254 or not re.fullmatch(r'[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.test', value, re.IGNORECASE):
        abort(400)
    return value.lower()


def valid_password(value):
    if not isinstance(value, str) or not 10 <= len(value) <= 128:
        abort(400)
    return value


def public_user(user):
    return {field: user[field] for field in ('id', 'name', 'email', 'role')}


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def issue_session(user):
    token = secrets.token_urlsafe(32)
    get_db().execute('INSERT INTO sessions VALUES (?,?,?)', (token_hash(token), user['id'], time.time() + 28800))
    get_db().commit()
    return {'token': token, 'user': public_user(user)}


def current_user():
    authorization = request.headers.get('Authorization', '')
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer' or len(parts[1]) > 256:
        abort(401)
    user = get_db().execute('SELECT users.* FROM users JOIN sessions ON sessions.user_id=users.id '
                            'WHERE sessions.token_hash=? AND sessions.expires_at>?',
                            (token_hash(parts[1]), time.time())).fetchone()
    if user is None:
        abort(401)
    return user


def create_app(database: Path | None = None) -> Flask:
    app = Flask(__name__)
    state = Path(os.getenv('PARCELPOINT_STATE_DIR', '/run/parcelpoint'))
    app.config.update(DATABASE=database if database is not None else state / 'parcelpoint.sqlite',
                      MAX_CONTENT_LENGTH=8192, DEBUG=False, TESTING=False)
    app.teardown_appcontext(close_db)

    @app.get('/')
    def index():
        return render_template('index.html'), 200, {'Link': '</api/openapi.json>; rel="service-desc"'}

    @app.get('/api/openapi.json')
    def api_description():
        from .openapi import document
        return jsonify(document())

    @app.post('/api/auth/reset/confirm')
    def confirm_reset():
        user = current_user()
        data = body_fields('email', 'code', 'new_password')
        email = valid_email(data['email'])
        password = valid_password(data['new_password'])
        if not isinstance(data['code'], str) or not 1 <= len(data['code']) <= 128:
            abort(400)
        # INTENTIONAL LAB FLAW: the reset owner is authenticated below, but the
        # body-selected target email is not bound to that owner. Fictional data only.
        password_hash = generate_password_hash(password)
        connection = get_db()
        # The code check, target lookup and password change share one SQLite transaction.
        # An unregistered target is rejected before the code is consumed so a typo can be retried.
        with connection:
            owned = connection.execute('SELECT id FROM reset_codes WHERE code_hash=? AND owner_id=? '
                                       'AND used=0 AND expires_at>?',
                                       (token_hash(data['code']), user['id'], time.time())).fetchone()
            if owned is None:
                abort(400)
            target = connection.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone()
            if target is None:
                return jsonify(error='This email is not registered.'), 404
            consumed = connection.execute('UPDATE reset_codes SET used=1 WHERE id=? AND used=0', (owned['id'],))
            if consumed.rowcount != 1:
                abort(400)
            connection.execute('UPDATE users SET password_hash=? WHERE id=?', (password_hash, target['id']))
            connection.execute('DELETE FROM sessions WHERE user_id=?', (target['id'],))
        return jsonify(message='Password updated.')

    @app.post('/api/auth/reset/request')
    def request_reset():
        user = current_user()
        data = body_fields('email')
        if not isinstance(data['email'], str) or data['email'].lower() != user['email']:
            return jsonify(error='Reset requests must use your own email.'), 400
        code = secrets.token_urlsafe(32)
        connection = get_db()
        connection.execute('INSERT INTO reset_codes(owner_id,code_hash,expires_at) VALUES (?,?,?)',
                           (user['id'], token_hash(code), time.time() + 600))
        connection.execute('INSERT INTO mailbox(user_id,subject,body,code,created_at) VALUES (?,?,?,?,?)',
                           (user['id'], 'ParcelPoint password reset',
                            f'Your reset code is {code}. It expires in 10 minutes. '
                            'For the dispatch review on locker PP-407, contact Jules Reed at '
                            'jules.reed@parcelpoint.test.', code,
                            datetime.now(timezone.utc).isoformat()))
        connection.commit()
        return jsonify(message='Reset code delivered to your lab mailbox.')

    @app.get('/api/mailbox')
    def mailbox():
        user = current_user()
        if request.args:
            abort(400)
        messages = get_db().execute('SELECT id,subject,body,code,created_at FROM mailbox WHERE user_id=? ORDER BY id DESC',
                                    (user['id'],))
        return jsonify(messages=[dict(message) for message in messages])

    @app.post('/api/auth/login')
    def login():
        data = body_fields('email', 'password')
        if not isinstance(data['email'], str) or not isinstance(data['password'], str) or len(data['password']) > 128:
            abort(401)
        user = get_db().execute('SELECT * FROM users WHERE email=?', (data['email'].lower(),)).fetchone()
        if user is None or not check_password_hash(user['password_hash'], data['password']):
            abort(401)
        return jsonify(issue_session(user))

    @app.get('/api/me')
    def me():
        return jsonify(user=public_user(current_user()))

    @app.post('/api/auth/logout')
    def logout():
        current_user()
        get_db().execute('DELETE FROM sessions WHERE token_hash=?', (token_hash(request.headers['Authorization'].split()[1]),))
        get_db().commit()
        return jsonify(ok=True)

    @app.post('/api/auth/register')
    def register():
        data = body_fields('name', 'email', 'password')
        email = valid_email(data['email'])
        password = valid_password(data['password'])
        if not isinstance(data['name'], str) or not 1 <= len(data['name'].strip()) <= 80:
            abort(400)
        connection = get_db()
        try:
            cursor = connection.execute('INSERT INTO users(name,email,password_hash,role) VALUES (?,?,?,?)',
                                        (data['name'].strip(), email, generate_password_hash(password), 'customer'))
        except sqlite3.IntegrityError:
            connection.rollback()
            return jsonify(error='Account already exists'), 409
        user = connection.execute('SELECT * FROM users WHERE id=?', (cursor.lastrowid,)).fetchone()
        return jsonify(issue_session(user)), 201

    @app.get('/api/lockers')
    def lockers():
        rows = get_db().execute('SELECT id,name,district,status,parcels,capacity FROM lockers ORDER BY id')
        return jsonify(lockers=[dict(row) for row in rows])

    @app.get('/api/lockers/<locker_id>')
    def locker_detail(locker_id):
        row = get_db().execute('SELECT id,name,district,status,parcels,capacity,address,updated_at,events '
                               'FROM lockers WHERE id=?', (locker_id,)).fetchone()
        if row is None:
            abort(404)
        locker = dict(row)
        locker['events'] = json.loads(locker['events'])
        return jsonify(locker=locker)

    @app.get('/health')
    def health():
        get_db().execute('SELECT 1 FROM lockers LIMIT 1').fetchone()
        return jsonify(service='parcelpoint', status='ok')

    def courier_user():
        user = current_user()
        if user['role'] != 'courier':
            abort(403)
        return user

    @app.get('/api/courier/dashboard')
    def courier_dashboard():
        user = courier_user()
        counts = get_db().execute('SELECT count(*) AS assigned_lockers, '
                                  "sum(CASE WHEN status='held' THEN 1 ELSE 0 END) AS held "
                                  'FROM lockers WHERE courier_id=?', (user['id'],)).fetchone()
        checkpoint = get_db().execute('SELECT value FROM runtime WHERE key=?', ('checkpoint_flag',)).fetchone()[0]
        return jsonify(checkpoint_flag=checkpoint, courier={'name': user['name'], 'email': user['email']},
                       summary=dict(counts))

    @app.get('/api/courier/routes')
    def courier_routes():
        user = courier_user()
        result = []
        for row in get_db().execute('SELECT id,name,dispatch_note FROM routes WHERE courier_id=? ORDER BY id',
                                    (user['id'],)):
            lockers = get_db().execute('SELECT lockers.id,lockers.name,lockers.status FROM lockers '
                                      'JOIN route_lockers ON route_lockers.locker_id=lockers.id '
                                      'WHERE route_lockers.route_id=? AND lockers.courier_id=? ORDER BY lockers.id',
                                      (row['id'], user['id']))
            result.append({**dict(row), 'lockers': [dict(locker) for locker in lockers]})
        return jsonify(routes=result)

    @app.post('/api/courier/lockers/<locker_id>/open')
    def open_locker(locker_id):
        user = courier_user()
        body_fields()
        locker = get_db().execute('SELECT status FROM lockers WHERE id=? AND courier_id=?',
                                  (locker_id, user['id'])).fetchone()
        if locker is None:
            abort(404)
        if locker['status'] != 'held':
            return jsonify(error='This locker has no held release manifest.'), 409
        row = get_db().execute('SELECT * FROM manifests WHERE locker_id=?', (locker_id,)).fetchone()
        if row is None:
            abort(404)
        flag = get_db().execute('SELECT value FROM runtime WHERE key=?', ('flag',)).fetchone()[0]
        return jsonify(manifest={**dict(row), 'release_flag': flag})

    @app.after_request
    def headers(response):
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self'; connect-src 'self'; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        )
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Referrer-Policy'] = 'no-referrer'
        return response

    @app.errorhandler(HTTPException)
    def http_error(error):
        response = error.get_response()
        response.data = app.json.dumps({'error': error.name})
        response.content_type = 'application/json'
        return response

    @app.errorhandler(Exception)
    def internal_error(_error):
        return jsonify(error='Internal server error'), 500

    return app
