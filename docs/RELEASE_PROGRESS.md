# Release progress — 2 November 2026

User instruction: continue through stages without stopping after each T. Technical implementation continues while previously identified business assumptions remain open.

| Stage | Status |
| --- | --- |
| T0–T1 | Contract, local prototype, synthetic corpus and real Azure comparison completed. Original customer files, human review and business validation pending. |
| T2 | Durable single-process SQLite jobs, immutable quote, bounded repair attempts, recovery, additive migration and consistent backup implemented. |
| T3 | Import, quote, exclusions, policy, item evidence, live status polling, same-tab recovery and protected downloads implemented. Rules and operator-gated real Azure extraction selectable. |
| T4 | Automated suite and build pass; desktop Chrome example flow verified. Store import and human time-saving benchmark pending external inputs. |
| T5 | Existing Sandbox app credentials are configured privately; catalogue checkout, capture and partial/full refund endpoints are implemented. Sandbox OAuth and actual order creation are verified. Real capture, Azure delivery and confirmed partial refund passed both locally and on Azure; refund retries preserved the original ID. See SANDBOX_VERIFICATION.md. |
| T6 | Azure deployment successful (OneDeploy 55e7f259-14e3-4004-b7d7-59459d83c0f4). Remote flows passed for rules and real Azure, including protected CSV/JSON downloads and operator gating. Public source publication was explicitly approved by the user and completed at https://github.com/MaciejR/servicepromise-ai . CI verification is tracked in GitHub Actions. Demo script prepared; final video and submission require verified Sandbox flow. |

The hosted catalogue defaults to demo settlement. Operator-protected jobs may now select actual PayPal Sandbox APIs with test funds, independently of extraction provider. Provider choice is frozen at job creation. Only an authenticated operator can create a job using the metered model; no model credential is sent to the browser.

Current validation: 52 local tests passed; TypeScript/Vite build passed. Live rules and Azure jobs each correctly delivered one item, left one undelivered and excluded one invalid-price row before quoting. This earlier pre-Sandbox test used simulation. The later Sandbox test captured USD 2 and confirmed a USD 1 partial refund through PayPal APIs.

Live restart check: completed catalogue results and the sole simulated settlement remained identical after an Azure App Service restart.

Sandbox integration release: 59 local tests passed; TypeScript/Vite build passed; GitHub CI passed for commit c66f898. Azure deployment a17d080f-99fe-4f99-ab13-486078ead8dc succeeded.

Sandbox financial persistence check passed after Azure restart; completed results and refund ID remained unchanged. Final video recording and Devpost submission are still outstanding. A submission text draft is prepared in DEVPOST_SUBMISSION.md.
