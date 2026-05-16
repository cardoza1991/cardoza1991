"""Supplier intel agent.

Pulls external risk signals (sanctions, CVEs, ICS advisories) from feeds,
matches them to suppliers in the catalog, and persists `SupplierIntelSignal`
rows that the risk engine consumes.

Designed offline-first: every feed has a bundled fixture and only attempts
live HTTP when `settings.intel_live_feeds` is true. This keeps the demo
deterministic and works in sandboxed environments where outbound traffic
is blocked.
"""

from .pipeline import run_intel_cycle, IntelCycleResult

__all__ = ["run_intel_cycle", "IntelCycleResult"]
