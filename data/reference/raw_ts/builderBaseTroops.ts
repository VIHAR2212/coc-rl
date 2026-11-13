

// Helper mapping Builder Base 2.0 troop level -> Star Laboratory & Builder Hall requirements
const getBbReq = (lvl: number, unlockBh: number, barracksLvl: number) => {
  if (lvl <= 2) return { bh: Math.max(unlockBh, 2), building: `Builder Barracks ${barracksLvl} / Star Lab 2` };
  if (lvl <= 4) return { bh: Math.max(unlockBh, 3), building: `Star Laboratory 3 (BH${Math.max(unlockBh, 3)})` };
  if (lvl <= 6) return { bh: Math.max(unlockBh, 4), building: `Star Laboratory 4 (BH${Math.max(unlockBh, 4)})` };
  if (lvl <= 8) return { bh: Math.max(unlockBh, 5), building: `Star Laboratory 5 (BH${Math.max(unlockBh, 5)})` };
  if (lvl <= 11) return { bh: Math.max(unlockBh, 6), building: `Star Laboratory 6 (BH${Math.max(unlockBh, 6)})` };
  if (lvl <= 14) return { bh: Math.max(unlockBh, 7), building: `Star Laboratory 7 (BH${Math.max(unlockBh, 7)})` };
  if (lvl <= 16) return { bh: Math.max(unlockBh, 8), building: `Star Laboratory 8 (BH${Math.max(unlockBh, 8)})` };
  if (lvl <= 18) return { bh: Math.max(unlockBh, 9), building: `Star Laboratory 9 (BH${Math.max(unlockBh, 9)})` };
  return { bh: Math.max(unlockBh, 10), building: 'Star Laboratory 10 (BH10)' };
};

