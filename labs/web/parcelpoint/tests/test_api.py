"""Exercise the real Flask API with disposable fictional accounts."""
from pathlib import Path
from contextlib import closing
import sqlite3
import tempfile
import unittest


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        from app.seed import initialize
        self.database = initialize(Path(self.temporary.name))

    def client(self):
        import app
        self.assertTrue(hasattr(app, 'create_app'), 'app factory is missing')
        self.app = app.create_app(self.database)
        return self.app.test_client()

    def register(self, client, email='player@example.test'):
        response = client.post('/api/auth/register', json={'name': 'Player', 'email': email, 'password': 'Example-pass-123'})
        self.assertEqual(response.status_code, 201)
        return response.json

    @staticmethod
    def bearer(token):
        return {'Authorization': 'Bearer ' + token}

    def reset_code(self, client, account):
        headers = self.bearer(account['token'])
        self.assertEqual(client.post('/api/auth/reset/request', headers=headers, json={'email': account['user']['email']}).status_code, 200)
        return client.get('/api/mailbox', headers=headers).json['messages'][0]['code']

    @staticmethod
    def email_of_length(length, local='a'):
        domain = '@example.test'
        return local * (length - len(domain)) + domain

    def test_server_enforces_documented_email_and_name_limits(self):
        client = self.client()
        password = 'Example-pass-123'
        register = lambda name, email: client.post('/api/auth/register', json={'name': name, 'email': email, 'password': password})
        self.assertEqual(register('Player', self.email_of_length(255)).status_code, 400)
        self.assertEqual(register('Player', self.email_of_length(254)).status_code, 201)
        self.assertEqual(register('n' * 81, 'long-name@example.test').status_code, 400)
        self.assertEqual(register('n' * 80, 'long-name@example.test').status_code, 201)
        account = self.register(client, 'limits@example.test')
        headers = self.bearer(account['token'])
        body = {'code': self.reset_code(client, account), 'new_password': 'Replacement-pass-123'}
        confirm = lambda email: client.post('/api/auth/reset/confirm', headers=headers, json=body | {'email': email})
        self.assertEqual(confirm(self.email_of_length(255, 'b')).status_code, 400)
        self.assertEqual(confirm(self.email_of_length(254, 'b')).status_code, 404)
        self.assertEqual(confirm(account['user']['email']).status_code, 200)

    def test_own_reset_consumes_valid_code_once_and_revokes_sessions(self):
        client = self.client()
        account = self.register(client)
        headers = self.bearer(account['token'])
        code = self.reset_code(client, account)
        body = {'email': account['user']['email'], 'code': code, 'new_password': 'Replacement-pass-123'}
        self.assertEqual(client.post('/api/auth/reset/confirm', json=body).status_code, 401)
        for change in [{'new_password': 'short'}, {'new_password': 'x' * 129}, {'code': 'wrong'}, {'code': None}]:
            response = client.post('/api/auth/reset/confirm', headers=headers, json=body | change)
            self.assertEqual(response.status_code, 400)
        other = self.register(client, 'other@example.test')
        self.assertEqual(client.post('/api/auth/reset/confirm', headers=self.bearer(other['token']), json=body).status_code, 400)
        response = client.post('/api/auth/reset/confirm', headers=headers, json=body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'message': 'Password updated.'})
        self.assertEqual(client.get('/api/me', headers=headers).status_code, 401)
        self.assertEqual(client.post('/api/auth/login', json={'email': body['email'], 'password': 'Example-pass-123'}).status_code, 401)
        logged_in = client.post('/api/auth/login', json={'email': body['email'], 'password': body['new_password']})
        self.assertEqual(logged_in.status_code, 200)
        new_headers = self.bearer(logged_in.json['token'])
        self.assertEqual(client.post('/api/auth/reset/confirm', headers=new_headers, json=body).status_code, 400)
        refreshed = {'user': account['user'], 'token': logged_in.json['token']}
        expired_code = self.reset_code(client, refreshed)
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute('UPDATE reset_codes SET expires_at=0')
        self.assertEqual(client.post('/api/auth/reset/confirm', headers=new_headers, json=body | {'code': expired_code}).status_code, 400)

    def test_lab_reset_identity_binding_flaw_changes_body_selected_account(self):
        client = self.client()
        account = self.register(client)
        other = self.register(client, 'other@example.test')
        headers = self.bearer(account['token'])
        for target, role in [(other['user']['email'], 'customer'),
                             ('jules.reed@parcelpoint.test', 'courier')]:
            code = self.reset_code(client, account)
            response = client.post('/api/auth/reset/confirm', headers=headers,
                                   json={'email': target, 'code': code, 'new_password': 'Lab-only-pass-123'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json, {'message': 'Password updated.'})
            login = client.post('/api/auth/login', json={'email': target, 'password': 'Lab-only-pass-123'})
            self.assertEqual(login.status_code, 200)
            self.assertEqual(login.json['user']['role'], role)
            self.assertEqual(client.post('/api/auth/reset/confirm', headers=headers,
                                        json={'email': target, 'code': code, 'new_password': 'Lab-only-pass-456'}).status_code, 400)
        self.assertEqual(client.get('/api/me', headers=self.bearer(other['token'])).status_code, 401)
        self.assertEqual(client.get('/api/me', headers=headers).status_code, 200)

    def test_reset_to_unregistered_email_is_rejected_without_consuming_code(self):
        client = self.client()
        account = self.register(client)
        headers = self.bearer(account['token'])
        code = self.reset_code(client, account)
        body = {'email': 'absent@example.test', 'code': code, 'new_password': 'Lab-only-pass-123'}
        response = client.post('/api/auth/reset/confirm', headers=headers, json=body)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json, {'error': 'This email is not registered.'})
        wrong_code = client.post('/api/auth/reset/confirm', headers=headers, json=body | {'code': 'wrong'})
        self.assertEqual(wrong_code.status_code, 400)
        retry = client.post('/api/auth/reset/confirm', headers=headers, json=body | {'email': account['user']['email']})
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(retry.json, {'message': 'Password updated.'})

    def test_registration_issues_opaque_customer_session_without_mass_assignment(self):
        client = self.client()
        account = self.register(client)
        self.assertEqual(set(account), {'user', 'token'})
        self.assertEqual(set(account['user']), {'id', 'name', 'email', 'role'})
        self.assertEqual(account['user']['role'], 'customer')
        self.assertGreaterEqual(len(account['token']), 32)
        with closing(sqlite3.connect(self.database)) as connection, connection:
            row = connection.execute('SELECT password_hash FROM users WHERE email=?', ('player@example.test',)).fetchone()
            self.assertNotEqual(row[0], 'Example-pass-123')
            self.assertNotIn(account['token'], str(connection.execute('SELECT * FROM sessions').fetchall()))
        duplicate = client.post('/api/auth/register', json={'name': 'Again', 'email': 'PLAYER@EXAMPLE.TEST', 'password': 'Example-pass-123'})
        self.assertEqual(duplicate.status_code, 409)
        base = {'name': 'Other', 'email': 'other@example.test', 'password': 'Example-pass-123'}
        for change in [{'role': 'courier'}, {'id': 1}, {'password': 'short'}, {'password': 'x' * 129},
                       {'password': 1234567890}, {'name': ''}, {'email': 'not-an-email'}, {'email': 'real@example.com'}]:
            response = client.post('/api/auth/register', json=base | change)
            self.assertEqual(response.status_code, 400, change)
            self.assertEqual(set(response.json), {'error'})
        for body in [[], None, 'text']:
            response = client.post('/api/auth/register', json=body)
            self.assertIn(response.status_code, (400, 415))

    def test_login_me_logout_enforce_server_side_session_lifecycle(self):
        client = self.client()
        account = self.register(client)
        response = client.post('/api/auth/login', json={'email': 'PLAYER@example.test', 'password': 'Example-pass-123'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['user'], account['user'])
        token = response.json['token']
        self.assertNotEqual(token, account['token'])
        for headers in [{}, self.bearer('unknown'), {'Authorization': account['token']}]:
            self.assertEqual(client.get('/api/me', headers=headers).status_code, 401)
        self.assertEqual(client.get('/api/me', headers=self.bearer(token)).json, {'user': account['user']})
        self.assertEqual(client.post('/api/auth/logout', headers=self.bearer(token)).json, {'ok': True})
        self.assertEqual(client.get('/api/me', headers=self.bearer(token)).status_code, 401)
        self.assertEqual(client.post('/api/auth/logout', headers=self.bearer(token)).status_code, 401)
        self.assertEqual(client.get('/api/me', headers=self.bearer(account['token'])).status_code, 200)
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute('UPDATE sessions SET expires_at=0')
        self.assertEqual(client.get('/api/me', headers=self.bearer(account['token'])).status_code, 401)
        for email, password in [('player@example.test', 'wrong-password'), ('absent@example.test', 'Example-pass-123'),
                                ("x' OR 1=1--@example.test", 'Example-pass-123')]:
            self.assertEqual(client.post('/api/auth/login', json={'email': email, 'password': password}).status_code, 401)

    def test_reset_delivery_is_random_private_and_principal_scoped(self):
        import time
        client = self.client()
        account = self.register(client)
        other = self.register(client, 'other@example.test')
        headers = self.bearer(account['token'])
        self.assertEqual(client.get('/api/mailbox', headers=headers).status_code, 200)
        self.assertEqual(client.get('/api/mailbox', headers=headers).json, {'messages': []})
        self.assertEqual(client.post('/api/auth/reset/request', json={'email': account['user']['email']}).status_code, 401)
        for email in ['absent@example.test', other['user']['email']]:
            denied = client.post('/api/auth/reset/request', headers=headers, json={'email': email})
            self.assertEqual(denied.status_code, 400)
            self.assertEqual(denied.json, {'error': 'Reset requests must use your own email.'})
        for _ in range(2):
            response = client.post('/api/auth/reset/request', headers=headers, json={'email': account['user']['email']})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json, {'message': 'Reset code delivered to your lab mailbox.'})
        messages = client.get('/api/mailbox', headers=headers).json['messages']
        self.assertEqual(len(messages), 2)
        self.assertGreater(messages[0]['id'], messages[1]['id'])
        self.assertNotEqual(messages[0]['code'], messages[1]['code'])
        for message in messages:
            self.assertEqual(set(message), {'id', 'subject', 'body', 'code', 'created_at'})
            self.assertRegex(message['code'], r'^[A-Za-z0-9_-]{32,}$')
            self.assertIn(message['code'], message['body'])
        self.assertEqual(client.get('/api/mailbox', headers=self.bearer(other['token'])).json, {'messages': []})
        self.assertEqual(client.get('/api/mailbox?email=' + other['user']['email'], headers=headers).status_code, 400)
        self.assertEqual(client.get('/api/mailbox').status_code, 401)
        with closing(sqlite3.connect(self.database)) as connection, connection:
            rows = connection.execute('SELECT code_hash,expires_at,used FROM reset_codes').fetchall()
            self.assertEqual(len(rows), 2)
            for digest, expiry, used in rows:
                self.assertNotIn(digest, [message['code'] for message in messages])
                self.assertTrue(time.time() + 590 <= expiry <= time.time() + 600)
                self.assertEqual(used, 0)

    def test_health_has_security_headers_and_json_errors(self):
        client = self.client()
        response = client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'service': 'parcelpoint', 'status': 'ok'})
        self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        csp = response.headers['Content-Security-Policy']
        self.assertIn("script-src 'self'", csp)
        self.assertIn("style-src 'self'", csp)
        self.assertNotIn('unsafe-inline', csp)
        for response in (client.get('/missing'), client.post('/health')):
            self.assertIn(response.status_code, (404, 405))
            self.assertEqual(set(response.json), {'error'})
            self.assertIsInstance(response.json['error'], str)

    def test_public_locker_board_exposes_only_dispatch_fields(self):
        client = self.client()
        response = client.get('/api/lockers')
        self.assertEqual(response.status_code, 200)
        lockers = response.json['lockers']
        self.assertEqual(len(lockers), 8)
        fields = {'id', 'name', 'district', 'status', 'parcels', 'capacity'}
        for locker in lockers:
            self.assertEqual(set(locker), fields)
            detail = client.get('/api/lockers/' + locker['id'])
            self.assertEqual(detail.status_code, 200)
            self.assertEqual(set(detail.json['locker']), fields | {'address', 'updated_at', 'events'})
        held = client.get('/api/lockers/PP-407').json['locker']
        self.assertNotIn('courier', held)
        self.assertNotIn('email', held)
        self.assertEqual(held['status'], 'held')
        for path in ['/api/lockers/unknown', '/api/lockers/%27%20OR%201=1--']:
            self.assertEqual(client.get(path).status_code, 404)
        self.assertNotIn('duck{', response.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
