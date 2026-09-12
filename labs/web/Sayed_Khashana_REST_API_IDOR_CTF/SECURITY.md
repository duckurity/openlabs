# Security Policy

## Educational & Laboratory Environment Notice

This repository contains an **intentionally vulnerable** application created solely for educational, research, and training purposes. The primary goal is to demonstrate **Insecure Direct Object Reference (IDOR)** and **Broken Object Level Authorization (BOLA)** vulnerabilities in a realistic, contained environment.

## Scope & Intentional Vulnerabilities

The business logic and authorization flaws contained within this application (specifically regarding resource ownership checks on document endpoints) are **intentional design components** of the CTF challenge.

- **Do NOT** submit security advisories or vulnerability reports regarding the intended challenge logic or intended IDOR/BOLA behaviors.
- **Do NOT** publicly share full solution walk-throughs or flags without appropriate spoiler warnings to preserve the learning value for others.

## Reporting Genuine Security Issues

If you discover a security issue that falls **outside** the intended educational challenge scope—such as:
- A vulnerability in the deployment automation, container isolation, or underlying tooling
- Accidental exposure of private credentials, personal information, or third-party secrets
- Remote code execution vulnerabilities outside the intended sandbox boundaries

Please report it responsibly to the project maintainer via:
- **Email:** Contact via the maintainer's GitHub profile ([@Khashana22](https://github.com/Khashana22))
- **GitHub Private Vulnerability Reporting:** If enabled on this repository

Please provide:
1. Description of the issue
2. Steps to reproduce
3. Impact assessment outside the intended challenge scope

## Rules of Engagement & Responsible Use

1. **Authorization:** This project must only be deployed and tested on locally hosted environments or infrastructure you own and have explicit written authorization to test.
2. **No Third-Party Targets:** Never use the tools, attack patterns, or techniques demonstrated in this repository against third-party systems, networks, or applications without authorization.
3. **Local Isolation:** When running the container or local server, ensure it binds to loopback interfaces (127.0.0.1 / localhost) and is not exposed to untrusted public networks.
