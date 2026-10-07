from medclaim.billing.history import get_statement_history
from medclaim.billing.statement import build_statement
from medclaim.claims import void_claim, void_claim_legacy
from medclaim.models import Contract


def test_statement_history_returns_data(client):
    history = get_statement_history(patient_id="P-1042")
    assert history is not None
    assert isinstance(history, list)


def test_statement_history_excludes_voided_claims(client, seed):
    claim = seed.claim(patient_id="P-1042", amount_cents=15_000)
    void_claim(claim.id, reason="duplicate")
    history = get_statement_history(patient_id="P-1042")
    assert claim.id not in [line.claim_id for line in history]
    assert all(line.is_voided is False for line in history)


def test_statement_history_excludes_legacy_voided_claims(client, seed):
    # T-103: claims voided via the legacy path still showed in history.
    claim = seed.claim(patient_id="P-1042", amount_cents=15_000)
    void_claim_legacy(claim.id, reason="correction")
    history = get_statement_history(patient_id="P-1042")
    assert claim.id not in [line.claim_id for line in history]


def test_build_statement_calls_contract_service(client, mocker):
    mock_contracts = mocker.patch("medclaim.billing.statement.resolve_contract")
    mock_contracts.return_value = Contract(rate_pct=80)
    build_statement(patient_id="P-1042")
    mock_contracts.assert_called_once()


def test_statement_totals_sum_to_balance(client, seed):
    seed.claims(patient_id="P-2001",
                amounts_cents=[12_500, 8_000, 30_000], adjusted=[0, 800, 0])
    stmt = build_statement(patient_id="P-2001")
    assert stmt.total_charges_cents == 50_500
    assert stmt.total_adjustments_cents == 800
    assert stmt.balance_cents == 49_700
