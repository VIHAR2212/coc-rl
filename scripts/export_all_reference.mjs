import fs from 'fs';
import path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '..');
const RAW_TS_DIR = path.join(ROOT, 'data', 'reference', 'raw_ts');
const REF_DIR = path.join(ROOT, 'data', 'reference');

// Escape CSV cells per RFC 4180
function escapeCsv(val) {
  if (val === undefined || val === null) return '';
  const str = String(val);
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

const sources = [
  { file: 'elixirTroops.ts', key: 'elixirTroopsData' },
  { file: 'darkElixirTroops.ts', key: 'darkElixirTroopsData' },
  { file: 'superTroops.ts', key: 'superTroopsData' },
  { file: 'builderBaseTroops.ts', key: 'builderBaseTroopsData' },
  { file: 'defensesData.ts', key: 'cannonsData' },
  { file: 'buildingsAndTrapsData.ts', key: 'buildingsAndTrapsData' },
  { file: 'heroesData.ts', key: 'heroesData' },
  { file: 'petsData.ts', key: 'heroPetsData' },
  { file: 'siegesData.ts', key: 'siegeMachinesData' },
  { file: 'equipmentData.ts', key: 'equipmentData' },
];

const allRows = [];

for (const s of sources) {
  const p = path.join(RAW_TS_DIR, s.file);
  const mod = await import(pathToFileURL(p).href);
  const data = mod[s.key] || [];
  console.log(`Loaded ${data.length} rows from ${s.file} [${s.key}]`);
  for (const r of data) {
    allRows.push({
      ...r,
      origin: `clash-of-clans-data-researcher-&-csv-explorer/src/data/${s.file}`,
    });
  }
}

// Also load troopBehaviors and conflicts
const behaviorsMod = await import(pathToFileURL(path.join(RAW_TS_DIR, 'troopBehaviors.ts')).href);
const behaviors = behaviorsMod.troopBehaviorsData || [];
console.log(`Loaded ${behaviors.length} behaviors from troopBehaviors.ts`);

const conflictsMod = await import(pathToFileURL(path.join(RAW_TS_DIR, 'conflicts.ts')).href);
const conflicts = conflictsMod.conflictAuditLog || [];
console.log(`Loaded ${conflicts.length} conflict audit logs from conflicts.ts`);

// Save JSON outputs
fs.writeFileSync(path.join(REF_DIR, 'clash_explorer_all.json'), JSON.stringify(allRows, null, 2), 'utf8');
fs.writeFileSync(path.join(REF_DIR, 'troop_behaviors.json'), JSON.stringify(behaviors, null, 2), 'utf8');
fs.writeFileSync(path.join(REF_DIR, 'conflicts.json'), JSON.stringify(conflicts, null, 2), 'utf8');

// Generate CSV with origin column
const headers = [
  'name',
  'village',
  'category',
  'level',
  'town hall (or building) level required',
  'hitpoints',
  'damage per second',
  'damage per hit',
  'attack speed (seconds between attacks)',
  'range (tiles)',
  'footprint (tiles, e.g. 3x3)',
  'housing space (troops)',
  'movement speed',
  'ground/air',
  'favorite target',
  'special ability or effect at this level',
  'source URLs',
  'confidence',
  'origin',
];

const csvLines = [headers.join(',')];

for (const r of allRows) {
  const urls = (r.sources || []).map(s => s.url).join(' ; ');
  const line = [
    escapeCsv(r.name),
    escapeCsv(r.village),
    escapeCsv(r.category),
    escapeCsv(r.level),
    escapeCsv(r.thRequired),
    escapeCsv(r.hitpoints),
    escapeCsv(r.dps),
    escapeCsv(r.damagePerHit),
    escapeCsv(r.attackSpeed),
    escapeCsv(r.range),
    escapeCsv(r.footprint),
    escapeCsv(r.housingSpace),
    escapeCsv(r.movementSpeed),
    escapeCsv(r.groundAir),
    escapeCsv(r.favoriteTarget),
    escapeCsv(r.specialAbility),
    escapeCsv(urls),
    escapeCsv(r.confidence),
    escapeCsv(r.origin),
  ].join(',');
  csvLines.push(line);
}

fs.writeFileSync(path.join(REF_DIR, 'clash_explorer_all.csv'), csvLines.join('\n'), 'utf8');

console.log(`\nSuccessfully exported:`);
console.log(`  data/reference/clash_explorer_all.json (${allRows.length} rows)`);
console.log(`  data/reference/clash_explorer_all.csv (${csvLines.length - 1} rows)`);
console.log(`  data/reference/troop_behaviors.json (${behaviors.length} entries)`);
console.log(`  data/reference/conflicts.json (${conflicts.length} entries)`);

