#!/usr/bin/env node
/**
 * BSc Defence Q&A Generator — Word Document Output
 * Renders questions, model answers, source labels, and study nudges
 *
 * Usage:
 *   node generate_questions_doc.js --questions-file /tmp/defence_questions.json --output /path/out.docx
 */

const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType, LevelFormat
} = require('docx');
const fs   = require('fs');
const path = require('path');

// ── Args ──────────────────────────────────────────────────────────────────────
const args    = process.argv.slice(2);
const get     = f => { const i = args.indexOf(f); return i !== -1 ? args[i+1] : null; };
const qFile   = get('--questions-file');
const outFile = get('--output') || '/mnt/user-data/outputs/DefenceQA.docx';

if (!qFile || !fs.existsSync(qFile)) {
  console.error('❌  --questions-file not found:', qFile);
  process.exit(1);
}

const data        = JSON.parse(fs.readFileSync(qFile, 'utf8'));
const studentName = data.student_name  || 'Student';
const firstName   = studentName.split(' ')[0];
const title       = data.project_title || 'Final Year Project';
const chapters    = data.chapters      || {};
const general     = data.general       || {};
const tip         = data.tip           || '';

// ── Colours ───────────────────────────────────────────────────────────────────
const TEAL   = '1F3864';
const BLUE   = '2E5496';
const GREEN  = '1A6B3C';
const AMBER  = '7F6000';
const RED    = 'C00000';
const PURPLE = '6B2D8B';
const GREY   = '555555';
const DGREY  = '333333';
const WHITE  = 'FFFFFF';
const LBLUE  = 'EEF4FB';
const LGREY  = 'F5F5F5';
const LGREEN = 'EAF7EC';
const LYELL  = 'FFFBE6';
const LRED   = 'FFF0F0';
const LPURP  = 'F5EFFE';

// Source label colours
const SOURCE_COLORS = {
  'From your report':                    GREEN,
  'Partial — from your report':          AMBER,
  'From general knowledge':              PURPLE,
  'From your report + general knowledge': BLUE,
};
const SOURCE_BG = {
  'From your report':                    LGREEN,
  'Partial — from your report':          LYELL,
  'From general knowledge':              LPURP,
  'From your report + general knowledge': LBLUE,
};

// ── Helpers ───────────────────────────────────────────────────────────────────
const bdr  = (c='AAAAAA') => ({ style: BorderStyle.SINGLE, size: 1, color: c });
const bdrs = c => ({ top:bdr(c), bottom:bdr(c), left:bdr(c), right:bdr(c) });

const r = (text, opts={}) => new TextRun({
  text, size: opts.size ?? 22, font: opts.font ?? 'Arial', ...opts
});

const sp = (n=1) => Array.from({length:n}, () =>
  new Paragraph({ spacing:{before:40,after:40}, children:[r('')] })
);

const div = () => new Paragraph({
  spacing:{before:160,after:160},
  border:{ bottom:{style:BorderStyle.SINGLE, size:4, color:'CCCCCC', space:1} },
  children:[r('')]
});

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing:{before:400,after:160},
    children:[r(text, {size:30,bold:true,color:TEAL})]
  });
}
function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing:{before:280,after:120},
    children:[r(text, {size:24,bold:true,color:BLUE})]
  });
}
function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing:{before:200,after:100},
    children:[r(text, {size:22,bold:true,color:BLUE})]
  });
}
function para(text, color=GREY, size=22) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing:{before:80,after:100,line:340},
    children:[r(text, {size,color})]
  });
}

// Tag colour
function tagColor(tag='') {
  const t = tag.toLowerCase();
  if (['challenge'].some(k=>t.includes(k)))     return RED;
  if (['justification'].some(k=>t.includes(k))) return RED;
  if (['reflection','ownership'].some(k=>t.includes(k))) return AMBER;
  if (['conceptual','theory','framework'].some(k=>t.includes(k))) return BLUE;
  if (['ethics','real-world'].some(k=>t.includes(k))) return PURPLE;
  if (['mapping','coherence'].some(k=>t.includes(k))) return GREEN;
  return TEAL;
}

// ── Question card builder ─────────────────────────────────────────────────────
// Each question becomes a bordered card with:
// [Q number + question text]
// [Answer source badge | Answer text]
// [Nudge box — only if nudge present]

