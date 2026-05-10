# Troubleshooting Log — azure-incident-bot

Post-mortem style log of issues encountered during the initial build and deployment.
Each entry follows the SRE format: **symptom → root cause → resolution**.

---

## Issue 1 — Azure Functions Core Tools not found after winget install

**Date:** 2026-05-10  
**Severity:** Low  
**Phase:** Local environment setup

### Symptom
Running `func --version` returned "func is not recognized as a name of a cmdlet."
`winget install Microsoft.AzureFunctionsCoreTools` returned "No package found matching input criteria."

### Root Cause
The Azure Functions Core Tools package ID changed in the winget registry and is no longer available under `Microsoft.AzureFunctionsCoreTools`.

### Resolution
Downloaded `func-cli-4.10.0-x64.msi` directly from the GitHub releases page:
`github.com/Azure/azure-functions-core-tools/releases/latest`

Installed via MSI, reopened VS Code terminal to refresh PATH.

### Prevention
Always verify tool availability via the official GitHub releases page rather than relying on winget package names which can change between versions.

---

## Issue 2 — Azure Functions local runtime blocked by AzureWebJobsStorage

**Date:** 2026-05-10  
**Severity:** Medium  
**Phase:** Local development and testing

### Symptom
`func start` reported the function as registered at `http://localhost:7071/api/incident_receiver` but all HTTP requests returned "No connection could be made because the target machine actively refused it." Health check logs showed `AzureWebJobsStorage: Unhealthy`.

### Root Cause
Azure Functions runtime v4.1048 requires a valid storage account connection for its internal WebJobs infrastructure even for HTTP-only functions running locally. The `UseDevelopmentStorage=false` setting did not fully suppress this requirement in this runtime version.

### Resolution attempts (unsuccessful)
- Set `AzureWebJobsStorage: "UseDevelopmentStorage=false"` in `local.settings.json`
- Installed Azurite local storage emulator via npm
- Set `AzureWebJobsStorage` connection string via environment variable before `func start`
- Runtime continued reporting storage as unhealthy despite Azurite running correctly

### Final Resolution
Bypassed local Azure Functions runtime entirely. Validated core logic (OpenRouter API call + Slack posting) using a standalone Python test script (`test_local.py`). Deployed directly to Azure where storage is handled automatically by the platform.

### Lesson Learned
The Azure Functions local runtime has known storage health check issues in v4.1048 with Python v2 programming model on Windows. For HTTP trigger functions, validating business logic via a standalone Python script is a faster path than fighting local runtime storage configuration.

---

## Issue 3 — azure-functions==2.1.0 not found during remote build

**Date:** 2026-05-10  
**Severity:** Medium  
**Phase:** Azure deployment

### Symptom
`func azure functionapp publish` failed during remote build with:
`ERROR: Could not find a version that satisfies the requirement azure-functions==2.1.0`

### Root Cause
`pip freeze` was run on a Python 3.14 local environment to generate `requirements.txt`. The `azure-functions` package version 2.1.0 is a pre-release build only available for Python 3.14 and not published to PyPI for the Python 3.11 runtime used by the Azure Function App.

### Resolution
Manually replaced `requirements.txt` with pinned stable versions compatible with Python 3.11:
azure-functions==1.21.3
httpx==0.28.1
python-dotenv==1.2.2
requests==2.33.1

### Prevention
Never use `pip freeze` to generate `requirements.txt` for Azure Functions when local Python version differs from the Azure runtime version. Always manually maintain `requirements.txt` with only the packages directly imported by the function code.

---

## Issue 4 — Invalid metric names for Azure Monitor alert rule

**Date:** 2026-05-10  
**Severity:** Low  
**Phase:** Azure Monitor configuration

### Symptom
`az monitor metrics alert create` failed with "Couldn't find a metric named CpuTime" and subsequently "Couldn't find a metric named CpuPercentage."

### Root Cause
Linux Consumption Plan Function Apps do not expose CPU metrics (`CpuTime`, `CpuPercentage`) through the Azure Monitor metrics API. These metrics are only available on dedicated App Service plans.

### Resolution
Queried available metrics using:
```powershell
az monitor metrics list-definitions \
  --resource <resource-id> \
  --query "[].name.value" \
  --output table
```
Selected `Http5xx` as the alert metric — a more operationally meaningful signal anyway, as 5xx errors directly indicate user-facing failures.

### Available metrics on Linux Consumption Plan
Key metrics available: `Requests`, `Http5xx`, `Http4xx`, `MemoryWorkingSet`, `FunctionExecutionCount`, `FunctionExecutionUnits`, `AverageResponseTime`

---

## Issue 5 — --use-common-alert-schema flag not supported in CLI

**Date:** 2026-05-10  
**Severity:** Low  
**Phase:** Azure Monitor configuration

### Symptom
`az monitor action-group create` with `--use-common-alert-schema true` returned "unrecognized arguments."

### Root Cause
The `--use-common-alert-schema` flag is not supported in the current version of the Azure CLI for the `monitor action-group create` command. It is a portal-only option at this CLI version.

### Resolution
Removed the flag. The webhook receiver was updated to handle both common schema and standard schema payloads gracefully via defensive parsing with `.get()` calls and fallback default values.

---

## Issue 6 — az monitor action-group test command not available

**Date:** 2026-05-10  
**Severity:** Low  
**Phase:** End-to-end testing

### Symptom
`az monitor action-group test` returned "'test' is misspelled or not recognized by the system."

### Root Cause
The `test` subcommand for action groups is not available in the current Azure CLI version.

### Resolution
Used the Azure Portal instead:
1. Navigate to **Monitor → Action Groups → ag-incident-bot**
2. Click **Test** at the top of the action group page
3. Select **Metric alert - Static threshold**
4. Click **Test**

End-to-end pipeline confirmed working — Azure Monitor → Action Group → Webhook → AI Runbook → Slack.

---

## Summary

| Issue | Phase | Impact | Resolution |
|-------|-------|--------|------------|
| func CLI not in winget | Setup | Blocked local dev | MSI direct install |
| AzureWebJobsStorage unhealthy | Local testing | Blocked local HTTP | Bypassed via standalone script + cloud deploy |
| azure-functions==2.1.0 not on PyPI | Deployment | Failed remote build | Manual requirements.txt with stable versions |
| Invalid metric names | Alert config | Failed alert creation | Queried available metrics, used Http5xx |
| --use-common-alert-schema unsupported | Alert config | CLI error | Removed flag |
| action-group test unavailable in CLI | Testing | Could not test via CLI | Used Azure Portal test feature |