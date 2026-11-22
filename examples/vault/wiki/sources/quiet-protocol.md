---
type: source
title: Quiet Protocol
sources: [quiet-protocol.md]
created: 2026-11-20
updated: 2026-11-20
tags: [consensus, protocol]
---

# Quiet Protocol

## Source metadata

- **Source file:** quiet-protocol.md

## Key claims

- Agreement is reached without broadcasting each intermediate vote.
- Traffic between stations drops compared with an open vote.
- The final record still shows when a reading was replaced.

## Structured summary

The paper proposes [[concepts/quiet-consensus|Quiet Consensus]] for log reconciliation by [[entities/lumen-council|Lumen Council]]. It keeps [[concepts/marker-decay|Marker Decay]] visible in the final record instead of hiding it. The comparison with the tide based method is recorded in [[synthesis/tidal-quiet-comparison|Tidal Quiet Comparison]].

## Entities

- [[entities/lumen-council|Lumen Council]]

## Concepts

- [[concepts/quiet-consensus|Quiet Consensus]]
- [[concepts/marker-decay|Marker Decay]]