function questionCard(q, idx) {
  const num    = q.number || idx + 1;
  const tag    = q.tag    || '';
  const answer = q.answer || '';
  const src    = q.answer_source || 'From your report';
  const nudge  = q.nudge  || null;
  const tc     = tagColor(tag);
  const srcCol = SOURCE_COLORS[src] || GREEN;
  const srcBg  = SOURCE_BG[src]     || LGREEN;

  const rows = [];

  // ── Row 1: Question ──────────────────────────────────────────────────
  rows.push(new TableRow({
    children:[
      // Number badge
      new TableCell({
        borders: bdrs(TEAL),
        width:{ size:520, type:WidthType.DXA },
        shading:{ fill:TEAL, type:ShadingType.CLEAR },
        margins:{top:100,bottom:100,left:80,right:80},
        verticalAlign:'center',
        children:[new Paragraph({
          alignment:AlignmentType.CENTER,
          children:[r(String(num), {bold:true,size:20,color:WHITE})]
        })]
      }),
      // Question text
      new TableCell({
        borders: bdrs(TEAL),
        columnSpan: 2,
        width:{ size:8840, type:WidthType.DXA },
        shading:{ fill:LBLUE, type:ShadingType.CLEAR },
        margins:{top:100,bottom:100,left:160,right:120},
        children:[
          new Paragraph({
            spacing:{before:0,after:0,line:320},
            children:[r(q.text||'', {size:22,bold:true,color:DGREY})]
          }),
          new Paragraph({
            spacing:{before:60,after:0},
            children:[r(`[${tag}]`, {size:18,bold:true,color:tc})]
          })
        ]
      }),
    ]
  }));

  // ── Row 2: Answer ─────────────────────────────────────────────────────
  if (answer) {
    rows.push(new TableRow({
      children:[
        // Label column
        new TableCell({
          borders: bdrs('CCCCCC'),
          width:{ size:520, type:WidthType.DXA },
          shading:{ fill:LGREEN, type:ShadingType.CLEAR },
          margins:{top:100,bottom:100,left:60,right:60},
          verticalAlign:'center',
          children:[new Paragraph({
            alignment:AlignmentType.CENTER,
            children:[r('ANS', {bold:true,size:17,color:GREEN})]
          })]
        }),
        // Source badge
        new TableCell({
          borders: bdrs('CCCCCC'),
          width:{ size:1800, type:WidthType.DXA },
          shading:{ fill:srcBg, type:ShadingType.CLEAR },
          margins:{top:100,bottom:100,left:100,right:80},
          verticalAlign:'center',
          children:[new Paragraph({
            alignment:AlignmentType.CENTER,
            children:[r(src, {size:17,bold:true,color:srcCol})]
          })]
        }),
        // Answer text
        new TableCell({
          borders: bdrs('CCCCCC'),
          width:{ size:7040, type:WidthType.DXA },
          shading:{ fill:WHITE, type:ShadingType.CLEAR },
          margins:{top:100,bottom:100,left:140,right:120},
          children: answer.split('\n').filter(Boolean).map(line =>
            new Paragraph({
              spacing:{before:0,after:60,line:320},
              children:[r(line.trim(), {size:21,color:DGREY})]
            })
          )
        }),
      ]
    }));
  }

  // ── Row 3: Study nudge ────────────────────────────────────────────────
  if (nudge) {
    const nudgeText = nudge.replace(/^📚\s*\*\*Study nudge\*\*:\s*/,'').replace(/^📚\s*/,'');
    rows.push(new TableRow({
      children:[
        // Icon cell
        new TableCell({
          borders: bdrs('F0A500'),
          width:{ size:520, type:WidthType.DXA },
          shading:{ fill:'FFF8E1', type:ShadingType.CLEAR },
          margins:{top:100,bottom:100,left:60,right:60},
          verticalAlign:'center',
          children:[new Paragraph({
            alignment:AlignmentType.CENTER,
            children:[r('📚', {size:20})]
          })]
        }),
        // "Study nudge" label
        new TableCell({
          borders: bdrs('F0A500'),
          width:{ size:1800, type:WidthType.DXA },
          shading:{ fill:LYELL, type:ShadingType.CLEAR },
          margins:{top:100,bottom:100,left:100,right:80},
          verticalAlign:'center',
          children:[new Paragraph({
            alignment:AlignmentType.CENTER,
            children:[r('STUDY\nNUDGE', {size:16,bold:true,color:AMBER})]
          })]
        }),
        // Nudge text
        new TableCell({
          borders: bdrs('F0A500'),
          width:{ size:7040, type:WidthType.DXA },
          shading:{ fill:'FFFDE7', type:ShadingType.CLEAR },
          margins:{top:100,bottom:100,left:140,right:120},
          children:[new Paragraph({
            spacing:{before:0,after:0,line:320},
            children:[r(nudgeText, {size:20,italics:true,color:AMBER})]
          })]
        }),
      ]
    }));
  }

  // Wrap in outer table
  return new Table({
    width:{ size:9360, type:WidthType.DXA },
    columnWidths:[520,1800,7040],
    rows,
  });
}

