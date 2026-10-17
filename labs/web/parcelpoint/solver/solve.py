"""Evaluator-only HTTP solve for the isolated ParcelPoint lab."""
from __future__ import annotations

import argparse
import json
import re
import secrets
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

FLAG = re.compile(r'^duck\{[a-z0-9_]{16,40}\}$')
MAX_RESPONSE = 64 * 1024


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_base_url(base_url: str) -> str:
    parsed = urlsplit(base_url)
    if (parsed.scheme != 'http' or parsed.hostname not in {'127.0.0.1', 'localhost', '::1'}
            or parsed.username or parsed.password or parsed.path not in {'', '/'}
            or parsed.query or parsed.fragment):
        raise ValueError('The evaluator solver only accepts an HTTP loopback URL.')
    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError('Invalid loopback URL port.') from error
    if port is not None and not 1 <= port <= 65535:
        raise ValueError('Invalid loopback URL port.')
    return f'http://{parsed.netloc}'


class Api:
    def __init__(self, base_url: str, timeout: float = 5):
        self.base_url = validate_base_url(base_url).rstrip('/')
        self.timeout = timeout
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def request(self, method: str, path: str, body: dict | None = None, token: str | None = None) -> dict:
        headers = {'Accept': 'application/json'}
        data = None
        if body is not None:
            data = json.dumps(body).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        if token:
            headers['Authorization'] = 'Bearer ' + token
        request = Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                raw = response.read(MAX_RESPONSE + 1)
                if len(raw) > MAX_RESPONSE:
                    raise RuntimeError('API response exceeded the evaluator size limit.')
                result = json.loads(raw)
        except HTTPError as error:
            raise RuntimeError(f'{method} {path} returned HTTP {error.code}.') from None
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            raise RuntimeError(f'{method} {path} could not complete: {type(error).__name__}.') from None
        if not isinstance(result, dict):
            raise RuntimeError(f'{method} {path} returned an unexpected response.')
        return result

    def service_description_path(self) -> str:
        request = Request(self.base_url + '/', headers={'Accept': 'text/html'}, method='GET')
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                raw = response.read(MAX_RESPONSE + 1)
                link = response.headers.get('Link', '')
        except HTTPError as error:
            raise RuntimeError(f'GET / returned HTTP {error.code}.') from None
        except (URLError, TimeoutError, OSError) as error:
            raise RuntimeError(f'GET / could not complete: {type(error).__name__}.') from None
        if len(raw) > MAX_RESPONSE:
            raise RuntimeError('Homepage response exceeded the evaluator size limit.')
        targets = re.findall(r'<([^<>]+)>\s*;\s*rel\s*=\s*"service-desc"', link, re.IGNORECASE)
        if len(targets) != 1:
            raise RuntimeError('Homepage did not advertise one service description.')
        resolved = urlsplit(urljoin(self.base_url + '/', targets[0]))
        base = urlsplit(self.base_url)
        if ((resolved.scheme, resolved.hostname, resolved.port) != (base.scheme, base.hostname, base.port)
                or resolved.username or resolved.password or resolved.query or resolved.fragment
                or not resolved.path.startswith('/')):
            raise RuntimeError('The service description link was not a same-origin path.')
        return resolved.path


def reset_target_field(api: Api) -> str:
    document = api.request('GET', api.service_description_path())
    operation = document.get('paths', {}).get('/api/auth/reset/confirm', {}).get('post', {})
    body = operation.get('requestBody', {}).get('content', {}).get('application/json', {}).get('schema', {})
    reference = body.get('$ref', '')
    schema_name = reference.rsplit('/', 1)[-1]
    properties = document.get('components', {}).get('schemas', {}).get(schema_name, {}).get('properties', {})
    target = properties.get('email')
    if (not isinstance(target, dict) or 'code' not in properties or 'new_password' not in properties
            or 'account whose password is updated' not in target.get('description', '')):
        raise RuntimeError('The reset confirmation schema does not identify its target field.')
    return 'email'


def contact_email(text: str, name: str) -> str:
    pattern = r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.test"
    addresses = re.findall(pattern, text)
    if name not in text or len(addresses) != 1:
        raise RuntimeError(f'The expected {name} dispatch contact was not identified.')
    return addresses[0].lower()


