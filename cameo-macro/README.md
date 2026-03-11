# Cameo Export Macros

These Groovy macros extract ICD definitions and requirements from your Cameo Systems Modeler project into structured JSON files that the pipeline consumes.

## Prerequisites

- Cameo Systems Modeler (2022x or later)
- Cameo Requirements Modeler Plugin (for requirements export)
- SysML profile applied to your model

## Installation

1. Open Cameo Systems Modeler
2. Go to **Tools > Macros > Organize Macros**
3. Click **Add** and select `ExportICD.groovy`
4. Click **Add** again and select `ExportRequirements.groovy`
5. (Optional) Add both macros to a custom toolbar for one-click access

## Usage

### Exporting Requirements

1. Open your model project
2. Go to **Tools > Macros > ExportRequirements**
3. The macro will export all requirements to `exports/requirements_export.json`
4. A confirmation dialog will show how many requirements were exported

### Exporting ICD

1. Open your model project
2. Go to **Tools > Macros > ExportICD**
3. The macro will export all interface blocks to `exports/icd_export.json`
4. A confirmation dialog will show how many interfaces were exported

### After Exporting

1. Review the generated JSON files in the `exports/` directory
2. Commit both files to Git along with any model changes
3. Push to trigger the pipeline

## Model Conventions

For the macros to work correctly, your model should follow these conventions:

### Requirements
- Use the SysML `<<Requirement>>` stereotype
- Set the `Id` tagged value (e.g., `SYS-REQ-001`)
- Set the `VerificationMethod` tagged value to one of: `Analysis`, `Demonstration`, `Inspection`, `Test`
- Set the `VerificationCriteria` tagged value with the verification description
- Optionally set `Priority`: `Critical`, `High`, `Medium`, `Low`

### ICD / Interfaces
- Use `<<InterfaceBlock>>` stereotype for interface definitions
- Define messages as owned Classes or Signals within the interface block
- Define fields as Properties with appropriate types
- Define enumerations as UML Enumerations within the interface block

## Troubleshooting

- **"No requirements found"**: Ensure your requirements have the `<<Requirement>>` stereotype applied
- **"No interfaces found"**: Ensure your ICD blocks have the `<<InterfaceBlock>>` stereotype
- **Missing verification method**: Requirements without a `VerificationMethod` tagged value will default to `Test`