// ── Count totals ──────────────────────────────────────────────────────────────
let totalQ    = 0;
let nudgeCount = 0;

const allQs = [];
Object.values(chapters).forEach(ch => {
  (ch.questions||[]).forEach(q => {
    allQs.push(q);
    totalQ++;
    if (q.nudge) nudgeCount++;
  });
});
(general.categories||[]).forEach(cat => {
  (cat.questions||[]).forEach(q => {
    allQs.push(q);
    totalQ++;
    if (q.nudge) nudgeCount++;
  });
});

// ── Title page ────────────────────────────────────────────────────────────────
function scoreBadge() {
  return new Table({
    width:{size:9360,type:WidthType.DXA},
    columnWidths:[4500,380,4480],
    rows:[new TableRow({ children:[
      // Left: questions total
      new TableCell({
        borders: bdrs(TEAL),
        width:{size:4500,type:WidthType.DXA},
        shading:{fill:LBLUE,type:ShadingType.CLEAR},
        margins:{top:180,bottom:180,left:300,right:200},
        children:[
          new Paragraph({alignment:AlignmentType.CENTER, children:[r('QUESTIONS', {size:20,bold:true,color:GREY})]}),
          new Paragraph({alignment:AlignmentType.CENTER, spacing:{before:40,after:40},
            children:[r(String(totalQ), {size:64,bold:true,color:TEAL})] }),
          new Paragraph({alignment:AlignmentType.CENTER,
            children:[r('with model answers', {size:19,italics:true,color:GREY})] }),
        ]
      }),
      // Divider
      new TableCell({
        borders:{top:bdr('FFFFFF'),bottom:bdr('FFFFFF'),left:bdr('CCCCCC'),right:bdr('CCCCCC')},
        width:{size:380,type:WidthType.DXA},
        shading:{fill:'F0F0F0',type:ShadingType.CLEAR},
        margins:{top:10,bottom:10,left:10,right:10},
        children:[new Paragraph({children:[r('')]})]
      }),
      // Right: nudge count
      new TableCell({
        borders: bdrs(AMBER),
        width:{size:4480,type:WidthType.DXA},
        shading:{fill:LYELL,type:ShadingType.CLEAR},
        margins:{top:180,bottom:180,left:200,right:300},
        children:[
          new Paragraph({alignment:AlignmentType.CENTER, children:[r('STUDY NUDGES', {size:20,bold:true,color:AMBER})]}),
          new Paragraph({alignment:AlignmentType.CENTER, spacing:{before:40,after:40},
            children:[r(String(nudgeCount), {size:64,bold:true,color:AMBER})] }),
          new Paragraph({alignment:AlignmentType.CENTER,
            children:[r('gaps to close before defence', {size:19,italics:true,color:AMBER})] }),
        ]
      }),
    ]})]
  });
}

// ── Legend table ──────────────────────────────────────────────────────────────
function legendTable() {
  const items = [
    [LGREEN, GREEN,  'From your report',                    'Answer drawn directly from your project text'],
    [LYELL,  AMBER,  'Partial — from your report',          'Your report gives part of the answer; study nudge covers the rest'],
    [LPURP,  PURPLE, 'From general knowledge',              'Technical concept not explained in your report — sourced from web/knowledge'],
    [LBLUE,  BLUE,   'From your report + general knowledge','Blend of your report and supplementary explanation'],
  ];
  return new Table({
    width:{size:9360,type:WidthType.DXA},
    columnWidths:[200,2200,7160], // colour swatch + label + description
    rows: items.map(([bg,col,label,desc],i) => new TableRow({ children:[
      new TableCell({
        borders:bdrs(col),
        width:{size:200,type:WidthType.DXA},
        shading:{fill:bg,type:ShadingType.CLEAR},
        margins:{top:60,bottom:60,left:60,right:60},
        children:[new Paragraph({children:[r('')]})]
      }),
      new TableCell({
        borders:bdrs('CCCCCC'),
        width:{size:2200,type:WidthType.DXA},
        shading:{fill:bg,type:ShadingType.CLEAR},
        margins:{top:60,bottom:60,left:100,right:80},
        children:[new Paragraph({children:[r(label,{bold:true,size:19,color:col})]})]
      }),
      new TableCell({
        borders:bdrs('CCCCCC'),
        width:{size:7160,type:WidthType.DXA},
        shading:{fill:i%2===0?LGREY:WHITE,type:ShadingType.CLEAR},
        margins:{top:60,bottom:60,left:120,right:100},
        children:[new Paragraph({children:[r(desc,{size:19,color:GREY})]})]
      }),
    ]}))
  });
}

