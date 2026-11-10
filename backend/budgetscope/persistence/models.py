from datetime import date

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    validates,
)


class Base(DeclarativeBase):
    pass

class FinancialState(Base):
    __tablename__ = "financial_state"

    id: Mapped[int] = mapped_column(primary_key=True)
    balance_cents: Mapped[int] = mapped_column(nullable=False)

class Category(Base):
    __tablename__ = "category"

    __table_args__ = (
        CheckConstraint(
            "type IN ('income', 'expense')",
            name="ck_category_type",
        ),
        UniqueConstraint(
            "type",
            "normalized_name",
            name="uq_category_type_normalized_name",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    normalized_name: Mapped[str] = mapped_column(nullable=False)
    type: Mapped[str] = mapped_column(nullable=False)
    active: Mapped[bool] = mapped_column(nullable=False)

    @validates("name")
    def _normalize_name(self, _key: str, name: str) -> str:
        """Preserve the display name and update its comparison key."""
        self.normalized_name = name.strip().casefold()
        return name

class MonthlyBudget(Base):
    __tablename__ = "monthly_budget"

    __table_args__ = (
        CheckConstraint(
            "amount_cents > 0",
            name="ck_monthly_budget_positive_amount",
        ),
        UniqueConstraint(
            "category_id",
            "budget_month",
            name="uq_monthly_budget_category_month",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("category.id"),
        nullable=False,
    )
    budget_month: Mapped[str] = mapped_column(nullable=False)
    amount_cents: Mapped[int] = mapped_column(nullable=False)

class RecurrenceRule(Base):
    __tablename__ = "recurrence_rule"

    __table_args__ = (
        CheckConstraint(
            "amount_cents > 0",
            name="ck_recurrence_rule_positive_amount",
        ),
        CheckConstraint(
            "interval IN ("
            "'monthly', 'quarterly', 'semiannual', 'annual'"
            ")",
            name="ck_recurrence_rule_interval",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("category.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(nullable=False)
    amount_cents: Mapped[int] = mapped_column(nullable=False)
    first_due_date: Mapped[date] = mapped_column(nullable=False)
    interval: Mapped[str] = mapped_column(nullable=False)
    active: Mapped[bool] = mapped_column(nullable=False)

class PlannedExpense(Base):
    __tablename__ = "planned_expense"

    __table_args__ = (
        CheckConstraint(
            "amount_cents > 0",
            name="ck_planned_expense_positive_amount",
        ),
        CheckConstraint(
            "status IN ('open', 'completed', 'cancelled')",
            name="ck_planned_expense_status",
        ),
        # Both recurrence fields must be set together or remain NULL.
        CheckConstraint(
            "(recurrence_rule_id IS NULL "
            "AND recurrence_occurrence_date IS NULL) "
            "OR "
            "(recurrence_rule_id IS NOT NULL "
            "AND recurrence_occurrence_date IS NOT NULL)",
            name="ck_planned_expense_recurrence_pair",
        ),
        UniqueConstraint(
            "recurrence_rule_id",
            "recurrence_occurrence_date",
            name="uq_planned_expense_recurrence_occurrence",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("category.id"),
        nullable=False,
    )
    recurrence_rule_id: Mapped[int | None] = mapped_column(
        ForeignKey("recurrence_rule.id"),
        nullable=True,
    )
    recurrence_occurrence_date: Mapped[date | None] = mapped_column(
        nullable=True,
    )
    name: Mapped[str] = mapped_column(nullable=False)
    due_date: Mapped[date] = mapped_column(nullable=False)
    amount_cents: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)

class Booking(Base):
    __tablename__ = "booking"

    __table_args__ = (
        CheckConstraint(
            "amount_cents > 0",
            name="ck_booking_positive_amount",
        ),
        CheckConstraint(
            "type IN ('income', 'expense')",
            name="ck_booking_type",
        ),
        CheckConstraint(
            "source IN ('manual', 'imported')",
            name="ck_booking_source",
        ),
        CheckConstraint(
            "(source = 'manual' AND import_fingerprint IS NULL) "
            "OR "
            "(source = 'imported' AND import_fingerprint IS NOT NULL)",
            name="ck_booking_source_fingerprint",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("category.id"),
        nullable=True,
    )
    type: Mapped[str] = mapped_column(nullable=False)
    booking_date: Mapped[date] = mapped_column(nullable=False)
    amount_cents: Mapped[int] = mapped_column(nullable=False)
    source: Mapped[str] = mapped_column(nullable=False)
    booking_text: Mapped[str | None] = mapped_column(nullable=True)
    purpose: Mapped[str | None] = mapped_column(nullable=True)
    counterparty: Mapped[str | None] = mapped_column(nullable=True)
    import_fingerprint: Mapped[str | None] = mapped_column(
        nullable=True,
    )
