# Spec: Phase 5 - Expanding Data Sources (Scraping)

**Status:** `pending`

This document outlines the tasks required to add scraping capabilities.

## TODO List

- [ ] Implement the dynamic module loader for scraper plugins in the Data Collector service.
- [ ] Develop the first county-level scraper (e.g., Vilas County tax delinquency).
- [ ] Add the new scraper to a Prefect flow.
- [ ] Update the Transformation service to handle the new `tax_status_change` event type.
