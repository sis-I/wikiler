---
title: Tidal Sorting
tags: [sorting, signals]
---

# Tidal Sorting

This article describes a sorting method that groups readings by the rhythm of
a manufactured tide rather than by their arrival order. The method is used by
the Lumen Council to compare sensor logs from different harbor stations.

![[tidal-chart.png]]
A small chart of the artificial tide used by the sorting method.

The method trades throughput for stability. Marker decay is the main failure
mode: when the markers fade, two groups can merge without any warning in the
log. Quiet consensus is not required for the sorting step, but it helps when
the council reconciles two stations.
