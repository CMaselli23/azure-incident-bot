import azure.functions as func
import logging
import json
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL", "#incidents")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3-haiku")


def parse_alert(payload: dict) -> dict:
    """Extract key fields from an Azure Monitor webhook payload."""
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
    """Call OpenRouter to generate a step-by-step runbook for the incident."""
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


def post_to_slack(incident: dict, runbook: str) -> bool:
    """Post a structured incident card to Slack."""
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
            return False
        return True
    except Exception as e:
        logging.error(f"Slack post error: {e}")
        return False


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

    success = post_to_slack(incident, runbook)

    if success:
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