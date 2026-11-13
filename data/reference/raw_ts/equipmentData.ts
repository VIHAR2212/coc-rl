

export interface EquipmentUpgradeStep {
  level: number;
  blacksmithRequired: number;
  thRequired: number;
  shinyOre: number;
  glowyOre: number;
  starryOre: number; // Epic only
  cumulativeShiny: number;
  cumulativeGlowy: number;
  cumulativeStarry: number;
  milestoneNote: string;
}

export interface EquipmentLevelMilestone {
  level: number;
  blacksmith: number;
  th: number;
  effectSummary: string;
}

export interface HeroEquipmentSpec {
  id: string;
  name: string;
  hero: 'Barbarian King' | 'Archer Queen' | 'Grand Warden' | 'Royal Champion' | 'Minion Prince' | 'Dragon Duke';
  rarity: 'Common' | 'Epic';
  maxLevel: number;
  rarityNote?: string;
  activationType: 'Active' | 'Passive' | 'Active + Passive';
  thRequired: number;
  blacksmithRequired: string;
  summary: string;
  passiveBonus: string;
  levelMilestones: EquipmentLevelMilestone[];
  sources: { title: string; url: string }[];
  confidence: 'HIGH' | 'MEDIUM' | 'LOW';
}

// Complete Level 1 -> 27 Ore & Blacksmith Progression Table (Common caps at Lvl 18, Epic at Lvl 27)
export const equipmentUpgradeLevels: EquipmentUpgradeStep[] = (() => {
  const stepCosts: Array<{ shiny: number; glowy: number; starry: number; note: string }> = [
    { shiny: 0, glowy: 0, starry: 0, note: 'Unlock baseline level' },
    { shiny: 120, glowy: 0, starry: 0, note: 'Minor stat scaling' },
    { shiny: 240, glowy: 20, starry: 0, note: 'Ability Tier 1 upgrade (Glowy Ore)' },
    { shiny: 400, glowy: 0, starry: 0, note: 'Minor stat scaling' },
    { shiny: 600, glowy: 0, starry: 0, note: 'Minor stat scaling' },
    { shiny: 840, glowy: 100, starry: 0, note: 'Ability Tier 2 upgrade (Glowy Ore)' },
    { shiny: 1120, glowy: 0, starry: 0, note: 'Minor stat scaling' },
    { shiny: 1440, glowy: 0, starry: 0, note: 'Minor stat scaling' },
    { shiny: 1800, glowy: 200, starry: 10, note: 'Blacksmith 1–2 cap · First Starry Ore milestone (Epic)' },
    { shiny: 1900, glowy: 0, starry: 0, note: 'Minor stat scaling (TH10+ / BS 3)' },
    { shiny: 2000, glowy: 0, starry: 0, note: 'Minor stat scaling' },
    { shiny: 2100, glowy: 400, starry: 20, note: 'Blacksmith 3–4 cap · Ability Tier 4 milestone' },
    { shiny: 2200, glowy: 0, starry: 0, note: 'Minor stat scaling (TH12+ / BS 5)' },
    { shiny: 2300, glowy: 0, starry: 0, note: 'Minor stat scaling' },
    { shiny: 2400, glowy: 600, starry: 30, note: 'Blacksmith 5–6 cap · Competitive mid-game sweet spot' },
    { shiny: 2500, glowy: 0, starry: 0, note: 'Minor stat scaling (TH14+ / BS 7)' },
    { shiny: 2600, glowy: 0, starry: 0, note: 'Minor stat scaling' },
    { shiny: 2700, glowy: 600, starry: 50, note: 'Common MAX (Lvl 18) · Critical Epic radius/power spike' },
    { shiny: 2800, glowy: 0, starry: 0, note: 'Epic scaling tier (TH14+ / BS 7)' },
    { shiny: 2900, glowy: 0, starry: 0, note: 'Epic scaling tier' },
    { shiny: 3000, glowy: 600, starry: 100, note: 'Blacksmith 7 cap · CWL-ready Epic breakpoint' },
    { shiny: 3100, glowy: 0, starry: 0, note: 'Epic scaling tier (TH15+ / BS 8)' },
    { shiny: 3200, glowy: 0, starry: 0, note: 'Epic scaling tier' },
    { shiny: 3300, glowy: 600, starry: 120, note: 'Blacksmith 8 cap · Pre-max Epic spike' },
    { shiny: 3400, glowy: 0, starry: 0, note: 'Epic scaling tier (TH16+ / BS 9)' },
    { shiny: 3500, glowy: 0, starry: 0, note: 'Epic scaling tier' },
    { shiny: 3600, glowy: 600, starry: 150, note: 'Epic MAX (Lvl 27) · Blacksmith 9–10 ceiling' },
  ];

  const getCapMeta = (lvl: number): { bs: number; th: number } => {
    if (lvl <= 9) return { bs: 1, th: 8 };
    if (lvl <= 12) return { bs: 3, th: 10 };
    if (lvl <= 15) return { bs: 5, th: 12 };
    if (lvl <= 18) return { bs: 7, th: 14 };
    if (lvl <= 21) return { bs: 7, th: 14 };
    if (lvl <= 24) return { bs: 8, th: 15 };
    return { bs: 9, th: 16 };
  };

  let cumShiny = 0;
  let cumGlowy = 0;
  let cumStarry = 0;

  return stepCosts.map((c, idx) => {
    const level = idx + 1;
    cumShiny += c.shiny;
    cumGlowy += c.glowy;
    cumStarry += c.starry;
    const cap = getCapMeta(level);
    return {
      level,
      blacksmithRequired: cap.bs,
      thRequired: cap.th,
      shinyOre: c.shiny,
      glowyOre: c.glowy,
      starryOre: c.starry,
      cumulativeShiny: cumShiny,
      cumulativeGlowy: cumGlowy,
      cumulativeStarry: cumStarry,
      milestoneNote: c.note,
    };
  });
})();

const commonMilestones = (
  baseTh: number,
  t1: string,
  t3: string,
  t9: string,
  t15: string,
  t18: string
): EquipmentLevelMilestone[] => [
  { level: 1, blacksmith: 1, th: baseTh, effectSummary: t1 },
  { level: 3, blacksmith: 1, th: baseTh, effectSummary: t3 },
  { level: 9, blacksmith: 1, th: Math.max(baseTh, 8), effectSummary: t9 },
  { level: 15, blacksmith: 5, th: Math.max(baseTh, 12), effectSummary: t15 },
  { level: 18, blacksmith: 7, th: Math.max(baseTh, 14), effectSummary: t18 },
];

