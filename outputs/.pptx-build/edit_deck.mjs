import fs from 'node:fs/promises';
import { FileBlob, PresentationFile } from '@oai/artifact-tool';

const root = '/Users/abhishekaithal/Documents/SEM 5/ML/Mini-Project/untitled folder';
const input = `${root}/outputs/survival_project_presentation_msk2024_recolored.pptx`;
const candidate = `${root}/outputs/.pptx-build/candidate.pptx`;
const qa = `${root}/outputs/pptx-edited-qa`;
await fs.mkdir(qa, { recursive: true });
const deck = await PresentationFile.importPptx(await FileBlob.load(input));
const before = deck.slides.items;
if (before.length !== 8) throw new Error(`Expected 8 slides, found ${before.length}`);
const initialSnapshot = await deck.inspect({ kind: 'slide', maxChars: 20000 });
const slideIds = initialSnapshot.ndjson.split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line).id);
if (slideIds.length !== 8) throw new Error(`Could not identify all slide anchors: ${slideIds.length}`);
// Keep the opening, workflow, demo results, and ending analysis slides.
// This removes the MSK classifier-results slide and moves the existing synthetic demo slide into its place.
deck.slides.keep([slideIds[0], slideIds[1], slideIds[2], slideIds[4], slideIds[5], slideIds[6], slideIds[7]]);
deck.slides.reorder([
  slideIds[0],
  slideIds[1],
  slideIds[2],
  slideIds[7],
  slideIds[4],
  slideIds[5],
  slideIds[6],
]);
const records = await deck.inspect({ kind: 'slide,textbox,table', maxChars: 50000 });
const shapes = records.ndjson.split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
const footerUpdates = new Map([
  ['UE24CS352A  ·  ML MINI-PROJECT                                           08 / 08', 'UE24CS352A  ·  ML MINI-PROJECT                                           04 / 07'],
  ['UE24CS352A  ·  ML MINI-PROJECT                                           05 / 08', 'UE24CS352A  ·  ML MINI-PROJECT                                           05 / 07'],
  ['UE24CS352A  ·  ML MINI-PROJECT                                           06 / 08', 'UE24CS352A  ·  ML MINI-PROJECT                                           06 / 07'],
  ['UE24CS352A  ·  ML MINI-PROJECT                                           07 / 08', 'UE24CS352A  ·  ML MINI-PROJECT                                           07 / 07'],
]);
for (const item of shapes) {
  if (item.kind === 'textbox' && footerUpdates.has(item.text)) {
    deck.resolve(item.id).text = footerUpdates.get(item.text);
  }
}
const after = await deck.inspect({ kind: 'slide,textbox,table', maxChars: 50000 });
await fs.writeFile(`${qa}/edited-inspect.ndjson`, after.ndjson, 'utf8');
if (deck.slides.items.length !== 7) throw new Error(`Expected 7 final slides, found ${deck.slides.items.length}`);
for (const [index, slide] of deck.slides.items.entries()) {
  const png = await deck.export({ slide, format: 'png', scale: 1 });
  await fs.writeFile(`${qa}/slide-${String(index + 1).padStart(2, '0')}.png`, new Uint8Array(await png.arrayBuffer()));
}
const pptx = await PresentationFile.exportPptx(deck);
await pptx.save(candidate);
console.log(`Saved candidate with ${deck.slides.items.length} slides: ${candidate}`);
