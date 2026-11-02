# PayPal Sandbox verification — 2 November 2026

The existing Default Application was reused. No credentials were regenerated and no scopes were expanded. Client ID and secret were stored privately in backend configuration and Azure application settings, never in source.

Confirmed: actual Sandbox OAuth token retrieval and actual Orders v2 creation for a USD 2 catalogue job. Automated tests cover capture gating, exact amount matching, duplicate requests, interrupted/old operation handling, full/partial policy refunds and reconciliation of pending refunds. 59 local tests pass.

A complete local-backend end-to-end test passed using PayPal's official generated Sandbox card and fictional buyer details: USD 2 captured, one item delivered by real Azure OpenAI, one item undelivered, USD 1 partial refund confirmed COMPLETED. Repeating the refund returned the same refund ID. The identical flow is being verified against the deployed Azure backend; its result will be added after provider confirmation.

No live funds or real customer card data are used. The public default remains Demo; Sandbox job creation and refund execution require the operator token.
