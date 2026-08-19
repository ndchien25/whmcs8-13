"""
mitmproxy addon script - Log all outbound HTTP/HTTPS traffic to file.
Used with mitmdump to capture WHMCS outgoing API calls.
"""
import datetime
import json
import os
from pathlib import Path
from urllib.parse import parse_qs

from mitmproxy import http

LOG_FILE = "/var/log/mitmproxy/api_traffic.log"
MAX_BODY_LENGTH = 2000
OVERRIDE_CONFIG = Path(
    os.environ.get(
        "ENOM_OVERRIDE_CONFIG",
        "/etc/mitmproxy/enom-overrides/config.json",
    )
)


def _load_override_config() -> dict:
    """Read on every request so bind-mounted changes apply immediately."""
    try:
        with OVERRIDE_CONFIG.open("r", encoding="utf-8-sig") as config_file:
            config = json.load(config_file)
        return config if isinstance(config, dict) else {}
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as error:
        print(f"[enom-override] Cannot read {OVERRIDE_CONFIG}: {error}")
        return {}


def _request_params(flow: http.HTTPFlow) -> dict:
    params = {}
    for key, value in flow.request.query.items(multi=True):
        params[str(key).casefold()] = value

    content_type = flow.request.headers.get("content-type", "").lower()
    if "application/x-www-form-urlencoded" in content_type:
        body = flow.request.get_text(strict=False)
        form_params = parse_qs(body, keep_blank_values=True)
        for key, values in form_params.items():
            if values:
                params[str(key).casefold()] = values[0]
    return params


def _enom_command(flow: http.HTTPFlow) -> str:
    return str(_request_params(flow).get("command", ""))


def _find_api_rule(config: dict, command: str):
    apis = config.get("apis", {})
    if not isinstance(apis, dict):
        return None

    wanted = command.casefold()
    for name, rule in apis.items():
        if str(name).casefold() == wanted and isinstance(rule, dict):
            return rule
    return None


def _select_response_variant(rule: dict, flow: http.HTTPFlow) -> dict:
    """Select a response matching eNom's optional ResponseType parameter."""
    variants = rule.get("response_types", {})
    if not isinstance(variants, dict):
        return rule

    response_type = str(_request_params(flow).get("responsetype", "")).casefold()
    for name, variant in variants.items():
        if str(name).casefold() == response_type and isinstance(variant, dict):
            return {**rule, **variant}
    return rule


def _override_body(rule: dict) -> bytes:
    if "body_file" in rule:
        response_path = (OVERRIDE_CONFIG.parent / str(rule["body_file"])).resolve()
        config_dir = OVERRIDE_CONFIG.parent.resolve()
        if config_dir not in response_path.parents:
            raise ValueError("body_file must stay inside the override directory")
        body = response_path.read_bytes()
        if str(rule.get("line_endings", "")).casefold() == "crlf":
            body = body.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
            body = body.replace(b"\n", b"\r\n")
        return body

    body = rule.get("body", "")
    if isinstance(body, (dict, list)):
        return json.dumps(body, ensure_ascii=False).encode("utf-8")
    return str(body).encode("utf-8")


def request(flow: http.HTTPFlow) -> None:
    """Short-circuit enabled eNom API commands before contacting upstream."""
    config = _load_override_config()
    hosts = config.get("hosts", ["reseller.enom.com", "resellertest.enom.com"])
    if not isinstance(hosts, list):
        return

    request_host = flow.request.pretty_host.casefold()
    if request_host not in {str(host).casefold() for host in hosts}:
        return

    command = _enom_command(flow)
    rule = _find_api_rule(config, command)
    if not rule or rule.get("enabled") is not True:
        return
    rule = _select_response_variant(rule, flow)

    try:
        body = _override_body(rule)
        status_code = int(rule.get("status_code", 200))
        headers = rule.get("headers", {})
        if not isinstance(headers, dict):
            headers = {}
        headers = {str(key): str(value) for key, value in headers.items()}
        headers.setdefault("content-type", "text/xml; charset=utf-8")
        headers["x-enom-response-override"] = command
        flow.response = http.Response.make(status_code, body, headers)
        print(f"[enom-override] {command}: returned configured response")
    except (OSError, TypeError, ValueError) as error:
        # A bad override must not take eNom offline: fall through to upstream.
        print(f"[enom-override] {command}: invalid rule, using upstream: {error}")


def _truncate(text: str, max_len: int = MAX_BODY_LENGTH) -> str:
    if text and len(text) > max_len:
        return text[:max_len] + f"\n... [TRUNCATED - {len(text)} total chars]"
    return text or ""


def _safe_decode(content: bytes) -> str:
    if not content:
        return ""
    try:
        return content.decode("utf-8", errors="replace")
    except Exception:
        return f"<binary data, {len(content)} bytes>"


def _format_headers(headers) -> dict:
    return dict(headers)


def response(flow):
    """Called when a full request/response cycle is complete."""
    req = flow.request
    res = flow.response

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    entry = {
        "timestamp": timestamp,
        "method": req.method,
        "url": req.pretty_url,
        "request": {
            "headers": _format_headers(req.headers),
            "body": _truncate(_safe_decode(req.content)),
        },
        "response": {
            "status_code": res.status_code,
            "reason": res.reason,
            "headers": _format_headers(res.headers),
            "body": _truncate(_safe_decode(res.content)),
        },
    }

    log_line = (
        f"\n{'='*100}\n"
        f"[{timestamp}] {req.method} {req.pretty_url}\n"
        f"{'─'*100}\n"
        f"► REQUEST HEADERS:\n"
    )

    for k, v in req.headers.items():
        log_line += f"  {k}: {v}\n"

    req_body = _truncate(_safe_decode(req.content))
    if req_body:
        log_line += f"► REQUEST BODY:\n{req_body}\n"

    log_line += (
        f"{'─'*100}\n"
        f"◄ RESPONSE: {res.status_code} {res.reason}\n"
        f"◄ RESPONSE HEADERS:\n"
    )

    for k, v in res.headers.items():
        log_line += f"  {k}: {v}\n"

    res_body = _truncate(_safe_decode(res.content))
    if res_body:
        log_line += f"◄ RESPONSE BODY:\n{res_body}\n"

    log_line += f"{'='*100}\n"

    # Also write JSON format for programmatic parsing
    json_file = LOG_FILE.replace(".log", ".jsonl")

    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line)

    with open(json_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
