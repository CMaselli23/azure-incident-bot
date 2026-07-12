# Azure Incident Response Bot 🚨

An AI-powered incident response bot that receives Azure Monitor webhook alerts,
generates step-by-step runbooks using Claude AI, posts structured incident cards
to Slack, and enables one-click auto-remediation — all automatically.

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
Azure Function — incident_receiver (HTTP Trigger)
        │  Parses alert payload
        │  Classifies severity (P1/P2/P3)
        ▼
OpenRouter API (Claude AI)
        │  Generates contextual runbook
        ▼
Slack #incidents
        │  Structured incident card + action buttons
        │
        ├── ✅ Acknowledge → threads reply tagging engineer
        ├── 🔄 Restart App → Azure REST API restart call
        └── 📈 Scale Out → Azure REST API scale call
                │
                ▼
        Azure Function — slack_interactions (HTTP Trigger)
                │  Verifies interaction
                │  Executes remediation
                ▼
        Threaded reply in Slack with result
```

---

## What It Does

When an Azure Monitor alert fires, this bot:

1. **Receives** the webhook payload from Azure Monitor via Action Group
2. **Parses** the alert — extracts resource, severity, description, timestamp
3. **Classifies** severity — maps Sev0/Sev1 → P1, Sev2 → P2, Sev3/Sev4 → P3
4. **Generates** a step-by-step AI runbook specific to the alert context
5. **Posts** a structured incident card to Slack with severity banner and runbook
6. **Enables** one-click remediation via interactive buttons:
   - **Acknowledge** — marks incident as owned, tags engineer in thread
   - **Restart App** — calls Azure REST API to restart the affected App Service
   - **Scale Out** — increases instance count by 1 via Azure REST API

---

## SRE Skills Demonstrated

| Skill | Implementation |
|-------|---------------|
| Webhook ingestion | Azure Functions HTTP trigger receives Azure Monitor payloads |
| Alert classification | Severity mapping from Azure schema to P1/P2/P3 |
| Runbook automation | Dynamic AI-generated runbooks via Claude — no static wiki pages |
| Incident notification | Structured Slack cards with Block Kit formatting |
| Auto-remediation | One-click restart and scale out via Azure Management REST API |
| Service principal auth | Azure AD client credentials flow for REST API access |
| Serverless deployment | Azure Functions Consumption plan — scales to zero, costs nothing at rest |
| Infrastructure as Code | All Azure resources provisioned via Azure CLI |
| Observability | Application Insights auto-provisioned with Function App |
| Post-mortem culture | TROUBLESHOOTING.md + POSTMORTEM_TEMPLATE.md included in repo |

---

## Tech Stack

- **Runtime:** Python 3.11, Azure Functions v4 (v2 programming model)
- **AI:** Claude via OpenRouter API
- **Alerting:** Azure Monitor metric alerts + Action Groups
- **Notification:** Slack Block Kit API with interactive buttons
- **Remediation:** Azure Management REST API (restart, scale)
- **Auth:** Azure AD service principal (client credentials flow)
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

[ ✅ Acknowledge ]  [ 🔄 Restart App ]  [ 📈 Scale Out ]
```

When Restart App is clicked:
```
Action taken by @Christian M: Restart App
Result: App Service maselli-app-service restarted successfully.
```

---

## Project Structure

```
azure-incident-bot/
├── function_app.py          # Both functions — incident receiver + Slack interactions
├── host.json                # Azure Functions host configuration
├── local.settings.json      # Local environment settings (not committed)
├── requirements.txt         # Python dependencies
├── .env                     # Secrets (not committed)
├── .gitignore
├── TROUBLESHOOTING.md       # Post-mortem style log of 8 build issues
├── POSTMORTEM_TEMPLATE.md   # Blameless post-mortem template for incidents
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

**Why thread replies instead of updating the original message?**
Threading preserves the full incident timeline in Slack — every action taken
is visible in chronological order under the original alert card, which maps
directly to how SRE teams document incident timelines.

**Known limitation — Slack 3-second timeout on Scale Out:**
The Scale Out action makes two sequential Azure REST API calls which can exceed
Slack's 3-second button response window. The action completes successfully but
Slack shows a timeout warning. Full fix would use response_url for async replies.
See TROUBLESHOOTING.md Issue 8.

---

## Deployment

### Prerequisites
- Azure CLI (`az --version`)
- Azure Functions Core Tools v4 (`func --version`)
- Python 3.11
- OpenRouter API key
- Slack Bot Token with `chat:write` and `chat:write.public` scopes
- Slack Signing Secret
- Azure Service Principal with Contributor role on resource group

### Environment Variables

| Variable | Description |
|----------|-------------|
| `SLACK_BOT_TOKEN` | Slack bot token (xoxb-...) |
| `SLACK_CHANNEL` | Target channel (#incidents) |
| `SLACK_SIGNING_SECRET` | Slack app signing secret |
| `OPENROUTER_API_KEY` | OpenRouter API key |
| `OPENROUTER_MODEL` | Model string (anthropic/claude-3-haiku) |
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_CLIENT_ID` | Service principal app ID |
| `AZURE_CLIENT_SECRET` | Service principal secret |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID |
| `AZURE_RESOURCE_GROUP` | Target resource group |

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
  --settings `
  SLACK_BOT_TOKEN="xoxb-..." `
  "SLACK_CHANNEL=#incidents" `
  SLACK_SIGNING_SECRET="..." `
  OPENROUTER_API_KEY="sk-or-..." `
  OPENROUTER_MODEL="anthropic/claude-3-haiku" `
  AZURE_TENANT_ID="..." `
  AZURE_CLIENT_ID="..." `
  AZURE_CLIENT_SECRET="..." `
  AZURE_SUBSCRIPTION_ID="..." `
  AZURE_RESOURCE_GROUP="rg-incident-bot"

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

### Enable Slack Interactivity

1. Go to api.slack.com/apps → incident-bot
2. Click Interactivity & Shortcuts
3. Toggle Interactivity On
4. Set Request URL: `https://maselli-incident-bot.azurewebsites.net/api/slack_interactions`
5. Save Changes

---

## Live Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/incident_receiver` | Receives Azure Monitor webhook alerts |
| `POST /api/slack_interactions` | Handles Slack button interactions |

---

## Part of the Maselli Technologies SRE Training Curriculum

| Month | Project | Focus | Status |
|-------|---------|-------|--------|
| 1 | Azure SLO Dashboard + AI Explainer | SLIs, SLOs, Error Budgets, AIOps | ✅ Complete |
| 2 | AI-Powered Incident Response Bot | Incident Management, Runbooks, Auto-Remediation | ✅ Complete |
| 3 | AKS Observability Stack | Kubernetes, Prometheus, Grafana | ✅ Complete |
| 4 | GitOps Continuous Delivery with Argo CD | GitOps, Declarative Delivery, AKS | ✅ Complete |
| 5 | Chaos Engineering Suite | Chaos Engineering, Resilience | ⏳ Planned |
| 6 | Full SRE Platform + AI Ops Chatbot | Capstone Integration | ⏳ Planned |
