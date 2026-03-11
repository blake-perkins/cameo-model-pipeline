# Cameo Model Pipeline

**Transform Cameo Systems Modeler exports into versioned protobuf artifacts for deployment.**

This pipeline ingests structured JSON exports from Cameo Systems Modeler (an MBSE tool by Dassault Systemes), validates them against JSON schemas, generates Protocol Buffer `.proto` files, and publishes versioned artifacts to Sonatype Nexus. It is designed for air-gapped environments with DoD/NIST compliance requirements.

---

## Architecture Overview

```
 +---------------------------+
 |  Cameo Systems Modeler    |
 |  (MBSE Authoring Tool)    |
 +------------+--------------+
              |
              | Groovy Macros (ExportICD / ExportRequirements)
              v
 +---------------------------+
 |  JSON Exports             |
 |  - requirements_export    |
 |  - icd_export             |
 +------------+--------------+
              |
              | git commit + push
              v
 +---------------------------+     +---------------------------+
 |  CI/CD Pipeline           |     |                           |
 |                           |     |  Downstream Consumer      |
 |  1. Validate Exports      |     |  (product-pipeline repo)  |
 |  2. Generate .proto files |---->|                           |
 |  3. Package artifact      |     |  Pulls versioned .zip     |
 |  4. Publish to Nexus      |     |  from Nexus               |
 |  5. Tag release           |     +---------------------------+
 +---------------------------+
```

---

## Repository Structure

```
cameo-model-pipeline/
|-- VERSION                          # Semantic version (X.Y.Z) for artifact tagging
|-- Jenkinsfile                      # Production CI/CD pipeline (Jenkins)
|-- .github/
|   +-- workflows/
|       +-- model-pipeline.yml       # Prototype CI/CD pipeline (GitHub Actions)
|-- cameo-macro/
|   +-- README.md                    # Instructions for Cameo Groovy macro usage
|-- exports/
|   |-- requirements_export.json     # Requirements JSON exported from Cameo
|   +-- icd_export.json              # ICD JSON exported from Cameo
|-- schemas/
|   |-- requirements_schema.json     # JSON Schema (Draft-07) for requirements export
|   +-- icd_schema.json              # JSON Schema (Draft-07) for ICD export
|-- scripts/
|   |-- validate_exports.py          # Schema + business-logic validation
|   |-- generate_protos.py           # Jinja2-based .proto file generator
|   |-- package_artifact.py          # Builds versioned zip artifact with manifest
|   |-- publish_to_nexus.sh          # Uploads artifact to Nexus raw repository
|   +-- requirements.txt             # Python dependencies
|-- templates/
|   +-- proto_template.j2            # Jinja2 template for .proto file generation
+-- build/                           # (generated) Build outputs, not committed
    |-- proto/                        # Generated .proto files
    |-- reports/                      # Validation reports
    +-- *.zip                         # Packaged artifact
```

---

## Prerequisites

| Dependency | Version | Purpose |
|---|---|---|
| Python | 3.10+ | Pipeline scripts |
| Jinja2 | (latest) | Proto file generation from templates |
| jsonschema | (latest) | JSON Schema Draft-07 validation |
| protoc | 3.x+ | Syntax validation of generated `.proto` files |
| Nexus Repository | 3.x | Artifact hosting (raw repository) |
| Cameo Systems Modeler | 2022x+ | Model authoring (systems engineers only) |

Install Python dependencies:

```bash
pip install -r scripts/requirements.txt
```

---

## Quick Start

Run each pipeline step locally from the repository root:

### 1. Validate exports against schemas

```bash
python scripts/validate_exports.py \
    --requirements exports/requirements_export.json \
    --icd exports/icd_export.json \
    --req-schema schemas/requirements_schema.json \
    --icd-schema schemas/icd_schema.json \
    --report-output build/reports/validation_report.json
```

### 2. Generate `.proto` files from ICD export

