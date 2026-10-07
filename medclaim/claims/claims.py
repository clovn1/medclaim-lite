# claims/claims.py  --  claim submit + void
#
# Mixed vintage. submit_claim and void_claim_legacy are ORIGINAL BUILD (2018).
# void_claim (the modern path) was added with the soft-delete work in 2022
# (ADR-002). Both void paths still exist; new code should use void_claim.

import logging
import uuid
from datetime import datetime

from medclaim import db

log = logging.getLogger("medclaim.claims")


def submit_claim(patient_id, payer_id, service_date, amount_cents, adjustment_cents=0):
    claim_id = "C-" + uuid.uuid4().hex[:10]
    conn = db.connect()
    try:
        conn.execute(
            "insert into claims (id, patient_id, payer_id, service_date, "
            "amount_cents, adjustment_cents, status, is_deleted) "
            "values (?, ?, ?, ?, ?, ?, 'submitted', 0)",
            (claim_id, patient_id, payer_id, service_date,
             amount_cents, adjustment_cents),
        )
        conn.commit()
    finally:
        conn.close()
    return claim_id


def void_claim(claim_id, reason=None):
    # MODERN void path (2022, ADR-002). Flip is_deleted to 1 AND record the void.
    # This is the one new code should call.
    conn = db.connect()
    try:
        conn.execute("update claims set is_deleted = 1 where id = ?", (claim_id,))
        conn.execute(
            "insert into void_log (claim_id, reason, method, voided_at) "
            "values (?, ?, 'modern', ?)",
            (claim_id, reason, datetime.utcnow().isoformat(timespec="seconds")),
        )
        conn.commit()
    finally:
        conn.close()


def void_claim_legacy(claim_id, reason=None):
    # ORIGINAL void path (2018). Still called from the old ERA-import and
    # correction flows. Sets is_deleted = 1 like the modern path (ADR-002, T-103).
    conn = db.connect()
    try:
        # no PHI in logs: claim id only, never patient name or MRN.
        log.info("legacy void: claim=%s", claim_id)
        conn.execute("update claims set is_deleted = 1 where id = ?", (claim_id,))
        conn.execute(
            "insert into void_log (claim_id, reason, method, voided_at) "
            "values (?, ?, 'legacy', ?)",
            (claim_id, reason, datetime.utcnow().isoformat(timespec="seconds")),
        )
        conn.commit()
    finally:
        conn.close()
