---
type: source
title: Tidal Sorting
sources: [tidal-sorting.md]
created: 2026-11-20
updated: 2026-11-20
tags: [sorting, signals]
---

# Tidal Sorting

## Source metadata

- **Source file:** tidal-sorting.md

## Key claims

- The method groups readings by a manufactured tide instead of arrival order.
- Stability is preferred over throughput.
- Marker decay can merge two groups without a warning in the log.

## Structured summary

The article describes a sorting step used by [[entities/lumen-council|Lumen Council]] to compare harbor sensor logs. The method relies on a repeating artificial tide, represented in the local asset `raw/assets/tidal-chart.png`. Its main failure mode is [[concepts/marker-decay|Marker Decay]], which can silently merge two sorted groups. The article does not require [[concepts/quiet-consensus|Quiet Consensus]] for sorting itself, but notes that reconciliation is easier when the stations agree quietly.

## Entities

- [[entities/lumen-council|Lumen Council]]

## Concepts

- [[concepts/marker-decay|Marker Decay]]
- [[concepts/quiet-consensus|Quiet Consensus]]
