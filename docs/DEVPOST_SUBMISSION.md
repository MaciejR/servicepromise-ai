# Devpost submission draft

Status: draft updated for v2 source assessment. Public video https://youtu.be/Dm09A60KTe4 records the verified v1 Sandbox refund scenario. Current v2 excludes source deficiencies before quoting.

## Project name

ServicePromise AI

## Tagline

AI catalogue preparation with source evidence and accountable per-item settlement.

## Inspiration

Paying for an AI service creates a practical question: what happens when some of the requested work cannot be delivered? We built a narrow commerce experiment where the acceptance rules are visible before checkout and undelivered items map to a specific refund amount.

Our pilot prepares simple textile catalogue entries from supplier text. It is a testable use case, not a claim that we have validated market demand.

## What it does

Upload a small CSV, inspect the free deterministic source assessment and download its report, review eligible rows and a fixed test quote, then choose a demo or operator-protected PayPal Sandbox checkout. Real Azure OpenAI can extract color and material with literal source evidence. A deterministic validator checks the limited contract and gives an unsuccessful item one repair attempt. Accepted products are exported as drafts; undelivered products are eligible for their entire individual service fee.

The recorded Azure scenario captured USD 3 in PayPal Sandbox. Azure OpenAI processed three products, two were delivered, and one was marked undelivered after two attempts. The operator issued a USD 1 partial refund and PayPal confirmed it. Refreshing restored the results and payment status. The demo uses Sandbox funds.

## How we built it

React, TypeScript and Vite provide import, quote, progress, evidence and download screens. FastAPI hosts the API and compiled UI on Azure App Service. A single-process SQLite worker checkpoints each attempt, preserves the accepted quote and resumes interrupted jobs. Additive migrations create consistent backups of existing data.

PayPal Orders v2 handles checkout and capture; Payments v2 handles policy refunds. Financial intents are persisted before network calls, operation IDs are stable, capture amounts are checked server-side, and pending refunds are distinguished from completed refunds. Provider credentials stay on the backend.

Azure OpenAI supplies an extraction result and source quotations. The model cannot set prices, change the policy or decide a refund amount. Real-model and Sandbox job creation are gated by a private operator token to bound access to paid resources.

## What we learned

In the first feasibility experiment, both the model and a context-aware rules parser matched all 60 provisional synthetic labels. The deterministic parser was substantially faster. This does not prove an AI advantage, and the small, assistant-authored corpus is not independent business validation. We keep the baseline available and disclose the result rather than presenting AI as automatically superior.

On eight fresh synthetic product-versus-packaging descriptions, the revised Azure prompt correctly identified the product color or abstained in 7/8 cases, compared with 3/8 for the rules provider. The shared validator still withheld two correct Azure proposals. The UI labels such proposals as unverified. Export and refund eligibility follow the validated delivery result.

The integration work was also a state-management problem: an API timeout is not evidence that a capture or refund did not happen. Persistence, stable request IDs and reconciliation matter as much as the checkout button.

## Reproduce the Sandbox walkthrough

Follow the repository README to run the frontend and backend locally. In the backend `.env`, set `CATALOG_PAYPAL_SANDBOX_ENABLED=true`, configure the PayPal Sandbox and Azure OpenAI settings listed in `.env.example`, and set a random `OPERATOR_TOKEN` of at least 32 characters. Set `PUBLIC_URL` to the frontend origin used for the walkthrough.

1. Open the app in a fresh browser session. Use the included example, choose Azure OpenAI and PayPal Sandbox, and enter the operator token.
2. Check source suitability. The current example excludes the invalid price and missing material, leaving two eligible rows. Create the USD 2 test quote and Sandbox checkout, approve with a Sandbox buyer, return to the app and capture.
3. Inspect both delivered rows and the source quotations. Download the draft CSV and evidence report. The missing-material row appears in the assessment report before payment.
4. Refresh to verify recovery of the accepted quote and results. The public video and verification record show the earlier v1 USD 3 capture and USD 1 refund; this is a historical integration demonstration. The current example has no refund when both quoted rows are delivered.

The public Azure walkthrough runs in simulation mode without an account. The full flow requires the operator token on Azure or your own Sandbox and Azure OpenAI configuration locally. The deployed flow was verified on 3 November 2026.

The real-data diagnostic used 20 records each from Flipkart, H&M and WDC-PAVE. Rules and Azure each delivered three Flipkart rows and zero rows in the other samples under the limited contract. This does not establish an AI benefit. H&M descriptions omitted color and sampled WDC materials were unsupported. Missing input is now addressed before a new quote.

## What is next

Evaluate original supplier files with a human operator, measure total preparation and review time, and verify import in a test store. Determine which catalogue tasks actually benefit from model reasoning before widening the scope. Production would require accounts, distributed worker leases, stronger abuse controls, webhook reconciliation and further payment hardening.

## Links

- Hosted build: https://api-servicepromise-mr-2026.azurewebsites.net/
- Public source and MIT license: https://github.com/MaciejR/servicepromise-ai
- Sandbox verification: https://github.com/MaciejR/servicepromise-ai/blob/main/docs/SANDBOX_VERIFICATION.md
- Demo video: Final English walkthrough (2:36). https://youtu.be/Dm09A60KTe4

## Tools

Python, FastAPI, SQLAlchemy/SQLite, React, TypeScript, Vite, Azure App Service, Azure OpenAI (GPT-4.1 mini), PayPal Sandbox Orders v2 and Payments v2, GitHub Actions.
