"""Audit Report schema — the canonical SPA/deliverable data contract.

The audit-report module's output IS `AuditData` (vendored from the Algolia Search Audit skill,
`prism_platform/v2/audit_data_schema.py`) — the exact contract the SPA + deliverable HTML
templates read. The module assembles AuditData from upstream module outputs (deterministic
fields) + LLM synthesis (prose). Re-exported here as `AuditReportOutput` for the registry.
"""

from __future__ import annotations

from core.audit_data_schema import AuditData, validate_audit_data

# The module's output schema is the canonical AuditData contract.
AuditReportOutput = AuditData

__all__ = ["AuditData", "AuditReportOutput", "validate_audit_data"]
