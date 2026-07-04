// Domain config — the only file that changes between the three projects.
export const siteConfig = {
  name: "Healthcare Knowledge Navigator",
  shortName: "Knowledge Navigator",
  tagline:
    "Ask clinical questions about the reference documents. Every answer cites the source it came from.",
  domainLabel: "Healthcare · Clinical",
  accent: "#16a34a", // green
  disclaimer:
    "Informational support for professionals — not medical advice. Sample data is synthetic.",
  apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000",
  githubRepo:
    process.env.NEXT_PUBLIC_GITHUB_REPO ?? "SathishKumarAI/healthcare-knowledge-navigator",
  apiKey: process.env.NEXT_PUBLIC_API_KEY ?? "",
  examples: [
    "What are the first-line options for hypertension?",
    "What is the eGFR contraindication for metformin?",
    "What is step 1 therapy for asthma?",
    "Are ACE inhibitors safe in pregnancy?",
  ],
};
