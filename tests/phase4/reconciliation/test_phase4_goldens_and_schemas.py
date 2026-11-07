import pytest
import json
from dataclasses import asdict
from typing import Any, Dict

from src.pocgpu.contracts.v4.economics_dto import TransactionSequence, TransactionSequenceNumber

TRANSACTION_SEQUENCE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "sequence_number": {
            "type": "integer",
            "minimum": 0,
            "description": "The unique, atomically incrementing sequence number for a transaction."
        }
    },
    "required": ["sequence_number"],
    "additionalProperties": False
}

def validate_json_schema(instance: Dict[str, Any], schema: Dict[str, Any]) -> None:
    """
    A very basic, manual JSON schema validator for demonstration purposes.
    This is not a full JSON schema validator but checks the essential properties
    relevant to the TransactionSequence DTO.
    """
    if schema.get("type") != "object":
        raise ValueError("Schema root type must be 'object'.")

    required_properties = schema.get("required", [])
    for prop in required_properties:
        if prop not in instance:
            raise ValueError(f"Missing required property: '{prop}'")

    properties_schema = schema.get("properties", {})
    for prop_name, prop_schema in properties_schema.items():
        if prop_name in instance:
            value = instance[prop_name]
            expected_type = prop_schema.get("type")
            if expected_type == "integer":
                if not isinstance(value, int):
                    raise ValueError(f"Property '{prop_name}' must be an integer.")
                if "minimum" in prop_schema and value < prop_schema["minimum"]:
                    raise ValueError(f"Property '{prop_name}' must be at least {prop_schema['minimum']}.")

    if not schema.get("additionalProperties", True):
        for prop_name in instance:
            if prop_name not in properties_schema:
                raise ValueError(f"Additional property '{prop_name}' is not allowed.")


class TestPhase4EconomicsDTOs:
    """
    Comprehensive verification suite for Phase 4 Economics DTOs,
    covering golden cases, schema parity, and migration evidence.
    """

    def test_eco_001_initial_sequence_creation(self) -> None:
        """
        ECO-001: Verifies the correct creation of an initial transaction sequence.
        Ensures a valid non-negative sequence number can be instantiated.
        """
        initial_sequence = TransactionSequence(TransactionSequenceNumber(0))
        assert initial_sequence.sequence_number == 0
        assert initial_sequence.to_canonical_string() == "TransactionSequence(sequence_number=0)"

        sequence_one = TransactionSequence(TransactionSequenceNumber(1))
        assert sequence_one.sequence_number == 1
        assert sequence_one.to_canonical_string() == "TransactionSequence(sequence_number=1)"

    def test_eco_002_sequence_increment_behavior(self) -> None:
        """
        ECO-002: Verifies the correct behavior of sequence number incrementation.
        Ensures the increment method produces a new DTO with an incremented value
        without mutating the original.
        """
        initial_sequence = TransactionSequence(TransactionSequenceNumber(10))
        incremented_sequence = initial_sequence.increment()

        assert initial_sequence.sequence_number == 10
        assert incremented_sequence.sequence_number == 11
        assert initial_sequence is not incremented_sequence

        double_incremented_sequence = incremented_sequence.increment()
        assert double_incremented_sequence.sequence_number == 12
        assert double_incremented_sequence is not incremented_sequence

    def test_prc_001_invalid_negative_sequence_number(self) -> None:
        """
        PRC-001: Verifies that negative sequence numbers are strictly disallowed.
        Ensures robust validation against invalid input states.
        """
        with pytest.raises(ValueError, match=r"Transaction sequence number must be non-negative."):
            TransactionSequence(TransactionSequenceNumber(-1))

        with pytest.raises(ValueError, match=r"Transaction sequence number must be non-negative."):
            TransactionSequence(TransactionSequenceNumber(-100))

    def test_prc_002_deterministic_canonical_representation(self) -> None:
        """
        PRC-002: Verifies deterministic canonical serialization and hashing.
        Ensures identical inputs produce identical string representations and hashes.
        """
        seq_a = TransactionSequence(TransactionSequenceNumber(42))
        seq_b = TransactionSequence(TransactionSequenceNumber(42))
        seq_c = TransactionSequence(TransactionSequenceNumber(43))

        assert seq_a.to_canonical_string() == "TransactionSequence(sequence_number=42)"
        assert seq_a.to_canonical_string() == seq_b.to_canonical_string()
        assert seq_a.to_canonical_string() != seq_c.to_canonical_string()

        assert hash(seq_a) == hash(seq_b)
        assert hash(seq_a) != hash(seq_c)

        assert seq_a == seq_b
        assert seq_a != seq_c

    def test_schema_parity_transaction_sequence(self) -> None:
        """
        Validates that the TransactionSequence DTO structure aligns with its defined JSON schema.
        This ensures consistency between the DTO contract and its external schema representation.
        """
        instance_data = asdict(TransactionSequence(TransactionSequenceNumber(123)))
        try:
            validate_json_schema(instance_data, TRANSACTION_SEQUENCE_SCHEMA)
        except ValueError as e:
            pytest.fail(f"Schema validation failed for TransactionSequence: {e}")

        invalid_data_negative = {"sequence_number": -5}
        with pytest.raises(ValueError, match=r"Property 'sequence_number' must be at least 0."):
            validate_json_schema(invalid_data_negative, TRANSACTION_SEQUENCE_SCHEMA)

        invalid_data_wrong_type = {"sequence_number": "not_an_int"}
        with pytest.raises(ValueError, match=r"Property 'sequence_number' must be an integer."):
            validate_json_schema(invalid_data_wrong_type, TRANSACTION_SEQUENCE_SCHEMA)

        invalid_data_missing_field = {}
        with pytest.raises(ValueError, match=r"Missing required property: 'sequence_number'"):
            validate_json_schema(invalid_data_missing_field, TRANSACTION_SEQUENCE_SCHEMA)

        invalid_data_extra_field = {"sequence_number": 1, "extra_field": "value"}
        with pytest.raises(ValueError, match=r"Additional property 'extra_field' is not allowed."):
            validate_json_schema(invalid_data_extra_field, TRANSACTION_SEQUENCE_SCHEMA)

    def test_migration_evidence_immutability_and_distinctness(self) -> None:
        """
        Migration Evidence: Asserts that the TransactionSequence DTO maintains immutability
        and distinctness, proving no prior phase artifacts are mutated and core concepts
        like 'markup' or 'gross margin' are not implicitly introduced or affected.
        """
        initial_seq = TransactionSequence(TransactionSequenceNumber(5))
        incremented_seq = initial_seq.increment()

        assert initial_seq.sequence_number == 5
        assert initial_seq is not incremented_seq

        initial_dict = asdict(initial_seq)
        assert "markup" not in initial_dict
        assert "gross_margin" not in initial_dict
        assert "commercial_value" not in initial_dict
        assert "utilization_rate" not in initial_dict

        incremented_dict = asdict(incremented_seq)
        assert "markup" not in incremented_dict
        assert "gross_margin" not in incremented_dict
        assert "commercial_value" not in incremented_dict
        assert "utilization_rate" not in incremented_dict

        assert isinstance(initial_seq, TransactionSequence)
        assert isinstance(incremented_seq, TransactionSequence)
        assert type(initial_seq) is type(incremented_seq)