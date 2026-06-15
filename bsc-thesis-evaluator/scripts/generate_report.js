#!/usr/bin/env node
/**
 * BSc Thesis Evaluator — Report Generator
 * Reads a feedback JSON file and produces a personalised .docx report
 *
 * Usage:
 *   node generate_report.js --feedback-file /tmp/thesis_feedback.json --output /mnt/user-data/outputs/report.docx
 */

const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
  LevelFormat, PageNumber, NumberFormat, VerticalAlign
} = require('docx');
const fs = require('fs');
const path = require('path');

// ─── Parse args ──────────────────────────────────────────────────────────────
const args = process.argv.slice(2);
const get = (flag) => { const i = args.indexOf(flag); return i !== -1 ? args[i + 1] : null; };

const feedbackFile = get('--feedback-file');
const outputFile   = get('--output') || '/mnt/user-data/outputs/ThesisEvaluationReport.docx';

if (!feedbackFile || !fs.existsSync(feedbackFile)) {
  console.error('❌  --feedback-file not found:', feedbackFile);
  process.exit(1);
}

const data = JSON.parse(fs.readFileSync(feedbackFile, 'utf8'));

const studentName  = data.student_name || 'Student';
const firstName    = studentName.split(' ')[0];
const projectTitle = data.project_title || 'Final Year Project';
const scores       = data.scores || {};
const feedback     = data.feedback || {};
const overallNote  = data.overall_summary || '';

// ─── Score totals ─────────────────────────────────────────────────────────────
const CRITERIA = {
  C1:  'Introduction Quality',
  C2:  'Statement of the Problem',
  C3:  'Aims and Objectives',
  C4:  'Literature Review',
  C5:  'Methodology Reporting',
  C6:  'Results Completeness',
  C7:  'Discussion and Evaluation',
  C8:  'Conclusion Chapter',
  C9:  'Paragraph and Citation Quality',
  C10: 'References Quality',
};

const CHAPTER_MAP = {
  C1: 'Chapter One', C2: 'Chapter One', C3: 'Chapter One',
  C4: 'Chapter Two',
  C5: 'Chapter Three',
  C6: 'Chapter Four', C7: 'Chapter Four',
  C8: 'Chapter Five',
  C9: 'Writing Quality', C10: 'Writing Quality',
};

const total = Object.values(scores).reduce((s, v) => s + (Number(v) || 0), 0);
const maxScore = 50;
const pct = Math.round((total / maxScore) * 100);

function grade(t) {
  if (t >= 43) return { label: 'Distinction', color: '1D6F42' };
  if (t >= 35) return { label: 'Merit',       color: '2E5496' };
  if (t >= 25) return { label: 'Pass',         color: '7F6000' };
  return             { label: 'Below Standard', color: 'C00000' };
}
const gradeInfo = grade(total);

// ─── Helpers ──────────────────────────────────────────────────────────────────
const TEAL   = '1F5C8B';
const DARK   = '1A1A2A';
const GREY   = '555555';
const RED    = 'C00000';
const GREEN  = '1D6F42';
const AMBER  = '7F6000';
const WHITE  = 'FFFFFF';
const LBLUE  = 'EEF4FB';
const LGREEN = 'EAF7EC';
const LRED   = 'FFF0F0';
const LGREY  = 'F5F5F5';

const bdr = (c = 'CCCCCC') => ({ style: BorderStyle.SINGLE, size: 1, color: c });
const borders = (c) => ({ top: bdr(c), bottom: bdr(c), left: bdr(c), right: bdr(c) });
const noBorders = { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE } };

function p(runs, opts = {}) {
  return new Paragraph({
    alignment: AlignmentType.LEFT,
    spacing: { before: opts.before ?? 80, after: opts.after ?? 100, line: opts.line ?? 340 },
    ...opts,
    children: Array.isArray(runs) ? runs : [runs],
  });
}

function run(text, opts = {}) {
  return new TextRun({ text, size: opts.size ?? 22, font: opts.font ?? 'Arial', ...opts });
}

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 400, after: 160 },
    children: [run(text, { size: 28, bold: true, color: TEAL })]
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 280, after: 120 },
    children: [run(text, { size: 24, bold: true, color: TEAL })]
  });
}

