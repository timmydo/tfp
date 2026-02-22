"""Cost basis tracking for taxable accounts using average cost method."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CostBasisTracker:
    total_basis: float = 0.0

    def add_basis(self, amount: float) -> None:
        if amount <= 0:
            return
        self.total_basis += amount

    def withdraw(self, amount: float, balance_before: float) -> float:
        """Apply a withdrawal and return realized gain for the withdrawn amount."""
        if amount <= 0 or balance_before <= 0:
            return 0.0

        basis_ratio = min(1.0, self.total_basis / balance_before)
        basis_reduction = amount * basis_ratio
        self.total_basis = max(0.0, self.total_basis - basis_reduction)
        return max(0.0, amount - basis_reduction)
