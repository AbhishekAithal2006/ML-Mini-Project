import fs from 'node:fs/promises';
import { FileBlob, PresentationFile } from '@oai/artifact-tool';

const root = '/Users/abhishekaithal/Documents/SEM 5/ML/Mini-Project/untitled folder';
const input = `${root}/outputs/survival_project_presentation_msk2024_recolored_synthetic_slides4_5.pptx`;
const candidate = `${root}/outputs/.pptx-build/candidate-nb-conclusion.pptx`;
const qa = `${root}/outputs/pptx-edited-qa-final`;
await fs.mkdir(qa, { recursive: true });
const deck = await PresentationFile.importPptx(await FileBlob.load(input));
if (deck.slides.items.length !== 7) throw new Error(`Expected 7 slides, found ${deck.slides.items.length}`);
const slide = deck.slides.items[6];
const bullet = slide.shapes.add({
  geometry: 'textbox',
  name: 'naive-bayes-demo-note-bullet',
  position: { left: 76, top: 417, width: 24, height: 44 },
  fill: 'none',
  line: { style: 'solid', fill: 'none', width: 0 },
});
bullet.text = '•';
bullet.text.style = { fontSize: 22, typeface: 'Aptos', color: '#D95D76', bold: true, alignment: 'left' };

const note = slide.shapes.add({
  geometry: 'textbox',
  name: 'naive-bayes-demo-note',
  position: { left: 110, top: 417, width: 1066, height: 58 },
  fill: 'none',
  line: { style: 'solid', fill: 'none', width: 0 },
});
note.text = 'Synthetic demo Naive Bayes scored 0.695 at 270 days versus the paper’s 0.69; the cohorts are not directly comparable.';
note.text.style = { fontSize: 20, typeface: 'Aptos', color: '#2D2B36', alignment: 'left' };

const inspect = await deck.inspect({ kind: 'slide,textbox,shape', maxChars: 50000 });
await fs.writeFile(`${qa}/edited-inspect.ndjson`, inspect.ndjson, 'utf8');
const preview = await deck.export({ slide, format: 'png', scale: 1 });
await fs.writeFile(`${qa}/slide-07.png`, new Uint8Array(await preview.arrayBuffer()));
const pptx = await PresentationFile.exportPptx(deck);
await pptx.save(candidate);
console.log(`Saved candidate: ${candidate}`);
