"""Scoped lifecycle and digest-only metadata synchronization for ParcelPoint."""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import urllib.request
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = 'parcelpoint'
SERVICES = {PROJECT, PROJECT + '-ingress'}
HASH_FIELDS = ('flag_hash', 'checkpoint_flag_hash')
HEALTH_URL = 'http://127.0.0.1:8080/health'
READER = 'import json; from app.seed import digest; print(json.dumps(digest(),sort_keys=True))'


def validate_digest(value: object) -> None:
    if not isinstance(value, dict) or set(value) != {'generation_id', *HASH_FIELDS}:
        raise ValueError('Expected a generation identifier and both SHA-256 digests only.')
    for field, length in [('generation_id', 32), *[(key, 64) for key in HASH_FIELDS]]:
        if not isinstance(value[field], str) or not re.fullmatch('[a-f0-9]{' + str(length) + '}', value[field]):
            raise ValueError('Invalid generation identifier or stage digest.')
    if value['flag_hash'] == value['checkpoint_flag_hash']:
        raise ValueError('Stage digests must be distinct.')


def update_metadata(path: Path, value: dict[str, str]) -> bool:
    validate_digest(value)
    original = path.read_bytes()
    text = original.decode('utf-8')
    for field in HASH_FIELDS:
        pattern = re.compile(r'^(' + field + r': )[a-f0-9]{64}(?=\r?$)', re.MULTILINE)
        if len(pattern.findall(text)) != 1 or len(re.findall(r'^' + field + r':', text, re.MULTILINE)) != 1:
            raise ValueError('lab.yml requires one unquoted SHA-256 scalar for each stage.')
        text = pattern.sub(lambda match: match.group(1) + value[field], text)
    updated = text.encode('utf-8')
    if updated == original:
        return False
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.lab-', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(updated)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return True


def run(*arguments: str, timeout: int = 150) -> str:
    environment = os.environ.copy()
    for key in ('COMPOSE_FILE', 'COMPOSE_PROJECT_NAME', 'COMPOSE_PROFILES', 'COMPOSE_ENV_FILES'):
        environment.pop(key, None)
    environment['COMPOSE_DISABLE_ENV_FILE'] = '1'
    result = subprocess.run(list(arguments), cwd=ROOT, env=environment, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f'{arguments[0]} operation failed (exit {result.returncode}).')
    return result.stdout


def compose(*arguments: str) -> str:
    return run('docker', 'compose', '--project-name', PROJECT, '--project-directory', str(ROOT), '--file', str(ROOT / 'docker-compose.yml'), *arguments)


def assert_ownership() -> None:
    containers = run('docker', 'ps', '-aq', '--filter', 'label=com.docker.compose.project=' + PROJECT).split()
    if containers:
        for record in json.loads(run('docker', 'inspect', *containers)):
            labels = record['Config'].get('Labels', {})
            owner = labels.get('com.docker.compose.project.working_dir', '')
            if labels.get('org.openlabs.lab') != PROJECT or labels.get('com.docker.compose.service') not in SERVICES or os.path.normcase(os.path.abspath(owner)) != os.path.normcase(str(ROOT)):
                raise RuntimeError('Compose project collision. Refusing to affect containers outside this workspace.')
    for name in (PROJECT + '_backend', PROJECT + '_frontend'):
        ids = run('docker', 'network', 'ls', '-q', '--filter', 'name=^' + name + '$').split()
        for record in json.loads(run('docker', 'network', 'inspect', *ids)) if ids else []:
            labels = record.get('Labels', {})
            if labels.get('org.openlabs.lab') != PROJECT or labels.get('com.docker.compose.project') != PROJECT:
                raise RuntimeError('Network-name collision. Refusing to adopt unrelated resources.')


@contextmanager
def operator_lock():
    directory = ROOT / '.runtime'
    directory.mkdir(exist_ok=True)
    with (directory / 'operator.lock').open('a+b') as stream:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise RuntimeError('Another ParcelPoint operator action is running.') from None
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def read_digest() -> dict[str, str]:
    value = json.loads(compose('exec', '-T', PROJECT, 'python', '-c', READER))
    validate_digest(value)
    return value


def sync() -> dict[str, str]:
    value = read_digest()
    update_metadata(ROOT / 'lab.yml', value)
    if read_digest() != value:
        raise RuntimeError('Instance changed during hash synchronization. Repeat startup/reset.')
    return value


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def verify_endpoint() -> None:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(HEALTH_URL, timeout=3) as response:
        payload = response.read(4097)
        if response.status != 200 or len(payload) > 4096 or json.loads(payload) != {'service': PROJECT, 'status': 'ok'}:
            raise RuntimeError('Published ParcelPoint health check failed.')


def start_or_reset(*, reset: bool) -> dict[str, str]:
    with operator_lock():
        assert_ownership()
        old = None
        if reset and compose('ps', '--status', 'running', '-q', PROJECT).strip():
            old = read_digest()
        try:
            compose('stop', '--timeout', '5', PROJECT + '-ingress')
            arguments = ['up', '-d', '--no-build', '--pull', 'never', '--no-deps', '--wait', '--wait-timeout', '60']
            if reset:
                arguments.append('--force-recreate')
            compose(*arguments, PROJECT)
            state = sync()
            if old and any(old[field] == state[field] for field in ('generation_id', *HASH_FIELDS)):
                raise RuntimeError('Reset did not rotate both stage flags and the generation.')
            compose('up', '-d', '--no-build', '--pull', 'never', '--no-deps', '--force-recreate', '--wait', '--wait-timeout', '60', PROJECT + '-ingress')
            verify_endpoint()
            return state
        except (Exception, KeyboardInterrupt):
            try:
                compose('stop', '--timeout', '5', PROJECT + '-ingress')
            except Exception:
                pass  # Cleanup cannot replace the original operation failure.
            raise
