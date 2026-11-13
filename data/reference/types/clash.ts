export type VillageType = 'Home Village' | 'Builder Base' | 'Clan Capital';

export type CategoryType =
  | 'Elixir Troop'
  | 'Dark Elixir Troop'
  | 'Super Troop'
  | 'Builder Base Troop'
  | 'Siege Machine'
  | 'Spell'
  | 'Defense'
  | 'Army Building'
  | 'Resource Building'
  | 'Trap'
  | 'Hero'
  | 'Hero Pet'
  | 'Hero Equipment';

export type ConfidenceRating = 'HIGH' | 'MEDIUM' | 'LOW';

export interface SourceCitation {
  title: string;
  url: string;
}

export interface ClashDataRow {
  id: string;
  name: string;
  village: VillageType;
  category: CategoryType;
  level: number;
  thRequired: number; // Town hall level required
  buildingRequired?: string; // e.g. "Laboratory 16 / Barracks 1"
  hitpoints: number | string;
  dps: number | string;
  damagePerHit: number | string;
  attackSpeed: number; // seconds per attack
  range: number | string; // tiles, e.g. 0.4, 3.5, 7
  footprint: string; // e.g. "1x1", "3x3"
  housingSpace: number; // Troop housing space
  movementSpeed: number;
  groundAir: string; // e.g. "Ground (Targets Ground)", "Air (Targets Ground & Air)"
  favoriteTarget: string; // e.g. "Defenses", "Any", "Resources (Damage x2)"
  specialAbility: string; // special ability or effect at this level
  sources: SourceCitation[];
  confidence: ConfidenceRating;
  conflictNotes?: string;
}

export interface TroopBehavior {
  troopName: string;
  category: CategoryType;
  targetPriority: string;
  distractionAndAggro: string;
  wallInteraction: string;
  deathAndSpawnEffects: string;
  pathfindingNotes: string;
  sources: SourceCitation[];
}

export interface ConflictRecord {
  id: string;
  name: string;
  level: number;
  field: string;
  sourceA: { name: string; value: string; url: string };
  sourceB: { name: string; value: string; url: string };
  reason: string;
  recommendation: string;
}