function sectionLine() {
  return new Paragraph({
    spacing: { before: 160, after: 160 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: 'CCCCCC', space: 1 } },
    children: [run('')]
  });
}

function spacer(n = 1) {
  return Array.from({ length: n }, () =>
    new Paragraph({ spacing: { before: 40, after: 40 }, children: [run('')] })
  );
}

function scoreBar(score, max = 5) {
  const filled = '█'.repeat(score);
  const empty  = '░'.repeat(max - score);
  const color  = score >= 4 ? GREEN : score >= 3 ? AMBER : RED;
  return [
    run(filled, { size: 20, font: 'Courier New', color }),
    run(empty,  { size: 20, font: 'Courier New', color: 'CCCCCC' }),
    run(`  ${score}/${max}`, { size: 20, bold: true, color }),
  ];
}

function bandColor(s) {
  return s >= 4 ? GREEN : s >= 3 ? AMBER : RED;
}

// ─── Title page ───────────────────────────────────────────────────────────────
function makeTitlePage() {
  return [
    ...spacer(3),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 120 },
      children: [run('THESIS EVALUATION REPORT', { size: 38, bold: true, color: TEAL })]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 80 },
      children: [run('Final Year BSc Project — Personalised Feedback', { size: 24, italics: true, color: GREY })]
    }),
    ...spacer(1),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [run('─────────────────────────────────────────', { color: TEAL })]
    }),
    ...spacer(1),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 60, after: 60 },
      children: [run('Student', { size: 20, bold: true, color: GREY })]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 80 },
      children: [run(studentName, { size: 28, bold: true, color: DARK })]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 40, after: 40 },
      children: [run('Project Title', { size: 20, bold: true, color: GREY })]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 120 },
      children: [run(projectTitle, { size: 22, italics: true, color: DARK })]
    }),
    ...spacer(2),
    // Score badge
    new Table({
      width: { size: 4320, type: WidthType.DXA },
      columnWidths: [4320],
      rows: [new TableRow({
        children: [new TableCell({
          borders: borders(TEAL),
          width: { size: 4320, type: WidthType.DXA },
          shading: { fill: LBLUE, type: ShadingType.CLEAR },
          margins: { top: 240, bottom: 240, left: 360, right: 360 },
          children: [
            new Paragraph({
              alignment: AlignmentType.CENTER,
              children: [run('OVERALL SCORE', { size: 20, bold: true, color: GREY })]
            }),
            new Paragraph({
              alignment: AlignmentType.CENTER,
              spacing: { before: 60, after: 60 },
              children: [
                run(`${total}`, { size: 72, bold: true, color: TEAL }),
                run(' / 50', { size: 36, bold: true, color: GREY }),
              ]
            }),
            new Paragraph({
              alignment: AlignmentType.CENTER,
              children: [run(`${pct}%  —  ${gradeInfo.label}`, { size: 24, bold: true, color: gradeInfo.color })]
            }),
          ]
        })]
      })]
    }),
  ];
}

