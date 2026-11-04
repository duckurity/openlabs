"""Exercise the production factory, browser delivery, and dispatch boundaries."""
from contextlib import closing
from pathlib import Path
import hashlib
import json
import os
import secrets
import sqlite3
import tempfile
import unittest
from unittest.mock import patch


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.state = Path(self.directory.name)
        from app.seed import initialize
        self.database = initialize(self.state)

    def test_default_factory_serves_browser_and_reads_seeded_database(self):
        from app import create_app
        with patch.dict(os.environ, {'PARCELPOINT_STATE_DIR': str(self.state)}):
            client = create_app().test_client()
            response = client.get('/')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'id="locker-bank"', response.data)
            self.assertEqual(len(client.get('/api/lockers').json['lockers']), 8)
            for asset in ['/static/style.css', '/static/app.js']:
                with client.get(asset) as response:
                    self.assertEqual(response.status_code, 200)
            self.assertEqual(client.post('/api/auth/login', data='x' * 20000, content_type='application/json').status_code, 413)

    def test_homepage_advertises_the_public_openapi_description(self):
        from app import create_app
        client = create_app(self.database).test_client()
        response = client.get('/')
        link = response.headers.get('Link', '')
        self.assertIn('rel="service-desc"', link)
        description_path = link.split(';', 1)[0].strip('<>')
        self.assertEqual(description_path, '/api/openapi.json')
        description = client.get(description_path)
        self.assertEqual(description.status_code, 200)
        self.assertIn('/api/auth/reset/confirm', description.json['paths'])

    def test_two_courier_escalation_chain_is_deterministic(self):
        from app import create_app
        from app.seed import digest
        client = create_app(self.database).test_client()
        player_password = secrets.token_urlsafe(18)
        player = client.post('/api/auth/register', json={
            'name': 'Player', 'email': 'player@example.test', 'password': player_password,
        }).json
        player_headers = {'Authorization': 'Bearer ' + player['token']}
        self.assertEqual(client.post('/api/auth/reset/request', headers=player_headers,
                                     json={'email': player['user']['email']}).status_code, 200)
        player_message = client.get('/api/mailbox', headers=player_headers).json['messages'][0]
        self.assertIn('Jules Reed', player_message['body'])
        self.assertIn('jules.reed@parcelpoint.test', player_message['body'])
        first_password = secrets.token_urlsafe(18)
        first_reset = client.post('/api/auth/reset/confirm', headers=player_headers, json={
            'email': 'jules.reed@parcelpoint.test', 'code': player_message['code'],
            'new_password': first_password,
        })
        self.assertEqual(first_reset.status_code, 200)
        jules = client.post('/api/auth/login', json={
            'email': 'jules.reed@parcelpoint.test', 'password': first_password,
        }).json
        jules_headers = {'Authorization': 'Bearer ' + jules['token']}
        expected = digest(self.state)
        checkpoint = client.get('/api/courier/dashboard', headers=jules_headers)
        self.assertEqual(checkpoint.status_code, 200)
        self.assertEqual(hashlib.sha256(checkpoint.json['checkpoint_flag'].encode()).hexdigest(),
                         expected['checkpoint_flag_hash'])
        routes = client.get('/api/courier/routes', headers=jules_headers).json['routes']
        jules_route = next(route for route in routes if route['id'] == 'RT-SOUTH')
        self.assertNotIn('PP-407', [locker['id'] for locker in jules_route['lockers']])
        self.assertIn('Mira Vale', jules_route['dispatch_note'])
        self.assertIn('mira.vale@parcelpoint.test', jules_route['dispatch_note'])
        self.assertEqual(client.post('/api/auth/reset/request', headers=jules_headers,
                                     json={'email': jules['user']['email']}).status_code, 200)
        jules_message = client.get('/api/mailbox', headers=jules_headers).json['messages'][0]
        second_password = secrets.token_urlsafe(18)
        second_reset = client.post('/api/auth/reset/confirm', headers=jules_headers, json={
            'email': 'mira.vale@parcelpoint.test', 'code': jules_message['code'],
            'new_password': second_password,
        })
        self.assertEqual(second_reset.status_code, 200)
        mira = client.post('/api/auth/login', json={
            'email': 'mira.vale@parcelpoint.test', 'password': second_password,
        }).json
        mira_headers = {'Authorization': 'Bearer ' + mira['token']}
        mira_routes = client.get('/api/courier/routes', headers=mira_headers).json['routes']
        self.assertIn('PP-407', [locker['id'] for route in mira_routes for locker in route['lockers']])
        release = client.post('/api/courier/lockers/PP-407/open', headers=mira_headers, json={})
        self.assertEqual(release.status_code, 200)
        self.assertEqual(hashlib.sha256(release.json['manifest']['release_flag'].encode()).hexdigest(),
                         expected['flag_hash'])

    def test_courier_dashboard_routes_and_manifest_enforce_assignment(self):
        from app import create_app
        from werkzeug.security import generate_password_hash
        client = create_app(self.database).test_client()
        customer = client.post('/api/auth/register', json={'name': 'Tester', 'email': 'tester@example.test', 'password': 'Customer-pass-123'}).json
        headers = {'Authorization': 'Bearer ' + customer['token']}
        for path in ['/api/courier/dashboard', '/api/courier/routes']:
            self.assertEqual(client.get(path).status_code, 401)
            self.assertEqual(client.get(path, headers=headers).status_code, 403)
        self.assertEqual(client.post('/api/courier/lockers/PP-407/open', headers=headers, json={}).status_code, 403)
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute('UPDATE users SET password_hash=? WHERE role=?',
                               (generate_password_hash('Courier-test-123'), 'courier'))
            expected = dict(connection.execute('SELECT key,value FROM runtime'))
        for email, owns_held in [('jules.reed@parcelpoint.test', False), ('mira.vale@parcelpoint.test', True)]:
            account = client.post('/api/auth/login', json={'email': email, 'password': 'Courier-test-123'}).json
            headers = {'Authorization': 'Bearer ' + account['token']}
            dashboard = client.get('/api/courier/dashboard', headers=headers)
            self.assertEqual(dashboard.status_code, 200)
            self.assertEqual(dashboard.json['checkpoint_flag'], expected['checkpoint_flag'])
            routes = client.get('/api/courier/routes', headers=headers)
            self.assertEqual(routes.status_code, 200)
            assigned = [locker['id'] for route in routes.json['routes'] for locker in route['lockers']]
            self.assertEqual('PP-407' in assigned, owns_held)
            manifest = client.post('/api/courier/lockers/PP-407/open', headers=headers, json={})
            self.assertEqual(manifest.status_code, 200 if owns_held else 404)
            if owns_held:
                self.assertEqual(manifest.json['manifest']['release_flag'], expected['flag'])
                self.assertEqual(manifest.json['manifest']['locker_id'], 'PP-407')
                self.assertEqual(client.post('/api/courier/lockers/PP-104/open', headers=headers, json={}).status_code, 409)
                self.assertEqual(client.post('/api/courier/lockers/PP-407/open', headers=headers, json={'role': 'courier'}).status_code, 400)

    def test_openapi_documents_every_api_operation_without_runtime_secrets(self):
        from app import create_app
        application = create_app(self.database)
        response = application.test_client().get('/api/openapi.json')
        self.assertEqual(response.status_code, 200)
        document = response.json
        self.assertEqual(document['openapi'], '3.0.3')
        actual = {(rule.rule.replace('<locker_id>', '{locker_id}'), method.lower())
                  for rule in application.url_map.iter_rules() if rule.rule.startswith('/api/') and rule.rule != '/api/openapi.json'
                  for method in rule.methods - {'HEAD', 'OPTIONS'}}
        declared = {(path, method) for path, operations in document['paths'].items()
                    for method in operations if method in {'get', 'post'}}
        self.assertEqual(actual, declared)
        self.assertEqual(document['components']['securitySchemes']['bearerAuth']['scheme'], 'bearer')
        reset_code = document['components']['schemas']['ResetConfirm']['properties']['code']
        self.assertEqual((reset_code.get('minLength'), reset_code.get('maxLength')), (1, 128))
        target_email = document['components']['schemas']['ResetConfirm']['properties']['email']
        self.assertIn('account whose password is updated', target_email.get('description', ''))
        self.assertNotIn('courier', document['components']['schemas']['LockerDetail']['properties'])
        locker_detail = document['paths']['/api/lockers/{locker_id}']['get']
        self.assertEqual(locker_detail['summary'], 'Read public locker status and event history')
        self.assertIn('dispatch_note', document['components']['schemas']['Route']['properties'])
        for path, operations in document['paths'].items():
            for method, operation in operations.items():
                self.assertIn('responses', operation)
                if path == '/api/auth/logout':
                    self.assertNotIn('requestBody', operation)
                elif method == 'post':
                    self.assertIn('requestBody', operation)
        self.assertIn('404', document['paths']['/api/auth/reset/confirm']['post']['responses'])
        self.assertNotIn('duck{', json.dumps(document))

    def test_openapi_documents_server_email_length_limit(self):
        from app import create_app
        client = create_app(self.database).test_client()
        document = client.get('/api/openapi.json').json
        for name in ('Register', 'Login', 'ResetRequest', 'ResetConfirm'):
            with self.subTest(schema=name):
                email = document['components']['schemas'][name]['properties']['email']
                self.assertEqual(email.get('maxLength'), 254)

    def test_seed_closes_database_connection(self):
        import gc
        import warnings
        from app.seed import initialize
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter('always', ResourceWarning)
            initialize(self.state)
            gc.collect()
        self.assertFalse([warning for warning in captured if issubclass(warning.category, ResourceWarning)])


if __name__ == '__main__':
    unittest.main()
