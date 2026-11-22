---
type: synthesis
title: Tidal Quiet Comparison
sources: [tidal-sorting.md, quiet-protocol.md]
created: 2026-11-20
updated: 2026-11-20
tags: [comparison, synthesis]
---

# Tidal Quiet Comparison

This page compares the tide based sort with the quiet protocol. Both are invented and are used here only to demonstrate a source grounded synthesis.

## Comparison

- The tide based sort groups readings by an artificial tide. See [[sources/tidal-sorting|Tidal Sorting]].
- The quiet protocol reaches agreement without broadcasting each vote. See [[sources/quiet-protocol|Quiet Protocol]].
- Both are operated by [[entities/lumen-council|Lumen Council]].

## Finding

[[concepts/marker-decay|Marker Decay]] is the shared failure mode. The tide based sort can merge groups silently, while the quiet protocol leaves the decay visible in the final record. [[concepts/quiet-consensus|Quiet Consensus]] reduces traffic but does not remove the need to watch the markers.

The follow up question is saved in [[queries/marker-decay-question|Marker Decay Question]].
