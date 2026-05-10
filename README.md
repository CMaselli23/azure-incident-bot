# Azure Incident Response Bot 🚨

An AI-powered incident response bot that receives Azure Monitor webhook alerts,
generates step-by-step runbooks using Claude AI, and posts structured incident
cards to Slack — automatically.

Part of the **Maselli Technologies SRE Training Curriculum** — Month 2 of 6.

---

## Live Architecture

```
Azure Monitor Alert
        │
        ▼
Action Group (Webhook)
        │
        ▼
Azure Function (HTTP Trigger)
        │  Parses alert payload
        │  Classifies severity (P1/P2/P3)
        ▼
OpenRouter API (Claude AI)
        │  Generates contextual runbook
        ▼
Slack #incidents
        │  Structured incident card
        │  Severity emoji + fields + runbook
        ▼
On-Call Engineer
```

---

## What It Does

When an Azure Monitor alert fires, this bot:

1. **Receives** the webhook payload from Azure Monitor
2. **Parses** the alert — extracts resource, severity, description, timestamp
3. **Classifies** severity — maps Sev0/Sev1 → P1, Sev2 → P2, Sev3/Sev4 → P3
4. **Generates** a step-by-step AI runbook specific to the alert context
5. **Posts** a structured incident card to Slack with severity banner and runbook

---

## SRE Skills Demonstrated

| Skill | Implementation |
|-------|---------------|
| Webhook ingestion | Azure Functions HTTP trigger receives Azure Monitor payloads |
| Alert classification | Severity mapping from Azure schema to P1/P2/P3 |
| Runbook automation | Dynamic AI-generated runbooks via Claude instead of static wiki pages |
| Incident notification | Structured Slack cards with Block Kit formatting |
| Serverless deployment | Azure Functions Consumption plan — scales to zero, costs nothing at rest |
| Infrastructure as Code | All Azure resources provisioned via Azure CLI |
| Observability | Application Insights auto-provisioned with Function App |
| Post-mortem culture | See TROUBLESHOOTING.md for blameless issue log |

---

## Tech Stack

- **Runtime:** Python 3.11, Azure Functions v4 (v2 programming model)
- **AI:** Claude via OpenRouter API
- **Alerting:** Azure Monitor metric alerts + Action Groups
- **Notification:** Slack Block Kit API
- **Deployment:** Azure Functions Consumption Plan (Linux, East US)
- **Observability:** Azure Application Insights

---

## Sample Incident Card

When a P1 alert fires, the bot posts this to Slack:

```
🔴 P1 — High CPU on App Service

Affected Resource:    maselli-app-service
Resource Type:        Microsoft.Web/sites
Severity:             Sev1 (P1)
Fired At:             2026-05-10T01:44:00Z

Description:
CPU usage exceeded 90% for 5 minutes

🤖 AI-Generated Runbook:
1. Immediate Triage (first 5 minutes)
   a. Acknowledge alert and take ownership
   b. Check CPU metrics in Azure Portal
   c. Review recent deployments for changes
   ...
```

---

## Project Structure

```
azure-incident-bot/
├── function_app.py          # Main function — webhook receiver, parser, AI caller, Slack poster
├── host.json                # Azure Functions host configuration
├── local.settings.json      # Local environment settings (not committed)
├── requirements.txt         # Python dependencies
├── .env                     # Secrets (not committed)
├── .gitignore
├── TROUBLESHOOTING.md       # Post-mortem style log of build issues
└── README.md
```

---

## Key Design Decisions

**Why OpenRouter instead of direct Anthropic API?**
Centralizes API spend across all projects in the SRE curriculum under one key
and allows model swapping without code changes.

**Why Http5xx for the alert metric?**
Linux Consumption Plan Function Apps do not expose CPU metrics via Azure Monitor.
Http5xx is a more operationally meaningful signal — it directly indicates
user-facing failures rather than infrastructure noise.

**Why bypass local Azure Functions runtime for testing?**
Azure Functions v4.1048 has a known storage health check issue on Windows with
the Python v2 programming model. Core logic was validated via standalone Python
script, then deployed directly to Azure where storage is platform-managed.
See TROUBLESHOOTING.md for full details.

---

## Deployment

### Prerequisites
- Azure CLI (`az --version`)
- Azure Functions Core Tools v4 (`func --version`)
- Python 3.11
- OpenRouter API key
- Slack Bot Token with `chat:write` scope

### Deploy to Azure

```powershell
# Create resource group
az group create --name rg-incident-bot --location eastus

# Create storage account
az storage account create --name maselliincidentbot --location eastus `
  --resource-group rg-incident-bot --sku Standard_LRS

# Create Function App
az functionapp create --resource-group rg-incident-bot `
  --consumption-plan-location eastus --runtime python `
  --runtime-version 3.11 --functions-version 4 `
  --name maselli-incident-bot --storage-account maselliincidentbot `
  --os-type linux

# Set environment variables
az functionapp config appsettings set --name maselli-incident-bot `
  --resource-group rg-incident-bot `
  --settings SLACK_BOT_TOKEN="xoxb-..." "SLACK_CHANNEL=#incidents" `
  OPENROUTER_API_KEY="sk-or-..." OPENROUTER_MODEL="anthropic/claude-3-haiku"

# Deploy code
func azure functionapp publish maselli-incident-bot
```

### Wire Azure Monitor

```powershell
# Create action group pointing to webhook
az monitor action-group create `
  --name "ag-incident-bot" `
  --resource-group rg-incident-bot `
  --short-name "incbot" `
  --action webhook "incident-receiver" `
  "https://maselli-incident-bot.azurewebsites.net/api/incident_receiver"

# Create alert rule
az monitor metrics alert create `
  --name "alert-high-5xx-incident-bot" `
  --resource-group rg-incident-bot `
  --scopes "<your-function-app-resource-id>" `
  --condition "total Http5xx > 0" `
  --window-size 5m `
  --evaluation-frequency 1m `
  --severity 1 `
  --action "ag-incident-bot"
```

---

## Part of the Maselli Technologies SRE Training Curriculum

| Month | Project | Focus | Status |
|-------|---------|-------|--------|
| 1 | Azure SLO Dashboard + AI Explainer | SLIs, SLOs, Error Budgets, AIOps | ✅ Complete |
| 2 | AI-Powered Incident Response Bot | Incident Management, Runbooks | ✅ Complete |
| 3 | AKS Observability Stack | Kubernetes, Prometheus, Grafana | 🔄 Up next |
| 4 | Internal Developer Platform API | Platform Engineering, GitOps | ⏳ Planned |
| 5 | Chaos Engineering Suite | Chaos Engineering, Resilience | ⏳ Planned |
| 6 | Full SRE Platform + AI Ops Chatbot | Capstone Integration | ⏳ Planned |
