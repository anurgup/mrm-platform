"""Orchestrates shadow-AI discovery across all configured scanners. Does NOT
persist anything (that's P-4.2) — just runs every scanner, collects results,
and deduplicates."""

import logging

from sqlalchemy.orm import Session

from app.scanners import DiscoveredAsset, get_configured_scanners

logger = logging.getLogger(__name__)


async def discover_assets(db: Session) -> list[DiscoveredAsset]:
    """Run all configured scanners, collect results, deduplicate by
    (name, source). `db` isn't used yet — persistence lands in P-4.2 — but
    the signature is already shaped for it so callers don't change later."""
    scanners = get_configured_scanners()
    all_assets: list[DiscoveredAsset] = []

    for scanner in scanners:
        try:
            assets = await scanner.scan()
            all_assets.extend(assets)
        except Exception as exc:
            # A single source failing to reach out shouldn't block the rest.
            logger.warning("Scanner %s failed: %s", scanner.__class__.__name__, exc)

    seen: set[tuple[str, str]] = set()
    deduplicated: list[DiscoveredAsset] = []
    for asset in all_assets:
        key = (asset.name, asset.source)
        if key not in seen:
            seen.add(key)
            deduplicated.append(asset)

    return deduplicated
