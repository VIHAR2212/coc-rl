import { ClashDataRow } from '../types/clash';

export function escapeCsvCell(val: string | number | undefined | null): string {
  if (val === undefined || val === null) return '';
  const str = String(val);
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

export function generateCsvString(rows: ClashDataRow[]): string {
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
  ];

  const lines = [headers.join(',')];

  for (const row of rows) {
    const urls = row.sources.map((s) => s.url).join(' ; ');
    const line = [
      escapeCsvCell(row.name),
      escapeCsvCell(row.village),
      escapeCsvCell(row.category),
      escapeCsvCell(row.level),
      escapeCsvCell(row.thRequired),
      escapeCsvCell(row.hitpoints),
      escapeCsvCell(row.dps),
      escapeCsvCell(row.damagePerHit),
      escapeCsvCell(row.attackSpeed),
      escapeCsvCell(row.range),
      escapeCsvCell(row.footprint),
      escapeCsvCell(row.housingSpace),
      escapeCsvCell(row.movementSpeed),
      escapeCsvCell(row.groundAir),
      escapeCsvCell(row.favoriteTarget),
      escapeCsvCell(row.specialAbility),
      escapeCsvCell(urls),
      escapeCsvCell(row.confidence),
    ].join(',');
    lines.push(line);
  }

  return lines.join('\n');
}

export function downloadCsv(filename: string, content: string) {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