```bash
python scripts/generate_protos.py \
    --icd exports/icd_export.json \
    --template-dir templates \
    --output-dir build/proto
```

### 3. Validate generated `.proto` files with `protoc`

```bash
for proto_file in build/proto/*.proto; do
    protoc --proto_path=build/proto --descriptor_set_out=/dev/null "$proto_file"
    echo "  VALID: $proto_file"
done
```

### 4. Package the versioned artifact

```bash
python scripts/package_artifact.py \
    --version-file VERSION \
    --build-number 0 \
    --proto-dir build/proto \
    --requirements exports/requirements_export.json \
    --requirements-schema schemas/requirements_schema.json \
    --icd-export exports/icd_export.json \
    --validation-report build/reports/validation_report.json \
    --output-dir build \
    --git-sha $(git rev-parse HEAD) \
    --git-branch $(git branch --show-current)
```

### 5. Publish to Nexus (requires credentials)

```bash
export NEXUS_URL="https://nexus.internal.example.com"
export NEXUS_USER="deployer"
export NEXUS_PASS="<token>"
bash scripts/publish_to_nexus.sh build/cameo-model-artifacts-*.zip
```

---

## Cameo Macro Workflow

Systems engineers use Groovy macros inside Cameo Systems Modeler to export model data. The pipeline never touches the `.mdzip` model file directly -- it only consumes the JSON exports.

### Workflow

1. Open the model project in Cameo Systems Modeler.
2. Run **Tools > Macros > ExportRequirements** to generate `exports/requirements_export.json`.
3. Run **Tools > Macros > ExportICD** to generate `exports/icd_export.json`.
4. Review the generated JSON files in the `exports/` directory.
5. Commit both export files to Git alongside any model changes.
6. Push to trigger the CI/CD pipeline.

### Model Conventions

- **Requirements**: Must use the SysML `<<Requirement>>` stereotype with `Id`, `VerificationMethod` (ADIT: Analysis, Demonstration, Inspection, Test), and `VerificationCriteria` tagged values.
- **Interfaces**: Must use the `<<InterfaceBlock>>` stereotype. Messages are modeled as owned Classes or Signals; fields as Properties; enumerations as UML Enumerations.

See [`cameo-macro/README.md`](cameo-macro/README.md) for full installation and troubleshooting instructions.

---

## JSON Schema Documentation

Both export files are validated against JSON Schema Draft-07 definitions in the `schemas/` directory.

### Requirements Export (`requirements_export.json`)

Top-level required fields: `exportMetadata`, `requirements`

**`exportMetadata`** object:

| Field | Type | Description |
|---|---|---|
| `exportTimestamp` | string (date-time) | ISO 8601 timestamp of the export |
| `cameoVersion` | string | Cameo Systems Modeler version |
| `projectName` | string | Name of the Cameo project |
| `modelVersion` | string (semver) | Semantic version matching the `VERSION` file |

**`requirements[]`** array items (required fields):

| Field | Type | Description |
|---|---|---|
| `requirementId` | string | Human-readable ID, pattern: `SYS-REQ-001` |
| `cameoUUID` | string | Cameo internal UUID for model traceability |
| `title` | string | Short requirement title |
| `description` | string | Full requirement text |
| `verificationMethod` | enum | One of: `Analysis`, `Demonstration`, `Inspection`, `Test` |
| `verificationCriteria` | string | Specific criteria for verification |
| `priority` | enum (optional) | `Critical`, `High`, `Medium`, or `Low` |
| `parentRequirementId` | string/null (optional) | Parent requirement ID for hierarchy |
| `satisfiedBy` | string[] (optional) | Model elements that satisfy this requirement |
| `tracesTo` | string[] (optional) | Related requirement IDs |

**Business-logic validations** (beyond schema):
- No duplicate `requirementId` or `cameoUUID` values.
- `verificationCriteria` must not be empty.
- `parentRequirementId`, if specified, must reference a known requirement.

### ICD Export (`icd_export.json`)

