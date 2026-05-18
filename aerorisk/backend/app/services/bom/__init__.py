"""BOM → CVE → fleet-impact pipeline.

Upload an SBOM (CycloneDX JSON or simple CSV), the pipeline:
1. parses the manifest into BomComponent rows,
2. matches each component to the existing Part / Supplier catalog,
3. enriches with CVE / KEV data,
4. rolls up an aggregate risk score and a list of affected tail numbers.

The cyber-physical wedge: maps a software/firmware vulnerability all the
way down to specific aircraft, not just "vendor X has a CVE."
"""

from .analyzer import analyze_bom_upload, AnalysisResult

__all__ = ["analyze_bom_upload", "AnalysisResult"]
