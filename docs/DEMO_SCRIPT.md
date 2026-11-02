# Demo outline — under 3 minutes

Status: recording script prepared; final video is not recorded or submitted. Use the actual running build and label all funds as PayPal Sandbox test funds. Enter the private operator token before recording, collapse Operator access, and never show credentials.

- 0:00–0:20: Explain the catalogue task and the per-item delivery promise. State the limited scope: color/material extraction with source evidence.
- 0:20–0:45: Load the four-row example. Choose PayPal Sandbox and Azure OpenAI. Show one invalid-price row excluded before quoting; the remaining three items cost USD 3 in test funds.
- 0:45–1:20: Create checkout, approve a guest test-card payment and confirm capture in the application. Speed up waiting periods transparently. Use only the official PayPal Sandbox card generator and fictional buyer data, with Save info / create account turned off. No real card is needed.
- 1:20–1:50: Inspect the actual model results. Show two delivered items and one without verifiable material after a repair attempt. Expand source quotations and error reasons.
- 1:50–2:15: Issue the eligible USD 1 Sandbox refund. Show confirmed completion and the refund ID; pending must remain visibly pending until confirmed. Download the delivered CSV and evidence report.
- 2:15–2:35: Refresh to show persistence, then show source and passing CI.
- 2:35–2:55: Disclose that the synthetic feasibility benchmark did not show an AI advantage over rules. Original supplier data, human time-savings measurement and actual store import remain open checks.

The separately verified cloud test used two rows (one delivered, one undelivered), captured USD 2 and confirmed a USD 1 refund. Do not splice its transaction identifiers into a recording of a different order. Record and describe the actual order shown.

Official test-card generator: https://developer.paypal.com/sandbox-testing/card-testing#credit-card-generator

The public application defaults to Demo. Selecting Sandbox creates a real transaction only within PayPal's test environment; it never uses live funds.
