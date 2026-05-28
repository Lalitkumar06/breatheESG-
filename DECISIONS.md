# Breathe ESG — Architecture & Design Decisions

This document acts as our living log of the engineering tradeoffs, pragmatism, and architecture decisions we made while building the Breathe platform.

---

## 1. SAP File Ingestion: Handling the Messy Reality
*   **The Problem:** SAP exports from real enterprise systems (like `MB51` inventory or `MM60` material lists) are notoriously inconsistent. Layouts change, localized systems export in German, and numbers use commas instead of dots for decimals.
*   **Our Decision:**
    1.  **Tab vs. Comma Auto-Detection:** The ingestion pipeline reads the first 2,000 bytes of any uploaded file to sniff the delimiter. We natively parse both standard CSVs and tab-delimited files (which SAP defaults to in standard exports).
    2.  **German Column Mapping:** We mapped stable German column headers (like `Buchungsdatum` to date, `Mengeneinheit` to unit, and `Werk` to plant) directly to our English schema. This keeps the user experience simple: they upload the raw report directly from SAP GUI without having to translate headers first.
    3.  **Flexible Date Parsing:** Standard SAP uses `DD.MM.YYYY` format. We attempt to parse European dates first, falling back to ISO `YYYY-MM-DD` and standard American formatting before flagging the row.

---

## 2. Decoupling the Ingestion Queue (Threading vs. Celery)
*   **The Problem:** Parsing large files (up to 10MB or 1,000+ rows) and calculating geodesic flight distances in a standard request-response loop leads to HTTP timeouts and a terrible user experience.
*   **Our Decision:** We implemented a lightweight, thread-safe background orchestrator using standard Python `threading`. 
*   **Why Not Celery?** Celery requires running a separate Redis or RabbitMQ container, adding extra cost and infrastructure complexity to early deployments. Threading is completely self-contained, runs cleanly on standard cloud platforms, and easily handles early-stage enterprise batch jobs. 
*   *Note: We included a clear migration route for Celery hooks in `pipeline.py` once we scale past 50 concurrent uploads.*

---

## 3. Scope 2 Grid Emission Factors
*   **The Problem:** Electricity doesn't emit carbon at the socket; the emissions depend entirely on how clean the grid is where the facility is located.
*   **Our Decision:**
    1.  We created a seeding database for `PlantLookup` that maps SAP plant codes (like `1000` or `3100`) to physical locations and regions.
    2.  If a facility is in India, we use the official Central Electricity Authority (CEA) factor (~0.71 kg CO2e/kWh) because of the country's coal-heavy mix. If it's in the UK, we use the cleaner DEFRA grid factor (~0.21 kg).
    3.  This location-based calculation is accurate enough to satisfy greenhouse gas protocol criteria for market-based scope 2 reporting.

---

## 4. The Geodesic Fallback for Flights (Scope 3)
*   **The Problem:** Corporate travel data from Concur or corporate cards often lacks distance tracking. We might get a row that says `DEL` to `BOM` (Delhi to Mumbai) with a transaction value, but no mileage.
*   **Our Decision:**
    1.  We built an IATA airport code distance registry directly into our normalizer, pre-loaded with the most common corporate city pairs.
    2.  If the flight is registered in our lookup table, we fetch the physical flight distance instantly and compute accurate Scope 3 emissions.
    3.  If the city pair is new, instead of crashing the batch job, we save the record, set `co2e_kg = NULL`, and trigger a `UNIT_FALLBACK` flag. This lets the analyst manually input the distance or let the platform calculate it, preserving database integrity.

---

## 5. Token Authentication over Session Cookies
*   **The Problem:** We wanted a secure, modern REST API that integrates cleanly with our React frontend.
*   **Our Decision:** We chose Django REST Framework's Token-based Authentication.
*   **Why?** It keeps the API stateless and completely avoids Cross-Site Request Forgery (CSRF) issues that come with session cookies when the React frontend is deployed on a different domain (like Vercel) than our Django backend (like Railway). The token is saved securely in the browser's `localStorage` and passed in the `Authorization: Token ...` header.
