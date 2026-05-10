import azure.functions as func
import logging
import json
import os
import hmac
import hashlib
import time
import httpx
from dotenv import load_dotenv

load_dotenv()

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL", "#incidents")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3-haiku")


# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_alert(payload: dict) -> dict:
    data = payload.get("data", {})
    essentials = data.get("essentials", {})
    severity_map = {
        "Sev0": "P1", "Sev1": "P1",
        "Sev2": "P2", "Sev3": "P3", "Sev4": "P3"
    }
    raw_severity = essentials.get("severity", "Sev2")
    return {
        "alert_name": essentials.get("alertRule", "Unknown Alert"),
        "severity": severity_map.get(raw_severity, "P2"),
        "raw_severity": raw_severity,
        "description": essentials.get("description", "No description provided."),
        "affected_resource": essentials.get("targetResourceName", "Unknown Resource"),
        "resource_type": essentials.get("targetResourceType", "Unknown Type"),
        "fired_at": essentials.get("firedDateTime", "Unknown Time"),
        "monitor_condition": essentials.get("monitorCondition", "Fired"),
        "alert_id": essentials.get("alertId", "unknown-id"),
    }


def generate_runbook(incident: dict) -> str:
    prompt = f"""You are an expert SRE. An Azure Monitor alert has fired. Generate a concise,
step-by-step incident response runbook for the on-call engineer.

Incident Details:
- Alert Name: {incident['alert_name']}
- Severity: {incident['severity']}
- Affected Resource: {incident['affected_resource']}
- Resource Type: {incident['resource_type']}
- Description: {incident['description']}
- Fired At: {incident['fired_at']}

Provide:
1. Immediate triage steps (first 5 minutes)
2. Likely root causes to investigate
3. Mitigation steps
4. Escalation criteria

Be specific to the resource type. Keep it under 300 words."""

    try:
        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logging.error(f"OpenRouter error: {e}")
        return "Runbook generation failed. Follow standard incident response procedures."


def post_to_slack(incident: dict, runbook: str) -> dict:
    severity_emoji = {"P1": "🔴", "P2": "🟡", "P3": "🔵"}.get(incident["severity"], "⚪")

    message = {
        "channel": SLACK_CHANNEL,
        "text": f"{severity_emoji} *{incident['severity']} Incident: {incident['alert_name']}*",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{severity_emoji} {incident['severity']} — {incident['alert_name']}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Affected Resource:*\n{incident['affected_resource']}"},
                    {"type": "mrkdwn", "text": f"*Resource Type:*\n{incident['resource_type']}"},
                    {"type": "mrkdwn", "text": f"*Severity:*\n{incident['raw_severity']} ({incident['severity']})"},
                    {"type": "mrkdwn", "text": f"*Fired At:*\n{incident['fired_at']}"},
                ]
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Description:*\n{incident['description']}"}
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*🤖 AI-Generated Runbook:*\n{runbook}"}
            },
            {"type": "divider"},
            {
                "type": "actions",
                "block_id": "incident_actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "✅ Acknowledge"},
                        "style": "primary",
                        "action_id": "acknowledge",
                        "value": json.dumps({
                            "alert_name": incident["alert_name"],
                            "affected_resource": incident["affected_resource"],
                            "resource_type": incident["resource_type"],
                        })
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🔄 Restart App"},
                        "style": "danger",
                        "action_id": "restart_app",
                        "value": json.dumps({
                            "alert_name": incident["alert_name"],
                            "affected_resource": incident["affected_resource"],
                            "resource_type": incident["resource_type"],
                        })
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📈 Scale Out"},
                        "action_id": "scale_out",
                        "value": json.dumps({
                            "alert_name": incident["alert_name"],
                            "affected_resource": incident["affected_resource"],
                            "resource_type": incident["resource_type"],
                        })
                    },
                ]
            }
        ]
    }

    try:
        response = httpx.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                "Content-Type": "application/json",
            },
            json=message,
            timeout=10,
        )
        result = response.json()
        if not result.get("ok"):
            logging.error(f"Slack error: {result.get('error')}")
            return {}
        return {"ts": result.get("ts"), "channel": result.get("channel")}
    except Exception as e:
        logging.error(f"Slack post error: {e}")
        return {}


def update_slack_message(channel: str, ts: str, action: str, user: str, result_text: str):
    text = f"*Action taken by <@{user}>:* {action}\n*Result:* {result_text}"
    try:
        httpx.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "channel": channel,
                "thread_ts": ts,
                "text": text,
            },
            timeout=10,
        )
    except Exception as e:
        logging.error(f"Slack update error: {e}")


# ── Remediation actions ───────────────────────────────────────────────────────

def get_azure_token() -> str:
    try:
        response = httpx.post(
            f"https://login.microsoftonline.com/{os.getenv('AZURE_TENANT_ID')}/oauth2/v2.0/token",
            data={
                "grant_type": "client_credentials",
                "client_id": os.getenv("AZURE_CLIENT_ID"),
                "client_secret": os.getenv("AZURE_CLIENT_SECRET"),
                "scope": "https://management.azure.com/.default",
            },
            timeout=15,
        )
        return response.json().get("access_token", "")
    except Exception as e:
        logging.error(f"Azure auth error: {e}")
        return ""


