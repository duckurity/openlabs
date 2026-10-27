"""Operator controls fail closed and synchronize both stage digests."""
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_control():
    path = ROOT / 'scripts/control.py'
    assert path.is_file(), 'ParcelPoint operator controls are not implemented'
    spec = importlib.util.spec_from_file_location('parcelpoint_control', path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OperatorTests(unittest.TestCase):
    def test_both_hashes_update_atomically_and_preserve_crlf(self):
        control = load_control()
        value = {'generation_id': 'a' * 32, 'flag_hash': 'b' * 64, 'checkpoint_flag_hash': 'c' * 64}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'lab.yml'
            original = ('name: parcelpoint\r\nflag_hash: ' + '0' * 64 + '\r\ncheckpoint_flag_hash: ' + '1' * 64 + '\r\n# retained\r\n').encode()
            path.write_bytes(original)
            self.assertTrue(control.update_metadata(path, value))
            self.assertEqual(path.read_bytes(), original.replace(b'0' * 64, b'b' * 64).replace(b'1' * 64, b'c' * 64))
            self.assertFalse(control.update_metadata(path, value))

    def test_invalid_and_duplicate_digests_never_write(self):
        control = load_control()
        value = {'generation_id': 'a' * 32, 'flag_hash': 'b' * 64, 'checkpoint_flag_hash': 'c' * 64}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'lab.yml'
            original = 'flag_hash: ' + '0' * 64 + '\ncheckpoint_flag_hash: ' + '1' * 64 + '\n'
            for text, state in [
                (original + 'flag_hash: ' + '2' * 64 + '\n', value),
                (original.replace('checkpoint_flag_hash: ', 'checkpoint_flag_hash: "'), value),
                (original, {**value, 'flag': 'not-allowed'}),
                (original, {**value, 'checkpoint_flag_hash': value['flag_hash']}),
                (original, {**value, 'generation_id': 'x'}),
            ]:
                path.write_bytes(text.encode())
                with self.assertRaises(ValueError):
                    control.update_metadata(path, state)
                self.assertEqual(path.read_bytes(), text.encode())

    def test_reset_rotates_both_stages_and_keeps_original_failure(self):
        control = load_control()
        old = {'generation_id': 'a' * 32, 'flag_hash': 'b' * 64, 'checkpoint_flag_hash': 'c' * 64}
        state = {**old, 'generation_id': 'd' * 32, 'flag_hash': 'e' * 64}
        calls = []

        def compose(*arguments):
            calls.append(arguments)
            if arguments[0] == 'ps':
                return 'owned-container\n'
            if arguments[0] == 'stop' and len(calls) > 2:
                raise RuntimeError('cleanup failed')
            return ''

        control.operator_lock = contextlib.nullcontext
        control.assert_ownership = lambda: None
        control.read_digest = lambda: old
        control.sync = lambda: state
        control.compose = compose
        with self.assertRaisesRegex(RuntimeError, 'Reset did not rotate'):
            control.start_or_reset(reset=True)
        self.assertEqual(calls[-1][0], 'stop')

    def test_compose_cannot_use_ambient_project_or_env_file(self):
        control = load_control()
        from unittest.mock import patch
        with patch.dict(os.environ, {'COMPOSE_FILE': 'foreign.yml', 'COMPOSE_PROJECT_NAME': 'other', 'COMPOSE_PROFILES': 'other'}):
            with patch.object(control.subprocess, 'run') as run:
                run.return_value.returncode = 0
                run.return_value.stdout = 'ok'
                self.assertEqual(control.compose('ps'), 'ok')
                argv = run.call_args.args[0]
                environment = run.call_args.kwargs['env']
                self.assertEqual(argv[:4], ['docker', 'compose', '--project-name', 'parcelpoint'])
                self.assertNotIn('COMPOSE_FILE', environment)
                self.assertNotIn('COMPOSE_PROJECT_NAME', environment)
                self.assertEqual(environment['COMPOSE_DISABLE_ENV_FILE'], '1')

    def test_foreign_container_collision_fails_before_mutation(self):
        control = load_control()
        calls = []

        def run(*arguments):
            calls.append(arguments)
            if arguments[1] == 'ps':
                return 'foreign-id'
            return json.dumps([{'Config': {'Labels': {'org.openlabs.lab': 'other'}}}])

        control.run = run
        with self.assertRaisesRegex(RuntimeError, 'collision'):
            control.assert_ownership()
        self.assertTrue(all(call[1] in {'ps', 'inspect'} for call in calls))


if __name__ == '__main__':
    unittest.main()
