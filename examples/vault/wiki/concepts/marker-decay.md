---
type: concept
title: Marker Decay
sources: [tidal-sorting.md]
created: 2026-11-20
updated: 2026-11-20
tags: [failure-mode, sorting]
---

# Marker Decay

Marker Decay is the gradual loss of the markers that separate two sorted groups. In the fixture sources it is the main failure mode of the tide based sort.

## Why it matters

When markers fade, two groups can merge without any warning in the log. The council treats this as a stability problem rather than a throughput problem.

The question in [[queries/marker-decay-question|Marker Decay Question]] asks how to detect the merge early. The comparison in [[synthesis/tidal-quiet-comparison|Tidal Quiet Comparison]] records how the quiet protocol leaves the same decay visible.

## Source

- [[sources/tidal-sorting|Tidal Sorting]]
