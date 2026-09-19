window.PORTAL_CONFIG = {
  institution: "Bataan Peninsula State University",
  campus: "Balanga Campus",
  college: "College of Business and Accountancy",
  accreditation: "AACCUP Level IV",
  portalMode: "Role-based",
  secureWorkspaceBase: "https://bpsu-evidence-portal-production.up.railway.app",
  publicEvidenceApi: "https://bpsu-evidence-portal-production.up.railway.app/api/public/evidence",
  programs: {
    BSA: "Bachelor of Science in Accountancy",
    BSBA: "Bachelor of Science in Business Administration"
  },
  areaTitles: {
    "Area I": "RESEARCH",
    "Area II": "PERFORMANCE OF GRADUATES",
    "Area III": "EXTENSION",
    "Area IV": "INTERNATIONALIZATION",
    "Area V": "PLANNING PROCESS"
  }
};

// Fallback only. Live published records are loaded from the portal API.
window.EVIDENCE_DATA = [];
