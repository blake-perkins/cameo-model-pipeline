/**
 * ExportICD.groovy
 *
 * Cameo Systems Modeler macro that exports ICD (Interface Control Document)
 * definitions to a structured JSON file for protobuf generation.
 *
 * Usage: Run from Cameo's Macro Engine (Tools > Macros > ExportICD)
 *        or add to a custom toolbar action for one-click export.
 *
 * Output: exports/icd_export.json
 *
 * This macro traverses the model looking for:
 *   - «interface» stereotyped blocks (SysML InterfaceBlocks)
 *   - Flow properties and their types
 *   - Enumerations
 *   - Signal/message definitions
 *
 * The output JSON follows the icd_schema.json contract and is consumed
 * by generate_protos.py to produce .proto files.
 */

import com.nomagic.magicdraw.core.Application
import com.nomagic.magicdraw.core.Project
import com.nomagic.uml2.ext.magicdraw.classes.mdkernel.*
import com.nomagic.uml2.ext.jmi.helpers.StereotypesHelper
import groovy.json.JsonBuilder
import java.time.Instant

// ─── Configuration ───
def OUTPUT_DIR = "exports"
def OUTPUT_FILE = "${OUTPUT_DIR}/icd_export.json"

// ─── Helpers ───

def getProject() {
    return Application.getInstance().getProject()
}

def isInterfaceBlock(Element element) {
    def stereotype = StereotypesHelper.getStereotype(getProject(), "InterfaceBlock")
    if (stereotype == null) {
        stereotype = StereotypesHelper.getStereotype(getProject(), "SysML::PortsAndFlows::InterfaceBlock")
    }
    return stereotype != null && StereotypesHelper.hasStereotype(element, stereotype)
}

def isSignal(Element element) {
    return element instanceof com.nomagic.uml2.ext.magicdraw.commonbehaviors.mdcommunications.Signal
}

def isEnumeration(Element element) {
    return element instanceof Enumeration
}

def mapToProtoType(String umlType) {
    def typeMap = [
        "Integer": "int32", "Int32": "int32", "int": "int32",
        "Long": "int64", "Int64": "int64",
        "UInt32": "uint32", "UInt64": "uint64",
        "Float": "float", "Double": "double",
        "Boolean": "bool", "bool": "bool",
        "String": "string", "Text": "string",
        "Bytes": "bytes", "Binary": "bytes",
        "byte": "bytes",
    ]
    return typeMap.getOrDefault(umlType, umlType)
}

// ─── Extract Messages from Interface Blocks ───

def extractMessages(Element interfaceBlock) {
    def messages = []
    int fieldCounter = 1

    for (Element owned : interfaceBlock.getOwnedElement()) {
        if (owned instanceof Class || isSignal(owned)) {
            def fields = []
            int fn = 1
            for (Element prop : owned.getOwnedElement()) {
                if (prop instanceof Property) {
                    def typeName = prop.getType()?.getName() ?: "string"
                    fields.add([
                        name       : prop.getName(),
                        type       : mapToProtoType(typeName),
                        fieldNumber: fn++,
                        repeated   : prop.isMultivalued(),
                        description: prop.getOwnedComment()?.collect { it.getBody() }?.join(" ") ?: "",
                    ])
                }
            }
            if (!fields.isEmpty()) {
                messages.add([
                    name       : owned.getName(),
                    description: owned.getOwnedComment()?.collect { it.getBody() }?.join(" ") ?: "",
                    fields     : fields,
                ])
            }
        }
    }
    return messages
}

// ─── Extract Enumerations ───

def extractEnums(Element container) {
    def enums = []
    for (Element owned : container.getOwnedElement()) {
        if (isEnumeration(owned)) {
            def values = []
            int num = 0
            for (def literal : ((Enumeration) owned).getOwnedLiteral()) {
                values.add([
                    name  : literal.getName(),
                    number: num++,
                ])
            }
            enums.add([
                name       : owned.getName(),
                description: owned.getOwnedComment()?.collect { it.getBody() }?.join(" ") ?: "",
                values     : values,
            ])
        }
    }
    return enums
}

// ─── Collect Interfaces ───

def collectInterfaces(Element element, List results) {
    if (isInterfaceBlock(element)) {
        def iface = [
            name       : element.getName(),
            description: element.getOwnedComment()?.collect { it.getBody() }?.join(" ") ?: "",
            messages   : extractMessages(element),
            enums      : extractEnums(element),
        ]
        if (!iface.messages.isEmpty() || !iface.enums.isEmpty()) {
            results.add(iface)
        }
    }

    // Recurse
    for (Element child : element.getOwnedElement()) {
        collectInterfaces(child, results)
    }
}

// ─── Execute ───

def project = getProject()
if (project == null) {
    Application.getInstance().getGUILog().showError("No project is open")
    return
}

def interfaces = []
collectInterfaces(project.getPrimaryModel(), interfaces)

def export = [
    exportMetadata: [
        exportTimestamp: Instant.now().toString(),
        cameoVersion  : Application.getInstance().getVersion().toString(),
        projectName   : project.getName(),
    ],
    interfaces: interfaces
]

// Write output
def outputDir = new File(project.getDirectory(), OUTPUT_DIR)
outputDir.mkdirs()
def outputFile = new File(project.getDirectory(), OUTPUT_FILE)

def json = new JsonBuilder(export).toPrettyString()
outputFile.text = json

Application.getInstance().getGUILog().showMessage(
    "Exported ${interfaces.size()} interface(s) to ${OUTPUT_FILE}"
)
