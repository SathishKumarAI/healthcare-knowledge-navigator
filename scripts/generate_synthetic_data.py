"""Synthetic clinical corpus generator (the code used to produce data/).

Generates plausible-looking but ENTIRELY FICTIONAL clinical reference documents so the
project runs out of the box without any real or copyrighted medical content. Values are
illustrative only and must not be used for care.

Usage:
    python scripts/generate_synthetic_data.py            # writes the default corpus
    python scripts/generate_synthetic_data.py --seed 7   # reproducible variation

Deterministic given a seed: no LLM, no network — just templates + a seeded RNG.
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DISCLAIMER = (
    "> SYNTHETIC SAMPLE — fictional content for demo/testing only. Not medical advice.\n"
)


def hypertension_guideline(rng: random.Random) -> tuple[str, str]:
    target = rng.choice(["130/80", "135/85", "140/90"])
    body = f"""# Hypertension Management Guideline (synthetic sample)

{DISCLAIMER}
## Diagnosis
Hypertension is diagnosed when office blood pressure is persistently at or above
{target} mmHg across two separate visits.

## First-line therapy
- Lifestyle: reduced sodium intake, weight loss, regular aerobic activity.
- Pharmacologic first-line options: a thiazide-type diuretic, an ACE inhibitor, an
  angiotensin receptor blocker (ARB), or a calcium channel blocker.
- ACE inhibitors and ARBs should NOT be combined (risk of hyperkalemia and renal injury).

## Monitoring
- Recheck blood pressure in 4 weeks after starting or changing therapy.
- Check serum potassium and creatinine within 2-4 weeks of starting an ACE inhibitor or ARB.

## Special populations
- In pregnancy, ACE inhibitors and ARBs are contraindicated.
"""
    return "hypertension_guideline.md", body


def metformin_drug_info(rng: random.Random) -> tuple[str, str]:
    egfr = rng.choice([30, 30, 45])
    body = f"""# Metformin — Drug Information (synthetic sample)

{DISCLAIMER}
## Indication
First-line oral agent for type 2 diabetes mellitus.

## Dosing
- Start 500 mg once daily with the evening meal; titrate weekly as tolerated.
- Maximum 2000 mg/day in divided doses.

## Contraindications
- eGFR below {egfr} mL/min/1.73m^2.
- Acute metabolic acidosis, including diabetic ketoacidosis.
- Conditions predisposing to lactic acidosis.

## Cautions / monitoring
- Hold before and 48 hours after iodinated contrast in at-risk patients.
- Monitor renal function at least annually, more often if eGFR is reduced.
- Most common adverse effects are gastrointestinal and often transient.
"""
    return "metformin_drug_info.md", body


def asthma_management(rng: random.Random) -> tuple[str, str]:
    body = """# Asthma Management Summary (synthetic sample)

{disc}
## Stepwise therapy
- Step 1: as-needed low-dose inhaled corticosteroid (ICS)-formoterol.
- Step 2: daily low-dose ICS.
- Step 3: low-dose ICS-LABA combination.
- Escalate if symptoms are uncontrolled despite good adherence and technique.

## Exacerbation
- Short-acting beta-agonist for acute relief.
- A short course of oral corticosteroids for moderate-to-severe exacerbations.

## Review
- Reassess control, inhaler technique, and adherence at every visit.
- Step down therapy after 3 months of sustained control.
""".format(disc=DISCLAIMER)
    return "asthma_management.md", body


def study_abstract(rng: random.Random) -> tuple[str, str]:
    n = rng.choice([842, 1206, 1530])
    reduction = rng.choice([18, 22, 27])
    body = f"""# Study Abstract: SYNTH-HTN Trial (synthetic sample)

{DISCLAIMER}
## Design
Randomized, double-blind, placebo-controlled trial of a fictional antihypertensive,
"compound SYN-1", in {n} adults with stage 2 hypertension over 24 weeks.

## Results
- Mean systolic blood pressure fell by {reduction} mmHg more than placebo (p < 0.001).
- No significant difference in serious adverse events between arms.
- Discontinuation due to dizziness was higher in the treatment arm (6% vs 3%).

## Conclusion
Compound SYN-1 reduced blood pressure versus placebo with an acceptable safety profile
in this synthetic study population.
"""
    return "synth_htn_trial_abstract.md", body


GENERATORS = [
    hypertension_guideline,
    metformin_drug_info,
    asthma_management,
    study_abstract,
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    rng = random.Random(args.seed)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for gen in GENERATORS:
        name, body = gen(rng)
        (DATA_DIR / name).write_text(body, encoding="utf-8")
        print(f"wrote data/{name}")


if __name__ == "__main__":
    main()
