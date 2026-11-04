# PayPal Sandbox verification — 2 November 2026

The existing Default Application was reused. No credentials were regenerated and no scopes were expanded. Client ID and secret were stored privately in backend configuration and Azure application settings, never in source.

Confirmed: actual Sandbox OAuth token retrieval and actual Orders v2 creation for a USD 2 catalogue job. Automated tests cover capture gating, exact amount matching, duplicate requests, interrupted/old operation handling, full/partial policy refunds and reconciliation of pending refunds. 59 local tests pass.

A complete local-backend end-to-end test passed using PayPal's official generated Sandbox card and fictional buyer details: USD 2 captured, one item delivered by real Azure OpenAI, one item undelivered, USD 1 partial refund confirmed COMPLETED. Repeating the refund returned the same refund ID. The same complete flow also passed against the deployed Azure App Service backend: USD 2 capture, real Azure extraction, USD 1 partial refund confirmed COMPLETED, and a refund retry returning the original refund ID. The cloud test used actual Sandbox APIs rather than mocked providers.

No live funds or real customer card data are used. The public default remains Demo; Sandbox job creation and refund execution require the operator token.

Deployment: `a17d080f-99fe-4f99-ab13-486078ead8dc` (OneDeploy status 4, successful). GitHub integration commit `c66f898` passed backend and frontend CI. Full refunds were tested with mocked providers; actual provider end-to-end verification covered a partial refund. No claim of live-money readiness is made.

A subsequent Azure App Service restart preserved the completed catalogue results, confirmed capture/refund records and the original refund ID. No additional capture or refund was issued by this persistence check.

## Release verification — 3 November 2026

Azure deployment `af1b5bd0-0ed7-48a9-94ac-ff3a030a814c` ran a fresh guest checkout against PayPal Sandbox. The app captured USD 3, processed three included rows through Azure OpenAI, delivered two and left one undelivered. The invalid-price row was excluded before checkout. Both protected exports returned successfully with job access, and the job endpoint returned 404 without it. PayPal confirmed a USD 1 partial refund. Retrying returned the original refund ID. The release passed 60 backend tests and the frontend build in GitHub Actions.

## Current v2 verification — 4 November 2026

A fresh PayPal Sandbox guest checkout passed against the deployed source-assessment release. Source checks excluded the missing-material row and invalid-price row before checkout. PayPal captured USD 2. Real Azure OpenAI delivered both included rows. Refund eligibility was zero. Protected CSV and report downloads succeeded, and unauthenticated job access returned 404. This run used test funds and fictional buyer details. The earlier v1 partial-refund verification remains a separate historical run.