export const builderBaseTroopsData: ClashDataRow[] = [
  // 1. SNEAKY ARCHER (Housing Space: 3) - Levels 1-20
  ...[
    { lvl: 1, hp: 196, dps: 60 },
    { lvl: 2, hp: 196, dps: 60 },
    { lvl: 3, hp: 216, dps: 66 },
    { lvl: 4, hp: 216, dps: 66 },
    { lvl: 5, hp: 237, dps: 72 },
    { lvl: 6, hp: 237, dps: 72 },
    { lvl: 7, hp: 261, dps: 79 },
    { lvl: 8, hp: 261, dps: 79 },
    { lvl: 9, hp: 287, dps: 86 },
    { lvl: 10, hp: 287, dps: 86 },
    { lvl: 11, hp: 316, dps: 95 },
    { lvl: 12, hp: 316, dps: 95 },
    { lvl: 13, hp: 347, dps: 104 },
    { lvl: 14, hp: 347, dps: 104 },
    { lvl: 15, hp: 382, dps: 112 },
    { lvl: 16, hp: 382, dps: 112 },
    { lvl: 17, hp: 420, dps: 119 },
    { lvl: 18, hp: 420, dps: 119 },
    { lvl: 19, hp: 462, dps: 125 },
    { lvl: 20, hp: 462, dps: 125 },
  ].map((u) => {
    const req = getBbReq(u.lvl, 2, 2);
    return {
      id: `bb-sneaky-archer-${u.lvl}`,
      name: 'Sneaky Archer',
      village: 'Builder Base' as const,
      category: 'Builder Base Troop' as const,
      level: u.lvl,
      thRequired: req.bh,
      buildingRequired: req.building,
      hitpoints: u.hp,
      dps: u.dps,
      damagePerHit: u.dps,
      attackSpeed: 1.0,
      range: 3.5,
      footprint: '0.75x0.75',
      housingSpace: 3,
      movementSpeed: 24,
      groundAir: 'Ground (Targets Ground & Air)',
      favoriteTarget: 'None (Any)',
      specialAbility: 'Cloak: Turns invisible to all defenses for the first several seconds after deployment (duration scales with level)',
      sources: [
        { title: 'Fandom Wiki: Sneaky Archer (BB)', url: 'https://clashofclans.fandom.com/wiki/Sneaky_Archer_(Builder_Base)' },
        { title: 'House of Clashers: Sneaky Archer', url: 'https://www.houseofclashers.com/clash-of-clans/builder-base/troops/sneaky-archer/' },
      ],
      confidence: 'HIGH' as const,
    };
  }),

  // 2. RAGED BARBARIAN (Housing Space: 4) - Levels 1-20
  ...[
    { lvl: 1, hp: 500, dps: 45 },
    { lvl: 2, hp: 500, dps: 45 },
    { lvl: 3, hp: 550, dps: 58 },
    { lvl: 4, hp: 550, dps: 58 },
    { lvl: 5, hp: 605, dps: 70 },
    { lvl: 6, hp: 605, dps: 70 },
    { lvl: 7, hp: 666, dps: 83 },
    { lvl: 8, hp: 666, dps: 83 },
    { lvl: 9, hp: 732, dps: 93 },
    { lvl: 10, hp: 732, dps: 93 },
    { lvl: 11, hp: 805, dps: 103 },
    { lvl: 12, hp: 805, dps: 103 },
    { lvl: 13, hp: 886, dps: 112 },
    { lvl: 14, hp: 886, dps: 112 },
    { lvl: 15, hp: 974, dps: 120 },
    { lvl: 16, hp: 974, dps: 120 },
    { lvl: 17, hp: 1072, dps: 128 },
    { lvl: 18, hp: 1072, dps: 128 },
    { lvl: 19, hp: 1179, dps: 136 },
    { lvl: 20, hp: 1179, dps: 136 },
  ].map((u) => {
    const req = getBbReq(u.lvl, 2, 1);
    return {
      id: `bb-raged-barbarian-${u.lvl}`,
      name: 'Raged Barbarian',
      village: 'Builder Base' as const,
      category: 'Builder Base Troop' as const,
      level: u.lvl,
      thRequired: req.bh,
      buildingRequired: req.building,
      hitpoints: u.hp,
      dps: u.dps,
      damagePerHit: Math.round(u.dps * 0.8),
      attackSpeed: 0.8,
      range: 0.4,
      footprint: '0.75x0.75',
      housingSpace: 4,
      movementSpeed: 16,
      groundAir: 'Ground (Targets Ground)',
      favoriteTarget: 'None (Any)',
      specialAbility: 'Rage: Automatically enraged upon deployment, boosting speed and damage for the opening seconds',
      sources: [
        { title: 'Fandom Wiki: Raged Barbarian', url: 'https://clashofclans.fandom.com/wiki/Raged_Barbarian' },
        { title: 'House of Clashers: Raged Barbarian', url: 'https://www.houseofclashers.com/clash-of-clans/builder-base/troops/raged-barbarian/' },
      ],
      confidence: 'HIGH' as const,
    };
  }),

  // 3. BETA MINION (Housing Space: 4) - Levels 1-20
  ...[
    { lvl: 1, hp: 165, dps: 50 },
    { lvl: 2, hp: 180, dps: 55 },
    { lvl: 3, hp: 200, dps: 60 },
    { lvl: 4, hp: 200, dps: 60 },
    { lvl: 5, hp: 220, dps: 65 },
    { lvl: 6, hp: 220, dps: 65 },
    { lvl: 7, hp: 242, dps: 72 },
    { lvl: 8, hp: 242, dps: 72 },
    { lvl: 9, hp: 266, dps: 81 },
    { lvl: 10, hp: 266, dps: 81 },
    { lvl: 11, hp: 293, dps: 90 },
    { lvl: 12, hp: 293, dps: 90 },
    { lvl: 13, hp: 322, dps: 99 },
    { lvl: 14, hp: 322, dps: 99 },
    { lvl: 15, hp: 355, dps: 108 },
    { lvl: 16, hp: 355, dps: 108 },
    { lvl: 17, hp: 390, dps: 117 },
    { lvl: 18, hp: 390, dps: 117 },
    { lvl: 19, hp: 429, dps: 126 },
    { lvl: 20, hp: 429, dps: 126 },
  ].map((u) => {
    const req = getBbReq(u.lvl, 3, 4);
    return {
      id: `bb-beta-minion-${u.lvl}`,
      name: 'Beta Minion',
      village: 'Builder Base' as const,
      category: 'Builder Base Troop' as const,
      level: u.lvl,
      thRequired: req.bh,
      buildingRequired: req.building,
      hitpoints: u.hp,
      dps: u.dps,
      damagePerHit: u.dps,
      attackSpeed: 1.0,
      range: 4.0,
      footprint: '0.75x0.75',
      housingSpace: 4,
      movementSpeed: 32,
      groundAir: 'Air (Targets Ground & Air)',
      favoriteTarget: 'None (Any)',
      specialAbility: 'Long Shot: First several attacks fire from extended range (7–8.5 tiles) with bonus opening damage',
      sources: [
        { title: 'Fandom Wiki: Beta Minion', url: 'https://clashofclans.fandom.com/wiki/Beta_Minion' },
        { title: 'ClashPerk: Beta Minion', url: 'https://clashperk.com' },
      ],
      confidence: 'HIGH' as const,
    };
  }),

  // 4. HOG GLIDER (Housing Space: 10) - Levels 15-20
  ...[
    { lvl: 15, hp: 600, dps: '900 (Glider) / 112 (Rider)' },
    { lvl: 16, hp: 650, dps: '1100 (Glider) / 112 (Rider)' },
    { lvl: 17, hp: 650, dps: '1100 (Glider) / 125 (Rider)' },
    { lvl: 18, hp: 650, dps: '1100 (Glider) / 125 (Rider)' },
    { lvl: 19, hp: 650, dps: '1100 (Glider) / 139 (Rider)' },
    { lvl: 20, hp: 700, dps: '1300 (Glider) / 139 (Rider)' },
  ].map((u) => {
    const req = getBbReq(u.lvl, 9, 11);
    return {
      id: `bb-hog-glider-${u.lvl}`,
      name: 'Hog Glider',
      village: 'Builder Base' as const,
      category: 'Builder Base Troop' as const,
      level: u.lvl,
      thRequired: req.bh,
      buildingRequired: req.building,
      hitpoints: u.hp,
      dps: u.dps,
      damagePerHit: u.dps,
      attackSpeed: 1.0,
      range: 0.5,
      footprint: '1x1',
      housingSpace: 10,
      movementSpeed: 24,
      groundAir: 'Air -> Ground (Targets Defenses)',
      favoriteTarget: 'Defenses',
      specialAbility: 'Stunning Glide: Flies over walls and crashes into target defense to stun it, then drops a wall-jumping Hog Rider',
      sources: [
        { title: 'Fandom Wiki: Hog Glider', url: 'https://clashofclans.fandom.com/wiki/Hog_Glider' },
        { title: 'ClashPerk: Hog Glider', url: 'https://clashperk.com' },
      ],
      confidence: 'LOW' as const,
      conflictNotes: 'User dataset specifies Housing Space 10; ClashPerk spring weight lists 12 while Builder Base 2.0 deploys 1 per camp.',
    };
  }),

  // 5. BOMBER (Housing Space: 12) - Levels 1-20 (Natively unlocks at Lvl 5 in BB 2.0)
  ...[
    { lvl: 5, hp: 605, dps: 80 },
    { lvl: 6, hp: 605, dps: 80 },
    { lvl: 7, hp: 666, dps: 90 },
    { lvl: 8, hp: 666, dps: 90 },
    { lvl: 9, hp: 732, dps: 100 },
    { lvl: 10, hp: 732, dps: 100 },
    { lvl: 11, hp: 805, dps: 110 },
    { lvl: 12, hp: 805, dps: 110 },
    { lvl: 13, hp: 886, dps: 120 },
    { lvl: 14, hp: 886, dps: 120 },
    { lvl: 15, hp: 974, dps: 130 },
    { lvl: 16, hp: 974, dps: 130 },
    { lvl: 17, hp: 1072, dps: 140 },
    { lvl: 18, hp: 1072, dps: 140 },
    { lvl: 19, hp: 1179, dps: 150 },
    { lvl: 20, hp: 1179, dps: 150 },
  ].map((u) => {
    const req = getBbReq(u.lvl, 4, 5);
    return {
      id: `bb-bomber-${u.lvl}`,
      name: 'Bomber',
      village: 'Builder Base' as const,
      category: 'Builder Base Troop' as const,
      level: u.lvl,
      thRequired: req.bh,
      buildingRequired: req.building,
      hitpoints: u.hp,
      dps: u.dps,
      damagePerHit: u.dps * 2,
      attackSpeed: 2.0,
      range: 3.5,
      footprint: '1x1',
      housingSpace: 12,
      movementSpeed: 16,
      groundAir: 'Ground (Targets Ground)',
      favoriteTarget: 'Walls (Massive Bonus Splash)',
      specialAbility: 'Bouncing Bomb (Active): Launches a giant bouncing bomb dealing massive splash damage across walls and nearby buildings',
      sources: [
        { title: 'Fandom Wiki: Bomber', url: 'https://clashofclans.fandom.com/wiki/Bomber' },
        { title: 'ClashPerk: Bomber', url: 'https://clashperk.com' },
      ],
      confidence: 'HIGH' as const,
    };
  }),

  // 6. NIGHT WITCH (Housing Space: 14) - Levels 9-20
  ...[
    { lvl: 9, hp: 750, dps: 176 },
    { lvl: 10, hp: 750, dps: 176 },
    { lvl: 11, hp: 830, dps: 193 },
    { lvl: 12, hp: 830, dps: 193 },
    { lvl: 13, hp: 915, dps: 216 },
    { lvl: 14, hp: 915, dps: 216 },
    { lvl: 15, hp: 1000, dps: 234 },
    { lvl: 16, hp: 1000, dps: 234 },
    { lvl: 17, hp: 1100, dps: 257 },
    { lvl: 18, hp: 1100, dps: 257 },
    { lvl: 19, hp: 1220, dps: 278 },
    { lvl: 20, hp: 1220, dps: 278 },
  ].map((u) => {
    const req = getBbReq(u.lvl, 6, 8);
    return {
      id: `bb-night-witch-${u.lvl}`,
      name: 'Night Witch',
      village: 'Builder Base' as const,
      category: 'Builder Base Troop' as const,
      level: u.lvl,
      thRequired: req.bh,
      buildingRequired: req.building,
      hitpoints: u.hp,
      dps: u.dps,
      damagePerHit: Math.round(u.dps * 0.7),
      attackSpeed: 0.7,
      range: 3.0,
      footprint: '1x1',
      housingSpace: 14,
      movementSpeed: 12,
      groundAir: 'Ground (Targets Ground & Air; Spawns Air Bats)',
      favoriteTarget: 'None (Any)',
      specialAbility: 'Bat Swarm (Active): Periodically summons flying Bats and can activate an instant enraged Bat burst',
      sources: [
        { title: 'Fandom Wiki: Night Witch', url: 'https://clashofclans.fandom.com/wiki/Night_Witch' },
        { title: 'ClashPerk: Night Witch', url: 'https://clashperk.com' },
      ],
      confidence: 'HIGH' as const,
    };
  }),

  // 7. ELECTROFIRE WIZARD (Housing Space: 14) - Levels 17-20
  ...[
    { lvl: 17, hp: 1100, dps: 220 },
    { lvl: 18, hp: 1100, dps: 220 },
    { lvl: 19, hp: 1210, dps: 253 },
    { lvl: 20, hp: 1210, dps: 253 },
  ].map((u) => {
    const req = getBbReq(u.lvl, 10, 12);
    return {
      id: `bb-electrofire-wizard-${u.lvl}`,
      name: 'Electrofire Wizard',
      village: 'Builder Base' as const,
      category: 'Builder Base Troop' as const,
      level: u.lvl,
      thRequired: req.bh,
      buildingRequired: req.building,
      hitpoints: u.hp,
      dps: u.dps,
      damagePerHit: `${u.dps} (Inferno Ramp / 4-Target Chain)`,
      attackSpeed: 0.128,
      range: 3.5,
      footprint: '1x1',
      housingSpace: 14,
      movementSpeed: 22.4,
      groundAir: 'Ground (Targets Ground & Air)',
      favoriteTarget: 'None (Any)',
      specialAbility: 'Change Mode (Active): Toggles dynamically between Inferno Mode (single-target ramping beam) and Electro Mode (4-target chain lightning)',
      sources: [
        { title: 'Fandom Wiki: Electrofire Wizard', url: 'https://clashofclans.fandom.com/wiki/Electrofire_Wizard' },
        { title: 'ClashPerk: Electrofire Wizard', url: 'https://clashperk.com' },
      ],
      confidence: 'HIGH' as const,
    };
  }),

  // 8. CANNON CART (Housing Space: 16) - Levels 7-20
  ...[
    { lvl: 7, hp: 666, dps: 115 },
    { lvl: 8, hp: 666, dps: 115 },
    { lvl: 9, hp: 732, dps: 130 },
    { lvl: 10, hp: 732, dps: 130 },
    { lvl: 11, hp: 805, dps: 150 },
    { lvl: 12, hp: 805, dps: 150 },
    { lvl: 13, hp: 886, dps: 170 },
    { lvl: 14, hp: 886, dps: 170 },
    { lvl: 15, hp: 974, dps: 190 },
    { lvl: 16, hp: 974, dps: 190 },
    { lvl: 17, hp: 1072, dps: 215 },
    { lvl: 18, hp: 1072, dps: 215 },
    { lvl: 19, hp: 1179, dps: 240 },
    { lvl: 20, hp: 1179, dps: 240 },
  ].map((u) => {
    const req = getBbReq(u.lvl, 5, 7);
    return {
      id: `bb-cannon-cart-${u.lvl}`,
      name: 'Cannon Cart',
      village: 'Builder Base' as const,
      category: 'Builder Base Troop' as const,
      level: u.lvl,
      thRequired: req.bh,
      buildingRequired: req.building,
      hitpoints: u.hp,
      dps: u.dps,
      damagePerHit: Math.round(u.dps * 1.2),
      attackSpeed: 1.2,
      range: 4.5,
      footprint: '1.2x1.2',
      housingSpace: 16,
      movementSpeed: 19.2,
      groundAir: 'Ground (Targets Ground)',
      favoriteTarget: 'None (Any)',
      specialAbility: 'Mortar Mode Toggle (Active): Switches between mobile Cannon Mode (4.5t single-target) and stationary Mortar Mode (long-range splash)',
      sources: [
        { title: 'Fandom Wiki: Cannon Cart', url: 'https://clashofclans.fandom.com/wiki/Cannon_Cart' },
        { title: 'ClashPerk: Cannon Cart', url: 'https://clashperk.com' },
      ],
      confidence: 'HIGH' as const,
    };
  }),

  // 9. BOXER GIANT (Housing Space: 18) - Levels 3-20
  ...[
    { lvl: 3, hp: 2530, dps: 65 },
    { lvl: 4, hp: 2530, dps: 65 },
    { lvl: 5, hp: 2783, dps: 70 },
    { lvl: 6, hp: 2783, dps: 70 },
    { lvl: 7, hp: 3061, dps: 76 },
    { lvl: 8, hp: 3061, dps: 76 },
    { lvl: 9, hp: 3367, dps: 83 },
    { lvl: 10, hp: 3367, dps: 83 },
    { lvl: 11, hp: 3704, dps: 91 },
    { lvl: 12, hp: 3704, dps: 91 },
    { lvl: 13, hp: 4075, dps: 100 },
    { lvl: 14, hp: 4075, dps: 100 },
    { lvl: 15, hp: 4482, dps: 109 },
    { lvl: 16, hp: 4482, dps: 109 },
    { lvl: 17, hp: 4930, dps: 119 },
    { lvl: 18, hp: 4930, dps: 119 },
    { lvl: 19, hp: 5423, dps: 129 },
    { lvl: 20, hp: 5423, dps: 129 },
  ].map((u) => {
    const req = getBbReq(u.lvl, 3, 3);
    return {
      id: `bb-boxer-giant-${u.lvl}`,
      name: 'Boxer Giant',
      village: 'Builder Base' as const,
      category: 'Builder Base Troop' as const,
      level: u.lvl,
      thRequired: req.bh,
      buildingRequired: req.building,
      hitpoints: u.hp,
      dps: u.dps,
      damagePerHit: u.dps * 2,
      attackSpeed: 2.0,
      range: 1.0,
      footprint: '1.5x1.5',
      housingSpace: 18,
      movementSpeed: 12,
      groundAir: 'Ground (Targets Ground)',
      favoriteTarget: 'Defenses',
      specialAbility: 'Power Punch & Boxer Block (Active): First strike deals heavy bonus damage; Boxer Block creates an invulnerable damage shield',
      sources: [
        { title: 'Fandom Wiki: Boxer Giant', url: 'https://clashofclans.fandom.com/wiki/Boxer_Giant' },
        { title: 'ClashPerk: Boxer Giant', url: 'https://clashperk.com' },
      ],
      confidence: 'HIGH' as const,
    };
  }),

  // 10. BABY DRAGON (BUILDER BASE) (Housing Space: 20) - Levels 5-20
  ...[
    { lvl: 5, hp: 1331, dps: 58 },
    { lvl: 6, hp: 1331, dps: 58 },
    { lvl: 7, hp: 1464, dps: 64 },
    { lvl: 8, hp: 1464, dps: 64 },
    { lvl: 9, hp: 1611, dps: 71 },
    { lvl: 10, hp: 1611, dps: 71 },
    { lvl: 11, hp: 1772, dps: 78 },
    { lvl: 12, hp: 1772, dps: 78 },
    { lvl: 13, hp: 1949, dps: 86 },
    { lvl: 14, hp: 1949, dps: 86 },
    { lvl: 15, hp: 2144, dps: 94 },
    { lvl: 16, hp: 2144, dps: 94 },
    { lvl: 17, hp: 2358, dps: 103 },
    { lvl: 18, hp: 2358, dps: 103 },
    { lvl: 19, hp: 2358, dps: 113 },
    { lvl: 20, hp: 2358, dps: 113 },
  ].map((u) => {
    const req = getBbReq(u.lvl, 5, 6);
    return {
      id: `bb-baby-dragon-${u.lvl}`,
      name: 'Baby Dragon (BB)',
      village: 'Builder Base' as const,
      category: 'Builder Base Troop' as const,
      level: u.lvl,
      thRequired: req.bh,
      buildingRequired: req.building,
      hitpoints: u.hp,
      dps: u.dps,
      damagePerHit: Math.round(u.dps * 1.8),
      attackSpeed: 1.8,
      range: 2.75,
      footprint: '1.2x1.2',
      housingSpace: 20,
      movementSpeed: 16,
      groundAir: 'Air (Targets Ground & Air)',
      favoriteTarget: 'None (Any)',
      specialAbility: 'Tantrum (Passive) & Fiery Sneeze (Active): Gains enraged damage/speed when solo away from air allies; blasts a cone of fire on activation',
      sources: [
        { title: 'Fandom Wiki: Baby Dragon (BB)', url: 'https://clashofclans.fandom.com/wiki/Baby_Dragon_(Builder_Base)' },
        { title: 'House of Clashers: Baby Dragon (BB)', url: 'https://www.houseofclashers.com/clash-of-clans/builder-base/troops/baby-dragon/' },
      ],
      confidence: 'HIGH' as const,
    };
  }),

  // 11. DROP SHIP (Housing Space: 20) - Levels 11-20
  ...[
    { lvl: 11, hp: 3400, dps: 10, deathDmg: 300 },
    { lvl: 12, hp: 3400, dps: 10, deathDmg: 300 },
    { lvl: 13, hp: 3740, dps: 10, deathDmg: 300 },
    { lvl: 14, hp: 3740, dps: 10, deathDmg: 400 },
    { lvl: 15, hp: 4114, dps: 10, deathDmg: 400 },
    { lvl: 16, hp: 4114, dps: 10, deathDmg: 400 },
    { lvl: 17, hp: 4525, dps: 10, deathDmg: 400 },
    { lvl: 18, hp: 4525, dps: 10, deathDmg: 500 },
    { lvl: 19, hp: 4978, dps: 10, deathDmg: 500 },
    { lvl: 20, hp: 4978, dps: 10, deathDmg: 500 },
  ].map((u) => {
    const req = getBbReq(u.lvl, 7, 9);
    return {
      id: `bb-drop-ship-${u.lvl}`,
      name: 'Drop Ship',
      village: 'Builder Base' as const,
      category: 'Builder Base Troop' as const,
      level: u.lvl,
      thRequired: req.bh,
      buildingRequired: req.building,
      hitpoints: u.hp,
      dps: u.dps,
      damagePerHit: `${u.deathDmg} (Death)`,
      attackSpeed: 2.0,
      range: 0.5,
      footprint: '1.5x1.5',
      housingSpace: 20,
      movementSpeed: 12,
      groundAir: 'Air (Targets Ground Defenses)',
      favoriteTarget: 'Defenses',
      specialAbility: `Skeleton Bomb (Active): Drops Skeletons while flying; active ability detonates a heavy Skeleton Bomb (${u.deathDmg} death crash damage)`,
      sources: [
        { title: 'Fandom Wiki: Drop Ship', url: 'https://clashofclans.fandom.com/wiki/Drop_Ship' },
        { title: 'ClashPerk: Drop Ship', url: 'https://clashperk.com' },
      ],
      confidence: 'HIGH' as const,
    };
  }),

  // 12. POWER P.E.K.K.A (Housing Space: 22) - Levels 13-20
  ...[
    { lvl: 13, hp: 3900, dps: 420 },
    { lvl: 14, hp: 3900, dps: 420 },
    { lvl: 15, hp: 4290, dps: 460 },
    { lvl: 16, hp: 4290, dps: 460 },
    { lvl: 17, hp: 4719, dps: 500 },
    { lvl: 18, hp: 4719, dps: 500 },
    { lvl: 19, hp: 5191, dps: 560 },
    { lvl: 20, hp: 5191, dps: 560 },
  ].map((u) => {
    const req = getBbReq(u.lvl, 8, 10);
    return {
      id: `bb-power-pekka-${u.lvl}`,
      name: 'Power P.E.K.K.A',
      village: 'Builder Base' as const,
      category: 'Builder Base Troop' as const,
      level: u.lvl,
      thRequired: req.bh,
      buildingRequired: req.building,
      hitpoints: u.hp,
      dps: u.dps,
      damagePerHit: Math.round(u.dps * 1.8),
      attackSpeed: 1.8,
      range: 0.8,
      footprint: '1.5x1.5',
      housingSpace: 22,
      movementSpeed: 16,
      groundAir: 'Ground (Targets Ground)',
      favoriteTarget: 'None (Any)',
      specialAbility: 'Overcharge (Active): Unleashes a heavy area shockwave on activation or upon destruction, shattering nearby buildings and walls',
      sources: [
        { title: 'Fandom Wiki: Power P.E.K.K.A', url: 'https://clashofclans.fandom.com/wiki/Power_P.E.K.K.A' },
        { title: 'House of Clashers: Power P.E.K.K.A', url: 'https://www.houseofclashers.com/clash-of-clans/builder-base/troops/power-pekka/' },
      ],
      confidence: 'HIGH' as const,
    };
  }),
];
