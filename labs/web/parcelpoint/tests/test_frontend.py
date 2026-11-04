"""Dependency-free structural checks for the ParcelPoint browser client.

Integration and visual behavior are exercised separately against the Flask service.
"""
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Document(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.elements = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))

    @property
    def ids(self):
        return {attrs['id']: (tag, attrs) for tag, attrs in self.elements if 'id' in attrs}


class FrontendTests(unittest.TestCase):
    def source(self, path):
        target = ROOT / path
        self.assertTrue(target.is_file(), f'Missing browser artifact: {path}')
        return target.read_text(encoding='utf-8')

    def test_public_depot_has_accessible_real_api_locker_explorer(self):
        html = self.source('app/templates/index.html')
        doc = Document(html)
        for identity in ('main', 'locker-search', 'district-filter', 'status-filter',
                         'locker-bank', 'locker-detail', 'refresh-lockers', 'status-message'):
            self.assertIn(identity, doc.ids)
        self.assertIn(('main', doc.ids['main'][1]), doc.elements)
        self.assertEqual(doc.ids['locker-search'][1].get('type'), 'search')
        self.assertEqual(doc.ids['status-message'][1].get('role'), 'status')
        self.assertIn('Synthetic', html)
        self.assertRegex(html, r'<script[^>]+src="/static/app.js"[^>]+defer')
        js = self.source('app/static/app.js')
        for value in ('/api/lockers', 'encodeURIComponent', 'aria-pressed',
                      'locker-search', 'district-filter', 'status-filter', 'AbortController'):
            self.assertIn(value, js)
        self.assertNotIn('innerHTML', js)
        self.assertNotIn('insertAdjacentHTML', js)
        css = self.source('app/static/style.css')
        self.assertIn('@media', css)
        self.assertIn('prefers-reduced-motion', css)
        self.assertIn(':focus-visible', css)

    def test_account_forms_cover_authenticated_reset_and_mailbox(self):
        html = self.source('app/templates/index.html')
        doc = Document(html)
        self.assertEqual(doc.ids['reset-code'][1].get('maxlength'), '128')
        for identity in ('login-form', 'register-form', 'reset-request-form',
                         'reset-confirm-form', 'mailbox-messages', 'refresh-mailbox',
                         'logout-button', 'auth-tabs', 'profile-panel'):
            self.assertIn(identity, doc.ids)
        labels = {attrs.get('for') for tag, attrs in doc.elements if tag == 'label'}
        for tag, attrs in doc.elements:
            if tag == 'input' and attrs.get('type') != 'hidden':
                self.assertIn(attrs.get('id'), labels, f'Unlabelled input: {attrs}')
            if attrs.get('autocomplete') == 'new-password':
                self.assertEqual(attrs.get('minlength'), '10')
                self.assertEqual(attrs.get('maxlength'), '128')
        js = self.source('app/static/app.js')
        for endpoint in ('/api/auth/register', '/api/auth/login', '/api/auth/logout',
                         '/api/auth/reset/request', '/api/auth/reset/confirm',
                         '/api/mailbox', '/api/me'):
            self.assertIn(endpoint, js)
        self.assertIn('sessionStorage', js)
        self.assertIn('headers.Authorization', js)
        self.assertNotIn('localStorage', js)
        self.assertIn('new_password', js)
        self.assertIn('ArrowRight', js)

    def test_reset_confirmation_sends_session_email_without_a_visible_email_field(self):
        html = self.source('app/templates/index.html')
        doc = Document(html)
        self.assertNotIn('reset-email', doc.ids)
        reset_inputs = [attrs for tag, attrs in doc.elements
                        if tag == 'input' and attrs.get('id') in {'reset-code', 'reset-password'}]
        self.assertEqual({attrs.get('name') for attrs in reset_inputs}, {'code', 'new_password'})
        js = self.source('app/static/app.js')
        self.assertIn('const resetEmail = state.user.email;', js)
        self.assertIn('body: { email: resetEmail, code: body.code, new_password: body.new_password }', js)
        self.assertNotIn('body.email.toLowerCase()', js)

    def test_registration_name_limit_matches_api_contract(self):
        doc = Document(self.source('app/templates/index.html'))
        self.assertEqual(
            doc.ids['register-name'][1].get('maxlength'),
            '80',
            'The browser must enforce the API registration-name limit.',
        )

    def test_email_input_limits_match_api_contract(self):
        doc = Document(self.source('app/templates/index.html'))
        email_inputs = [attrs for tag, attrs in doc.elements if tag == 'input' and attrs.get('type') == 'email']
        self.assertGreater(len(email_inputs), 0, 'The account UI should expose its email fields.')
        for attrs in email_inputs:
            self.assertEqual(
                attrs.get('maxlength'),
                '254',
                f"Email field {attrs.get('id')} must match the API's 254-character limit.",
            )

    def test_courier_dispatch_is_role_gated_and_renders_api_manifest(self):
        doc = Document(self.source('app/templates/index.html'))
        for identity in ('courier-gate', 'courier-workspace', 'route-board',
                         'manifest-content', 'refresh-courier', 'checkpoint-value'):
            self.assertIn(identity, doc.ids)
        self.assertIn('hidden', doc.ids['courier-workspace'][1])
        self.assertIn('hidden', doc.ids['courier-nav'][1])
        js = self.source('app/static/app.js')
        for value in ('/api/courier/dashboard', '/api/courier/routes',
                      '/api/courier/lockers/${encodeURIComponent(id)}/open',
                      "state.user.role !== 'courier'", 'checkpoint_flag',
                      'manifest.reference', 'manifest.recipient', 'manifest.contents',
                      'manifest.release_flag', "body: {}"):
            self.assertIn(value, js)
        self.assertNotIn('PP-407', js)
        self.assertNotRegex(js, r'duck\{[a-z0-9_]+\}')

    def test_openapi_description_is_not_rendered_in_application_ui(self):
        doc = Document(self.source('app/templates/index.html'))
        self.assertNotIn('view-api', doc.ids)
        self.assertFalse(any(attrs.get('data-view') == 'api' for _, attrs in doc.elements))
        self.assertNotIn('API explorer', self.source('app/templates/index.html'))
        js = self.source('app/static/app.js')
        for value in ('/api/openapi.json', 'renderOpenApi', 'loadOpenApi', 'openApiSpec'):
            self.assertNotIn(value, js)

    def test_compact_filters_keep_labels_available_to_assistive_technology(self):
        css = self.source('app/static/style.css')
        self.assertNotRegex(css, r'\.select-field label\s*\{\s*display:\s*none')
        doc = Document(self.source('app/templates/index.html'))
        labels = {attrs.get('for') for tag, attrs in doc.elements if tag == 'label'}
        for tag, attrs in doc.elements:
            if tag == 'select':
                self.assertIn(attrs['id'], labels)

    def test_browser_delivery_keeps_credentials_out_of_urls_and_all_assets_local(self):
        html = self.source('app/templates/index.html')
        doc = Document(html)
        destinations = {
            'login-form': '/api/auth/login', 'register-form': '/api/auth/register',
            'reset-request-form': '/api/auth/reset/request',
            'reset-confirm-form': '/api/auth/reset/confirm',
        }
        for identity, destination in destinations.items():
            attrs = doc.ids[identity][1]
            self.assertEqual(attrs.get('method'), 'post', 'Never send a password in a URL when JavaScript is unavailable')
            self.assertEqual(attrs.get('action'), destination)
        all_ids = [attrs['id'] for _, attrs in doc.elements if 'id' in attrs]
        self.assertEqual(len(all_ids), len(set(all_ids)), 'Duplicate DOM IDs break labels and controls')
        for tag, attrs in doc.elements:
            self.assertNotIn('style', attrs, 'Self-only CSP forbids inline styles')
            self.assertFalse(any(name.startswith('on') for name in attrs), 'Inline handlers violate CSP')
            if tag == 'script':
                self.assertTrue(attrs.get('src', '').startswith('/static/'))
            for name in ('src', 'href'):
                self.assertNotRegex(attrs.get(name, ''), r'^(?:https?:)?//')
            for name in ('aria-controls', 'aria-labelledby', 'aria-describedby'):
                for reference in attrs.get(name, '').split():
                    self.assertIn(reference, doc.ids, f'Broken {name} reference: {reference}')
        css = self.source('app/static/style.css')
        self.assertNotIn('@import', css)
        self.assertNotRegex(css, r'url\([\s\"\']*(?:https?:)?//')
        js = self.source('app/static/app.js')
        self.assertNotRegex(js, r'(?i)solve\s*(?:button|challenge)|exploit|victim')
        # This is a forbidden-source string assertion, not execution of dynamic code.
        self.assertNotIn('eval(', js)


if __name__ == '__main__':
    unittest.main()
