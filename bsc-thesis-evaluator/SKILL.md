---
name: bsc-thesis-evaluator
description: >
  Evaluates a final year BSc project thesis uploaded by a student and produces a scored
  feedback report as a Word document. Use this skill whenever a student uploads or pastes
  their project thesis or dissertation and asks for feedback, evaluation, review, a score,
  or wants to know what to improve. Also triggers when someone says "check my project",
  "evaluate my thesis", "review my final year project", "give me a score on my work",
  or uploads a .docx/.pdf and asks what to fix. The skill reads every chapter, scores
  the work out of 50, and produces a personalised .docx feedback report telling the
  student exactly what to fix.
---

# BSc Thesis Evaluator

Evaluate a final year BSc project thesis uploaded by a student. Produce a scored,
personalised Word document feedback report (out of 50) with specific, actionable
improvement notes for each chapter and writing quality area.

---

## Overview

**Target document**: BSc final year project (50–70 pages typical, may be longer)  
**Output**: Personalised `.docx` feedback report  
**Scoring**: 50 points total across 10 criteria (5 points each)  
**Tone**: Direct, warm, personalised — address the student by name if known, otherwise "you"

---

## Step 1 — Get the thesis

The student must upload their thesis file (PDF or DOCX) or paste the full text.

If no file is present, ask:
> "Please upload your project file (PDF or Word document) so I can evaluate it."

Once the file is present, extract its full text using the appropriate method:
- DOCX: `extract-text /mnt/user-data/uploads/<filename>`
- PDF: read the SKILL.md at `/mnt/skills/public/pdf-reading/SKILL.md` and follow it

---

## Step 2 — Extract student name and project title

Scan the title page or first page for:
- Student name (use throughout the report for personalisation)
- Project title
- Department / institution (if visible)

If no name is found, use "you" / "your work" throughout.

---

## Step 3 — Read and evaluate all chapters

Read the full extracted text carefully. Map chapter headings to the evaluation rubric below.
If chapter boundaries are unclear, infer from heading patterns (Chapter 1 / 1.0 Introduction, etc.).

---

## Evaluation Rubric (50 points — 5 points each criterion)

Score each criterion 0–5:

| Points | Meaning |
|--------|---------|
| 5 | Excellent — meets all requirements with no significant gaps |
| 4 | Good — meets most requirements, minor issues only |
| 3 | Adequate — meets some requirements, clear gaps |
| 2 | Weak — attempts the requirement but falls significantly short |
| 1 | Very weak — barely present or largely incorrect |
| 0 | Absent — missing entirely |

### C1 — Introduction Quality (5 pts)
- At least 5 paragraphs
- Each paragraph: topic sentence + 3–5 sentences minimum + transition/closing
- Funnel structure (broad → specific)
- Each claim-making paragraph has at least one citation
- Academic tone throughout

### C2 — Statement of the Problem (5 pts)
- Presents a genuine, specific research gap (not just a topic)
- Problem is grounded in and supported by existing literature with citations
- Problem is clearly stated — reader can summarise it in one sentence
- Logical argument: what is known → what is missing → why it matters

### C3 — Aims and Objectives (5 pts)
- Aim clearly stated (broad purpose)
- Objectives use action verbs and are specific, measurable, feasible
- Every objective maps directly to an aspect of the stated problem
- No objective is peripheral or unaddressed in results

### C4 — Literature Review (5 pts)
- Covers all thematic areas required by objectives
- Goes beyond description — compares, contrasts, or critiques studies
- At least ~15 pages (for a 50–70 page project this is proportionate)
- Uses figures/tables where comparisons or models need visual representation
- Ends with a clear research gap statement

### C5 — Methodology Reporting (5 pts)
- Research design explicitly stated and justified
- Population, sample, sampling technique clearly described (if empirical)
- Data collection instrument described in enough detail to replicate
- Analysis techniques named with tools/software identified and justified
- Validity/reliability measures addressed

### C6 — Results Completeness (5 pts)
- Results presented for every objective stated in Chapter One
- Results clearly presented (tables, figures, statistics, or themes)
- All tables/figures labelled, referenced in text, and interpreted
- No objective is left without a corresponding result section

### C7 — Discussion and Evaluation (5 pts)
- Discussion interprets findings — not just restates results
- Connects findings back to literature reviewed in Chapter Two
- Evaluation uses a recognised method (user testing, benchmarking, stats, expert review, etc.)
- Claims of significance backed by evidence (statistical or qualitative)

### C8 — Conclusion Chapter (5 pts)
- Summarises key findings and answers the research aim
- States the contribution of the study clearly
- At least 2 substantive limitations stated
- At least 2 specific, actionable recommendations for future work

