/**
 * ExportRequirements.groovy
 *
 * Cameo Systems Modeler macro that exports all requirements with their
 * verification criteria to a structured JSON file consumable by the
 * model pipeline.
 *
 * Usage: Run from Cameo's Macro Engine (Tools > Macros > ExportRequirements)
 *        or add to a custom toolbar action for one-click export.
 *
 * Output: exports/requirements_export.json
 *
 * Prerequisites:
 *   - Cameo Requirements Modeler Plugin must be installed
 *   - Model must use SysML Requirement stereotypes
 *   - Verification method must be set as a tagged value (INCOSE ADIT)
 */

import com.nomagic.magicdraw.core.Application
import com.nomagic.magicdraw.core.Project
import com.nomagic.uml2.ext.magicdraw.classes.mdkernel.Class
import com.nomagic.uml2.ext.magicdraw.classes.mdkernel.Element
import com.nomagic.uml2.ext.jmi.helpers.StereotypesHelper
import groovy.json.JsonBuilder
import java.time.Instant

// ─── Configuration ───
def OUTPUT_DIR = "exports"
def OUTPUT_FILE = "${OUTPUT_DIR}/requirements_export.json"
def VERSION_FILE = "VERSION"

// ─── Helpers ───

def getProject() {
    return Application.getInstance().getProject()
}

def getVersion() {
    def versionFile = new File(getProject().getDirectory(), VERSION_FILE)
    if (versionFile.exists()) {
        return versionFile.text.trim()
    }
    return "0.0.0"
}

def getTaggedValue(Element element, String stereotypeName, String tagName) {
    def stereotype = StereotypesHelper.getStereotype(getProject(), stereotypeName)
    if (stereotype == null) return null

    def values = StereotypesHelper.getStereotypePropertyValue(element, stereotype, tagName)
    if (values != null && !values.isEmpty()) {
        return values[0]?.toString()
    }
    return null
}

def isRequirement(Element element) {
    // Check if element has the SysML Requirement stereotype
    def reqStereotype = StereotypesHelper.getStereotype(getProject(), "Requirement")
    if (reqStereotype == null) {
        // Try the full qualified name
        reqStereotype = StereotypesHelper.getStereotype(getProject(), "SysML::Requirements::Requirement")
    }
    return reqStereotype != null && StereotypesHelper.hasStereotype(element, reqStereotype)
}

def getRequirementId(Element element) {
    // Try tagged value first, then fall back to name-based ID
    def id = getTaggedValue(element, "Requirement", "Id")
    if (id == null || id.isEmpty()) {
        id = getTaggedValue(element, "Requirement", "id")
    }
    if (id == null || id.isEmpty()) {
        // Fall back to element name
        id = element.getName()
    }
    return id
}

def getVerificationCriteria(Element element, String reqId) {
    // INCOSE ADIT: Analysis, Demonstration, Inspection, Test
    // Reads the existing tagged values and wraps them in the array format.
    def method = getTaggedValue(element, "Requirement", "VerificationMethod")
    if (method == null) {
        method = getTaggedValue(element, "VerifyRequirement", "method")
    }
    method = method ?: "Test" // Default to Test if not specified

    def criteria = getTaggedValue(element, "Requirement", "VerificationCriteria")
    if (criteria == null) {
        criteria = getTaggedValue(element, "Requirement", "verificationCriteria")
    }
    criteria = criteria ?: ""

    def vcs = [[
        verificationCriteriaId: "${reqId}-VC-${String.format('%02d', 1)}",
        method                : method,
        criteria              : criteria,
    ]]
    return vcs
}

def getPriority(Element element) {
    def priority = getTaggedValue(element, "Requirement", "Priority")
    if (priority == null) {
        priority = getTaggedValue(element, "Requirement", "priority")
    }
    return priority
}

def getDescription(Element element) {
    // Get the requirement text (often stored in the "Text" tagged value)
    def text = getTaggedValue(element, "Requirement", "Text")
    if (text == null || text.isEmpty()) {
        text = getTaggedValue(element, "Requirement", "text")
    }
    if (text == null || text.isEmpty()) {
        // Fall back to the documentation/comment
        def doc = element.getOwnedComment()
        if (doc != null && !doc.isEmpty()) {
            text = doc.collect { it.getBody() }.join("\n")
        }
    }
    return text ?: element.getName()
}

def getSatisfiedBy(Element element) {
    // Find elements connected via «satisfy» relationships
    def satisfiedBy = []
    // This is simplified — actual implementation depends on model structure
    // In Cameo, satisfy relationships are Abstraction dependencies with «Satisfy» stereotype
    return satisfiedBy
}

def getTracesTo(Element element) {
    // Find requirements connected via «trace» or «deriveReqt» relationships
    def tracesTo = []
    return tracesTo
}

def getParentRequirementId(Element element) {
    def owner = element.getOwner()
    if (owner != null && isRequirement(owner)) {
        return getRequirementId(owner)
    }
    return null
}

// ─── Main Export Logic ───

def collectRequirements(Element rootElement, List results) {
    if (isRequirement(rootElement)) {
        def reqData = [
            requirementId      : getRequirementId(rootElement),
            cameoUUID          : rootElement.getID(),
            title              : rootElement.getName(),
            description        : getDescription(rootElement),
            priority           : getPriority(rootElement),
            status             : getTaggedValue(rootElement, "Requirement", "Status") ?: "Draft",
            parentRequirementId: getParentRequirementId(rootElement),
            verificationCriteria: getVerificationCriteria(rootElement, getRequirementId(rootElement)),
            satisfiedBy        : getSatisfiedBy(rootElement),
            tracesTo           : getTracesTo(rootElement),
        ]
        results.add(reqData)
    }

    // Recurse into owned elements
    for (Element child : rootElement.getOwnedElement()) {
        collectRequirements(child, results)
    }
}

// ─── Execute ───

def project = getProject()
if (project == null) {
    Application.getInstance().getGUILog().showError("No project is open")
    return
}

def requirements = []
collectRequirements(project.getPrimaryModel(), requirements)

def export = [
    exportMetadata: [
        exportTimestamp: Instant.now().toString(),
        cameoVersion  : Application.getInstance().getVersion().toString(),
        projectName   : project.getName(),
        modelVersion  : getVersion(),
    ],
    requirements: requirements
]

// Write output
def outputDir = new File(project.getDirectory(), OUTPUT_DIR)
outputDir.mkdirs()
def outputFile = new File(project.getDirectory(), OUTPUT_FILE)

def json = new JsonBuilder(export).toPrettyString()
outputFile.text = json

Application.getInstance().getGUILog().showMessage(
    "Exported ${requirements.size()} requirements to ${OUTPUT_FILE}"
)