// ── Chapter sections ──────────────────────────────────────────────────────────
const chapterSections = Object.entries(chapters).flatMap(([key, ch]) => {
  const qs = ch.questions || [];
  const chNum = key.replace('chapter','Chapter ');
  return [
    div(),
    h1(`${chNum.toUpperCase()} — ${(ch.title||'').toUpperCase()}`),
    para(`${qs.length} questions with model answers.`, GREY, 20),
    ...sp(1),
    ...qs.flatMap((q,i) => [questionCard(q,i), ...sp(1)]),
  ];
});

// ── General sections ──────────────────────────────────────────────────────────
const generalSections = [
  div(),
  h1('GENERAL QUESTIONS — FULL PROJECT'),
  para('These questions span the entire project and test holistic understanding, intellectual ownership, and the ability to defend every decision.', GREY, 20),
  ...sp(1),
  ...(general.categories||[]).flatMap((cat) => {
    const qs = cat.questions || [];
    return [
      h2(cat.name || 'Category'),
      para(`${qs.length} questions`, GREY, 20),
      ...sp(1),
      ...qs.flatMap((q,i) => [questionCard(q,i), ...sp(1)]),
    ];
  })
];

// ── Closing checklist ─────────────────────────────────────────────────────────
const closing = [
  div(),
  h1('FINAL PREPARATION CHECKLIST'),
  ...sp(1),
  new Table({
    width:{size:9360,type:WidthType.DXA},
    columnWidths:[480,8880],
    rows:[
      ['Can I state my research problem in one sentence without reading my document?'],
      ['Can I explain every objective and show exactly where in Chapter 4 it is answered?'],
      ['Can I justify my methodology — why I chose it over the obvious alternatives?'],
      ['Can I walk through any table or figure without reading the caption?'],
      ['Can I interpret my main result in plain language without technical jargon?'],
      ['Can I connect my findings back to at least two sources from my literature review?'],
      ['Can I state my two most significant limitations and explain why they arose?'],
      ['Can I give two specific, actionable recommendations for future work?'],
      ['Have I read up on every concept flagged with a 📚 study nudge in this document?'],
      ['Have I practised answering questions out loud — not just reading my document?'],
    ].map((q,i) => new TableRow({ children:[
      new TableCell({
        borders:bdrs('CCCCCC'),
        width:{size:480,type:WidthType.DXA},
        shading:{fill:i%2===0?LGREY:WHITE,type:ShadingType.CLEAR},
        margins:{top:80,bottom:80,left:120,right:80},
        children:[new Paragraph({alignment:AlignmentType.CENTER, children:[r('☐',{size:24,color:TEAL})]})]
      }),
      new TableCell({
        borders:bdrs('CCCCCC'),
        width:{size:8880,type:WidthType.DXA},
        shading:{fill:i%2===0?LGREY:WHITE,type:ShadingType.CLEAR},
        margins:{top:80,bottom:80,left:140,right:100},
        children:[new Paragraph({spacing:{before:0,after:0}, children:[r(q[0],{size:21})]})]
      })
    ]}))
  }),
  ...sp(2),
  new Paragraph({ alignment:AlignmentType.CENTER, spacing:{before:160,after:80},
    children:[r(`Good luck, ${firstName}. You wrote this project — now own every word of it.`, {size:22,bold:true,color:TEAL})] }),
  new Paragraph({ alignment:AlignmentType.CENTER, spacing:{before:0,after:0},
    children:[r('─── End of Defence Q&A Bank ───', {size:20,italics:true,color:GREY})] }),
];

