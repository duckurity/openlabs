"""Regression tests for scoped SealDesk metadata and operator guards."""

from __future__ import annotations

import copy
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

LAB_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB_ROOT))

from scripts import control


class OperatorControlTests(unittest.TestCase):
    def test_flag_digest_update_is_atomic_idempotent_and_preserves_crlf_comment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            metadata = Path(directory) / "lab.yml"
            original = (
                b"name: sealdesk\r\n"
                b"flag_hash: " + b"0" * 64 + b"  # synchronized value\r\n"
                b"status: experimental\r\n"
            )
            metadata.write_bytes(original)
            if os.name != "nt":
                metadata.chmod(0o640)
            digest = "a" * 64

            changed = control.update_flag_hash(metadata, digest)

            self.assertTrue(changed)
            updated = metadata.read_bytes()
            self.assertEqual(
                updated,
                b"name: sealdesk\r\n"
                + b"flag_hash: " + digest.encode("ascii") + b"  # synchronized value\r\n"
                + b"status: experimental\r\n",
            )
            if os.name != "nt":
                self.assertEqual(stat.S_IMODE(metadata.stat().st_mode), 0o640)
            self.assertFalse(control.update_flag_hash(metadata, digest))
            self.assertEqual(metadata.read_bytes(), updated)

    def test_invalid_digest_and_duplicate_metadata_leave_original_bytes_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            metadata = Path(directory) / "lab.yml"
            original = b"name: sealdesk\nflag_hash: " + b"0" * 64 + b"\n"
            metadata.write_bytes(original)

            with self.assertRaises(ValueError):
                control.update_flag_hash(metadata, "A" * 64)
            self.assertEqual(metadata.read_bytes(), original)

            duplicate = original + b"flag_hash: " + b"1" * 64 + b"\n"
            metadata.write_bytes(duplicate)
            with self.assertRaises(ValueError):
                control.update_flag_hash(metadata, "a" * 64)
            self.assertEqual(metadata.read_bytes(), duplicate)

    def test_digest_reader_rejects_extra_fields_and_non_hex_values(self) -> None:
        self.assertEqual(control.parse_flag_hash_output('{"flag_hash":"' + "b" * 64 + '"}'), "b" * 64)
        for payload in (
            {"flag_hash": "B" * 64},
            {"flag_hash": "c" * 63},
            {"flag_hash": "d" * 64, "access_code": "private"},
            [],
        ):
            with self.subTest(payload=type(payload).__name__):
                with self.assertRaises(ValueError):
                    control.parse_flag_hash_output(json.dumps(payload))

    def test_reset_refuses_to_mutate_when_checker_hash_is_stale(self) -> None:
        control.require_current_flag_hash("a" * 64, "a" * 64)
        with self.assertRaises(control.OperatorError):
            control.require_current_flag_hash("b" * 64, "c" * 64)

    def test_reset_refuses_a_foreign_container_before_any_compose_command(self) -> None:
        with (
            patch.object(control, "_local_context", return_value="desktop-linux"),
            patch.object(control, "_owned_stack", side_effect=control.OperatorError("foreign")),
            patch.object(control, "_run") as run,
        ):
            with self.assertRaises(control.OperatorError):
                control.reset_instance()
            run.assert_not_called()

    def test_reset_refuses_stale_runtime_hash_before_any_compose_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            metadata = Path(directory) / "lab.yml"
            metadata.write_text("name: sealdesk\nflag_hash: " + "b" * 64 + "\n", encoding="utf-8")
            with (
                patch.object(control, "LAB_METADATA", metadata),
                patch.object(control, "_local_context", return_value="desktop-linux"),
                patch.object(control, "_owned_stack", return_value=("a" * 64, "b" * 64, {})),
                patch.object(control, "_read_running_flag_hash", return_value="c" * 64),
                patch.object(control, "_run") as run,
            ):
                with self.assertRaises(control.OperatorError):
                    control.reset_instance()
                run.assert_not_called()

    def test_compose_scope_is_pinned_and_override_variables_are_removed(self) -> None:
        command = control.compose_command("desktop-linux", "ps", "--all", "--quiet", "sealdesk")
        environment = control.compose_environment({
            "PATH": "path-value",
            "COMPOSE_FILE": "untrusted.yml",
            "COMPOSE_PROJECT_NAME": "another-project",
            "COMPOSE_PROFILES": "untrusted",
            "DOCKER_HOST": "tcp://remote.invalid:2375",
            "DOCKER_CONTEXT": "remote",
            "DOCKER_TLS_VERIFY": "1",
            "DOCKER_CERT_PATH": "remote-certs",
            "COMPOSE_DISABLE_ENV_FILE": "0",
            "DOCKER_CONFIG": "docker-config-path",
        })

        self.assertEqual(command[0:3], ["docker", "--context", "desktop-linux"])
        self.assertIn("--project-directory", command)
        self.assertIn("--file", command)
        self.assertEqual(command[-4:], ["ps", "--all", "--quiet", "sealdesk"])
        self.assertEqual(environment, {
            "PATH": "path-value",
            "DOCKER_CONFIG": "docker-config-path",
            "COMPOSE_DISABLE_ENV_FILE": "1",
        })

    def test_inspect_identity_accepts_tmpfs_when_docker_omits_it_from_mounts(self) -> None:
        labels = {
            "org.openlabs.lab": "sealdesk",
            "com.docker.compose.project": "sealdesk",
            "com.docker.compose.service": "sealdesk",
        }
        ports = {"8000/tcp": None}
        tmpfs = {
            "/run/sealdesk": "rw,noexec,nosuid,nodev,size=16m,uid=10001,gid=10001,mode=0700",
            "/tmp": "rw,noexec,nosuid,nodev,size=16m,uid=10001,gid=10001,mode=0700",
        }
        container_output = "|".join((
            json.dumps(labels), json.dumps(ports), "10001:10001", "true",
            json.dumps(["ALL"]), json.dumps([]), json.dumps(["no-new-privileges:true"]),
            "false", "sealdesk_default", "", "private", json.dumps([]),
            "64", "268435456", "268435456", "1000000000", json.dumps(tmpfs),
            json.dumps({"sealdesk_default": {"NetworkID": "d" * 64}}),
            "sealdesk:local", "running", "true", "no",
        ))

        with patch.object(control, "_run", return_value=container_output) as run:
            identity = control._inspect_identity("desktop-linux", "a" * 64)

        run.assert_called_once()
        self.assertEqual(identity["mounts"], [])
        self.assertEqual(identity["tmpfs"], tmpfs)
        self.assertEqual(identity["network_names"], ["sealdesk_default"])
        self.assertTrue(control.is_owned_container(identity, "sealdesk"))

    def test_reset_closes_ingress_until_new_app_ready_and_checker_refreshed(self) -> None:
        events = []
        old_app_id, ingress_id, new_app_id = "a" * 64, "b" * 64, "c" * 64
        old_digest, new_digest = "1" * 64, "2" * 64
        stack_results = iter(((old_app_id, ingress_id, {}), (new_app_id, ingress_id, {})))

        def run(command, **_kwargs):
            if "stop" in command and command[-1] == "ingress":
                events.append("close_ingress")
            elif "up" in command and command[-1] == "sealdesk":
                events.append("recreate_app")
                self.assertIn("--wait", command)
            elif "up" in command and command[-1] == "ingress":
                events.append("open_ingress")
                self.assertIn("--wait", command)
            return ""

        def owned_stack(_context):
            events.append("verify_stack")
            return next(stack_results)

        def owned_app(_context):
            events.append("verify_new_app")
            return new_app_id, {}

        def read_digest(_context, container_id):
            events.append("read_old_digest" if container_id == old_app_id else "read_new_digest")
            return old_digest if container_id == old_app_id else new_digest

        with (
            patch.object(control, "_local_context", return_value="desktop-linux"),
            patch.object(control, "_owned_stack", side_effect=owned_stack),
            patch.object(control, "_owned_app", side_effect=owned_app),
            patch.object(control, "_validated_metadata_hash", return_value=old_digest),
            patch.object(control, "_read_running_flag_hash", side_effect=read_digest),
            patch.object(control, "_run", side_effect=run),
            patch.object(control, "_health_check", side_effect=lambda: events.append("health_check")),
            patch.object(
                control,
                "update_flag_hash",
                side_effect=lambda _path, _digest: events.append("refresh_checker"),
            ),
        ):
            control.reset_instance()

        steps = [event for event in events if event != "verify_stack"]
        self.assertEqual(steps, [
            "read_old_digest", "close_ingress", "recreate_app", "verify_new_app",
            "read_new_digest", "refresh_checker", "open_ingress", "health_check",
        ])
        self.assertEqual(events.count("verify_stack"), 2)

    def test_owned_stack_requires_internal_app_and_loopback_ingress_only(self) -> None:
        tmpfs_options = "rw,noexec,nosuid,nodev,size=16m,uid=10001,gid=10001,mode=0700"

        def container(service, identifier, networks, ports, tmpfs, memory, nano_cpus, network_mode):
            return {
                "labels": {
                    "org.openlabs.lab": "sealdesk",
                    "com.docker.compose.project": "sealdesk",
                    "com.docker.compose.service": service,
                },
                "ports": ports,
                "user": "10001:10001",
                "read_only": True,
                "cap_drop": ["ALL"],
                "cap_add": [],
                "security_options": ["no-new-privileges:true"],
                "privileged": False,
                "network_mode": network_mode,
                "pid_mode": "",
                "ipc_mode": "private",
                "mounts": [],
                "container_id": identifier,
                "image": "sealdesk:local" if service == "sealdesk" else "sealdesk-ingress:local",
                "network_names": networks,
                "state": "running",
                "init": True,
                "restart_policy": "no",
                "pids_limit": 64,
                "memory_limit": memory,
                "memory_swap_limit": memory,
                "nano_cpus": nano_cpus,
                "tmpfs": tmpfs,
            }

        app_id, ingress_id = "a" * 64, "b" * 64
        stack = {
            "services": {
                "sealdesk": container(
                    "sealdesk", app_id, ["sealdesk_default"], {"8000/tcp": None},
                    {"/run/sealdesk": tmpfs_options, "/tmp": tmpfs_options},
                    268435456, 1000000000, "sealdesk_default",
                ),
                "ingress": container(
                    "ingress", ingress_id,
                    ["sealdesk_default", "sealdesk_ingress"],
                    {"8000/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8080"}]},
                    {"/tmp": tmpfs_options}, 67108864, 250000000,
                    "sealdesk_default",
                ),
            },
            "networks": {
                "sealdesk_default": {
                    "name": "sealdesk_default",
                    "internal": True,
                    "driver": "bridge",
                    "enable_ipv6": False,
                    "labels": {
                        "org.openlabs.lab": "sealdesk",
                        "com.docker.compose.project": "sealdesk",
                    },
                    "attached_container_ids": [app_id, ingress_id],
                },
                "sealdesk_ingress": {
                    "name": "sealdesk_ingress",
                    "internal": False,
                    "driver": "bridge",
                    "enable_ipv6": False,
                    "labels": {
                        "org.openlabs.lab": "sealdesk",
                        "com.docker.compose.project": "sealdesk",
                    },
                    "attached_container_ids": [ingress_id],
                },
            },
        }
        self.assertTrue(control.is_owned_container(stack["services"]["sealdesk"], "sealdesk"))
        self.assertTrue(control.is_owned_container(stack["services"]["ingress"], "ingress"))
        self.assertTrue(control.is_owned_instance(stack))

        weakened = []
        exposed_app = copy.deepcopy(stack)
        exposed_app["services"]["sealdesk"]["ports"] = {
            "8000/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8000"}]
        }
        weakened.append(exposed_app)
        public_ingress = copy.deepcopy(stack)
        public_ingress["services"]["ingress"]["ports"]["8000/tcp"][0]["HostIp"] = "0.0.0.0"
        weakened.append(public_ingress)
        app_on_ingress = copy.deepcopy(stack)
        app_on_ingress["services"]["sealdesk"]["network_names"].append("sealdesk_ingress")
        weakened.append(app_on_ingress)
        public_backend = copy.deepcopy(stack)
        public_backend["networks"]["sealdesk_default"]["internal"] = False
        weakened.append(public_backend)
        foreign_ingress_peer = copy.deepcopy(stack)
        foreign_ingress_peer["networks"]["sealdesk_ingress"]["attached_container_ids"].append("c" * 64)
        weakened.append(foreign_ingress_peer)
        for candidate in weakened:
            with self.subTest(candidate=candidate["services"]["sealdesk"]["network_names"]):
                self.assertFalse(control.is_owned_instance(candidate))

    def test_container_identity_requires_sealdesk_label_and_exact_loopback_port(self) -> None:
        tmpfs_options = "rw,noexec,nosuid,nodev,size=16m,uid=10001,gid=10001,mode=0700"
        identity = {
            "labels": {
                "org.openlabs.lab": "sealdesk",
                "com.docker.compose.project": "sealdesk",
                "com.docker.compose.service": "ingress",
            },
            "ports": {"8000/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8080"}]},
            "user": "10001:10001",
            "read_only": True,
            "cap_drop": ["ALL"],
            "cap_add": [],
            "security_options": ["no-new-privileges:true"],
            "privileged": False,
            "network_mode": "sealdesk_default",
            "pid_mode": "private",
            "ipc_mode": "private",
            "mounts": [{"type": "tmpfs", "destination": "/tmp", "rw": True}],
            "tmpfs": {"/tmp": tmpfs_options},
            "network_names": ["sealdesk_default", "sealdesk_ingress"],
            "container_id": "a" * 64,
            "image": "sealdesk-ingress:local",
            "state": "running",
            "init": True,
            "restart_policy": "no",
            "pids_limit": 64,
            "memory_limit": 67108864,
            "memory_swap_limit": 67108864,
            "nano_cpus": 250000000,
        }
        self.assertTrue(control.is_owned_container(identity, "ingress"))
        for changed in (
            {**identity, "labels": {**identity["labels"], "org.openlabs.lab": "other"}},
            {**identity, "labels": {**identity["labels"], "com.docker.compose.project": "other"}},
            {**identity, "labels": {**identity["labels"], "com.docker.compose.service": "sealdesk"}},
            {**identity, "ports": {"8000/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8080"}]}},
            {**identity, "ports": {"8000/tcp": [{"HostIp": "127.0.0.1", "HostPort": "9999"}]}},
            {**identity, "ports": {"8000/tcp": []}},
            {**identity, "tmpfs": {"/tmp": "rw"}},
            {**identity, "privileged": True},
            {**identity, "cap_add": ["NET_ADMIN"]},
            {**identity, "network_mode": "host"},
            {**identity, "pid_mode": "host"},
            {**identity, "ipc_mode": "host"},
            {**identity, "mounts": identity["mounts"] + [{"type": "bind", "destination": "/etc", "rw": True}]},
            {**identity, "network_names": ["sealdesk_default", "sealdesk_ingress", "outside"]},
            {**identity, "read_only": False},
            {**identity, "state": "exited"},
        ):
            with self.subTest(identity=changed):
                self.assertFalse(control.is_owned_container(changed, "ingress"))

    def test_player_readme_helper_commands_name_existing_lab_files(self) -> None:
        readme = (LAB_ROOT / "README.md").read_text(encoding="utf-8")
        helpers = sorted({
            path for path in re.findall(r"\bpython3? ([\w./-]+\.py)\b", readme)
            if not path.startswith("../")
        })

        self.assertIn("scripts/sync_flag_hash.py", helpers)
        self.assertIn("reset.py", helpers)
        for helper in helpers:
            with self.subTest(helper=helper):
                self.assertTrue((LAB_ROOT / helper).is_file())

    def test_sync_helper_imports_its_operator_module_from_any_working_directory(self) -> None:
        helper = LAB_ROOT / "scripts" / "sync_flag_hash.py"
        probe = "import runpy, sys; runpy.run_path(sys.argv[1], run_name='sealdesk_probe')"

        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, "-B", "-c", probe, str(helper)],
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr[-500:])


if __name__ == "__main__":
    unittest.main()
