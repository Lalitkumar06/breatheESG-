# Breathe ESG — Engineering Tradeoffs & Pragmatism

In any real software project, deciding what **not** to build is just as important as deciding what to build. To deliver a stable, highly performant platform on schedule, we made three conscious scoping tradeoffs. 

Here is our transparent log of what we deliberately skipped and why:

---

## 1. Static Factors vs. Live API Integration
*   **What we did:** Hardcoded standard DEFRA 2023 and CEA India emission factors into a static database lookup (`EmissionFactor`).
*   **Deliberately skipped:** Building integration hooks with live external carbon APIs (like Climatiq).
*   **Why?**
    1.  **Audits Require Stability:** Auditors expect numbers to remain frozen. If an external API updates its factors midway through a compliance audit, the historical totals will shift, invalidating the entire report.
    2.  **No Single Source of Truth:** No public, reliable, free global API covers all industries. By holding the factor ledger in our own DB, our clients have full visibility and control over exactly what values are being applied.

---

## 2. Ingesting via File Uploads vs. Live Webhook Integrations
*   **What we did:** Focused entirely on a robust, multi-format file-upload model (CSV/TSV processing).
*   **Deliberately skipped:** Building real-time API integrations or webhooks with SAP, Concur, or Utility providers.
*   **Why?**
    1.  **ERP Systems Don't Stream:** Large enterprise SAP setups rarely stream real-time data to third parties. They run on scheduled exports.
    2.  **The Analyst Workflow:** In compliance environments, sustainability teams collect monthly data packages, review them, and upload them in batches. Direct API sync would bypass the critical human verification stage, leading to immediate database pollution.

---

## 3. In-App Outlier Flagging vs. Automated AI Cleansing
*   **What we did:** Built a clean outlier detector (the 3-Sigma statistical rule) that flags anomalous records for manual analyst approval.
*   **Deliberately skipped:** Writing code to automatically "correct" or scrub anomalous data.
*   **Why?**
    *   **Regulatory Risk:** Automatically modifying a company's data under the hood is a compliance nightmare. If an AI or heuristic automatically changes a value, we can no longer guarantee the database matches the raw files.
    *   **Human in the Loop:** A statistical flag is helpful; auto-cleansing is dangerous. The final decision to approve or reject a correction should always rest with a human analyst.