def solve(base_url: str = 'http://127.0.0.1:8080', timeout: float = 5) -> dict[str, str]:
    """Follow only the supported HTTP workflow and return the two captured flags."""
    api = Api(base_url, timeout)
    target_field = reset_target_field(api)
    lockers = api.request('GET', '/api/lockers').get('lockers')
    if not isinstance(lockers, list):
        raise RuntimeError('The locker list response is invalid.')
    held = next((locker for locker in lockers if isinstance(locker, dict) and locker.get('status') == 'held'), None)
    if held is None or not isinstance(held.get('id'), str):
        raise RuntimeError('No held locker is available for the evaluator path.')
    locker_id = held['id']

    suffix = secrets.token_hex(8)
    email = 'evaluator-' + suffix + '@example.test'
    password = 'Customer-' + secrets.token_urlsafe(18)
    customer = api.request('POST', '/api/auth/register', {
        'name': 'ParcelPoint Evaluator', 'email': email, 'password': password,
    })
    customer_token = customer.get('token')
    if not isinstance(customer_token, str) or customer.get('user', {}).get('role') != 'customer':
        raise RuntimeError('The evaluator account could not be created.')

    api.request('POST', '/api/auth/reset/request', {'email': email}, customer_token)
    messages = api.request('GET', '/api/mailbox', token=customer_token).get('messages')
    if not isinstance(messages, list) or not messages or not isinstance(messages[0].get('code'), str):
        raise RuntimeError('The evaluator mailbox did not return a reset code.')
    first_message = messages[0]
    target = contact_email(first_message.get('body', ''), 'Jules Reed')
    jules_password = 'Courier-' + secrets.token_urlsafe(18)
    api.request('POST', '/api/auth/reset/confirm', {
        target_field: target, 'code': first_message['code'], 'new_password': jules_password,
    }, customer_token)

    jules = api.request('POST', '/api/auth/login', {'email': target, 'password': jules_password})
    jules_token = jules.get('token')
    if not isinstance(jules_token, str) or jules.get('user', {}).get('name') != 'Jules Reed':
        raise RuntimeError('The recovered Jules courier account could not sign in.')
    dashboard = api.request('GET', '/api/courier/dashboard', token=jules_token)
    checkpoint = dashboard.get('checkpoint_flag')
    routes = api.request('GET', '/api/courier/routes', token=jules_token).get('routes')
    if not isinstance(routes, list):
        raise RuntimeError('Jules\'s courier route response is invalid.')
    handoffs = [route.get('dispatch_note', '') for route in routes if isinstance(route, dict)
                and locker_id in route.get('dispatch_note', '') and 'Mira Vale' in route.get('dispatch_note', '')]
    if len(handoffs) != 1:
        raise RuntimeError('Jules\'s courier routes did not identify one handoff for the held locker.')
    target_mira = contact_email(handoffs[0], 'Mira Vale')
    jules_lockers = []
    for route in routes:
        if isinstance(route, dict) and isinstance(route.get('lockers', []), list):
            jules_lockers.extend(locker.get('id') for locker in route.get('lockers', [])
                                 if isinstance(locker, dict))
    if locker_id in jules_lockers:
        raise RuntimeError('The handoff route unexpectedly owns the held locker.')

    api.request('POST', '/api/auth/reset/request', {'email': target}, jules_token)
    jules_messages = api.request('GET', '/api/mailbox', token=jules_token).get('messages')
    if not isinstance(jules_messages, list) or not jules_messages or not isinstance(jules_messages[0].get('code'), str):
        raise RuntimeError('Jules\'s mailbox did not return a reset code.')
    mira_password = 'Courier-' + secrets.token_urlsafe(18)
    api.request('POST', '/api/auth/reset/confirm', {
        target_field: target_mira, 'code': jules_messages[0]['code'], 'new_password': mira_password,
    }, jules_token)

    mira = api.request('POST', '/api/auth/login', {'email': target_mira, 'password': mira_password})
    mira_token = mira.get('token')
    if not isinstance(mira_token, str) or mira.get('user', {}).get('name') != 'Mira Vale':
        raise RuntimeError('The recovered Mira courier account could not sign in.')
    mira_routes = api.request('GET', '/api/courier/routes', token=mira_token).get('routes')
    assigned = isinstance(mira_routes, list) and any(
        isinstance(route, dict) and any(isinstance(item, dict) and item.get('id') == locker_id
                                        for item in route.get('lockers', []))
        for route in mira_routes
    )
    if not assigned:
        raise RuntimeError('Mira is not assigned to the held locker.')
    release = api.request('POST', '/api/courier/lockers/' + locker_id + '/open', {}, mira_token)
    final = release.get('manifest', {}).get('release_flag')
    if not isinstance(checkpoint, str) or not FLAG.fullmatch(checkpoint):
        raise RuntimeError('The checkpoint response did not contain a valid flag.')
    if not isinstance(final, str) or not FLAG.fullmatch(final) or checkpoint == final:
        raise RuntimeError('The release response did not contain a distinct valid final flag.')
    return {'checkpoint': checkpoint, 'final': final}


def verify_with_shared_checker(flags: dict[str, str], lab_dir: Path | None = None) -> None:
    lab_dir = (lab_dir or Path(__file__).resolve().parents[1]).resolve()
    checker = lab_dir.parent.parent.parent / 'scripts' / 'check.py'
    for stage, flag, expected in [('checkpoint', flags['checkpoint'], 'checkpoint solved'),
                                  ('final', flags['final'], 'solved')]:
        result = subprocess.run([sys.executable, str(checker), str(lab_dir)], input=flag + '\n',
                                text=True, capture_output=True, timeout=10, check=False)
        if result.returncode != 0 or result.stdout.strip() != 'flag: ' + expected:
            raise RuntimeError(f'The shared checker did not accept the {stage} flag.')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Run the evaluator-only ParcelPoint solve against a local instance.')
    parser.add_argument('--url', default='http://127.0.0.1:8080', help='HTTP loopback URL for the local lab')
    args = parser.parse_args(argv)
    try:
        flags = solve(args.url)
        verify_with_shared_checker(flags)
    except (RuntimeError, ValueError, OSError, subprocess.SubprocessError) as error:
        print(f'Solve failed: {error}', file=sys.stderr)
        return 1
    print('Solve complete. The local checker accepted both challenge stages.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