const epicMilestones = (
  baseTh: number,
  t1: string,
  t9: string,
  t18: string,
  t21: string,
  t27: string
): EquipmentLevelMilestone[] => [
  { level: 1, blacksmith: 1, th: baseTh, effectSummary: t1 },
  { level: 9, blacksmith: 1, th: Math.max(baseTh, 8), effectSummary: t9 },
  { level: 18, blacksmith: 7, th: Math.max(baseTh, 14), effectSummary: t18 },
  { level: 21, blacksmith: 7, th: Math.max(baseTh, 14), effectSummary: t21 },
  { level: 27, blacksmith: 9, th: Math.max(baseTh, 16), effectSummary: t27 },
];

// All 43 Hero Equipment pieces across 6 Heroes
export const heroEquipmentSpecs: HeroEquipmentSpec[] = [
  // ================= BARBARIAN KING (8 pieces) =================
  {
    id: 'eq-barbarian-puppet',
    name: 'Barbarian Puppet',
    hero: 'Barbarian King',
    rarity: 'Common',
    maxLevel: 18,
    activationType: 'Active + Passive',
    thRequired: 7,
    blacksmithRequired: 'Default (TH7 / Blacksmith 1)',
    summary: 'Summons a swarm of enraged Barbarians and heals the King on activation.',
    passiveBonus: 'Passive DPS increase + HP recovery',
    levelMilestones: commonMilestones(
      7,
      'Spawns 8 Barbarians; small HP recovery & +DPS',
      'Spawns 12 Barbarians; Tier 1 passive boost',
      'Spawns 22 Barbarians; reliable early-TH funnel swarm',
      'Spawns 35 Barbarians; strong HP recovery bump',
      'Max Lvl 18: Spawns 44 enraged Barbarians + full passive DPS/HP recovery'
    ),
    sources: [
      { title: 'Fandom Wiki: Barbarian Puppet', url: 'https://clashofclans.fandom.com/wiki/Barbarian_Puppet' },
      { title: 'coc.guide: Barbarian Puppet', url: 'https://coc.guide' },
    ],
    confidence: 'HIGH',
  },
  {
    id: 'eq-rage-vial',
    name: 'Rage Vial',
    hero: 'Barbarian King',
    rarity: 'Common',
    maxLevel: 18,
    activationType: 'Active + Passive',
    thRequired: 7,
    blacksmithRequired: 'Default (TH7 / Blacksmith 1)',
    summary: 'Enrages the King for 10s, dramatically multiplying damage and movement speed.',
    passiveBonus: 'Increases King base DPS',
    levelMilestones: commonMilestones(
      7,
      '10s Rage: +80% Damage & +18 Speed boost',
      '10s Rage: +100% Damage & +20 Speed boost',
      '10s Rage: +130% Damage & +24 Speed boost',
      '10s Rage: +155% Damage & +28 Speed boost',
      'Max Lvl 18: 10s Rage with +170% Damage, +30 Speed & max passive DPS'
    ),
    sources: [
      { title: 'Fandom Wiki: Rage Vial', url: 'https://clashofclans.fandom.com/wiki/Rage_Vial' },
      { title: 'ClashPerk: Rage Vial', url: 'https://clashperk.com' },
    ],
    confidence: 'HIGH',
  },
  {
    id: 'eq-earthquake-boots',
    name: 'Earthquake Boots',
    hero: 'Barbarian King',
    rarity: 'Common',
    maxLevel: 18,
    activationType: 'Active + Passive',
    thRequired: 8,
    blacksmithRequired: 'Blacksmith Level 1 (TH8)',
    summary: 'Creates an 8-tile Earthquake shockwave that destroys Walls and chunks nearby buildings.',
    passiveBonus: 'Flat Hitpoints and DPS bonus',
    levelMilestones: commonMilestones(
      8,
      'Destroys low-level walls in 6–8t radius; 20% building DMG',
      'Upgraded wall-break damage & passive HP boost',
      'One-shots mid-tier walls in 8-tile radius',
      'Reliably breaks TH14+ walls; ~40%+ building HP damage',
      'Max Lvl 18: Instant wall destruction in 8t radius + maximum building HP% damage'
    ),
    sources: [
      { title: 'Fandom Wiki: Earthquake Boots', url: 'https://clashofclans.fandom.com/wiki/Earthquake_Boots' },
      { title: 'coc.guide: Earthquake Boots', url: 'https://coc.guide' },
    ],
    confidence: 'HIGH',
  },
  {
    id: 'eq-vampstache',
    name: 'Vampstache',
    hero: 'Barbarian King',
    rarity: 'Common',
    maxLevel: 18,
    activationType: 'Passive',
    thRequired: 10,
    blacksmithRequired: 'Blacksmith Level 3 (TH10)',
    summary: 'Heals the Barbarian King on every melee swing.',
    passiveBonus: 'Attack Speed boost + passive DPS increase',
    levelMilestones: commonMilestones(
      10,
      'Heals ~120 HP per hit; slight attack speed boost',
      'Heals ~160 HP per hit',
      'Heals ~220 HP per hit + noticeable swing speed increase',
      'Heals ~280 HP per hit; strong outside funnel sustain',
      'Max Lvl 18: Heals 300+ HP per hit with max attack speed & DPS boost'
    ),
    sources: [
      { title: 'Fandom Wiki: Vampstache', url: 'https://clashofclans.fandom.com/wiki/Vampstache' },
      { title: 'ClashPerk: Vampstache', url: 'https://clashperk.com' },
    ],
    confidence: 'HIGH',
  },
  {
    id: 'eq-giant-gauntlet',
    name: 'Giant Gauntlet',
    hero: 'Barbarian King',
    rarity: 'Epic',
    maxLevel: 27,
    activationType: 'Active + Passive',
    thRequired: 8,
    blacksmithRequired: 'Event / Trader / League Shop (Blacksmith 1+)',
    summary: 'Turns the King giant-sized with splash melee damage and heavy damage reduction.',
    passiveBonus: 'Self-healing per second + Hitpoints & DPS boost',
    levelMilestones: epicMilestones(
      8,
      '12s duration; 25% incoming damage reduction & splash cleave',
      '14s duration; ~35% damage reduction; first Starry Ore tier',
      '16s duration; ~45% damage reduction; high passive HP/s heal',
      '16.5s duration; ~48% damage reduction; CWL meta threshold',
      'Max Lvl 27: 17s duration, up to 50% damage reduction, max splash & HP recovery'
    ),
    sources: [
      { title: 'Fandom Wiki: Giant Gauntlet', url: 'https://clashofclans.fandom.com/wiki/Giant_Gauntlet' },
      { title: 'ClashPerk: Giant Gauntlet', url: 'https://clashperk.com' },
    ],
    confidence: 'HIGH',
  },
  {
    id: 'eq-spiky-ball',
    name: 'Spiky Ball',
    hero: 'Barbarian King',
    rarity: 'Epic',
    maxLevel: 27,
    activationType: 'Active + Passive',
    thRequired: 8,
    blacksmithRequired: 'Event / Trader (Blacksmith 1+)',
    summary: 'Throws a spiked ball that bounces across multiple buildings dealing massive burst damage.',
    passiveBonus: 'Large flat Hitpoints & DPS increase',
    levelMilestones: epicMilestones(
      8,
      'Bounces across 4 targets with base burst damage',
      'Bounces across 5 targets; solid early TH cleanup burst',
      'Bounces across 7 targets; heavy passive HP & DPS jump',
      'Bounces across 8 targets; CWL compartment-clear breakpoint',
      'Max Lvl 27: Maximum bounce damage across up to 8 structures + peak passive stats'
    ),
    sources: [
      { title: 'Fandom Wiki: Spiky Ball', url: 'https://clashofclans.fandom.com/wiki/Spiky_Ball' },
      { title: 'ClashPerk: Spiky Ball', url: 'https://clashperk.com' },
    ],
    confidence: 'HIGH',
  },
  {
    id: 'eq-snake-bracelet',
    name: 'Snake Bracelet',
    hero: 'Barbarian King',
    rarity: 'Epic',
    maxLevel: 27,
    activationType: 'Passive',
    thRequired: 8,
    blacksmithRequired: 'Event / Trader (Blacksmith 1+)',
    summary: 'Summons Snakes to distract defenses and assist whenever the King takes damage.',
    passiveBonus: 'Boosts Hitpoints, DPS, and HP recovery',
    levelMilestones: epicMilestones(
      8,
      'Spawns low-level Snakes on incoming damage hits',
      'Increases Snake spawn count & Snake level cap',
      'High Snake durability + strong passive HP bonus',
      'CWL funnel tanking threshold with elevated Snake cap',
      'Max Lvl 27: Maximum Snake spawns, peak Snake level & King HP/DPS scaling'
    ),
    sources: [
      { title: 'Fandom Wiki: Snake Bracelet', url: 'https://clashofclans.fandom.com/wiki/Snake_Bracelet' },
      { title: 'ClashPerk: Snake Bracelet', url: 'https://clashperk.com' },
    ],
    confidence: 'HIGH',
  },
  {
    id: 'eq-stick-horse',
    name: 'Stick Horse',
    hero: 'Barbarian King',
    rarity: 'Epic',
    maxLevel: 27,
    activationType: 'Active + Passive',
    thRequired: 8,
    blacksmithRequired: 'Event / Trader (Blacksmith 1+)',
    summary: 'Enables the Barbarian King to leap directly over Walls with boosted mobility.',
    passiveBonus: 'Passive Hitpoints and speed scaling',
    levelMilestones: epicMilestones(
      8,
      'Enables base wall-jump mobility boost',
      'Extended mobility duration + higher passive HP',
      'Strong wall-leap uptime for hybrid core dives',
      'CWL-ready cooldown/duration jump with Spiky Ball combo',
      'Max Lvl 27: Maximum wall-jumping ability uptime & passive stat ceiling'
    ),
    sources: [
      { title: 'Fandom Wiki: Stick Horse', url: 'https://clashofclans.fandom.com/wiki/Stick_Horse' },
    ],
    confidence: 'HIGH',
  },

  // ================= ARCHER QUEEN (8 pieces) =================
  {
    id: 'eq-archer-puppet',
    name: 'Archer Puppet',
    hero: 'Archer Queen',
    rarity: 'Common',
    maxLevel: 18,
    activationType: 'Active + Passive',
    thRequired: 9,
    blacksmithRequired: 'Default (TH9 / Blacksmith 2)',
    summary: 'Summons Archers around the Queen and recovers Hitpoints.',
    passiveBonus: 'Passive DPS boost',
    levelMilestones: commonMilestones(
      9,
      'Spawns 8 Archers + small HP recovery',
      'Spawns 11 Archers + Tier 1 DPS boost',
      'Spawns 18 Archers; baseline TH9-10 boost',
      'Spawns 26 Archers; significant HP recovery',
      'Max Lvl 18: Spawns 31 Archers + max passive DPS increase'
    ),
    sources: [{ title: 'Fandom Wiki: Archer Puppet', url: 'https://clashofclans.fandom.com/wiki/Archer_Puppet' }],
    confidence: 'HIGH',
  },
  {
    id: 'eq-invisibility-vial',
    name: 'Invisibility Vial',
    hero: 'Archer Queen',
    rarity: 'Common',
    maxLevel: 18,
    activationType: 'Active + Passive',
    thRequired: 9,
    blacksmithRequired: 'Default (TH9 / Blacksmith 2)',
    summary: 'Renders the Queen invisible to defenses while granting huge per-shot bonus damage.',
    passiveBonus: 'Passive DPS increase',
    levelMilestones: commonMilestones(
      9,
      '4.5s invisibility + moderate bonus damage',
      '5.0s invisibility + Tier 1 DPS boost',
      '6.0s invisibility; solid Queen Charge safety window',
      '7.0s invisibility + high burst shot damage',
      'Max Lvl 18: 7.5s invisibility + maximum burst DPS bonus'
    ),
    sources: [{ title: 'Fandom Wiki: Invisibility Vial', url: 'https://clashofclans.fandom.com/wiki/Invisibility_Vial' }],
    confidence: 'HIGH',
  },
  {
    id: 'eq-giant-arrow',
    name: 'Giant Arrow',
    hero: 'Archer Queen',
    rarity: 'Common',
    maxLevel: 18,
    activationType: 'Active + Passive',
    thRequired: 9,
    blacksmithRequired: 'Blacksmith Level 2 (TH9)',
    summary: 'Fires a map-wide piercing arrow triggering traps and sniping Air Defenses & Sweepers.',
    passiveBonus: 'Passive Hitpoints and DPS bonus',
    levelMilestones: commonMilestones(
      9,
      'Fires full-map arrow; base burst damage',
      'Clears low-level Sweepers on line hit',
      'One-shots mid-TH Air Sweepers',
      'One-shots high-level Air Defenses (TH14–15)',
      'Max Lvl 18: One-shots max Air Defenses & Sweepers across the entire map'
    ),
    sources: [{ title: 'Fandom Wiki: Giant Arrow', url: 'https://clashofclans.fandom.com/wiki/Giant_Arrow' }],
    confidence: 'HIGH',
  },
  {
    id: 'eq-healer-puppet',
    name: 'Healer Puppet',
    hero: 'Archer Queen',
    rarity: 'Common',
    maxLevel: 18,
    activationType: 'Active + Passive',
    thRequired: 12,
    blacksmithRequired: 'Blacksmith Level 5 (TH12)',
    summary: 'Spawns up to 3 housing-free Healers onto the Queen on activation.',
    passiveBonus: 'Self-healing per second + flat Hitpoints boost',
    levelMilestones: commonMilestones(
      12,
      'Spawns 1–2 Healers; modest passive HP/s',
      'Upgrades spawned Healer level',
      'Spawns 2 Healers with stronger passive heal',
      'Spawns 3 Healers (critical breakpoint)',
      'Max Lvl 18: Spawns 3 max-tier Healers + peak self-healing & HP boost'
    ),
    sources: [{ title: 'Fandom Wiki: Healer Puppet', url: 'https://clashofclans.fandom.com/wiki/Healer_Puppet' }],
    confidence: 'HIGH',
  },
  {
    id: 'eq-frozen-arrow',
    name: 'Frozen Arrow',
    hero: 'Archer Queen',
    rarity: 'Epic',
    maxLevel: 27,
    activationType: 'Passive',
    thRequired: 9,
    blacksmithRequired: 'Event / Trader (Blacksmith 2+)',
    summary: 'Chills and slows defenses and enemy heroes with every Queen shot.',
    passiveBonus: 'Passive DPS increase',
    levelMilestones: epicMilestones(
      9,
      '30% slow on hit targets',
      '45% slow on hit targets',
      '60% slow; counters Single Infernos & Monoliths',
      '65% slow + strong passive DPS',
      'Max Lvl 27: Up to 75% target slow + peak passive DPS boost'
    ),
    sources: [{ title: 'Fandom Wiki: Frozen Arrow', url: 'https://clashofclans.fandom.com/wiki/Frozen_Arrow' }],
    confidence: 'HIGH',
  },
  {
    id: 'eq-magic-mirror',
    name: 'Magic Mirror',
    hero: 'Archer Queen',
    rarity: 'Epic',
    maxLevel: 27,
    activationType: 'Active + Passive',
    thRequired: 9,
    blacksmithRequired: 'Event / Trader (Blacksmith 2+)',
    summary: 'Summons up to 2 attacking Queen clone illusions with brief 1s invisibility.',
    passiveBonus: 'Flat Hitpoints and HP recovery boost',
    levelMilestones: epicMilestones(
      9,
      'Summons 1 Queen clone illusion',
      'Increases clone HP & damage percentage',
      'Summons 2 Queen clone illusions (major power spike)',
      'Extended clone duration (~27s) with higher clone DPS',
      'Max Lvl 27: 2 full-duration high-DPS Queen clones + peak HP recovery'
    ),
    sources: [{ title: 'Fandom Wiki: Magic Mirror', url: 'https://clashofclans.fandom.com/wiki/Magic_Mirror' }],
    confidence: 'HIGH',
  },
  {
    id: 'eq-action-figure',
    name: 'Action Figure',
    hero: 'Archer Queen',
    rarity: 'Epic',
    maxLevel: 27,
    activationType: 'Active + Passive',
    thRequired: 9,
    blacksmithRequired: 'Event / Trader (Blacksmith 2+)',
    summary: 'Summons a massive Giant Giant frontline tank alongside the Queen.',
    passiveBonus: 'Boosts Queen DPS, Hitpoints, and HP recovery',
    levelMilestones: epicMilestones(
      9,
      'Summons base Giant Giant tank',
      'Scales Giant Giant HP & damage',
      'Strong tank HP (~13,000+) for core pushing',
      'CWL threshold (~15,500+ Giant Giant HP)',
      'Max Lvl 27: Giant Giant exceeds 18,000 HP + peak Queen passive bonuses'
    ),
    sources: [{ title: 'Fandom Wiki: Action Figure', url: 'https://clashofclans.fandom.com/wiki/Action_Figure' }],
    confidence: 'HIGH',
  },
  {
    id: 'eq-monolith-arrow',
    name: 'Monolith Arrow',
    hero: 'Archer Queen',
    rarity: 'Epic',
    maxLevel: 27,
    activationType: 'Active + Passive',
    thRequired: 9,
    blacksmithRequired: 'Event / Trader (Blacksmith 2+)',
    summary: 'Fires a heavy high-HP structure-shredding projectile line through defenses.',
    passiveBonus: 'Passive DPS and Hitpoints scaling',
    levelMilestones: epicMilestones(
      9,
      'Unlocks Monolith-piercing projectile line',
      'Increases line damage and passive DPS',
      'Strong burst against high-HP cores & storages',
      'CWL sniping damage threshold',
      'Max Lvl 27: Maximum piercing projectile burst + full passive HP/DPS'
    ),
    sources: [{ title: 'Fandom Wiki: Monolith Arrow', url: 'https://clashofclans.fandom.com/wiki/Monolith_Arrow' }],
    confidence: 'HIGH',
  },

  // ================= MINION PRINCE (7 pieces) =================
  {
    id: 'eq-henchmen-puppet',
    name: 'Henchmen Puppet',
    hero: 'Minion Prince',
    rarity: 'Common',
    maxLevel: 18,
    activationType: 'Active + Passive',
    thRequired: 9,
    blacksmithRequired: 'Default (TH9 / Hero Hall 3)',
    summary: 'Grants brief invisibility and summons flying Henchman bodyguards to absorb Seeking Air Mines.',
    passiveBonus: 'Passive DPS and HP recovery bonus',
    levelMilestones: commonMilestones(
      9,
      'Brief invisibility + summons 2 Henchmen',
      'Upgrades Henchman HP/DPS',
      'Improved invisibility buffer & Henchmen tanking',
      'High-HP Henchmen bodyguards for Dragon/Lalo raids',
      'Max Lvl 18: Peak Henchmen stats + max passive DPS/HP recovery'
    ),
    sources: [{ title: 'Fandom Wiki: Henchmen Puppet', url: 'https://clashofclans.fandom.com/wiki/Henchmen_Puppet' }],
    confidence: 'HIGH',
  },
  {
    id: 'eq-dark-orb',
    name: 'Dark Orb',
    hero: 'Minion Prince',
    rarity: 'Common',
    maxLevel: 18,
    activationType: 'Active + Passive',
    thRequired: 9,
    blacksmithRequired: 'Default (TH9 / Hero Hall 3)',
    summary: 'Launches a huge piercing Dark Orb across the map dealing splash damage and slowing defenses by 50%.',
    passiveBonus: 'Passive Hitpoints and DPS bonus',
    levelMilestones: commonMilestones(
      9,
      'Piercing orb; ~8s defensive slow',
      'Expanded slow duration & orb burst',
      '~12s slow duration; strong air defense suppression',
      '~16s slow duration (meta stopping tier)',
      'Max Lvl 18: Up to 18s 50% defense slow + max orb splash damage'
    ),
    sources: [{ title: 'Fandom Wiki: Dark Orb', url: 'https://clashofclans.fandom.com/wiki/Dark_Orb' }],
    confidence: 'HIGH',
  },
  {
    id: 'eq-metal-pants',
    name: 'Metal Pants',
    hero: 'Minion Prince',
    rarity: 'Common',
    maxLevel: 18,
    activationType: 'Active + Passive',
    thRequired: 10,
    blacksmithRequired: 'Blacksmith Level 3 (TH10)',
    summary: 'Projects a protective armor barrier cutting all incoming damage by up to 70%.',
    passiveBonus: 'Passive Hitpoints and HP recovery',
    levelMilestones: commonMilestones(
      10,
      '~40% damage reduction barrier',
      '~48% damage reduction',
      '~56% damage reduction; absorbs Seeking Air Mines',
      '~65% damage reduction for 10–12s',
      'Max Lvl 18: Up to 70% damage reduction for 12s + peak HP recovery'
    ),
    sources: [{ title: 'Fandom Wiki: Metal Pants', url: 'https://clashofclans.fandom.com/wiki/Metal_Pants' }],
    confidence: 'HIGH',
  },
  {
    id: 'eq-noble-iron',
    name: 'Noble Iron',
    hero: 'Minion Prince',
    rarity: 'Common',
    maxLevel: 18,
    activationType: 'Passive',
    thRequired: 11,
    blacksmithRequired: 'Blacksmith Level 4 (TH11)',
    summary: 'Empowers opening shots with extended sniping range, boosted attack speed, and bonus damage.',
    passiveBonus: 'Passive DPS scaling',
    levelMilestones: commonMilestones(
      11,
      'First 4 shots empowered with extended range',
      'Higher opening shot damage multiplier',
      'More empowered opening shots + faster burst',
      'Long-range opening snipe for air funneling',
      'Max Lvl 18: Maximum empowered opening volleys + peak passive DPS'
    ),
    sources: [{ title: 'Fandom Wiki: Noble Iron', url: 'https://clashofclans.fandom.com/wiki/Noble_Iron' }],
    confidence: 'HIGH',
  },
  {
    id: 'eq-dark-crown',
    name: 'Dark Crown',
    hero: 'Minion Prince',
    rarity: 'Epic',
    maxLevel: 27,
    activationType: 'Passive',
    thRequired: 9,
    blacksmithRequired: 'Event / Trader (Blacksmith 2+)',
    summary: 'Stacks up to 3 progressive health and damage buffs as friendly army units fall.',
    passiveBonus: 'Baseline Hitpoints and DPS boost',
    levelMilestones: epicMilestones(
      9,
      'Base 3-stack scaling on ally defeat',
      'Stronger per-stack HP/DPS multiplier',
      'Major late-raid cleanup scaling breakpoint',
      'CWL endgame power surge at 3 stacks',
      'Max Lvl 27: Maximum 3-stack damage/HP boost for late-raid carries'
    ),
    sources: [{ title: 'Fandom Wiki: Dark Crown', url: 'https://clashofclans.fandom.com/wiki/Dark_Crown' }],
    confidence: 'HIGH',
  },
  {
    id: 'eq-meteor-staff',
    name: 'Meteor Staff',
    hero: 'Minion Prince',
    rarity: 'Epic',
    maxLevel: 27,
    activationType: 'Active + Passive',
    thRequired: 9,
    blacksmithRequired: 'Event / Trader (Blacksmith 2+)',
    summary: 'Calls down meteor strikes boosting air raid burst damage across clustered defenses.',
    passiveBonus: 'Passive Hitpoints and DPS increase',
    levelMilestones: epicMilestones(
      9,
      'Calls down base meteor burst',
      'Increases meteor impact damage & radius',
      'Clears dense TH15+ air-defense pockets',
      'CWL burst threshold',
      'Max Lvl 27: Peak meteor strike damage + full passive HP/DPS'
    ),
    sources: [{ title: 'Fandom Wiki: Meteor Staff', url: 'https://clashofclans.fandom.com/wiki/Meteor_Staff' }],
    confidence: 'HIGH',
  },
  {
    id: 'eq-portal-pendant',
    name: 'Portal Pendant',
    hero: 'Minion Prince',
    rarity: 'Epic',
    maxLevel: 27,
    activationType: 'Active + Passive',
    thRequired: 9,
    blacksmithRequired: 'Event / Trader (Blacksmith 2+)',
    summary: 'Provides dimensional repositioning and troop support utility during aerial assaults.',
    passiveBonus: 'Passive Hitpoints and speed scaling',
    levelMilestones: epicMilestones(
      9,
      'Unlocks base dimensional utility effect',
      'Improved uptime & passive stats',
      'Mid-to-late epic tactical utility spike',
      'CWL threshold',
      'Max Lvl 27: Maximum portal duration/effect + full passive scaling'
    ),
    sources: [{ title: 'Fandom Wiki: Portal Pendant', url: 'https://clashofclans.fandom.com/wiki/Portal_Pendant' }],
    confidence: 'HIGH',
  },

  // ================= GRAND WARDEN (7 pieces) =================
  {
    id: 'eq-eternal-tome',
    name: 'Eternal Tome',
    hero: 'Grand Warden',
    rarity: 'Common',
    maxLevel: 18,
    activationType: 'Active',
    thRequired: 11,
    blacksmithRequired: 'Default (TH11 / Blacksmith 4)',
    summary: 'Grants complete invulnerability to the Warden and nearby troops inside his aura.',
    passiveBonus: 'None (pure active invulnerability anchor)',
    levelMilestones: commonMilestones(
      11,
      '5.0s total invulnerability duration',
      '5.5s invulnerability duration',
      '6.5s invulnerability duration',
      '7.5s invulnerability (widely used sweet spot)',
      'Max Lvl 18: 8.0s–9.5s full aura invulnerability (scales nearly every level)'
    ),
    sources: [{ title: 'Fandom Wiki: Eternal Tome', url: 'https://clashofclans.fandom.com/wiki/Eternal_Tome' }],
    confidence: 'HIGH',
  },
  {
    id: 'eq-life-gem',
    name: 'Life Gem',
    hero: 'Grand Warden',
    rarity: 'Common',
    maxLevel: 18,
    activationType: 'Passive',
    thRequired: 11,
    blacksmithRequired: 'Default (TH11 / Blacksmith 4)',
    summary: 'Passively boosts maximum Hitpoints of all troops inside the Warden aura up to a cap.',
    passiveBonus: 'Increases Grand Warden base DPS and HP',
    levelMilestones: commonMilestones(
      11,
      '+35% aura HP boost (low HP cap)',
      '+45% aura HP boost',
      '+65% aura HP boost',
      '+85% aura HP boost',
      'Max Lvl 18: Up to +100% aura HP boost (capped) + max Warden HP/DPS'
    ),
    sources: [{ title: 'Fandom Wiki: Life Gem', url: 'https://clashofclans.fandom.com/wiki/Life_Gem' }],
    confidence: 'HIGH',
  },
  {
    id: 'eq-rage-gem',
    name: 'Rage Gem',
    hero: 'Grand Warden',
    rarity: 'Common',
    maxLevel: 18,
    activationType: 'Passive',
    thRequired: 11,
    blacksmithRequired: 'Blacksmith Level 4 (TH11)',
    summary: 'Continuously increases attack damage (+50% max) of friendly troops and heroes in aura.',
    passiveBonus: 'Increases Grand Warden attack speed and DPS',
    levelMilestones: commonMilestones(
      11,
      '+20% passive aura damage boost',
      '+25% passive aura damage boost',
      '+35% passive aura damage boost',
      '+45% passive aura damage boost',
      'Max Lvl 18: +50% continuous aura damage boost + max Warden attack speed'
    ),
    sources: [{ title: 'Fandom Wiki: Rage Gem', url: 'https://clashofclans.fandom.com/wiki/Rage_Gem' }],
    confidence: 'HIGH',
  },
  {
    id: 'eq-healing-tome',
    name: 'Healing Tome',
    hero: 'Grand Warden',
    rarity: 'Common',
    maxLevel: 18,
    activationType: 'Active + Passive',
    thRequired: 13,
    blacksmithRequired: 'Blacksmith Level 6 (TH13)',
    summary: 'Emits a rapid healing pulse across the Warden aura countering Multi-Infernos and Scattershots.',
    passiveBonus: 'Increases Warden Hitpoints and HP recovery',
    levelMilestones: commonMilestones(
      13,
      '14s healing pulse; modest HPS',
      '16s healing pulse',
      '18s healing pulse',
      '20s healing pulse (strong hybrid/smash sustain)',
      'Max Lvl 18: 22s healing pulse + peak HPS & Warden HP recovery'
    ),
    sources: [{ title: 'Fandom Wiki: Healing Tome', url: 'https://clashofclans.fandom.com/wiki/Healing_Tome' }],
    confidence: 'HIGH',
  },
  {
    id: 'eq-fireball',
    name: 'Fireball',
    hero: 'Grand Warden',
    rarity: 'Epic',
    maxLevel: 27,
    activationType: 'Active + Passive',
    thRequired: 11,
    blacksmithRequired: 'Event / Trader (Blacksmith 4+)',
    summary: 'Launches an explosive Fireball at the nearest defense with massive splash damage.',
    passiveBonus: 'Substantial flat DPS increase for Warden Walks',
    levelMilestones: epicMilestones(
      11,
      'Small splash radius; low burst damage',
      'Expanded radius; chips key core defenses',
      'CRITICAL Lvl 18: Unlocks 6-tile radius to one-shot core defenses w/ Quake',
      'Lvl 21: Reliably deletes Monolith/Scattershot pockets',
      'Max Lvl 27: 4,100+ Fireball splash damage across 6-tile radius'
    ),
    sources: [{ title: 'Fandom Wiki: Fireball', url: 'https://clashofclans.fandom.com/wiki/Fireball' }],
    confidence: 'HIGH',
  },
  {
    id: 'eq-heroic-torch',
    name: 'Heroic Torch',
    hero: 'Grand Warden',
    rarity: 'Epic',
    maxLevel: 27,
    activationType: 'Active + Passive',
    thRequired: 11,
    blacksmithRequired: 'Event / Trader (Blacksmith 4+)',
    summary: 'Allows ground troops inside the aura to walk straight through Walls with speed & damage resistance.',
    passiveBonus: 'Increases Warden DPS, max HP, and HP recovery',
    levelMilestones: epicMilestones(
      11,
      'Short wall-bypass aura with minor damage reduction',
      'Longer aura uptime + improved speed boost',
      'Major wall-bypass window for Valkyrie/Root/Yeti smashes',
      'CWL threshold with high incoming damage resistance',
      'Max Lvl 27: Peak aura duration, speed boost, and damage reduction'
    ),
    sources: [{ title: 'Fandom Wiki: Heroic Torch', url: 'https://clashofclans.fandom.com/wiki/Heroic_Torch' }],
    confidence: 'HIGH',
  },
  {
    id: 'eq-lavaloon-puppet',
    name: 'Lavaloon Puppet',
    hero: 'Grand Warden',
    rarity: 'Epic',
    maxLevel: 27,
    activationType: 'Active + Passive',
    thRequired: 11,
    blacksmithRequired: 'Event / Trader (Blacksmith 4+)',
    summary: 'Spawns high-HP flying Lavaloons directly into the raid to soak Seeking Air Mines and snipe defenses.',
    passiveBonus: 'Increases Warden Hitpoints and HP recovery',
    levelMilestones: epicMilestones(
      11,
      'Spawns 1 base-level Lavaloon',
      'Upgrades spawned Lavaloon tier',
      'Spawns 2 Lavaloons (key power spike)',
      'Higher Lavaloon HP & Lavapup spawns',
      'Max Lvl 27: Spawns max-tier Lavaloons + full Warden passive HP'
    ),
    sources: [{ title: 'Fandom Wiki: Lavaloon Puppet', url: 'https://clashofclans.fandom.com/wiki/Lavaloon_Puppet' }],
    confidence: 'HIGH',
  },

  // ================= ROYAL CHAMPION (7 pieces) =================
  {
    id: 'eq-haste-vial',
    name: 'Haste Vial',
    hero: 'Royal Champion',
    rarity: 'Common',
    maxLevel: 18,
    activationType: 'Active + Passive',
    thRequired: 15,
    blacksmithRequired: 'Blacksmith Level 8 (TH15)',
    summary: 'Supercharges Royal Champion movement and attack speed to tear through defensive cores.',
    passiveBonus: 'Passive Attack Speed and DPS increase',
    levelMilestones: commonMilestones(
      15,
      '7.5s haste burst; moderate speed boost',
      '8.5s haste burst',
      '9.5s haste burst',
      '10.5s haste burst (strong Hog/Spirit Fox pairing)',
      'Max Lvl 18: 11.5s extreme attack speed burst + peak passive DPS'
    ),
    sources: [{ title: 'Fandom Wiki: Haste Vial', url: 'https://clashofclans.fandom.com/wiki/Haste_Vial' }],
    confidence: 'HIGH',
  },
  {
    id: 'eq-rocket-spear',
    name: 'Rocket Spear',
    hero: 'Royal Champion',
    rarity: 'Epic',
    maxLevel: 27,
    rarityNote: 'User table marked Common (18); Fandom Wiki & ClashPerk classify as Epic (Max 27)',
    activationType: 'Active + Passive',
    thRequired: 13,
    blacksmithRequired: 'Event / Trader (Blacksmith 6+)',
    summary: 'Empowers next spears with 10-tile standoff range and explosive splash damage.',
    passiveBonus: 'Substantial DPS and Hitpoints scaling',
    levelMilestones: epicMilestones(
      13,
      '5 empowered 10-tile splash spears',
      '6–7 empowered spears; higher splash damage',
      '8–9 empowered spears; sniper funnel breakpoint',
      '9 empowered high-damage spears',
      'Max Lvl 27: Up to 10 empowered 10-tile spears + max passive DPS/HP'
    ),
    sources: [
      { title: 'Fandom Wiki: Rocket Spear', url: 'https://clashofclans.fandom.com/wiki/Rocket_Spear' },
      { title: 'ClashPerk: Rocket Spear', url: 'https://clashperk.com' },
    ],
    confidence: 'LOW',
  },
  {
    id: 'eq-seeking-shield',
    name: 'Seeking Shield',
    hero: 'Royal Champion',
    rarity: 'Common',
    maxLevel: 18,
    activationType: 'Active + Passive',
    thRequired: 13,
    blacksmithRequired: 'Default (TH13 / Blacksmith 6)',
    summary: 'Throws buckler shield bouncing across 4 defenses dealing high burst damage.',
    passiveBonus: 'Passive Hitpoints boost',
    levelMilestones: commonMilestones(
      13,
      '1,200 shield damage across 4 defenses',
      '1,450 shield damage',
      '1,900 shield damage',
      '2,450 shield damage',
      'Max Lvl 18: Up to 2,800–3,200 shield damage across 4 defenses + peak HP'
    ),
    sources: [{ title: 'Fandom Wiki: Seeking Shield', url: 'https://clashofclans.fandom.com/wiki/Seeking_Shield' }],
    confidence: 'HIGH',
  },
  {
    id: 'eq-frost-flake',
    name: 'Frost Flake',
    hero: 'Royal Champion',
    rarity: 'Epic',
    maxLevel: 27,
    rarityNote: 'User table marked Common (18); Fandom Wiki & ClashPerk classify as Epic (Max 27)',
    activationType: 'Active + Passive',
    thRequired: 13,
    blacksmithRequired: 'Event / Trader (Blacksmith 6+)',
    summary: 'Throws freezing/slowing projectiles locking down multiple nearby defenses.',
    passiveBonus: 'Passive Hitpoints and utility scaling',
    levelMilestones: epicMilestones(
      13,
      'Slows/freezes 2–3 nearby targets briefly',
      'Increases target count & freeze duration',
      'Strong multi-defense lockdown for deep RC dives',
      'CWL freeze duration spike',
      'Max Lvl 27: Maximum frozen target count, duration & passive HP'
    ),
    sources: [
      { title: 'Fandom Wiki: Frost Flake', url: 'https://clashofclans.fandom.com/wiki/Frost_Flake' },
      { title: 'ClashPerk: Frost Flake', url: 'https://clashperk.com' },
    ],
    confidence: 'LOW',
  },
  {
    id: 'eq-hog-rider-puppet',
    name: 'Hog Rider Puppet',
    hero: 'Royal Champion',
    rarity: 'Common',
    maxLevel: 18,
    activationType: 'Active + Passive',
    thRequired: 14,
    blacksmithRequired: 'Blacksmith Level 7 (TH14)',
    summary: 'Grants 1s invisibility and spawns up to 9 Hog Riders to tank single-target defenses.',
    passiveBonus: 'Flat HP and HP recovery',
    levelMilestones: commonMilestones(
      14,
      '1s invisibility + 5 Hog Riders',
      '6 Hog Riders',
      '7 Hog Riders; upgrades Hog Rider level',
      '8 Hog Riders; strong defense distraction',
      'Max Lvl 18: 1s invisibility + 9 max-level Hog Riders + peak HP recovery'
    ),
    sources: [{ title: 'Fandom Wiki: Hog Rider Puppet', url: 'https://clashofclans.fandom.com/wiki/Hog_Rider_Puppet' }],
    confidence: 'HIGH',
  },
  {
    id: 'eq-royal-gem',
    name: 'Royal Gem',
    hero: 'Royal Champion',
    rarity: 'Common',
    maxLevel: 18,
    activationType: 'Active + Passive',
    thRequired: 13,
    blacksmithRequired: 'Default (TH13 / Blacksmith 6)',
    summary: 'Instantly heals a huge chunk of Royal Champion Hitpoints upon activation.',
    passiveBonus: 'Boosts Royal Champion DPS and maximum HP',
    levelMilestones: commonMilestones(
      13,
      '+1,200 instant HP recovery',
      '+1,550 instant HP recovery',
      '+2,150 instant HP recovery',
      '+2,850 instant HP recovery',
      'Max Lvl 18: +3,300–3,750 instant HP recovery + max passive DPS/HP'
    ),
    sources: [{ title: 'Fandom Wiki: Royal Gem', url: 'https://clashofclans.fandom.com/wiki/Royal_Gem' }],
    confidence: 'HIGH',
  },
  {
    id: 'eq-electro-boots',
    name: 'Electro Boots',
    hero: 'Royal Champion',
    rarity: 'Epic',
    maxLevel: 27,
    activationType: 'Passive',
    thRequired: 13,
    blacksmithRequired: 'Event / Trader (Blacksmith 6+)',
    summary: 'Emits a continuous electric aura zapping surrounding buildings, CC troops, and Skeletons.',
    passiveBonus: 'Self-healing per second + flat Hitpoints bonus',
    levelMilestones: epicMilestones(
      13,
      '~100 DPS aura pulse; clears Skeleton traps',
      '~135 DPS aura pulse; solid Spirit Walk opener',
      '~175 DPS aura pulse + strong HP/s heal',
      '~190 DPS aura pulse (CWL Spirit Walk meta)',
      'Max Lvl 27: ~200+ DPS continuous shock aura + peak HP/s regeneration'
    ),
    sources: [{ title: 'Fandom Wiki: Electro Boots', url: 'https://clashofclans.fandom.com/wiki/Electro_Boots' }],
    confidence: 'HIGH',
  },

  // ================= DRAGON DUKE (6 pieces) =================
  {
    id: 'eq-fire-heart',
    name: 'Fire Heart',
    hero: 'Dragon Duke',
    rarity: 'Common',
    maxLevel: 18,
    activationType: 'Passive',
    thRequired: 15,
    blacksmithRequired: 'Default (TH15 / Hero Hall 9)',
    summary: 'Grants continuous HP/s regeneration without breaking Royal Rampage isolation, plus fiery death blast.',
    passiveBonus: 'Passive Hitpoints + continuous HP/s self-healing',
    levelMilestones: commonMilestones(
      15,
      'Modest HP/s self-heal + base fiery death blast',
      'Upgraded death explosion damage',
      '~120 HP/s self-heal; preserves solo Royal Rampage',
      '~155 HP/s self-heal + heavy death shockwave',
      'Max Lvl 18: ~175 HP/s continuous self-heal + max fiery death explosion'
    ),
    sources: [
      { title: 'Fandom Wiki: Fire Heart', url: 'https://clashofclans.fandom.com/wiki/Fire_Heart' },
      { title: 'ClashPerk: Fire Heart', url: 'https://clashperk.com' },
    ],
    confidence: 'HIGH',
  },
  {
    id: 'eq-flame-blower',
    name: 'Flame Blower',
    hero: 'Dragon Duke',
    rarity: 'Common',
    maxLevel: 18,
    activationType: 'Active + Passive',
    thRequired: 15,
    blacksmithRequired: 'Default (TH15 / Hero Hall 9)',
    summary: 'Breathes a directional cone of fire scorching structures and defending units ahead.',
    passiveBonus: 'Passive DPS and Hitpoints increase',
    levelMilestones: commonMilestones(
      15,
      'Base forward fire cone burst',
      'Improved cone damage',
      'Clears trash & defending CC clusters reliably',
      'High splash cone damage for Dragon Duke funnels',
      'Max Lvl 18: Peak directional flame burst + full passive DPS/HP'
    ),
    sources: [{ title: 'Fandom Wiki: Flame Blower', url: 'https://clashofclans.fandom.com/wiki/Flame_Blower' }],
    confidence: 'HIGH',
  },
  {
    id: 'eq-stun-blaster',
    name: 'Stun Blaster',
    hero: 'Dragon Duke',
    rarity: 'Common',
    maxLevel: 18,
    activationType: 'Active + Passive',
    thRequired: 15,
    blacksmithRequired: 'Blacksmith Level 8 (TH15)',
    summary: 'Releases an 8-tile AoE shockwave damaging and stunning surrounding defenses and troops.',
    passiveBonus: 'Passive Hitpoints and damage boost',
    levelMilestones: commonMilestones(
      15,
      '8-tile shockwave with brief defense stun',
      'Longer stun duration + shockwave damage',
      'Resets Single Infernos & Monoliths in 8t radius',
      'Strong multi-defense lockdown window',
      'Max Lvl 18: Maximum 8-tile stun duration & AoE burst + peak HP/DPS'
    ),
    sources: [
      { title: 'Fandom Wiki: Stun Blaster', url: 'https://clashofclans.fandom.com/wiki/Stun_Blaster' },
      { title: 'ClashPerk: Stun Blaster', url: 'https://clashperk.com' },
    ],
    confidence: 'HIGH',
  },
  {
    id: 'eq-electro-fangs',
    name: 'Electro Fangs',
    hero: 'Dragon Duke',
    rarity: 'Common',
    maxLevel: 18,
    activationType: 'Passive',
    thRequired: 15,
    blacksmithRequired: 'Blacksmith Level 8 (TH15)',
    summary: 'Imbues Dragon Duke attacks with chain lightning bouncing onto adjacent buildings.',
    passiveBonus: 'Passive Hitpoints boost',
    levelMilestones: commonMilestones(
      15,
      'Adds short chain-lightning bounce to attacks',
      'Higher chain bounce damage percentage',
      'Clears clustered compartments faster while solo enraged',
      'High chain damage scaling under Royal Rampage',
      'Max Lvl 18: Maximum chain-lightning bounce damage + full passive HP'
    ),
    sources: [
      { title: 'Fandom Wiki: Electro Fangs', url: 'https://clashofclans.fandom.com/wiki/Electro_Fangs' },
      { title: 'ClashPerk: Electro Fangs', url: 'https://clashperk.com' },
    ],
    confidence: 'HIGH',
  },
  {
    id: 'eq-rocket-backpack',
    name: 'Rocket Backpack',
    hero: 'Dragon Duke',
    rarity: 'Epic',
    maxLevel: 27,
    rarityNote: 'User table marked Common (18); LDShop & ClashPerk classify as Epic (Max 27)',
    activationType: 'Active + Passive',
    thRequired: 15,
    blacksmithRequired: 'Event / Trader (Blacksmith 8+)',
    summary: 'Propels the Dragon Duke in a straight line across the village breathing fire and slicing compartments.',
    passiveBonus: 'Passive Hitpoints and burst pathing scaling',
    levelMilestones: epicMilestones(
      15,
      'Enables straight-line aerial dash & trail fire',
      'Lvl 9: First major pathing damage jump for funneling',
      'Lvl 18: Mid-tier dash survivability & boosted trail DPS',
      'Lvl 21: Massive active damage spike (CWL minimum target)',
      'Max Lvl 27: Peak straight-line dash damage & core slicing impact'
    ),
    sources: [
      { title: 'ClashPerk: Rocket Backpack', url: 'https://clashperk.com' },
      { title: 'LDShop: Dragon Duke Rocket Backpack Guide', url: 'https://www.ldshop.gg' },
    ],
    confidence: 'LOW',
  },
  {
    id: 'eq-revenge-deck',
    name: 'Revenge Deck',
    hero: 'Dragon Duke',
    rarity: 'Epic',
    maxLevel: 27,
    activationType: 'Passive',
    thRequired: 15,
    blacksmithRequired: 'Event / Trader (Blacksmith 8+)',
    summary: 'Retaliates against any enemy defenses or units that strike the Dragon Duke, turning heavy fire into counter-damage.',
    passiveBonus: 'Passive Hitpoints and counter-retaliation scaling',
    levelMilestones: epicMilestones(
      15,
      'Unlocks base defensive counter-attack retaliation',
      'Increases retaliatory damage dealt per incoming hit',
      'Strong synergy with solo frontline tanking & Ice Block',
      'Lvl 21: High counter-damage breakpoint against rapid-fire defenses',
      'Max Lvl 27: Maximum retaliatory counter-damage + full passive HP scaling'
    ),
    sources: [
      { title: 'ClashRecord: Revenge Deck', url: 'https://clashrecord.com' },
      { title: 'ClashPerk: Revenge Deck', url: 'https://clashperk.com' },
    ],
    confidence: 'HIGH',
  },
];

// Normalized per-milestone ClashDataRow records so CSV export & search include detailed level progression
export const equipmentData: ClashDataRow[] = heroEquipmentSpecs.flatMap((eq) =>
  eq.levelMilestones.map((m) => ({
    id: `${eq.id}-lvl-${m.level}`,
    name: eq.name,
    village: 'Home Village' as const,
    category: 'Hero Equipment' as const,
    level: m.level,
    thRequired: m.th,
    buildingRequired: `Blacksmith ${m.blacksmith} (${eq.blacksmithRequired})`,
    hitpoints: `${eq.rarity} · Max ${eq.maxLevel}`,
    dps: eq.activationType,
    damagePerHit: eq.hero,
    attackSpeed: 0,
    range: 'Equipment Slot',
    footprint: 'Slot (2/Hero)',
    housingSpace: 0,
    movementSpeed: 0,
    groundAir: eq.hero,
    favoriteTarget: `${eq.rarity} · ${eq.activationType}`,
    specialAbility: `Lvl ${m.level}: ${m.effectSummary} | Passive: ${eq.passiveBonus}`,
    sources: eq.sources,
    confidence: eq.confidence,
    conflictNotes: eq.rarityNote,
  }))
);
