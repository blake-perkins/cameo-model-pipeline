#!/usr/bin/env python3
"""
validate_exports.py

Validates Cameo export JSON files against their schemas.
Exits with non-zero status if validation fails.
"""
import argparse
import json
import sys
from pathlib import Path

try:
    import jsonschema
    from jsonschema import validate, ValidationError
except ImportError:
    print("ERROR: jsonschema package required. Install with: pip install jsonschema")
    sys.exit(1)


def load_json(path: str) -> dict:
    """Load a JSON file and return its contents."""
    file_path = Path(path)
    if not file_path.exists():
        print(f"ERROR: File not found: {path}")
        sys.exit(1)
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_file(data_path: str, schema_path: str, file_label: str) -> list[str]:
    """Validate a JSON file against a schema. Returns list of error messages."""
    data = load_json(data_path)
    schema = load_json(schema_path)
    errors = []

    validator = jsonschema.Draft7Validator(schema)
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        path = " -> ".join(str(p) for p in error.absolute_path) or "(root)"
        errors.append(f"  [{file_label}] {path}: {error.message}")

    return errors


def validate_requirements_content(data_path: str) -> list[str]:
    """Additional business-logic validations beyond JSON schema."""
    data = load_json(data_path)
    errors = []
    seen_ids = set()
    seen_uuids = set()

    for i, req in enumerate(data.get("requirements", [])):
        req_id = req.get("requirementId", f"(index {i})")

        # Check for duplicate requirement IDs
        if req_id in seen_ids:
            errors.append(f"  [requirements] Duplicate requirementId: {req_id}")
        seen_ids.add(req_id)

        # Check for duplicate UUIDs
        uuid = req.get("cameoUUID", "")
        if uuid and uuid in seen_uuids:
            errors.append(f"  [requirements] Duplicate cameoUUID: {uuid} (on {req_id})")
        if uuid:
            seen_uuids.add(uuid)

        # Check verification criteria is non-empty
        criteria = req.get("verificationCriteria", "").strip()
        if not criteria:
            errors.append(
                f"  [requirements] {req_id}: verificationCriteria is empty"
            )

        # Check parent reference exists if specified
        parent = req.get("parentRequirementId")
        if parent and parent not in seen_ids and parent not in {
            r.get("requirementId") for r in data.get("requirements", [])
        }:
            errors.append(
                f"  [requirements] {req_id}: parentRequirementId '{parent}' "
                f"does not reference a known requirement"
            )

    return errors


def validate_icd_content(data_path: str) -> list[str]:
    """Additional business-logic validations for ICD export."""
    data = load_json(data_path)
    errors = []

    for iface in data.get("interfaces", []):
        iface_name = iface.get("name", "(unnamed)")

        for msg in iface.get("messages", []):
            msg_name = msg.get("name", "(unnamed)")
            field_numbers = set()

            for field in msg.get("fields", []):
                fn = field.get("fieldNumber")
                if fn in field_numbers:
                    errors.append(
                        f"  [icd] {iface_name}.{msg_name}: "
                        f"duplicate fieldNumber {fn}"
                    )
                field_numbers.add(fn)

        # Check enum values for duplicates
        for enum in iface.get("enums", []):
            enum_name = enum.get("name", "(unnamed)")
            numbers = set()
            names = set()
            for val in enum.get("values", []):
                if val.get("number") in numbers:
                    errors.append(
                        f"  [icd] {iface_name}.{enum_name}: "
                        f"duplicate enum number {val.get('number')}"
                    )
                numbers.add(val.get("number"))
                if val.get("name") in names:
                    errors.append(
                        f"  [icd] {iface_name}.{enum_name}: "
                        f"duplicate enum name '{val.get('name')}'"
                    )
                names.add(val.get("name"))

    return errors


def generate_report(errors: list[str], output_path: str | None) -> dict:
    """Generate a validation report."""
    report = {
        "valid": len(errors) == 0,
        "errorCount": len(errors),
        "errors": errors,
    }
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
    return report


def main():
    parser = argparse.ArgumentParser(
        description="Validate Cameo export JSON files against schemas"
    )
    parser.add_argument(
        "--requirements",
        required=True,
        help="Path to requirements_export.json",
    )
    parser.add_argument(
        "--icd",
        required=True,
        help="Path to icd_export.json",
    )
    parser.add_argument(
        "--req-schema",
        required=True,
        help="Path to requirements_schema.json",
    )
    parser.add_argument(
        "--icd-schema",
        required=True,
        help="Path to icd_schema.json",
    )
    parser.add_argument(
        "--report-output",
        default=None,
        help="Path to write validation report JSON",
    )
    args = parser.parse_args()

    all_errors = []

    # Schema validation
    print("Validating requirements export against schema...")
    all_errors.extend(
        validate_file(args.requirements, args.req_schema, "requirements-schema")
    )

    print("Validating ICD export against schema...")
    all_errors.extend(validate_file(args.icd, args.icd_schema, "icd-schema"))

    # Business logic validation
    print("Running requirements content validation...")
    all_errors.extend(validate_requirements_content(args.requirements))

    print("Running ICD content validation...")
    all_errors.extend(validate_icd_content(args.icd))

    # Generate report
    report = generate_report(all_errors, args.report_output)

    if all_errors:
        print(f"\nVALIDATION FAILED: {len(all_errors)} error(s) found:\n")
        for err in all_errors:
            print(err)
        sys.exit(1)
    else:
        print("\nVALIDATION PASSED: All exports are valid.")
        sys.exit(0)


if __name__ == "__main__":
    main()
