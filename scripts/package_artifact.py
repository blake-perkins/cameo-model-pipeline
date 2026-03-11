#!/usr/bin/env python3
"""
package_artifact.py

Assembles the versioned zip artifact containing proto files, requirements,
and build metadata for publishing to Nexus.
"""
import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile


def read_version(version_file: str) -> str:
    """Read and validate semantic version from VERSION file."""
    path = Path(version_file)
    if not path.exists():
        print(f"ERROR: VERSION file not found: {version_file}")
        sys.exit(1)
    version = path.read_text().strip()
    parts = version.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        print(f"ERROR: Invalid semver in VERSION file: '{version}' (expected X.Y.Z)")
        sys.exit(1)
    return version


def create_manifest(
    version: str,
    build_number: str,
    git_sha: str,
    git_branch: str,
    proto_dir: str,
    requirements_path: str,
) -> dict:
    """Create the manifest.json contents."""
    proto_count = len(list(Path(proto_dir).glob("*.proto"))) if Path(proto_dir).exists() else 0

    req_count = 0
    if Path(requirements_path).exists():
        with open(requirements_path) as f:
            data = json.load(f)
            req_count = len(data.get("requirements", []))

    return {
        "artifactId": "cameo-model-artifacts",
        "version": version,
        "buildNumber": build_number,
        "gitCommitSha": git_sha,
        "gitBranch": git_branch,
        "buildTimestamp": datetime.now(timezone.utc).isoformat(),
        "contents": {
            "protoFileCount": proto_count,
            "requirementCount": req_count,
        },
    }


def package_zip(
    version: str,
    build_number: str,
    proto_dir: str,
    requirements_path: str,
    requirements_schema_path: str,
    icd_export_path: str,
    validation_report_path: str | None,
    output_dir: str,
    git_sha: str,
    git_branch: str,
) -> str:
    """Create the versioned zip artifact. Returns the path to the zip file."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    artifact_name = f"cameo-model-artifacts-{version}-build.{build_number}.zip"
    zip_path = output / artifact_name

    manifest = create_manifest(
        version, build_number, git_sha, git_branch, proto_dir, requirements_path
    )

    with ZipFile(zip_path, "w") as zf:
        # VERSION
        zf.writestr("VERSION", version)

        # manifest.json
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))

        # Proto files
        proto_path = Path(proto_dir)
        if proto_path.exists():
            for proto_file in proto_path.glob("*.proto"):
                zf.write(proto_file, f"proto/{proto_file.name}")

        # Requirements
        if Path(requirements_path).exists():
            zf.write(requirements_path, "requirements/requirements.json")
        if Path(requirements_schema_path).exists():
            zf.write(
                requirements_schema_path, "requirements/requirements_schema.json"
            )

        # ICD export (raw)
        if Path(icd_export_path).exists():
            zf.write(icd_export_path, "icd/icd_export.json")

        # Validation report
        if validation_report_path and Path(validation_report_path).exists():
            zf.write(
                validation_report_path, "reports/validation_report.json"
            )

    print(f"Packaged artifact: {zip_path}")
    print(f"  Version: {version}")
    print(f"  Build: {build_number}")
    print(f"  Proto files: {manifest['contents']['protoFileCount']}")
    print(f"  Requirements: {manifest['contents']['requirementCount']}")

    return str(zip_path)


def main():
    parser = argparse.ArgumentParser(
        description="Package Cameo model artifacts into a versioned zip"
    )
    parser.add_argument("--version-file", default="VERSION")
    parser.add_argument(
        "--build-number", default=os.environ.get("BUILD_NUMBER", "0")
    )
    parser.add_argument("--proto-dir", default="build/proto")
    parser.add_argument(
        "--requirements", default="exports/requirements_export.json"
    )
    parser.add_argument(
        "--requirements-schema", default="schemas/requirements_schema.json"
    )
    parser.add_argument("--icd-export", default="exports/icd_export.json")
    parser.add_argument("--validation-report", default=None)
    parser.add_argument("--output-dir", default="build")
    parser.add_argument(
        "--git-sha", default=os.environ.get("GIT_COMMIT", "unknown")
    )
    parser.add_argument(
        "--git-branch", default=os.environ.get("GIT_BRANCH", "unknown")
    )
    args = parser.parse_args()

    version = read_version(args.version_file)

    zip_path = package_zip(
        version=version,
        build_number=args.build_number,
        proto_dir=args.proto_dir,
        requirements_path=args.requirements,
        requirements_schema_path=args.requirements_schema,
        icd_export_path=args.icd_export,
        validation_report_path=args.validation_report,
        output_dir=args.output_dir,
        git_sha=args.git_sha,
        git_branch=args.git_branch,
    )

    print(f"\nArtifact ready for publishing: {zip_path}")


if __name__ == "__main__":
    main()