### C9 — Paragraph and Citation Quality (5 pts)
- All paragraphs: minimum 3 sentences each (flag violations)
- All paragraphs in Chapters 1 and 2 that make factual/conceptual claims have a citation
- Academic register throughout (no colloquial language, inappropriate first-person)
- No orphan paragraphs (single-sentence stubs not used as deliberate transitions)

### C10 — References Quality (5 pts)
- References formatted consistently in one style (APA, IEEE, Harvard, etc.)
- At least 70% of references published between 2021–2026
- No orphan citations (cited in text but missing from reference list)
- No bare URL references or non-academic sources used as primary evidence

---

## Step 4 — Run the report generation script

After completing your evaluation, call:

```bash
node /home/claude/bsc-thesis-evaluator/scripts/generate_report.js \
  --name "<student_name>" \
  --title "<project_title>" \
  --scores "C1=X,C2=X,C3=X,C4=X,C5=X,C6=X,C7=X,C8=X,C9=X,C10=X" \
  --feedback-file /tmp/thesis_feedback.json \
  --output /mnt/user-data/outputs/ThesisReport_<lastname>.docx
```

Before running the script, write a JSON file at `/tmp/thesis_feedback.json` containing your findings (see format below), then run the script.

### Feedback JSON format

```json
{
  "student_name": "Amaka Okafor",
  "project_title": "Full project title here",
  "scores": {
    "C1": 4, "C2": 3, "C3": 4, "C4": 2,
    "C5": 3, "C6": 4, "C7": 3, "C8": 2,
    "C9": 3, "C10": 2
  },
  "feedback": {
    "C1": {
      "strengths": ["Good funnel structure — moves from broad to specific", "Paragraphs are well-developed"],
      "issues": ["Paragraph 3 has only 2 sentences — expand to at least 3", "Paragraph 5 makes a claim about the field without a citation"]
    },
    "C2": {
      "strengths": ["Problem is specific and researchable"],
      "issues": ["The problem is not sufficiently grounded in literature — only 1 citation supports it", "Missing logical argument: what is known → gap → why it matters"]
    },
    "C3": {
      "strengths": ["Objectives use action verbs and are clearly written"],
      "issues": ["Objective 4 ('to review related work') does not map to any result in Chapter Four — revise or remove it"]
    },
    "C4": {
      "strengths": ["Good thematic coverage of the core concepts"],
      "issues": ["No comparison table despite comparing 5 tools — add a table", "Chapter ends without identifying the research gap", "Estimated at ~10 pages — should be closer to 15 for a BSc project of this scope"]
    },
    "C5": {
      "strengths": ["Research design is clearly stated"],
      "issues": ["Sample size is given (120) but no justification for why 120 was chosen", "Cronbach alpha or pilot test for the questionnaire is not reported"]
    },
    "C6": {
      "strengths": ["Most objectives have corresponding results"],
      "issues": ["Objective 3 has no result section — this must be addressed before submission"]
    },
    "C7": {
      "strengths": ["Discussion section is present"],
      "issues": ["Discussion restates results without interpreting them — explain what the findings MEAN", "No reference back to Chapter Two studies — compare your findings to prior work"]
    },
    "C8": {
      "strengths": ["Limitations section is present and substantive"],
      "issues": ["Conclusion introduces new information (the cost estimate) not discussed in earlier chapters — remove it", "Only one recommendation for future work — add at least one more specific recommendation"]
    },
    "C9": {
      "strengths": ["Writing is generally academic and formal"],
      "issues": ["Chapter Two, paragraph 4 has only 1 sentence — expand it", "Several paragraphs in Chapter Two make claims without citations (e.g., 'Many studies have shown...' — which studies?)"]
    },
    "C10": {
      "strengths": ["References are formatted in APA style consistently"],
      "issues": ["Only 48% of references are from 2021–2026 — the standard requires 70%. Add more recent sources.", "3 in-text citations (Adebayo, 2019; Nwosu, 2020; Smith, 2021) are missing from the reference list"]
    }
  },
  "overall_summary": "Your project shows a solid foundation and real effort. The main areas to focus on are strengthening your literature review, making sure every objective has a result, and updating your references to include more recent work."
}
```

---

## Step 5 — Present the report

After the script runs successfully, call `present_files` with the output path.

Then tell the student their total score and the top 3 things to fix before resubmission.

---

## Script setup note

The report generation script lives at `/home/claude/bsc-thesis-evaluator/scripts/generate_report.js`.
If it is not present (first run after install), write it fresh using the template in `scripts/generate_report.js` in this skill package before executing it.
