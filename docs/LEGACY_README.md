# ServicePromise AI

**A promise you can measure.** A hackathon MVP for accountable AI commerce: agree a quality policy, pay for an AI marketing brief, evaluate the delivery, and settle a partial refund when the policy is breached.

## Catalogue correction pilot — 2 November 2026

Technical continuation: [durable catalogue jobs and demo API (T2)](docs/CATALOG_T2.md) are now implemented locally. The full backend suite has **50 passing tests**. This continuation follows the user's instruction; the pilot's unverified business assumptions remain open.

A separate local feasibility prototype now prepares a small product catalogue with evidence-based color/material extraction, validation, one repair attempt, CSV export and a simulated per-item settlement. It does not alter the currently deployed brief application or call PayPal.

- [Correction plan](docs/CORRECTION_PLAN.md)
- [Prototype contract and commands](docs/CATALOG_CONTRACT.md)
- [Measured pilot results and decision](docs/CATALOG_PILOT_RESULTS.md)
- [Sample data provenance](examples/catalog/PROVENANCE.md)

The context-aware rules baseline and real Azure OpenAI both matched the provisional expected decisions on all 60 synthetic cases. The rules took about 0.013 seconds, Azure about 123.4 seconds across sequential batch requests. This does not establish an AI advantage or customer demand. Further payment/UI investment is gated on real supplier data, human review/time measurement and a store import test. The original marketing-brief flow below remains the deployed demo.

## What works

- Responsive React + TypeScript interface with checkout, delivery, quality evidence, settlement and transaction trail.
- FastAPI API with persistent SQLAlchemy orders: SQLite locally; PostgreSQL through `DATABASE_URL`.
- Fully runnable **demo mode**, including successful delivery, deliberately poor delivery and simulated refunds. Demo content and scores are explicitly labeled fixtures, not actual model output. Demo never calls PayPal or an LLM.
- PayPal **Sandbox** adapter for OAuth, Orders v2 creation, buyer approval, capture and Payments v2 partial refund. Live PayPal is deliberately unsupported.
- Azure OpenAI v1 generation and a separate evaluator call. JSON validation rejects malformed or out-of-range verdicts; provider failures do not trigger refunds.
- Deterministic, versioned settlement rules. The model does not decide refund amounts.
- Bearer capability per order, sandbox operator gate, server-side prices, capture amount checks, row-level transaction locks and stable PayPal request IDs.
- Opt-in automatic settlement via `AUTO_REFUND=true`; manual policy refund is the default.

## Quick start

Requires Python 3.12+ and Node.js 22.12+ (or 24+). Use two terminals.

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Frontend:

```bash
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. API documentation: http://127.0.0.1:8000/docs.

1. Enter a business brief and select **Create my promise**.
2. Select **Simulate payment**.
3. Choose **Promise kept** or **Promise breached**, then **Deliver & evaluate**.
4. For a breach, select **Simulate policy refund**. With `AUTO_REFUND=true`, the backend settles immediately after evaluation.
5. Start a new order to show the other outcome. Refresh preserves the current order within the same browser tab.

The application holds only the latest order capability in session storage. Save order IDs and capabilities privately if long-term access is needed; this MVP has no account recovery.

## Quality promise (v1)

| Condition | Verification | Refund |
| --- | --- | --- |
| 120–220 words, with Audience / Value / Action headings | Deterministic word and heading checks | 25% if either formatting requirement fails |
| Mean relevance, clarity and usefulness score ≥70/100 | Separate Azure OpenAI judge; simulated fixture in demo | 25% if quality fails |
| Total cap | Deterministic server-side policy | Maximum 50% ($6 of the $12 price) |

Only captured orders can be delivered, and only evaluated breaches can be refunded. Repeating delivery returns the stored verdict. Concurrent/repeated refund requests do not create another local settlement; PayPal retries carry the same idempotency key. A PayPal `PENDING` refund remains `refund_pending`, never displayed as completed.

## Connect PayPal Sandbox and Azure OpenAI

Create an app in the [PayPal Developer dashboard](https://developer.paypal.com/dashboard/applications/sandbox). Use sandbox merchant credentials and a separate sandbox buyer. No live credentials are accepted by configuration.

In `backend/.env`:

```dotenv
PAYMENT_MODE=sandbox
PAYPAL_CLIENT_ID=your-sandbox-app-client-id
PAYPAL_CLIENT_SECRET=your-sandbox-app-secret
PUBLIC_URL=http://localhost:5173
CORS_ORIGINS=http://localhost:5173
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your-resource-key
AZURE_OPENAI_DEPLOYMENT=your-chat-deployment-name
OPERATOR_TOKEN=replace-with-a-random-secret-at-least-32-characters
AUTO_REFUND=false
```

Use a chat deployment that supports JSON-object output and `max_completion_tokens`. `AZURE_OPENAI_ENDPOINT` is the resource root, without `/openai/v1`. Secrets stay on the backend; never use a `VITE_` variable for a secret.

Restart the API. Create a new order, go to sandbox checkout and approve with the sandbox buyer. On return, select **I approved — capture payment**. Set the operator token through **Operator settings** to generate/evaluate or issue a refund.

In sandbox mode, deliberate poor-delivery injection is disabled. Refunds require a genuine evaluated policy breach. Live Azure OpenAI generation and evaluation have been tested. The external PayPal Sandbox end-to-end flow still requires your PayPal credentials and has not yet been performed.

## Azure hosting

### Deployed backend — 2 November 2026

- App: `api-servicepromise-mr-2026`, in resource group `rg-servicepromise-ai-hackathon`.
- API health: https://api-servicepromise-mr-2026.azurewebsites.net/api/health
- Interactive API documentation: https://api-servicepromise-mr-2026.azurewebsites.net/docs
- The compiled UI is also served at https://api-servicepromise-mr-2026.azurewebsites.net/.
- Runtime: App Service Linux B1, Python 3.12, one instance and one Uvicorn worker.
- Persistent SQLite path: `/home/servicepromise/servicepromise.db`. Keep one instance; migrate to PostgreSQL before scaling out.
- Payment mode remains `demo`: content, scoring, payments and refunds in the public demo are simulated. Azure OpenAI credentials are configured server-side for the later sandbox integration.
- HTTPS-only, minimum TLS 1.2, FTP disabled, Always On enabled, CORS restricted to the app origin and the existing Static Web App origin.
- No `.env`, database, test order capabilities or credentials are included in the deployment ZIP. Secrets are Azure application settings.

The configured model is `servicepromise-chat` / GPT-4.1 mini, version `2025-04-14`, Global Standard, capacity 10 (10,000 TPM). Real model generation and evaluation were tested separately; PayPal Sandbox is not connected yet.

To deploy a new backend release, ZIP `backend/app/`, `backend/requirements.txt`, and `backend/startup.sh` at the ZIP root. Optionally include the compiled frontend under `static/`. Keep tests, `.env`, runtime databases and dependency caches out. Use `az webapp deploy --type zip`; the configured remote build installs runtime dependencies. `startup.sh` starts one Uvicorn worker and creates the persistent database directory.

Provisioned foundation:

| Item | Value |
| --- | --- |
| Subscription | Visual Studio Enterprise (`44cdb4a7-f92a-4cd5-b07c-ade8c398b3f0`) |
| Resource group | `rg-servicepromise-ai-hackathon` |
| Static Web App | `swa-servicepromise-ai` |
| Region / plan | West Europe / Free |

The separate Static Web App resource exists; this source has **not** been deployed there. The App Service deployment serves a copy of the compiled UI alongside its API. `infra/main.bicep` reproduces only the Static Web App resource, not the deployed App Service, database, model, secrets or budgets.

### Split frontend + API

1. Host `backend/` as an HTTPS API in Azure App Service or Container Apps, using the provided container as an alternative.
2. Configure a persistent PostgreSQL connection, e.g. `postgresql+psycopg://user:password@host:5432/servicepromise?sslmode=require`. Use secret references; do not put database passwords in source.
3. Set backend `PUBLIC_URL` and `CORS_ORIGINS` to the exact Static Web App HTTPS origin. Multiple allowed CORS origins are comma-separated.
4. Set `VITE_API_BASE_URL=https://your-api-host` in the frontend build environment. Run `npm ci && npm run build`.
5. Deploy `frontend/dist` to the existing Static Web App through SWA CLI or GitHub Actions. Keep the deployment token in a secret store.