def restart_app_service(resource_name: str) -> str:
    subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
    resource_group = os.getenv("AZURE_RESOURCE_GROUP", "rg-incident-bot")
    token = get_azure_token()

    if not token:
        return "Restart failed — could not authenticate with Azure."

    try:
        response = httpx.post(
            f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Web/sites/{resource_name}/restart?api-version=2022-03-01",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        if response.status_code in [200, 204]:
            return f"App Service *{resource_name}* restarted successfully."
        else:
            return f"Restart returned status {response.status_code}. Verify manually in Azure Portal."
    except Exception as e:
        logging.error(f"Restart error: {e}")
        return f"Restart failed: {str(e)}"


def scale_out_app_service(resource_name: str) -> str:
    subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
    resource_group = os.getenv("AZURE_RESOURCE_GROUP", "rg-incident-bot")
    token = get_azure_token()

    if not token:
        return "Scale out failed — could not authenticate with Azure."

    try:
        get_response = httpx.get(
            f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Web/sites/{resource_name}?api-version=2022-03-01",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        current = get_response.json().get("properties", {}).get("siteConfig", {}).get("numberOfWorkers", 1)
        new_count = min(current + 1, 10)

        patch_response = httpx.patch(
            f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Web/sites/{resource_name}?api-version=2022-03-01",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"properties": {"siteConfig": {"numberOfWorkers": new_count}}},
            timeout=30,
        )
        if patch_response.status_code in [200, 202]:
            return f"App Service *{resource_name}* scaled from {current} to {new_count} instance(s)."
        else:
            return f"Scale out returned status {patch_response.status_code}. Verify manually."
    except Exception as e:
        logging.error(f"Scale out error: {e}")
        return f"Scale out failed: {str(e)}"


# ── Route 1: Azure Monitor webhook ───────────────────────────────────────────

@app.route(route="incident_receiver", methods=["POST"])
def incident_receiver(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Incident receiver triggered.")

    try:
        payload = req.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON payload.", status_code=400)

    incident = parse_alert(payload)
    logging.info(f"Parsed incident: {incident['alert_name']} | {incident['severity']}")

    runbook = generate_runbook(incident)
    logging.info("Runbook generated.")

    result = post_to_slack(incident, runbook)

    if result:
        return func.HttpResponse(
            json.dumps({"status": "ok", "incident": incident["alert_name"]}),
            status_code=200,
            mimetype="application/json"
        )
    else:
        return func.HttpResponse(
            json.dumps({"status": "partial", "message": "Runbook generated but Slack post failed."}),
            status_code=500,
            mimetype="application/json"
        )


# ── Route 2: Slack interactions ───────────────────────────────────────────────

@app.route(route="slack_interactions", methods=["POST"])
def slack_interactions(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Slack interaction received.")
    try:
        body = req.get_body().decode("utf-8")
        logging.info(f"Body length: {len(body)}")
        logging.info(f"Body preview: {body[:200]}")

        if not body.startswith("payload="):
            logging.error("Unexpected body format")
            return func.HttpResponse("", status_code=200)

        import urllib.parse
        payload = json.loads(urllib.parse.unquote(body[8:]))
        logging.info(f"Payload type: {payload.get('type')}")
        logging.info(f"Actions: {payload.get('actions')}")

        actions = payload.get("actions", [])
        if not actions:
            logging.info("No actions found — returning 200")
            return func.HttpResponse("", status_code=200)

        action = actions[0]
        action_id = action.get("action_id", "unknown")
        user = payload.get("user", {}).get("id", "unknown")
        channel = payload.get("channel", {}).get("id", "")
        message_ts = payload.get("message", {}).get("ts", "")

        logging.info(f"Action ID: {action_id} | User: {user} | Channel: {channel}")

        try:
            action_value = json.loads(action.get("value", "{}"))
        except Exception:
            action_value = {}

        affected_resource = action_value.get("affected_resource", "Unknown Resource")
        alert_name = action_value.get("alert_name", "Unknown Alert")

        if action_id == "acknowledge":
            result_text = f"Incident *{alert_name}* acknowledged. Investigating now."
        elif action_id == "restart_app":
            result_text = restart_app_service(affected_resource)
        elif action_id == "scale_out":
            result_text = scale_out_app_service(affected_resource)
        else:
            result_text = f"Unknown action: {action_id}"

        logging.info(f"Result: {result_text}")

        if channel and message_ts:
            update_slack_message(channel, message_ts, action_id.replace("_", " ").title(), user, result_text)
            logging.info("Slack thread update sent.")

        return func.HttpResponse("", status_code=200)

    except Exception as e:
        logging.error(f"slack_interactions fatal error: {str(e)}", exc_info=True)
        return func.HttpResponse("", status_code=200)