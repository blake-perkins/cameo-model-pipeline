#!/usr/bin/env python3
"""
generate_protos.py

Transforms icd_export.json from Cameo into .proto files using Jinja2 templates.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


# Type mapping from common ICD type names to protobuf types
TYPE_MAP = {
    "integer": "int32",
    "int": "int32",
    "int32": "int32",
    "long": "int64",
    "int64": "int64",
    "uint32": "uint32",
    "uint64": "uint64",
    "float": "float",
    "double": "double",
    "boolean": "bool",
    "bool": "bool",
    "string": "string",
    "text": "string",
    "bytes": "bytes",
    "binary": "bytes",
}


def to_snake_case(name: str) -> str:
    """Convert CamelCase to snake_case for proto package names."""
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def normalize_field_types(interface: dict) -> dict:
    """Normalize field type names to protobuf-compatible types."""
    for msg in interface.get("messages", []):
        for field in msg.get("fields", []):
            original_type = field["type"]
            normalized = TYPE_MAP.get(original_type.lower(), original_type)
            field["type"] = normalized
    return interface


def generate_proto_files(
    icd_path: str, template_dir: str, output_dir: str
) -> list[str]:
    """Generate .proto files from ICD export JSON. Returns list of generated files."""
    with open(icd_path, "r", encoding="utf-8") as f:
        icd_data = json.load(f)

    metadata = icd_data.get("exportMetadata", {})
    interfaces = icd_data.get("interfaces", [])

    env = Environment(
        loader=FileSystemLoader(template_dir),
        keep_trailing_newline=True,
    )
    template = env.get_template("proto_template.j2")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    generated_files = []

    for interface in interfaces:
        interface = normalize_field_types(interface)
        package_name = interface.get("protoPackage") or to_snake_case(interface["name"])
        file_name = f"{to_snake_case(interface['name'])}.proto"
        file_path = output_path / file_name

        rendered = template.render(
            interface=interface,
            metadata=metadata,
            package_name=package_name,
        )

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(rendered)

        generated_files.append(str(file_path))
        print(f"  Generated: {file_path}")

    return generated_files


def main():
    parser = argparse.ArgumentParser(
        description="Generate .proto files from Cameo ICD export"
    )
    parser.add_argument(
        "--icd", required=True, help="Path to icd_export.json"
    )
    parser.add_argument(
        "--template-dir",
        default=str(Path(__file__).parent.parent / "templates"),
        help="Path to directory containing proto_template.j2",
    )
    parser.add_argument(
        "--output-dir",
        default="build/proto",
        help="Output directory for generated .proto files",
    )
    args = parser.parse_args()

    print(f"Generating .proto files from {args.icd}...")
    files = generate_proto_files(args.icd, args.template_dir, args.output_dir)
    print(f"\nGenerated {len(files)} .proto file(s)")

    if not files:
        print("WARNING: No interfaces found in ICD export. No .proto files generated.")
        sys.exit(1)


if __name__ == "__main__":
    main()