// ─── Score summary table ──────────────────────────────────────────────────────
function makeScoreTable() {
  const headerRow = new TableRow({
    children: [
      ['Criterion', 2400], ['Chapter', 2000], ['Score', 1200], ['Band', 3760]
    ].map(([label, w]) => new TableCell({
      borders: borders('1F3864'),
      width: { size: w, type: WidthType.DXA },
      shading: { fill: '1F3864', type: ShadingType.CLEAR },
      margins: { top: 80, bottom: 80, left: 120, right: 120 },
      children: [p(run(label, { bold: true, color: WHITE, size: 20 }))]
    }))
  });

  const dataRows = Object.entries(CRITERIA).map(([key, name], i) => {
    const s = scores[key] ?? 0;
    const fill = i % 2 === 0 ? LGREY : WHITE;
    const cols = [
      [name,                             2400, false],
      [CHAPTER_MAP[key] || '',           2000, false],
      [`${s} / 5`,                       1200, true],
      [s >= 4 ? 'Strong' : s >= 3 ? 'Adequate' : s >= 2 ? 'Needs Work' : 'Weak', 3760, false],
    ];
    return new TableRow({
      children: cols.map(([text, w, isBold]) => new TableCell({
        borders: borders('CCCCCC'),
        width: { size: w, type: WidthType.DXA },
        shading: { fill, type: ShadingType.CLEAR },
        margins: { top: 60, bottom: 60, left: 100, right: 100 },
        children: [p(run(text, { size: 20, bold: isBold, color: isBold ? bandColor(s) : DARK }))]
      }))
    });
  });

  const totalRow = new TableRow({
    children: [
      ['TOTAL SCORE', 2400], [`${total} / ${maxScore}`, 2000], [`${pct}%`, 1200], [gradeInfo.label, 3760]
    ].map(([label, w]) => new TableCell({
      borders: borders(TEAL),
      width: { size: w, type: WidthType.DXA },
      shading: { fill: LBLUE, type: ShadingType.CLEAR },
      margins: { top: 80, bottom: 80, left: 120, right: 120 },
      children: [p(run(label, { bold: true, color: TEAL, size: 20 }))]
    }))
  });

  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [2400, 2000, 1200, 3760],
    rows: [headerRow, ...dataRows, totalRow]
  });
}

// ─── Per-criterion feedback block ─────────────────────────────────────────────
function makeCriterionBlock(key) {
  const score  = scores[key] ?? 0;
  const name   = CRITERIA[key];
  const chap   = CHAPTER_MAP[key];
  const fb     = feedback[key] || {};
  const strengths = fb.strengths || [];
  const issues    = fb.issues    || [];

  const bandFill  = score >= 4 ? LGREEN : score >= 3 ? 'FFFBE6' : LRED;
  const bandBdr   = score >= 4 ? GREEN  : score >= 3 ? AMBER    : RED;

  const rows = [];

  // Header row
  rows.push(new TableRow({
    children: [new TableCell({
      borders: borders(bandBdr),
      columnSpan: 1,
      width: { size: 9360, type: WidthType.DXA },
      shading: { fill: bandFill, type: ShadingType.CLEAR },
      margins: { top: 120, bottom: 120, left: 180, right: 180 },
      children: [
        new Paragraph({
          spacing: { before: 0, after: 0 },
          children: [
            run(`${key}  ·  ${name}`, { bold: true, size: 24, color: DARK }),
            run('    ', { size: 22 }),
            ...scoreBar(score),
            run(`    ${chap}`, { size: 18, italics: true, color: GREY }),
          ]
        })
      ]
    })]
  }));

  // Strengths
  if (strengths.length > 0) {
    rows.push(new TableRow({
      children: [new TableCell({
        borders: borders('CCCCCC'),
        width: { size: 9360, type: WidthType.DXA },
        shading: { fill: WHITE, type: ShadingType.CLEAR },
        margins: { top: 100, bottom: 40, left: 180, right: 180 },
        children: [
          p(run('✔  What you did well', { bold: true, color: GREEN, size: 20 }), { before: 0, after: 60 }),
          ...strengths.map(s =>
            new Paragraph({
              numbering: { reference: 'bullets-green', level: 0 },
              spacing: { before: 40, after: 40 },
              children: [run(s, { size: 20, color: '1D4E2A' })]
            })
          )
        ]
      })]
    }));
  }

  // Issues
  if (issues.length > 0) {
    rows.push(new TableRow({
      children: [new TableCell({
        borders: borders('CCCCCC'),
        width: { size: 9360, type: WidthType.DXA },
        shading: { fill: WHITE, type: ShadingType.CLEAR },
        margins: { top: 100, bottom: 120, left: 180, right: 180 },
        children: [
          p(run('✘  What you need to fix', { bold: true, color: RED, size: 20 }), { before: 0, after: 60 }),
          ...issues.map((issue, idx) =>
            new Paragraph({
              numbering: { reference: 'bullets-red', level: 0 },
              spacing: { before: 40, after: 40 },
              children: [run(issue, { size: 20, color: '5C0000' })]
            })
          )
        ]
      })]
    }));
  }

  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [9360],
    rows,
  });
}