// ── Title page content ────────────────────────────────────────────────────────
const titlePage = [
  ...sp(3),
  new Paragraph({ alignment:AlignmentType.CENTER, spacing:{before:0,after:120},
    children:[r('PROJECT DEFENCE', {size:42,bold:true,color:TEAL})] }),
  new Paragraph({ alignment:AlignmentType.CENTER, spacing:{before:0,after:120},
    children:[r('QUESTION & ANSWER BANK', {size:34,bold:true,color:BLUE})] }),
  new Paragraph({ alignment:AlignmentType.CENTER, spacing:{before:0,after:80},
    children:[r('Personalised Viva Voce Preparation', {size:24,italics:true,color:GREY})] }),
  ...sp(1),
  new Paragraph({ alignment:AlignmentType.CENTER,
    children:[r('────────────────────────────────────────────', {color:BLUE})] }),
  ...sp(1),
  new Paragraph({ alignment:AlignmentType.CENTER, spacing:{before:80,after:40},
    children:[r('Prepared for', {size:20,bold:true,color:GREY})] }),
  new Paragraph({ alignment:AlignmentType.CENTER, spacing:{before:0,after:80},
    children:[r(studentName, {size:30,bold:true,color:TEAL})] }),
  new Paragraph({ alignment:AlignmentType.CENTER, spacing:{before:40,after:40},
    children:[r('Project', {size:20,bold:true,color:GREY})] }),
  new Paragraph({ alignment:AlignmentType.CENTER, spacing:{before:0,after:160},
    children:[r(title, {size:22,italics:true,color:DGREY})] }),
  ...sp(2),
  scoreBadge(),
  ...sp(2),

  // How to use
  new Paragraph({ alignment:AlignmentType.LEFT, spacing:{before:80,after:60},
    children:[r('HOW TO USE THIS DOCUMENT', {size:22,bold:true,color:TEAL})] }),
  para(`${firstName}, every question in this bank has been generated specifically from your project report. Each question comes with a model answer drawn from what you actually wrote, so you know exactly what a strong response sounds like. Practise by reading the question, closing the document, answering out loud, then comparing your answer to the model.`, DGREY),
  para('Questions with a 📚 STUDY NUDGE highlight areas where your report does not give enough detail for a confident answer. You must read up on those concepts before your defence — they are the most likely areas a panel will push you on.', DGREY),
  para('Answer source labels (green = from your report, amber = partial, purple = general knowledge) tell you where each answer comes from so you know which answers to own fully and which to supplement with further reading.', DGREY),

  ...(tip ? [
    ...sp(1),
    new Paragraph({ spacing:{before:80,after:40},
      children:[r(`📌  Examiner's Tip for ${firstName}`, {size:21,bold:true,color:AMBER})] }),
    para(tip, AMBER),
  ] : []),

  ...sp(1),
  // Legend
  h2('Answer Source Legend'),
  legendTable(),
];

// ── Build document ────────────────────────────────────────────────────────────
const doc = new Document({
  styles:{
    default:{ document:{ run:{ font:'Arial', size:22 } } },
    paragraphStyles:[
      { id:'Heading1', name:'Heading 1', basedOn:'Normal', next:'Normal', quickFormat:true,
        run:{size:30,bold:true,font:'Arial',color:TEAL},
        paragraph:{spacing:{before:400,after:160},outlineLevel:0} },
      { id:'Heading2', name:'Heading 2', basedOn:'Normal', next:'Normal', quickFormat:true,
        run:{size:24,bold:true,font:'Arial',color:BLUE},
        paragraph:{spacing:{before:280,after:120},outlineLevel:1} },
      { id:'Heading3', name:'Heading 3', basedOn:'Normal', next:'Normal', quickFormat:true,
        run:{size:22,bold:true,font:'Arial',color:BLUE},
        paragraph:{spacing:{before:200,after:100},outlineLevel:2} },
    ]
  },
  sections:[{
    properties:{
      page:{
        size:{ width:12240, height:15840 },
        margin:{ top:1260, right:1260, bottom:1260, left:1260 }
      }
    },
    children:[
      ...titlePage,
      ...chapterSections,
      ...generalSections,
      ...closing,
    ]
  }]
});

Packer.toBuffer(doc).then(buf => {
  fs.mkdirSync(path.dirname(outFile), { recursive:true });
  fs.writeFileSync(outFile, buf);
  console.log(`✅  Saved: ${outFile}`);
}).catch(err => {
  console.error('❌  Error:', err.message);
  process.exit(1);
});
