# Devpost submission draft

Status: ready-to-review text; not submitted. The final video link must be added after recording.

## Project name

ServicePromise AI

## Tagline

AI catalogue preparation with source evidence and accountable per-item settlement.

## Inspiration

Paying for an AI service creates a practical question: what happens when some of the requested work cannot be delivered? We built a narrow commerce experiment where the acceptance rules are visible before checkout and undelivered items map to a specific refund amount.

Our pilot prepares simple textile catalogue entries from supplier text. It is a testable use case, not a claim that we have validated market demand.

## What it does

Upload a small CSV, review excluded rows and a fixed service quote, then choose a demo or operator-protected PayPal Sandbox checkout. Real Azure OpenAI can extract color and material with literal source evidence. A deterministic validator checks the limited contract and gives an unsuccessful item one repair attempt. Accepted products are exported as drafts; undelivered products are eligible for their entire individual service fee.

The verified Azure scenario captured USD 2 in PayPal Sandbox, delivered one item using the real model, marked a second item undelivered, and issued a USD 1 partial refund that PayPal confirmed as completed. Retrying the refund returned the same refund ID. No real funds were used.

## How we built it

React, TypeScript and Vite provide import, quote, progress, evidence and download screens. FastAPI hosts the API and compiled UI on Azure App Service. A single-process SQLite worker checkpoints each attempt, preserves the accepted quote and resumes interrupted jobs. Additive migrations create consistent backups of existing data.

PayPal Orders v2 handles checkout and capture; Payments v2 handles policy refunds. Financial intents are persisted before network calls, operation IDs are stable, capture amounts are checked server-side, and pending refunds are distinguished from completed refunds. Provider credentials stay on the backend.

Azure OpenAI supplies an extraction result and source quotations. The model cannot set prices, change the policy or decide a refund amount. Real-model and Sandbox job creation are gated by a private operator token to bound access to paid resources.

## What we learned

In the first feasibility experiment, both the model and a context-aware rules parser matched all 60 provisional synthetic labels. The deterministic parser was substantially faster. This does not prove an AI advantage, and the small, assistant-authored corpus is not independent business validation. We keep the baseline available and disclose the result rather than presenting AI as automatically superior.

The integration work was also a state-management problem: an API timeout is not evidence that a capture or refund did not happen. Persistence, stable request IDs and reconciliation matter as much as the checkout button.

## What is next

Evaluate original supplier files with a human operator, measure total preparation and review time, and verify import in a test store. Determine which catalogue tasks actually benefit from model reasoning before widening the scope. Production would require accounts, distributed worker leases, stronger abuse controls, webhook reconciliation and further payment hardening.

## Links

- Hosted build: https://api-servicepromise-mr-2026.azurewebsites.net/
- Public source and MIT license: https://github.com/MaciejR/servicepromise-ai
- Sandbox verification: https://github.com/MaciejR/servicepromise-ai/blob/main/docs/SANDBOX_VERIFICATION.md
- Demo video: PENDING RECORDING — do not submit this placeholder.

## Tools

Python, FastAPI, SQLAlchemy/SQLite, React, TypeScript, Vite, Azure App Service, Azure OpenAI (GPT-4.1 mini), PayPal Sandbox Orders v2 and Payments v2, GitHub Actions.