// ─── Priority fix list ────────────────────────────────────────────────────────
function makeTopFixes() {
  // Gather lowest-scoring criteria
  const sorted = Object.entries(scores)
    .sort(([, a], [, b]) => a - b)
    .filter(([, s]) => s < 4)
    .slice(0, 5);

  if (sorted.length === 0) {
    return [p(run('All criteria scored well — minor refinements only.', { color: GREEN }))];
  }

  return [
    p(run(`${firstName}, here are your top priorities before resubmission:`, { bold: true, size: 22, color: DARK }), { after: 160 }),
    ...sorted.map(([key, s], i) => {
      const issues = (feedback[key] || {}).issues || [];
      const topIssue = issues[0] || 'See detailed feedback above.';
      return new Paragraph({
        numbering: { reference: 'numbers', level: 0 },
        spacing: { before: 80, after: 80 },
        children: [
          run(`${CRITERIA[key]}  `, { bold: true, size: 22, color: DARK }),
          run(`(scored ${s}/5)`, { size: 20, color: GREY }),
          run(`\n${topIssue}`, { size: 20, color: '4A0000' }),
        ]
      });
    })
  ];
}

// ─── Assemble document ────────────────────────────────────────────────────────
const doc = new Document({
  numbering: {
    config: [
      {
        reference: 'bullets-green',
        levels: [{ level: 0, format: LevelFormat.BULLET, text: '–', alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 540, hanging: 300 } } } }]
      },
      {
        reference: 'bullets-red',
        levels: [{ level: 0, format: LevelFormat.BULLET, text: '→', alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 540, hanging: 300 } } } }]
      },
      {
        reference: 'numbers',
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 540, hanging: 300 } } } }]
      },
    ]
  },
  styles: {
    default: { document: { run: { font: 'Arial', size: 22 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 28, bold: true, font: 'Arial', color: TEAL },
        paragraph: { spacing: { before: 400, after: 160 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 24, bold: true, font: 'Arial', color: TEAL },
        paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 1 } },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1260, right: 1260, bottom: 1260, left: 1260 }
      }
    },
    children: [
      // Title page
      ...makeTitlePage(),
      ...spacer(2),
      sectionLine(),

      // Overall summary
      h1('Overall Summary'),
      p(run(overallNote || `${firstName}, here is your full evaluation. Read through each section carefully — every item in the "What you need to fix" lists is something you should address before your final submission.`, { size: 22, color: DARK }), { after: 160 }),

      // Score table
      h2('Score Breakdown'),
      makeScoreTable(),
      ...spacer(1),
      sectionLine(),

      // Top priorities
      h1('Your Priority Action List'),
      ...makeTopFixes(),
      ...spacer(1),
      sectionLine(),

      // Per-criterion detailed feedback
      h1('Detailed Feedback by Criterion'),
      p(run('Each section below shows your score, what you did well, and exactly what you need to fix.', { italics: true, color: GREY }), { after: 160 }),

      ...Object.keys(CRITERIA).flatMap(key => [
        makeCriterionBlock(key),
        ...spacer(1),
      ]),

      sectionLine(),

      // Closing note
      h1('Final Note'),
      p(run(`${firstName}, your score of ${total}/50 (${pct}% — ${gradeInfo.label}) reflects the current state of your project. The feedback above is specific and actionable — work through each "fix" item systematically and your project will improve significantly. Good luck with your revisions.`, { size: 22, color: DARK }), { after: 160 }),
    ]
  }]
});

// ─── Write output ─────────────────────────────────────────────────────────────
Packer.toBuffer(doc).then(buf => {
  fs.mkdirSync(path.dirname(outputFile), { recursive: true });
  fs.writeFileSync(outputFile, buf);
  console.log(`✅  Report saved to: ${outputFile}`);
}).catch(err => {
  console.error('❌  Failed to write report:', err.message);
  process.exit(1);
});
