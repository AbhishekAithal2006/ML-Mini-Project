import fs from 'node:fs/promises';
import { FileBlob, PresentationFile } from '@oai/artifact-tool';

const root = '/Users/abhishekaithal/Documents/SEM 5/ML/Mini-Project/untitled folder';
const input = '/Users/abhishekaithal/Documents/SEM 5/ML/Mini-Project/survival_project_presentation_msk2024_recolored.pptx';
const candidate = `${root}/outputs/.pptx-build/candidate-slide5.pptx`;
const qa = `${root}/outputs/pptx-edited-qa-slide5`;
await fs.mkdir(qa, { recursive: true });
const deck = await PresentationFile.importPptx(await FileBlob.load(input));
if (deck.slides.items.length !== 7) throw new Error(`Expected 7 slides, found ${deck.slides.items.length}`);

const snap = await deck.inspect({ kind: 'slide,textbox,shape', maxChars: 50000 });
const records = snap.ndjson.split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
const slideRecords = records.filter((item) => item.slideIndex === 4);
const replacements = new Map([
  ['Threshold sensitivity and interpretation', 'Synthetic demo threshold sensitivity'],
  ['Naive Bayes balanced accuracy across MSK survival horizons', 'Naive Bayes balanced accuracy across tested horizons'],
  ['Highest exploratory NB score: 240 days (0.664). Primary comparison stays at 270 days.', 'Best Naive Bayes score in this demo: 270 days (0.695).'],
  ['The horizon sweep is exploratory and not nested selection. Results depend on the cohort and censoring pattern.', 'Synthetic demo only. At 270 days: 148 known labels, 73 high-risk cases, 12 excluded.'],
]);
for (const item of slideRecords) {
  if (item.kind === 'textbox' && replacements.has(item.text)) {
    deck.resolve(item.id).text = replacements.get(item.text);
  }
}

// Use the demo CSV values for Naive Bayes balanced accuracy at 240, 270, 300, 330, and 360 days.
const scores = [0.6618319269, 0.6952511416, 0.6157201008, 0.6769837973, 0.6534858388];
const labels = ['0.662', '0.695', '0.616', '0.677', '0.653'];
const lefts = [172, 372, 572, 772, 972];
for (let i = 0; i < lefts.length; i += 1) {
  const bar = slideRecords.find((item) =>
    item.kind === 'shape' &&
    Math.abs(item.position?.left - lefts[i]) < 1 &&
    Math.abs(item.position?.width - 118) < 1
  );
  if (!bar) throw new Error(`Could not locate threshold bar at x=${lefts[i]}`);
  const height = scores[i] * 387;
  const target = deck.resolve(bar.id);
  target.position = { ...target.position, top: 528 - height, height };
  const valueLabel = slideRecords.find((item) =>
    item.kind === 'textbox' &&
    item.position?.left === lefts[i] &&
    /^0\.\d{3}$/.test(item.text ?? '')
  );
  if (!valueLabel) throw new Error(`Could not locate value label at x=${lefts[i]}`);
  const labelTarget = deck.resolve(valueLabel.id);
  labelTarget.text = labels[i];
  labelTarget.position = { ...labelTarget.position, top: 528 - height - 34 };
}

const after = await deck.inspect({ kind: 'slide,textbox,shape,table', maxChars: 50000 });
await fs.writeFile(`${qa}/edited-inspect.ndjson`, after.ndjson, 'utf8');
for (const [index, slide] of deck.slides.items.entries()) {
  const png = await deck.export({ slide, format: 'png', scale: 1 });
  await fs.writeFile(`${qa}/slide-${String(index + 1).padStart(2, '0')}.png`, new Uint8Array(await png.arrayBuffer()));
}
const pptx = await PresentationFile.exportPptx(deck);
await pptx.save(candidate);
console.log(`Saved candidate: ${candidate}`);
