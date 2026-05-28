# Breathe ESG — Backend Data Model Architecture

When we designed the database schema for Breathe, we had one high-level goal in mind: **auditable integrity**. In carbon accounting, you cannot just calculate numbers and show a dashboard; every single gram of CO2e must be traceable back to its messy origin.

Here is a look under the hood at how our Django models represent this reality, structured in a way that makes sense for developers, analysts, and green-auditors alike.

---

## 1. The Multi-Tenancy Hierarchy

Every piece of data belongs to a specific corporate entity (`Tenant`). We strictly isolate client databases to prevent any accidental leakage.

```
                  ┌──────────────┐
                  │    Tenant    │ (Acme Corp, GreenTech Ltd)
                  └──────┬───────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
  ┌─────────────┐ ┌─────────────┐ ┌──────────────┐
  │ UserProfile │ │ DataSource  │ │ IngestionJob │ (Tracks file uploads)
  └─────────────┘ └─────────────┘ └──────┬───────┘
                                         │
                                         ▼
                                  ┌──────────────┐
                                  │EmissionRecord│ (Normalized data row)
                                  └──────┬───────┘
                                         │
                                         ▼
                                  ┌──────────────┐
                                  │   AuditLog   │ (Immutable change ledger)
                                  └──────────────┘
```

### The Scoping Rules
*   **Users** are linked to a single Tenant via `UserProfile`. If an analyst from *Acme Corp* logs in, our API views automatically filter all queries to their tenant.
*   **Superusers** act as cross-tenant auditors and can view dashboard summaries across the entire ecosystem.
*   **The Tenant Slug** is used as a folder name when saving raw files to media storage (e.g. `media/raw_uploads/acme-corp/...`).

---

## 2. Decoupling Raw Data from Normalized Metrics

Enterprise data is incredibly messy. SAP exports come in German with mixed metric/imperial units. Utility providers bill on random dates in MWh. Flight expensing apps give us city codes instead of distances.

To handle this elegantly without losing original context, the `EmissionRecord` keeps a clear separation of concerns:

### The Raw Payload
We never throw away the user's original data. Every record has a `raw_data` JSON field that saves the **verbatim row** from the CSV or TSV exactly as it was uploaded. If there is ever an audit dispute, we can point to this field and say: *"This is the exact line SAP gave us."*

### The Normalized Metric Pair
To make reporting possible, we normalize everything. We store the original values **and** the standardized ones side-by-side:
*   **Fuels** are normalized to **liters** (converting from metric tons, gallons, or kilograms using standard fuel densities).
*   **Electricity** is normalized to **kilowatt-hours (kWh)**.
*   **Travel** is normalized to **kilometers (km)**.

This lets us run simple math queries for charts while preserving the original units (`GAL`, `MWh`, `miles`) for human validation.

---

## 3. Scope & Category Mapping

The greenhouse gas (GHG) protocol defines three scopes. Here is how we map our dynamic ingestion sources into standard accounting metrics:

### Scope 1: Direct Emissions (Direct Fuel Combustion)
*   **Source:** SAP Fuel logs (`sap_sample.tsv`).
*   **Category:** `FUEL`.
*   **How it works:** We map materials like `DLS-001` to standard diesel, convert liters, and multiply by the DEFRA 2023 combustion factor (~2.67 kg CO2e/liter).

### Scope 2: Indirect Emissions (Purchased Grid Power)
*   **Source:** Utility bills (`utility_sample.csv`).
*   **Category:** `ELECTRICITY`.
*   **How it works:** We calculate the grid emission factor depending on the facility location. For example, Indian facilities default to the CEA grid factor (~0.71 kg CO2e/kWh), which is much higher than European or UK grids.

### Scope 3: Value Chain (Travel & Procurement)
*   **Source:** Corporate travel logs (`travel_sample.csv`) and SAP procurement documents.
*   **Categories:** `FLIGHT`, `HOTEL`, `GROUND`, `PROCUREMENT`.
*   **Our Fallback Chain:**
    *   *Flights:* If flight codes are present (e.g. DEL → BOM), we estimate the geodesic distance. If that fails, we flag the record for review.
    *   *Hotels:* We prefer night-based tracking (17.5 kg CO2e/room-night). If the analyst didn't input the night count, we fall back to a spend-based factor (0.29 kg CO2e/USD).

---

## 4. The Perfect Audit Trail (No Deletions!)

In standard SaaS, when someone makes a mistake, they hit "Delete." **In ESG carbon accounting, deleting data is a massive red flag.** If an auditor sees missing transaction IDs, they might reject the entire carbon filing.

We solved this with two strict rules:

### 1. Status-Based Lifecycles
Records are never dropped from the database. Instead, they move through a lifecycle state-machine:
`PENDING_REVIEW` ──► `APPROVED` / `REJECTED` / `FLAGGED`

If a record is incorrect, the analyst rejects it and leaves a comment. It remains visible in the historic table, marked in red, showing exactly why it was excluded.

### 2. Snapshots in the Audit Ledger
Whenever a record is edited (e.g. correcting a typo in a fuel quantity), or approved, our backend automatically generates an `AuditLog` entry.
This ledger is **strictly read-only** and records:
*   Who performed the action.
*   A timestamp.
*   A JSON diff of the fields changed (`before_state` vs `after_state`).
*   Any reasoning or comments supplied by the analyst.

Once a record is locked (`is_locked=True`), the system blocks all future mutations. This ensures that once the financial year is signed off, the data is frozen forever.

---

## 5. Ingestion Pipeline & Auto-Flagging

Whenever a file is uploaded, a background thread spins up to run it through our validation engine. If a row smells fishy, we auto-flag it. 

We flag records if they violate any of these human-sensible checks:
1.  **Future Dates:** Activity dates set in the future (e.g. a flight booked for next month).
2.  **Stale Data:** Dates older than 2 years (usually indicates someone uploaded the wrong historical sheet).
3.  **Zero/Null Values:** If the CO2e calculations end up empty or zero, pointing to faulty data inputs.
4.  **Fallback Triggered:** When we couldn't resolve a unit and had to rely on a loose spend-based proxy or default factor.
5.  **Statistical Outliers (The 3-Sigma Rule):** If a fuel entry is 3 standard deviations higher than the average for that tenant, it's flagged. This instantly catches common spreadsheet typos (like typing `120000` instead of `12000`).

Flagged records show up instantly on the analyst's dashboard with a bright purple warning, demanding eyes-on review before they can be merged into the audit totals.
