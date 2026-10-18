"""CSV exports: SCADA log, work orders, vibration trend, KPIs and the IT service catalog.

Header = row 1. LF line endings. The work-order export imitates a maintenance-system export:
semicolon separated with a UTF-8 byte order mark.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence

from . import datasets
from .world import World


def _csv(columns: Sequence[str], rows: Sequence[dict[str, str]], delimiter: str = ",") -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(columns), delimiter=delimiter,
                            lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def scada_log(w: World) -> str:
    return _csv(datasets.SCADA_COLUMNS, datasets.scada_rows())


def work_orders(w: World) -> str:
    rows = [
        {key: value.replace(";", ",") for key, value in row.items()}
        for row in datasets.work_order_rows()
    ]
    return _csv(datasets.WORK_ORDER_COLUMNS, rows, delimiter=";")


def vibration(w: World) -> str:
    return _csv(datasets.VIBRATION_COLUMNS, datasets.vibration_rows())


def kpi(w: World) -> str:
    return _csv(datasets.KPI_COLUMNS, datasets.kpi_rows())


IT_CATALOG_COLUMNS = [
    "service",
    "description",
    "owner_team",
    "tier",
    "on_call_rotation",
    "runbook",
    "slo_availability_pct",
    "depends_on",
]


def it_catalog(w: World) -> str:
    rows = [
        {"service": "ticketing-api", "description": "Ticket booking API", "owner_team":
         "platform operations", "tier": "1", "on_call_rotation": "sre-primary",
         "runbook": "RB-TKT-002", "slo_availability_pct": "99.9",
         "depends_on": "orders-db notification-worker"},
        {"service": "checkout-web", "description": "Checkout web front end", "owner_team":
         "web", "tier": "1", "on_call_rotation": "sre-primary", "runbook": "RB-CHK-001",
         "slo_availability_pct": "99.9", "depends_on": "ticketing-api orders-db"},
        {"service": "orders-db", "description": "Orders database (PostgreSQL, primary and "
         "standby)", "owner_team": "data platform", "tier": "1", "on_call_rotation":
         "dba-primary", "runbook": "PRC-DB-007", "slo_availability_pct": "99.95",
         "depends_on": ""},
        {"service": "notification-worker", "description": "E-mail and push notifications",
         "owner_team": "platform operations", "tier": "2", "on_call_rotation": "sre-secondary",
         "runbook": "RB-NTF-003", "slo_availability_pct": "99.5", "depends_on": "ticketing-api"},
        {"service": "reporting-batch", "description": "Nightly sales reporting", "owner_team":
         "data platform", "tier": "3", "on_call_rotation": "business-hours",
         "runbook": "RB-RPT-001", "slo_availability_pct": "99.0", "depends_on": "orders-db"},
    ]
    return _csv(IT_CATALOG_COLUMNS, rows)
