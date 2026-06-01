// Syntax checker for Workflow scripts (a special dialect: `export const meta`,
// top-level `await`, and a top-level `return` all coexist — no standard module
// mode parses that, and `node --check file.js` silently passes broken files).
//
// We strip the leading `export` and compile the body as the constructor of an
// async function whose params are the Workflow runtime globals. Top-level
// `return`/`await` are legal there, and a real syntax error throws.
//
// Usage: node .claude/workflows/__tests__/check-syntax.mjs <path-to-workflow.js>
import { readFileSync } from 'node:fs'

const path = process.argv[2]
if (!path) { console.error('usage: check-syntax.mjs <workflow.js>'); process.exit(2) }

const src = readFileSync(path, 'utf8').replace(/^export\s+const\s+meta\b/m, 'const meta')
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const GLOBALS = ['agent', 'parallel', 'pipeline', 'phase', 'log', 'args', 'budget', 'workflow']

try {
  // eslint-disable-next-line no-new
  new AsyncFunction(...GLOBALS, src)
  console.log(`SYNTAX OK: ${path}`)
} catch (e) {
  console.error(`SYNTAX ERROR in ${path}: ${e.message}`)
  process.exit(1)
}
