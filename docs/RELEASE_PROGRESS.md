# Release progress — 2 November 2026

User instruction: continue through stages without stopping after each T. Technical implementation continues while previously identified business assumptions remain open.

| Stage | Status |
| --- | --- |
| T0–T1 | Contract, local prototype, synthetic corpus and real Azure comparison completed. Original customer files, human review and business validation pending. |
| T2 | Durable single-process SQLite jobs, immutable quote, bounded repair attempts, recovery, additive migration and consistent backup implemented. |
| T3 | Import, quote, exclusions, policy, item evidence, live status polling, same-tab recovery and protected downloads implemented. Rules and operator-gated real Azure extraction selectable. |
| T4 | Automated suite and build pass; desktop Chrome example flow verified. Store import and human time-saving benchmark pending external inputs. |
| T5 | PayPal Developer opens at Face ID/Touch ID sign-in. User login is required. No catalogue payment or refund has been sent to PayPal. |
| T6 | Azure deployment in progress; source publication and demo script prepared. Final video and hackathon submission require verified Sandbox flow. |

The current hosted catalogue uses simulated payment capture and refund eligibility, including when real Azure extraction is selected. Provider choice is frozen at job creation. Only an authenticated operator can create a job using the metered model; no model credential is sent to the browser.
