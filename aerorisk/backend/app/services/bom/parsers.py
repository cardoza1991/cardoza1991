"""SBOM parsers.

Supported on day 1:
- CycloneDX 1.4/1.5 JSON  (cyclonedx.org/specification)
- Simple CSV with columns: part_number,name,vendor,product,version,cpe,purl

SPDX is intentionally out of scope for v1 — the spec is heavier and most
aerospace SBOMs we'll see come from defense suppliers using CycloneDX.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass
class ParsedComponent:
    name: str
    vendor: Optional[str] = None
    version: Optional[str] = None
    purl: Optional[str] = None
    cpe: Optional[str] = None
    part_number_raw: Optional[str] = None


def parse_cyclonedx(raw: bytes | str) -> list[ParsedComponent]:
    """Parse a CycloneDX JSON document. Tolerates 1.4 and 1.5 shapes."""
    data = json.loads(raw) if isinstance(raw, (bytes, bytearray, str)) and not isinstance(raw, dict) else raw
    if isinstance(data, dict) is False:
        raise ValueError("CycloneDX root must be a JSON object")
    if data.get("bomFormat") != "CycloneDX":
        # Be permissive — some exporters omit bomFormat. Require `components` instead.
        if "components" not in data:
            raise ValueError("not a CycloneDX manifest (missing components)")

    out: list[ParsedComponent] = []
    for c in data.get("components", []) or []:
        name = (c.get("name") or "").strip()
        if not name:
            continue
        # Vendor cascade: publisher → supplier.name (if dict) → group.
        vendor = c.get("publisher")
        if not vendor:
            sup = c.get("supplier")
            if isinstance(sup, dict):
                vendor = sup.get("name")
        if not vendor:
            vendor = c.get("group")
        cpe = c.get("cpe")
        purl = c.get("purl")
        version = c.get("version")
        # Some defense exporters stash a part number in `properties` as
        # {name: "aerospace:part_number", value: "..."}
        pn = None
        for prop in c.get("properties", []) or []:
            pname = (prop.get("name") or "").lower()
            if "part_number" in pname or pname == "partnumber":
                pn = prop.get("value")
                break
        out.append(ParsedComponent(
            name=name, vendor=vendor, version=version,
            purl=purl, cpe=cpe, part_number_raw=pn,
        ))
    return out


def parse_csv(raw: bytes | str) -> list[ParsedComponent]:
    """Parse a simple CSV. Required column: `name`. Optional: vendor / product
    / version / cpe / purl / part_number.

    `product` is folded into name if `name` is missing on a row.
    """
    text = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else raw
    reader = csv.DictReader(io.StringIO(text))
    out: list[ParsedComponent] = []
    for row in reader:
        # Normalize header casing once per row.
        norm = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        name = norm.get("name") or norm.get("product") or norm.get("component") or ""
        if not name:
            continue
        out.append(ParsedComponent(
            name=name,
            vendor=norm.get("vendor") or norm.get("publisher") or norm.get("supplier"),
            version=norm.get("version"),
            purl=norm.get("purl"),
            cpe=norm.get("cpe"),
            part_number_raw=norm.get("part_number") or norm.get("partnumber"),
        ))
    return out


def detect_format(filename: str, raw: bytes | str) -> str:
    """Return CYCLONEDX or CSV based on filename + content sniffing."""
    fname = (filename or "").lower()
    if fname.endswith(".csv"):
        return "CSV"
    if fname.endswith(".json") or fname.endswith(".cdx.json"):
        return "CYCLONEDX"
    # Sniff
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, (bytes, bytearray)) else raw
    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        return "CYCLONEDX"
    return "CSV"


def parse(filename: str, raw: bytes | str) -> tuple[str, list[ParsedComponent]]:
    """Detect and parse. Returns (format, components)."""
    fmt = detect_format(filename, raw)
    if fmt == "CYCLONEDX":
        return fmt, parse_cyclonedx(raw)
    return fmt, parse_csv(raw)
