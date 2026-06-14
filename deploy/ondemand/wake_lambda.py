"""On-demand "wake" Lambda for the AskUS AI EC2 instance.

Deployed behind a Lambda Function URL (always-on, ~free). When a visitor opens
the URL it:
  1. starts the EC2 instance if it is stopped,
  2. serves a small "warming up" page that polls until the app is healthy,
  3. redirects the visitor to the app.

Environment variables:
  INSTANCE_ID   - the EC2 instance id to manage (required)
  APP_URL       - public app URL to redirect to (default askus-ai.duckdns.org)
  TARGET_REGION - region of the instance (defaults to the Lambda's region)

IAM: the Lambda's execution role needs ec2:DescribeInstances and
ec2:StartInstances (see iam-lambda-start-policy.json).
"""

import json
import os
import urllib.request

import boto3

INSTANCE_ID = os.environ["INSTANCE_ID"]
APP_URL = os.environ.get("APP_URL", "https://askus-ai.duckdns.org").rstrip("/")
HEALTH_URL = APP_URL + "/api/health"
REGION = os.environ.get("TARGET_REGION") or os.environ.get("AWS_REGION", "ap-south-1")

ec2 = boto3.client("ec2", region_name=REGION)


def _state() -> str:
    resp = ec2.describe_instances(InstanceIds=[INSTANCE_ID])
    return resp["Reservations"][0]["Instances"][0]["State"]["Name"]


def _start_if_stopped(state: str) -> bool:
    if state == "stopped":
        ec2.start_instances(InstanceIds=[INSTANCE_ID])
        return True
    return state == "pending"


def _app_ready() -> bool:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=4) as r:
            return r.status == 200
    except Exception:
        return False


def _resp(status: int, body: str, content_type: str):
    return {
        "statusCode": status,
        "headers": {"content-type": content_type, "cache-control": "no-store"},
        "body": body,
    }


def handler(event, _context):
    qs = (event.get("queryStringParameters") or {}) if isinstance(event, dict) else {}
    api = qs.get("api")

    if api == "ready":
        return _resp(200, json.dumps({"ready": _app_ready()}), "application/json")

    if api == "status":
        state = _state()
        starting = _start_if_stopped(state)
        return _resp(
            200,
            json.dumps({"state": state, "starting": starting, "app_url": APP_URL}),
            "application/json",
        )

    # Default: kick off a start and serve the warming-up page.
    try:
        _start_if_stopped(_state())
    except Exception:
        pass
    return _resp(200, PAGE_HTML.replace("__APP_URL__", APP_URL), "text/html; charset=utf-8")


PAGE_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Starting AskUS AI…</title>
<style>
  :root { color-scheme: dark; }
  body { margin:0; min-height:100vh; display:grid; place-items:center;
    font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
    background: radial-gradient(1200px 600px at 50% -10%, #1e2a5a 0%, #0b1020 60%); color:#e8ecff; }
  .card { text-align:center; padding:40px 32px; max-width:420px; }
  h1 { font-size:22px; margin:0 0 8px; }
  p { color:#9fb0d9; margin:6px 0 0; font-size:14px; }
  .spinner { width:54px; height:54px; margin:0 auto 22px; border-radius:50%;
    border:4px solid rgba(255,255,255,.15); border-top-color:#6c8cff; animation:spin 1s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .status { margin-top:18px; font-weight:600; color:#c7d4ff; }
</style>
</head>
<body>
  <div class="card">
    <div class="spinner"></div>
    <h1>Waking up AskUS AI</h1>
    <p>The server was asleep to save resources. This usually takes 60–90 seconds.</p>
    <div class="status" id="status">Starting server…</div>
  </div>
<script>
  const APP_URL = "__APP_URL__";
  const elt = document.getElementById("status");
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  async function getJSON(q) {
    const res = await fetch(q, { cache: "no-store" });
    return res.json();
  }
  (async () => {
    // 1) wait until the instance is running
    while (true) {
      try {
        const s = await getJSON("?api=status");
        if (s.state === "running") break;
        elt.textContent = "Booting instance… (" + s.state + ")";
      } catch (e) { elt.textContent = "Contacting AWS…"; }
      await sleep(5000);
    }
    // 2) wait until the app responds healthy
    elt.textContent = "Loading the app…";
    while (true) {
      try {
        const r = await getJSON("?api=ready");
        if (r.ready) break;
      } catch (e) {}
      await sleep(5000);
    }
    // 3) go
    elt.textContent = "Ready! Redirecting…";
    await sleep(800);
    window.location.href = APP_URL;
  })();
</script>
</body>
</html>"""
