# SOURCES.md — Data Source Research Notes

## Source 1: SAP (Fuel & Procurement) — Scope 1 & 3

### Real-World Format Researched
- SAP MM module reports: MB51 (Material Document List), MM60 (Inventory Turnover), ME2M (Purchase Orders by Material)
- Standard export: **tab-delimited flat file** from SAP GUI's "Local File" export function
- SAP uses German as the default UI language in most European/Asian implementations; column headers in German even for English-language companies

### What Was Learned
- Column names vary by SAP version (ECC vs S/4HANA), customization level, and which info types are added to the layout
- `Buchungsdatum` (posting date) is always DD.MM.YYYY — SAP uses European date format regardless of locale
- `Mengeneinheit` (unit of measure) uses SAP's internal unit codes (L, LTR, GAL, KG, T, ST, EA)
- `Werk` (plant) is a 4-digit numeric code — meaningless without a plant master data lookup
- `Material` numbers follow a company-specific numbering convention (not standardized across clients)
- Movement types (Bewegungsart) classify the transaction: 261=goods issue to production, 101=goods receipt, 122=return to vendor

### Why the Sample Data Looks This Way
- 3 plant codes (1000/2300/3100) reflecting a typical mid-size company with manufacturing + logistics + tech sites
- German column headers throughout — this is what you actually get from SAP, not localized
- Mix of L, LTR, GAL, KG, T units — reflects procurement of fuel from different suppliers with different unit conventions (US-origin diesel often shipped in gallons)
- One row with missing Mengeneinheit — a known SAP quirk when unit is left blank in the material master

### What Would Break in Production
1. **Company-specific material code schemes** — our mapping table covers generic prefixes; real clients have codes like "MAT-00034521" with no obvious fuel indicator
2. **Multiple SAP systems** — large companies run SAP ECC + S/4HANA simultaneously; column names may differ between systems
3. **Currency/amount fields** — if monetary value rather than quantity is exported, emission factors must be spend-based (much less accurate)
4. **Batch splits** — a single fuel delivery may appear as multiple MB51 rows with partial quantities

---

## Source 2: Utility (Electricity) — Scope 2

### Real-World Format Researched
- Indian utility portals: MSEDCL (Maharashtra), BESCOM (Bangalore), CESC (Kolkata) — all offer PDF and CSV downloads
- Format varies significantly by utility: some use comma-delimited, some pipe-delimited
- Billing periods are calendar-based for most but aligned to meter reading cycles for others (often 28–32 days)

### What Was Learned
- Multiple meter IDs per account are common for large commercial premises (separate meters for HVAC, lighting, server room)
- Utility bills in India often include both "units consumed" (kWh) and "maximum demand" (kVA) — only kWh is relevant for Scope 2
- Tariff codes (e.g., TRF-GEN-A) vary by utility and consumption bracket; they affect pricing but not emission factor
- Gaps in billing periods occur during: meter replacement, disputed bills, estimated reads replaced by actual reads, site closures
- MWh units appear for large industrial/data centre accounts (> 500 kW sanctioned load)

### Why the Sample Data Looks This Way
- Billing periods starting on day 14 (Pune HQ) vs day 1 (Mumbai/Bangalore) — reflects real meter reading schedules that don't align to calendar months
- MTR-002 (Mumbai) has a gap in July 2024 — simulates a missed billing cycle (common during meter replacement)
- MTR-003 (Bangalore Data Centre) uses MWh — realistic for a data centre with high sanctioned load
- 3 different tariff codes — preserved as metadata, not used in emission calculation

### What Would Break in Production
1. **PDF-only utility portals** — many Indian utilities don't offer CSV; PDF extraction requires OCR + parsing
2. **Estimated vs actual reads** — utilities sometimes issue estimated bills that are later corrected; both appear as rows with different amounts
3. **Net metering / solar offset** — companies with rooftop solar have negative consumption rows; our parser flags these as errors
4. **Multi-site utilities** — one utility account may cover multiple physical sites if under a group tariff; site attribution is lost

---

## Source 3: Corporate Travel — Scope 3

### Real-World Format Researched
- Concur Travel & Expense export (CSV via "Analyze" module)
- Navan (formerly TripActions) expense export
- Standard columns differ slightly between platforms but all include transaction ID, employee ID, date, category, amounts

### What Was Learned
- Concur/Navan categorize expenses as AIR, HOTEL, CAR, RAIL — consistent across implementations
- Flight distance is **often missing** from expense reports; employees book by price/schedule, not by distance
- IATA airport codes are reliable (3-letter codes are globally standardized by IATA)
- Hotel expenses often lack night count — employees report total spend but don't break out nightly rate × nights
- Employee IDs instead of names are standard practice for privacy compliance (GDPR, PDPA)
- `trip_purpose` is a mandatory field in some company policies but left blank when employees don't fill it
- Radiative forcing index (RFI) — aviation's non-CO2 warming effects increase the effective CO2e by ~1.9× above direct CO2; DEFRA 2023 factors include RFI

### Why the Sample Data Looks This Way
- Some flight rows have `distance_km` populated (when the booking system provides it) and some don't (when booked via external OTA)
- One DEL→LHR international flight to show cross-border distance estimation
- HOTEL rows with `nights` filled in (when expense policy requires it) and some with only spend
- RAIL rows (IRCTC) with distance but no seat class — realistic for Indian rail bookings
- Missing `trip_purpose` on some rows — reflects real-world non-compliance with expense policy

### What Would Break in Production
1. **Multi-leg flights** — a DEL→DXB→LHR itinerary may appear as one row or two; current parser treats each row as one leg
2. **Group travel** — if one employee books for a team, the headcount is lost and CO2e is underestimated
3. **Non-IATA codes** — some regional Indian airports use non-standard codes; our lookup table would return NULL distance
4. **Currency conversion** — travel expenses in non-USD currencies need FX conversion for spend-based fallbacks
5. **Blended travel** — when one trip combines flight + hotel + car as a single line item, categorization fails
