window.PORTAL_CONFIG = {
  institution: "Bataan Peninsula State University",
  campus: "Balanga Campus",
  college: "College of Business and Accountancy",
  accreditation: "AACCUP Level IV",
  portalMode: "Read-only",
  lastUpdated: "2026-09-18",
  areaTitles: {
    "Area I": "Official area title to be configured",
    "Area II": "Official area title to be configured",
    "Area III": "Official area title to be configured",
    "Area IV": "Official area title to be configured",
    "Area V": "Official area title to be configured",
    "Area VI": "Official area title to be configured",
    "Area VII": "Official area title to be configured",
    "Area VIII": "Official area title to be configured",
    "Area IX": "Official area title to be configured",
    "Area X": "Official area title to be configured"
  }
};

/*
  PUBLISHING RULE:
  Only records intentionally added to EVIDENCE_DATA are displayed.
  Keep this file limited to evidence approved for external/accreditor viewing.

  Example record (remove the surrounding comment to use as a model):
  {
    id: "BPSU-CBA-L4-AI-0001-v1",
    docCode: "BPSU-CBA-L4-AI-0001",
    version: 1,
    title: "Example Approved Evidence",
    description: "Short description for accreditors.",
    area: "Area I",
    criterion: "I.1",
    docType: "Report",
    academicYear: "2025-2026",
    tags: ["example", "approved"],
    publishedDate: "2026-09-18",
    owner: "College of Business and Accountancy",
    fileUrl: "documents/example-approved-evidence.pdf"
  }
*/
window.EVIDENCE_DATA = [];
