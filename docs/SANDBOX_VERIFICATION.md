# PayPal Sandbox verification — 2 November 2026

The existing Default Application was reused. No credentials were regenerated and no scopes were expanded. Client ID and secret were stored privately in backend configuration and Azure application settings, never in source.

Confirmed: actual Sandbox OAuth token retrieval and actual Orders v2 creation for a USD 2 catalogue job. Automated tests cover capture gating, exact amount matching, duplicate requests, interrupted/old operation handling, full/partial policy refunds and reconciliation of pending refunds. 59 local tests pass.

A complete local-backend end-to-end test passed using PayPal's official generated Sandbox card and fictional buyer details: USD 2 captured, one item delivered by real Azure OpenAI, one item undelivered, USD 1 partial refund confirmed COMPLETED. Repeating the refund returned the same refund ID. The same complete flow also passed against the deployed Azure App Service backend: USD 2 capture, real Azure extraction, USD 1 partial refund confirmed COMPLETED, and a refund retry returning the original refund ID. The cloud test used actual Sandbox APIs rather than mocked providers.

No live funds or real customer card data are used. The public default remains Demo; Sandbox job creation and refund execution require the operator token.

Deployment: `a17d080f-99fe-4f99-ab13-486078ead8dc` (OneDeploy status 4, successful). GitHub integration commit `c66f898` passed backend and frontend CI. Full refunds were tested with mocked providers; actual provider end-to-end verification covered a partial refund. No claim of live-money readiness is made.

A subsequent Azure App Service restart preserved the completed catalogue results, confirmed capture/refund records and the original refund ID. No additional capture or refund was issued by this persistence check.
