import path from 'node:path';
import { pathToFileURL } from 'node:url';

const skillDir = '/Users/abhishekaithal/.codex/plugins/cache/openai-primary-runtime/presentations/26.1007.11041/skills/presentations';
const workspaceDir = '/Users/abhishekaithal/Documents/SEM 5/ML/Mini-Project/untitled folder';
const candidatePath = path.join(workspaceDir, 'outputs/.pptx-build/candidate.pptx');
const finalPath = path.join(workspaceDir, 'outputs/survival_project_presentation_msk2024_recolored_demo_slide4.pptx');
const { finalizePresentation } = await import(pathToFileURL(
  path.join(skillDir, 'container_tools/artifact_tool_utils.mjs'),
).href);
const result = await finalizePresentation({
  explicitTotalSlideCount: 7,
  requiredNativeTableOwnerSlides: [4],
  workspaceDir,
  candidatePath,
  finalPath,
  pythonExecutable: '/Users/abhishekaithal/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3',
  integrityValidatorPath: path.join(skillDir, 'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath: path.join(skillDir, 'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs: ['--expected-slide-size-emu', '12192000,6858000', '--validate-bullet-geometry', '--validate-heading-fit', '--require-native-table-slide', '4'],
  fontPolicy: {
    basis: 'reference',
    families: ['Aptos'],
    referencePath: path.join(workspaceDir, 'outputs/survival_project_presentation_msk2024_recolored.pptx'),
    referenceSha256: '8353994a963c770fc4d5e2b024fbb26bdd00ea0566063c1681ca709948f70598',
  },
  verifyArtifactToolImport: true,
  receiptPath: path.join(workspaceDir, '.presentation-build/finalization-validation.json'),
});
console.log(JSON.stringify(result, null, 2));
