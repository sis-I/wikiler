---
title: Quiet Protocol
tags: [consensus, protocol]
---

# Quiet Protocol

This paper proposes a protocol in which a group reaches agreement without
broadcasting each intermediate vote. The Lumen Council uses it to reconcile
station logs after a long interval.

Quiet consensus lowers the amount of traffic between stations. Marker decay
is still visible in the final record, so the protocol does not hide when a
reading was replaced.
