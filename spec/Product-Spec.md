# PRODUCT SPECIFICATION
## Wisconsin Real Estate (WI-RE) Analysis Platform

**Version:** 0.9
**Status:** Draft

---

## 1. Project Overview

This document outlines the product and data specifications for the **Wisconsin Real Estate (WI-RE) Analysis Platform**. The platform's objective is to aggregate, analyze, and monitor statewide real estate data to identify distressed second-home properties in key "vacation hotspot" counties.

The ultimate goal is to generate a qualified list of properties where the underlying mortgage can be acquired directly from the lender.

## 2. Core Objectives

* **Aggregate Disparate Data:** Ingest and link data from multiple state and county sources (parcels, sales, taxes, foreclosures, deeds).
* **Identify Target Properties:** Isolate "second homes" (absentee-owned) in high-value recreational counties.
* **Monitor Distress:** Track "distress" signals, primarily tax delinquency and foreclosure filings, over time.
* **Discover Mortgage Holder:** Provide a workflow to identify the "mortgagee" (lender) for high-priority targets.
* **Time-Series Analysis:** Maintain a historical, time-series record of all key data points (ownership, sales, tax status) to track trends and changes.
* **LLM-Ready Export:** Generate clean, structured datasets (per-county) suitable for Retrieval-Augmented Generation (RAG) to power local LLM analysis.

## 3. System & Technical Requirements

### 3.1. Database: Time-Series
All ingested data must be stored in a time-series database (e.g., TimescaleDB, InfluxDB).

* **Rationale:** This is critical for tracking changes over time. We must be able to query not just the *current* state of a property, but its entire history of ownership, sales, and tax status.
* **Schema:** The schema must be event-based. For example:
    * `event_type: 'sale'`, `timestamp: '2023-10-20'`, `parcel_id: '123'`, `data: {price: 500000}`
    * `event_type: 'tax_status_change'`, `timestamp: '2024-02-01'`, `parcel_id: '123'`, `data: {status: 'Delinquent'}`
    * `event_type: 'owner_change'`, `timestamp: '2023-10-20'`, `parcel_id: '123'`, `data: {owner: 'John Doe', mailing_addr: '...'}`

### 3.2. Data Pipeline: ETL & Periodic Updates
The system will require an automated ETL (Extract, Transform, Load) pipeline.

* **Extraction:** A set of scripts (e.g., Python) to download bulk data and scrape county websites.
* **Transformation:** Scripts to clean data, normalize addresses, and link all datasets using the `PARCEL_ID` as the primary key.
* **Loading:** A service to load transformed data into the time-series database, creating new timestamped events.
* **Update Cadence:** The pipeline must run on a schedule to keep data fresh:
    * **Monthly:** Ingest new RETR (sales) data.
    * **Quarterly (or Monthly):** Scrape County Treasurer sites for tax delinquency updates.
    * **Weekly (or Daily):** Scrape WCCA for new foreclosure filings.
    * **Annually:** Perform a full refresh of the core parcel/owner data from the SCO.

### 3.3. RAG Export
The system must have a feature to export data formatted for RAG.

* **Format:** JSONL, or a collection of structured `.txt` / `.md` files (one per property).
* **Scope:** The export process shall be run on a **per-county basis** (e.g., "Export RAG data for Vilas County").
* **Content:** Each "document" in the RAG dataset will represent one property and contain a natural-language summary of its *current* state.

> **Example RAG Document (`parcel_123.txt`):**
>
> "Property `010-0555-0000` is located in Vilas County, WI. It is a single-family residential property.
> **Current Owner:** John A. Doe
> **Owner Mailing Address:** 123 Main St, Chicago, IL 60601
> **Property Address:** 456 Lakeview Dr, Eagle River, WI 54521
> **Status:** Absentee Owner / Second Home
> **Tax Status:** Delinquent (as of 2025-Q4)
> **Sales History:** Last sold on 2021-06-15 for $450,000.
> **Distress Signals:** No active WCCA foreclosure case found."

## 4. Data Sourcing Specification

### 4.1. Core Foundation Data (Statewide)

This data forms the base layer of the entire system.

| Data Type | Source | Format | Update Freq. | Link |
| :--- | :--- | :--- | :--- | :--- |
| **Parcel & Owner Data** | WI State Cartographer's Office (SCO) | File Geodatabase (`.gdb`) **V11** | Annually | `https://www.sco.wisc.edu/parcels/data/` |
| **Sales History** | WI Dept. of Revenue (RETR) | CSV (in `.zip` files) | Monthly | `https://www.revenue.wi.gov/Pages/ERETR/data-home.aspx` |

### 4.2. Distress & Target Data (County-Level)

This data must be collected on a county-by-county basis, focusing on "hotspot" counties.

| Data Type | Source | Format | Update Freq. | Example Link (Vilas Co.) |
| :--- | :--- | :--- | :--- | :--- |
| **Tax Delinquency** | County Treasurer Website | Varies (HTML, CSV, PDF) | Monthly/Quarterly | `https://www.vilascountywi.gov/departments/administration___officials/treasurer/` |
| **Foreclosure Filings** | WI Circuit Court Access (WCCA) | HTML (Web Portal) | Daily/Weekly | `https://wcca.wicourts.gov/` |
| **Mortgage Holder** | County Register of Deeds | Web Portal (Pay-per-doc) | On-Demand | `https://landshark.vilascountywi.gov/` |

### 4.3. Target "Hotspot" Counties

Initial data collection efforts will be prioritized for counties with a high density of seasonal/recreational homes.

* **Tier 1 (Primary):** Vilas, Oneida, Door, Sawyer, Burnett
* **Tier 2 (Secondary):** Adams, Juneau, Waushara, Marquette

## 5. Analytical Workflow (User Story)

1.  **Selection:** The user selects "Vilas County" to analyze.
2.  **Filtering:** The system queries the database for all Vilas County properties.
3.  **Identification (Logic):**
    * The system filters for properties where `SITE_ADDR` does not equal `OWNER_MAIL_ADDR`. These are flagged as `Is_Second_Home = TRUE`.
    * The system cross-references this list with the latest tax data, flagging properties where `Tax_Status = 'Delinquent'`.
    * The system cross-references this list with WCCA data, flagging properties with an active `Case_Type = 'Foreclosure of Mortgage'`.
4.  **RAG Generation:** The user triggers the "RAG Export" for the resulting list of distressed second homes. The system generates the structured text files.
5.  **LLM Analysis:** The user loads the RAG dataset into their local LLM for Q&A and deep analysis.
6.  **Manual Triage:** Based on the LLM's output, the user identifies 5 "prime" targets.
7.  **Final Lookup:** The user takes the 5 Parcel IDs to the **Vilas County Register of Deeds (LandShark)** portal, pays the fee, and retrieves the mortgage document to identify the "Mortgagee" (the lender).
8.  **Action:** The user now has the final, actionable list to begin outreach to the mortgage holders.