The SWA Free frontend calls the API on its separate HTTPS origin using CORS. It does not use SWA's paid “bring your own API” linking feature. Do not point `VITE_API_BASE_URL` at the frontend itself without a hosted `/api` backend.

### Single container

```bash
docker build -t servicepromise-ai .
docker run --rm -p 8000:8000 --env-file backend/.env \
  -e DATABASE_URL=sqlite:////data/servicepromise.db \
  -e PUBLIC_URL=http://localhost:8000 \
  -e CORS_ORIGINS=http://localhost:8000 \
  -v servicepromise-data:/data servicepromise-ai
```

The container serves the compiled UI and API together at http://localhost:8000. Container SQLite needs the mounted volume and **one instance**; use PostgreSQL for multiple replicas. The Docker build itself has not been executed in this environment.

## Validation

```bash
cd backend
python -m pytest -q
cd ../frontend
npm run build
```

Tests cover payment gating, order isolation, success, breach, capped refund, concurrent refund retries, automatic settlement, immutable delivery, sandbox capture amount checks, operator authorization, invalid judge output, provider failures and strict separation of simulated payments.

Verified in the development environment: **12 tests passed**, TypeScript checking and Vite production build passed. A complete sandbox flow is covered with mocked payment/model providers; it is not a live integration result. Browser interaction and a container build have not been validated here.

Verified against the deployed HTTPS backend on 2 November 2026: health, UI HTTP response, API docs, CORS preflight, successful demo service, failed demo service with a simulated $6 refund, refund retry idempotency, and refusal to read an order without its bearer capability. Public deployment still uses fixtures for AI and payments; it does not make chargeable model calls or real PayPal transactions.

## Scope before public release

This is a hackathon MVP, not a production payment platform. Before exposing sandbox generation publicly, add edge rate limits and usage quotas, user accounts instead of session capabilities, database migrations, a model evaluation dataset and human-review thresholds. The operator token is a temporary access gate, not full role-based authentication. Add signed PayPal webhook verification and reconciliation for pending captures/refunds; the current flow uses provider API responses and explicit buyer return. A `refund_pending` result is not automatically polled yet. There is no SLA deadline scheduler; v1 guarantees output format and quality only. Do not put customer data or live funds into this build.

External code dependencies require internet access to install. The frontend build and API tests can be checked separately; neither proves a live PayPal transaction or deployed Azure behavior.

## Reference APIs

- [PayPal Orders API](https://developer.paypal.com/api/rest/integration/orders-api)
- [PayPal captured-payment refunds](https://developer.paypal.com/api/payments/v2/captures-refund)
- [Azure OpenAI v1 API](https://learn.microsoft.com/azure/ai-foundry/openai/api-version-lifecycle)
- [Azure Static Web Apps API options](https://learn.microsoft.com/azure/static-web-apps/apis-overview)

## License

MIT. See [LICENSE](LICENSE).
