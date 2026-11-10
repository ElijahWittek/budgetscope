from collections.abc import Iterator
from datetime import date
from pathlib import Path
from secrets import token_urlsafe

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from budgetscope.persistence.database import (
    configure_foreign_key_enforcement,
)
from budgetscope.persistence.models import (
    Base,
    Booking,
    Category,
    FinancialState,
    MonthlyBudget,
    PlannedExpense,
    RecurrenceRule,
)


def test_financial_state_persists_in_encrypted_database(
        tmp_path: Path,
) -> None:
    database_path = tmp_path / "financial_state.db"

    database_url = URL.create(
        "sqlite+pysqlcipher",
        username="",
        password=token_urlsafe(32),
        database=str(database_path),
    )

    engine = create_engine(database_url)

    try:
        # Test-only schema setup; production schema changes use Alembic migrations.
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            session.add(
                FinancialState(id=1, balance_cents=-5000)
            )
            session.commit()

        with Session(engine) as session:
            stored_state = session.get(FinancialState, 1)

            assert stored_state is not None
            assert stored_state.balance_cents == -5000
    finally:
        engine.dispose()

def test_category_persists_in_encrypted_database(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "category.db"

    database_url = URL.create(
        "sqlite+pysqlcipher",
        username="",
        password=token_urlsafe(32),
        database=str(database_path),
    )

    engine = create_engine(database_url)

    try:
        # Test-only schema setup; production uses Alembic migrations.
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            session.add(
                Category(
                    name="Lebensmittel",
                    type="expense",
                    active=True,
                )
            )
            session.commit()

        with Session(engine) as session:
            stored_category = session.get(Category, 1)

            assert stored_category is not None
            assert stored_category.name == "Lebensmittel"
            assert stored_category.type == "expense"
            assert stored_category.active is True
    finally:
        engine.dispose()

def test_category_rejects_invalid_type(
        tmp_path: Path,
) -> None:
    database_path = tmp_path / "invalid_category.db"

    database_url = URL.create(
        "sqlite+pysqlcipher",
        username="",
        password=token_urlsafe(32),
        database=str(database_path),
    )

    engine = create_engine(database_url)

    try:
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            session.add(
                Category(
                    name="Ungültige Kategorie",
                    type="transfer",
                    active=True,
                )
            )

            with pytest.raises(IntegrityError):
                session.commit()
    finally:
        engine.dispose()

@pytest.fixture
def category_engine(tmp_path: Path) -> Iterator[Engine]:
    database_url = URL.create(
        "sqlite+pysqlcipher",
        username="",
        password=token_urlsafe(32),
        database=str(tmp_path / "category_uniqueness.db"),
    )

    engine = create_engine(database_url)
    configure_foreign_key_enforcement(engine)

    try:
        # Isolate schema setup from production Alembic migrations.
        Base.metadata.create_all(engine)
        yield engine
    finally:
        engine.dispose()

@pytest.mark.parametrize(
    ("name", "duplicate"),
    [
        ("Lebensmittel", "lebensmittel"),
        ("Lebensmittel", " Lebensmittel "),
        ("Überweisung", "überweisung"),
        ("Straße", "STRASSE"),
    ],
)
def test_category_rejects_duplicate_normalized_name(
    category_engine: Engine,
    name: str,
    duplicate: str,
) -> None:
    with Session(category_engine) as session:
        category = Category(
            name=name,
            type="expense",
            active=True,
        )
        session.add(category)
        session.commit()

        assert category.name == name
        assert category.normalized_name == name.strip().casefold()

    with Session(category_engine) as session:
        session.add(
            Category(
                name=duplicate,
                type="expense",
                active=True,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()

def test_category_name_allowed_for_different_types(
        category_engine: Engine,
) -> None:
    with Session(category_engine) as session:
        session.add_all(
            [
                Category(
                    name="Lebensmittel",
                    type="expense",
                    active=True,
                ),
                Category(
                    name="lebensmittel",
                    type="income",
                    active=True,
                ),
            ]
        )
        session.commit()

def test_category_rename_updates_normalized_name(
        category_engine: Engine,
) -> None:
    with Session(category_engine) as session:
        category = Category(
            name="Freizeit",
            type="expense",
            active=True,
        )
        session.add(category)
        session.commit()

        category.name = " Überweisung "

        assert category.normalized_name == "überweisung"

        session.commit()
        session.refresh(category)

        assert category.name == " Überweisung "
        assert category.normalized_name == "überweisung"

def test_monthly_budget_persists(
        category_engine: Engine,
) -> None:
    with Session(category_engine) as session:
        category = Category(
            name="Lebensmittel",
            type="expense",
            active=True,
        )
        session.add(category)
        session.flush()

        budget = MonthlyBudget(
            category_id=category.id,
            budget_month="2026-11",
            amount_cents=35000,
        )
        session.add(budget)
        session.commit()

        budget_id = budget.id

    with Session(category_engine) as session:
        stored_budget = session.get(MonthlyBudget, budget_id)

        assert stored_budget is not None
        assert stored_budget.budget_month == "2026-11"
        assert stored_budget.amount_cents == 35000

def test_monthly_budget_rejects_duplicate_category_month(
    category_engine: Engine,
) -> None:
    with Session(category_engine) as session:
        category = Category(
            name="Lebensmittel",
            type="expense",
            active=True,
        )
        session.add(category)
        session.flush()

        session.add(
            MonthlyBudget(
                category_id=category.id,
                budget_month="2026-11",
                amount_cents=35000,
            )
        )
        session.commit()

        session.add(
            MonthlyBudget(
                category_id=category.id,
                budget_month="2026-11",
                amount_cents=40000,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()

@pytest.mark.parametrize("amount_cents", [0, -100])
def test_monthly_budget_rejects_non_positive_amount(
    category_engine: Engine,
    amount_cents: int,
) -> None:
    with Session(category_engine) as session:
        category = Category(
            name="Lebensmittel",
            type="expense",
            active=True,
        )
        session.add(category)
        session.flush()

        session.add(
            MonthlyBudget(
                category_id=category.id,
                budget_month="2026-11",
                amount_cents=amount_cents,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()

def test_monthly_budget_rejects_unknown_category(
    category_engine: Engine,
) -> None:
    with Session(category_engine) as session:
        session.add(
            MonthlyBudget(
                category_id=999_999,
                budget_month="2026-11",
                amount_cents=10000,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()

@pytest.mark.parametrize(
    "interval",
    ["monthly", "quarterly", "semiannual", "annual"],
)
def test_recurrence_rule_persists(
    category_engine: Engine,
    interval: str,
) -> None:
    with Session(category_engine) as session:
        category = Category(
            name="Strom",
            type="expense",
            active=True,
        )
        session.add(category)
        session.flush()

        rule = RecurrenceRule(
            category_id=category.id,
            name="Stromabschlag",
            amount_cents=8500,
            first_due_date=date(2026, 12, 1),
            interval=interval,
            active=True,
        )
        session.add(rule)
        session.commit()

        rule_id = rule.id

    with Session(category_engine) as session:
        stored_rule = session.get(RecurrenceRule, rule_id)

        assert stored_rule is not None
        assert stored_rule.name == "Stromabschlag"
        assert stored_rule.amount_cents == 8500
        assert stored_rule.first_due_date == date(2026, 12, 1)
        assert stored_rule.interval == interval
        assert stored_rule.active is True

@pytest.mark.parametrize(
    ("amount_cents", "interval"),
    [
        (0, "monthly"),
        (-100, "monthly"),
        (8500, "weekly"),
    ],
)
def test_recurrence_rule_rejects_invalid_values(
    category_engine: Engine,
    amount_cents: int,
    interval: str,
) -> None:
    with Session(category_engine) as session:
        category = Category(
            name="Strom",
            type="expense",
            active=True,
        )
        session.add(category)
        session.flush()

        session.add(
            RecurrenceRule(
                category_id=category.id,
                name="Stromabschlag",
                amount_cents=amount_cents,
                first_due_date=date(2026, 12, 1),
                interval=interval,
                active=True,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()

def test_recurrence_rule_rejects_unknown_category(
    category_engine: Engine,
) -> None:
    with Session(category_engine) as session:
        session.add(
            RecurrenceRule(
                category_id=999_999,
                name="Unbekannte Kategorie",
                amount_cents=8500,
                first_due_date=date(2026, 12, 1),
                interval="monthly",
                active=True,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()

def test_manual_planned_expense_persists(
    category_engine: Engine,
) -> None:
    with Session(category_engine) as session:
        category = Category(
            name="Haushalt",
            type="expense",
            active=True,
        )
        session.add(category)
        session.flush()

        expense = PlannedExpense(
            category_id=category.id,
            recurrence_rule_id=None,
            recurrence_occurrence_date=None,
            name="Neue Waschmaschine",
            due_date=date(2026, 12, 15),
            amount_cents=45000,
            status="open",
        )
        session.add(expense)
        session.commit()

        expense_id = expense.id

    with Session(category_engine) as session:
        stored = session.get(PlannedExpense, expense_id)

        assert stored is not None
        assert stored.name == "Neue Waschmaschine"
        assert stored.amount_cents == 45000
        assert stored.due_date == date(2026, 12, 15)
        assert stored.status == "open"
        assert stored.recurrence_rule_id is None
        assert stored.recurrence_occurrence_date is None

def test_recurring_planned_expense_rejects_duplicate_occurrence(
    category_engine: Engine,
) -> None:
    with Session(category_engine) as session:
        category = Category(
            name="Strom",
            type="expense",
            active=True,
        )
        session.add(category)
        session.flush()

        rule = RecurrenceRule(
            category_id=category.id,
            name="Stromabschlag",
            amount_cents=8500,
            first_due_date=date(2026, 11, 30),
            interval="monthly",
            active=True,
        )
        session.add(rule)
        session.flush()

        expense = PlannedExpense(
            category_id=category.id,
            recurrence_rule_id=rule.id,
            recurrence_occurrence_date=date(2026, 11, 30),
            name="Stromabschlag November",
            due_date=date(2026, 12, 1),
            amount_cents=8500,
            status="open",
        )
        session.add(expense)
        session.commit()

        assert (
            expense.recurrence_occurrence_date
            == date(2026, 11, 30)
        )
        assert expense.due_date == date(2026, 12, 1)

        session.add(
            PlannedExpense(
                category_id=category.id,
                recurrence_rule_id=rule.id,
                recurrence_occurrence_date=date(2026, 11, 30),
                name="Doppelte Ausgabe",
                due_date=date(2026, 12, 2),
                amount_cents=8500,
                status="open",
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()

@pytest.mark.parametrize(
    ("include_rule", "include_occurrence"),
    [
        (True, False),
        (False, True),
    ],
)
def test_planned_expense_rejects_incomplete_recurrence(
    category_engine: Engine,
    include_rule: bool,
    include_occurrence: bool,
) -> None:
    with Session(category_engine) as session:
        category = Category(
            name="Versicherung",
            type="expense",
            active=True,
        )
        session.add(category)
        session.flush()

        rule = RecurrenceRule(
            category_id=category.id,
            name="Versicherung",
            amount_cents=12000,
            first_due_date=date(2027, 1, 1),
            interval="annual",
            active=True,
        )
        session.add(rule)
        session.flush()

        session.add(
            PlannedExpense(
                category_id=category.id,
                recurrence_rule_id=(
                    rule.id if include_rule else None
                ),
                recurrence_occurrence_date=(
                    date(2027, 1, 1)
                    if include_occurrence
                    else None
                ),
                name="Versicherungsbeitrag",
                due_date=date(2027, 1, 1),
                amount_cents=12000,
                status="open",
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()

@pytest.mark.parametrize(
    ("amount_cents", "status"),
    [
        (0, "open"),
        (-100, "open"),
        (10000, "pending"),
    ],
)
def test_planned_expense_rejects_invalid_values(
    category_engine: Engine,
    amount_cents: int,
    status: str,
) -> None:
    with Session(category_engine) as session:
        category = Category(
            name="Haushalt",
            type="expense",
            active=True,
        )
        session.add(category)
        session.flush()

        session.add(
            PlannedExpense(
                category_id=category.id,
                recurrence_rule_id=None,
                recurrence_occurrence_date=None,
                name="Geplante Anschaffung",
                due_date=date(2026, 12, 15),
                amount_cents=amount_cents,
                status=status,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()

def test_planned_expense_rejects_unknown_category(
    category_engine: Engine,
) -> None:
    with Session(category_engine) as session:
        session.add(
            PlannedExpense(
                category_id=999_999,
                recurrence_rule_id=None,
                recurrence_occurrence_date=None,
                name="Unbekannte Kategorie",
                due_date=date(2026, 12, 15),
                amount_cents=10000,
                status="open",
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()

def test_planned_expense_rejects_unknown_recurrence_rule(
    category_engine: Engine,
) -> None:
    with Session(category_engine) as session:
        category = Category(
            name="Versicherung",
            type="expense",
            active=True,
        )
        session.add(category)
        session.flush()

        session.add(
            PlannedExpense(
                category_id=category.id,
                recurrence_rule_id=999_999,
                recurrence_occurrence_date=date(2027, 1, 1),
                name="Versicherungsbeitrag",
                due_date=date(2027, 1, 1),
                amount_cents=12000,
                status="open",
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()

def test_manual_booking_persists_without_category(
    category_engine: Engine,
) -> None:
    with Session(category_engine) as session:
        booking = Booking(
            category_id=None,
            type="expense",
            booking_date=date(2026, 11, 10),
            amount_cents=2499,
            source="manual",
            booking_text="Haushaltseinkauf",
            purpose=None,
            counterparty=None,
            import_fingerprint=None,
        )
        session.add(booking)
        session.commit()
        booking_id = booking.id

    with Session(category_engine) as session:
        stored = session.get(Booking, booking_id)

        assert stored is not None
        assert stored.category_id is None
        assert stored.type == "expense"
        assert stored.booking_date == date(2026, 11, 10)
        assert stored.amount_cents == 2499
        assert stored.source == "manual"
        assert stored.booking_text == "Haushaltseinkauf"
        assert stored.purpose is None
        assert stored.counterparty is None
        assert stored.import_fingerprint is None

def test_imported_booking_preserves_bank_fields(
    category_engine: Engine,
) -> None:
    with Session(category_engine) as session:
        category = Category(
            name="Gehalt",
            type="income",
            active=True,
        )
        session.add(category)
        session.flush()

        booking = Booking(
            category_id=category.id,
            type="income",
            booking_date=date(2026, 11, 2),
            amount_cents=250000,
            source="imported",
            booking_text="Gutschrift",
            purpose="Gehalt November",
            counterparty="Beispielunternehmen GmbH",
            import_fingerprint="test-fingerprint-001",
        )
        session.add(booking)
        session.commit()
        booking_id = booking.id
        category_id = category.id

    with Session(category_engine) as session:
        stored = session.get(Booking, booking_id)

        assert stored is not None
        assert stored.category_id == category_id
        assert stored.type == "income"
        assert stored.source == "imported"
        assert stored.booking_text == "Gutschrift"
        assert stored.purpose == "Gehalt November"
        assert stored.counterparty == "Beispielunternehmen GmbH"
        assert stored.import_fingerprint == "test-fingerprint-001"

def test_imported_bookings_allow_duplicate_fingerprints(
    category_engine: Engine,
) -> None:
    with Session(category_engine) as session:
        first = Booking(
            category_id=None,
            type="expense",
            booking_date=date(2026, 11, 10),
            amount_cents=1999,
            source="imported",
            booking_text="Kartenzahlung",
            purpose="Einkauf",
            counterparty="Beispielmarkt",
            import_fingerprint="shared-fingerprint",
        )

        second = Booking(
            category_id=None,
            type="expense",
            booking_date=date(2026, 11, 10),
            amount_cents=1999,
            source="imported",
            booking_text="Kartenzahlung",
            purpose="Einkauf",
            counterparty="Beispielmarkt",
            import_fingerprint="shared-fingerprint",
        )

        session.add_all([first, second])
        session.commit()

        assert first.id != second.id

@pytest.mark.parametrize(
    ("booking_type", "amount_cents", "source"),
    [
        ("transfer", 1000, "manual"),
        ("expense", 0, "manual"),
        ("expense", -100, "manual"),
        ("expense", 1000, "unknown"),
    ],
)
def test_booking_rejects_invalid_values(
    category_engine: Engine,
    booking_type: str,
    amount_cents: int,
    source: str,
) -> None:
    with Session(category_engine) as session:
        session.add(
            Booking(
                category_id=None,
                type=booking_type,
                booking_date=date(2026, 11, 10),
                amount_cents=amount_cents,
                source=source,
                booking_text="Testbuchung",
                purpose=None,
                counterparty=None,
                import_fingerprint=None,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()

@pytest.mark.parametrize(
    ("source", "fingerprint"),
    [
        ("manual", "unexpected-fingerprint"),
        ("imported", None),
    ],
)
def test_booking_rejects_inconsistent_fingerprint(
    category_engine: Engine,
    source: str,
    fingerprint: str | None,
) -> None:
    with Session(category_engine) as session:
        session.add(
            Booking(
                category_id=None,
                type="expense",
                booking_date=date(2026, 11, 10),
                amount_cents=1000,
                source=source,
                booking_text="Testbuchung",
                purpose=None,
                counterparty=None,
                import_fingerprint=fingerprint,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()

def test_booking_rejects_unknown_category(
    category_engine: Engine,
) -> None:
    with Session(category_engine) as session:
        session.add(
            Booking(
                category_id=999_999,
                type="expense",
                booking_date=date(2026, 11, 10),
                amount_cents=1000,
                source="manual",
                booking_text="Testbuchung",
                purpose=None,
                counterparty=None,
                import_fingerprint=None,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()
