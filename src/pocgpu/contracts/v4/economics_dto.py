from dataclasses import dataclass, field
from typing import NewType, Self

TransactionSequenceNumber = NewType("TransactionSequenceNumber", int)

@dataclass(frozen=True, slots=True)
class TransactionSequence:
    """
    Represents a unique, atomically incrementing transaction sequence number.

    This DTO encapsulates a sequence number that is expected to be
    atomically incremented by an external system to ensure uniqueness
    and ordering of economic transactions. It serves as a strict,
    versioned contract for identifying a specific point in a sequence.
    """
    sequence_number: TransactionSequenceNumber = field(metadata={"description": "The unique, atomically incrementing sequence number for a transaction."})

    def __post_init__(self) -> None:
        """
        Performs post-initialization validation to ensure the sequence number is non-negative.
        """
        if self.sequence_number < 0:
            raise ValueError("Transaction sequence number must be non-negative.")

    def increment(self) -> Self:
        """
        Returns a new TransactionSequence instance with the sequence number incremented by one.
        This method simulates the atomic increment operation by producing a new immutable DTO.
        """
        return TransactionSequence(TransactionSequenceNumber(self.sequence_number + 1))

    def to_canonical_string(self) -> str:
        """
        Generates a deterministic canonical string representation of the DTO.
        This is crucial for consistent hashing and serialization.
        """
        return f"TransactionSequence(sequence_number={self.sequence_number})"

    def __str__(self) -> str:
        return self.to_canonical_string()

    def __repr__(self) -> str:
        return self.to_canonical_string()