Top-level required fields: `exportMetadata`, `interfaces`

**`interfaces[]`** array items:

| Field | Type | Description |
|---|---|---|
| `name` | string | Interface name; becomes the `.proto` file/package name |
| `description` | string (optional) | Human-readable description |
| `protoPackage` | string (optional) | Override for the proto package name |
| `messages` | array | Message definitions with `name`, `fields[]` |
| `enums` | array (optional) | Enum definitions with `name`, `values[]` |
| `services` | array (optional) | gRPC service definitions with `name`, `methods[]` |

**`messages[].fields[]`** items:

| Field | Type | Description |
|---|---|---|
| `name` | string | Field name (snake_case) |
| `type` | string | Protobuf type or reference to enum/message name |
| `fieldNumber` | integer | Proto field number (must be unique within message) |
| `repeated` | boolean (optional) | Whether the field is repeated |
| `optional` | boolean (optional) | Whether the field is optional |

**Business-logic validations** (beyond schema):
- No duplicate `fieldNumber` values within a message.
- No duplicate enum value names or numbers within an enum.

---

## Semantic Versioning Policy

The `VERSION` file contains a single semver string (`MAJOR.MINOR.PATCH`). It must be manually bumped before merging to `main`.

| Change Type | Bump | Example |
|---|---|---|
| Breaking changes to `.proto` message structure (removed fields, renumbered fields, changed types) | **MAJOR** | `1.2.0` -> `2.0.0` |
| New messages, new fields (additive), new interfaces, new requirements | **MINOR** | `1.2.0` -> `1.3.0` |
| Documentation updates, requirement text edits, metadata corrections, bug fixes in export macros | **PATCH** | `1.2.0` -> `1.2.1` |

On merge to `main`, the pipeline creates a Git tag (`v0.1.0`) and publishes the artifact. Nexus will reject uploads if the version already exists -- always bump the `VERSION` file before merging.

---

## Artifact Output Structure

The pipeline produces a zip file named `cameo-model-artifacts-{VERSION}-build.{BUILD_NUMBER}.zip` with the following contents:

```
cameo-model-artifacts-0.1.0-build.42.zip
|-- VERSION                                  # Plain-text version string
|-- manifest.json                            # Build metadata (version, git SHA, timestamps, counts)
|-- proto/
|   +-- system_comms.proto                   # Generated .proto files (one per interface)
|-- requirements/
|   |-- requirements.json                    # Requirements export
|   +-- requirements_schema.json             # Schema for downstream validation
|-- icd/
|   +-- icd_export.json                      # Raw ICD export
+-- reports/
    +-- validation_report.json               # Validation results
```

The `manifest.json` includes:

```json
{
  "artifactId": "cameo-model-artifacts",
  "version": "0.1.0",
  "buildNumber": "42",
  "gitCommitSha": "<sha>",
  "gitBranch": "main",
  "buildTimestamp": "2026-03-10T14:30:00+00:00",
  "contents": {
    "protoFileCount": 1,
    "requirementCount": 6
  }
}
```

---

## CI/CD Pipelines

### GitHub Actions (Prototype)

Defined in `.github/workflows/model-pipeline.yml`. Runs on `ubuntu-latest` with Python 3.11.

| Job | Trigger | Stages |
|---|---|---|
| `validate-and-generate` | Push/PR to `main` | Install deps, read version, validate exports exist, schema validation, generate protos, validate protos with `protoc`, package artifact, upload artifact |
| `tag-release` | Merge to `main` only | Create Git tag, create GitHub Release with the zip attached |

Artifacts (zip and validation reports) are uploaded via `actions/upload-artifact` for inspection on any run.

### Jenkins (Production)

Defined in `Jenkinsfile`. Runs on agent labeled `model-pipeline`.

