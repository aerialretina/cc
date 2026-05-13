"""Enrichment pipeline.

Stages (§2):
  1. Dedup (3 steps: source / cross-source / semantic) → canonical Posting
  2. Occupation classification (NOC + SOC + industrial overlay)
  3. Skills NER
  4. Compensation extract + estimate
  5. Org entity resolution
  6. Location geocoding
"""
