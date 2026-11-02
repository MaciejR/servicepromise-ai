# Release progress — 2 November 2026

User instruction: continue through stages without stopping after each T. Technical implementation continues while previously identified business assumptions remain open.

| Stage | Status |
| --- | --- |
| T0–T1 | Contract, local prototype, synthetic corpus and real Azure comparison completed. Original customer files, human review and business validation pending. |
| T2 | Durable single-process SQLite jobs, immutable quote, bounded repair attempts, recovery, additive migration and consistent backup implemented. |
| T3 | Import, quote, exclusions, policy, item evidence, live status polling, same-tab recovery and protected downloads implemented. Rules and operator-gated real Azure extraction selectable. |
| T4 | Automated suite and build pass; desktop Chrome example flow verified. Store import and human time-saving benchmark pending external inputs. |
| T5 | PayPal Developer opens at Face ID/Touch ID sign-in. User login is required. No catalogue payment or refund has been sent to PayPal. |
| T6 | Azure deployment successful (OneDeploy 55e7f259-14e3-4004-b7d7-59459d83c0f4). Remote flows passed for rules and real Azure, including protected CSV/JSON downloads and operator gating. Public source publication was explicitly approved by the user and completed at https://github.com/MaciejR/servicepromise-ai . CI verification is tracked in GitHub Actions. Demo script prepared; final video and submission require verified Sandbox flow. |

The current hosted catalogue uses simulated payment capture and refund eligibility, including when real Azure extraction is selected. Provider choice is frozen at job creation. Only an authenticated operator can create a job using the metered model; no model credential is sent to the browser.

Current validation: 52 local tests passed; TypeScript/Vite build passed. Live rules and Azure jobs each correctly delivered one item, left one undelivered and excluded one invalid-price row before quoting. Refund eligibility was 100 cents in simulation; no PayPal transaction occurred.

Live restart check: completed catalogue results and the sole simulated settlement remained identical after an Azure App Service restart.