| Stage | Description |
|---|---|
| Read Version | Reads and validates semver from `VERSION` file |
| Validate Exports Exist | Fails fast if export files are missing |
| Schema Validation | Runs `validate_exports.py`; archives validation report |
| Generate Proto Files | Runs `generate_protos.py` with Jinja2 templates |
| Validate Proto Files | Runs `protoc` on each generated `.proto` file |
| Package Artifact | Runs `package_artifact.py` to build the versioned zip |
| Publish to Nexus | Uploads the zip to a Nexus raw repository using credentials |
| Tag Release | (main branch only) Creates and pushes an annotated Git tag |

Pipeline options: 30-minute timeout, concurrent builds disabled, last 20 builds retained.

---

## Air-Gapped Environment Considerations

This pipeline is designed to operate in disconnected or air-gapped networks.

**Python dependencies**: Pre-download wheels for `jinja2`, `jsonschema`, `markupsafe`, and their transitive dependencies. Host them on an internal PyPI mirror or install from a vendored directory:

```bash
pip install --no-index --find-links ./vendor -r scripts/requirements.txt
```

**protoc**: Obtain the `protobuf-compiler` package for your target OS and make it available on the build agent. No network access is required at runtime.

**Nexus Repository**: Must be reachable from the build agent on the internal network. Configure `NEXUS_URL` to point to the internal instance.

**Container images**: If running Jenkins in containers, pre-pull and push images to an internal registry. The pipeline does not pull external container images at runtime.

**GitHub Actions**: The GitHub Actions workflow is intended as a prototype for development environments with internet access. In production air-gapped deployments, use the Jenkins pipeline exclusively.

---

## Integration with product-pipeline

This repository is the **upstream model source**. The [`product-pipeline`](../product-pipeline) repository is the **downstream consumer** that builds deployable software artifacts.

The integration flow:

1. **cameo-model-pipeline** validates, generates, packages, and publishes `cameo-model-artifacts-{VERSION}.zip` to Nexus.
2. **product-pipeline** pulls the versioned artifact from Nexus by specifying the model version it depends on.
3. The product pipeline extracts the `.proto` files and uses `protoc` to generate language-specific bindings (e.g., C++, Java, Python).
4. The generated bindings are compiled into the product software alongside the requirements traceability data.

This decoupling ensures that model changes are versioned and published independently of software builds. The product pipeline pins to a specific model artifact version, providing reproducibility and auditability.

---

## Contributing

### Branching and Workflow

1. Create a feature branch from `main`.
2. If modifying the Cameo model, run the export macros and commit the updated JSON files in `exports/`.
3. If adding new interfaces or requirements, ensure the JSON exports conform to the schemas in `schemas/`.
4. Bump the `VERSION` file according to the [versioning policy](#semantic-versioning-policy).
5. Open a pull request targeting `main`. The CI pipeline will validate exports and generate protos automatically.
6. After review and merge, the pipeline tags the release and publishes to Nexus.

### Development Guidelines

- **Do not manually edit files in `exports/`**. These are machine-generated by the Cameo macros. Manual edits will diverge from the model and cause traceability issues.
- **Do not manually edit files in `build/`**. The build directory is ephemeral and regenerated by the pipeline.
- **Schema changes** (files in `schemas/`) must be backward-compatible or coordinated with a MAJOR version bump.
- **Template changes** (`templates/proto_template.j2`) affect all generated `.proto` files. Test locally with `generate_protos.py` before committing.
- **Script changes** should be tested locally using the [Quick Start](#quick-start) steps before pushing.

### Adding a New Export Type

1. Create the Groovy macro in `cameo-macro/` and document it in `cameo-macro/README.md`.
2. Add a JSON Schema in `schemas/`.
3. Add validation logic to `scripts/validate_exports.py`.
4. If the export produces proto-generatable data, add a Jinja2 template in `templates/` and update `scripts/generate_protos.py`.
5. Update `scripts/package_artifact.py` to include the new export in the zip.
6. Update the pipeline stages in both `Jenkinsfile` and `.github/workflows/model-pipeline.yml`.
