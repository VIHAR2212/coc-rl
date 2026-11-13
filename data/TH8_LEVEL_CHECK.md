# TH8 Troop Level Verification: Laboratory & Town Hall Tables

**Document:** `data/TH8_LEVEL_CHECK.md`  
**Date:** 2026-11-13  
**Question:** Does the Clash of Clans Fandom Wiki specify Level 5 or Level 6 as the maximum available level for Giant, Barbarian, Archer, Wall Breaker, and Goblin at Town Hall 8?  
**Finding:** **Level 5 is verified with 100% certainty across all 5 troops.** Town Hall 8 caps the Laboratory at Level 6, and Level 6 Laboratory unlocks Level 5 troops. Level 6 troops strictly require Laboratory Level 7 (Town Hall 9) or Laboratory Level 8 (Town Hall 10).

---

## 1. Town Hall 8 Laboratory Level Cap

**Source URL:** [https://clashofclans.fandom.com/wiki/Town_Hall](https://clashofclans.fandom.com/wiki/Town_Hall)  
**Raw Source File:** `data/raw/Town_Hall.json`  

From the Town Hall upgrade table (Army Buildings per Town Hall level):
```json
{
  "TH Level": "8",
  "Army Camp": "6",
  "Barracks": "10",
  "Laboratory": "6",
  "Spell Factory": "3",
  "Dark Barracks": "4",
  "Hero Hall": "2",
  "Dark Spell Factory": "2",
  "Blacksmith": "1",
  "Workshop": "-",
  "Pet House": "-"
}
```
- **Max Laboratory Level at TH8:** **Level 6**
- **Town Hall required for Laboratory Level 7:** **Town Hall 9**

---

## 2. Laboratory Upgrade Requirements

**Source URL:** [https://clashofclans.fandom.com/wiki/Laboratory](https://clashofclans.fandom.com/wiki/Laboratory)  
**Raw Source File:** `data/raw/Laboratory.json`  

From the Laboratory upgrade table:
```json
{
  "Level": "6",
  "Hitpoints": "750",
  "Build Cost": "400,000",
  "Build Time": "16h",
  "Experience Gained": "240",
  "Town Hall Level Required": "8"
}
```
```json
{
  "Level": "7",
  "Hitpoints": "830",
  "Build Cost": "800,000",
  "Build Time": "1d",
  "Experience Gained": "293",
  "Town Hall Level Required": "9"
}
```
- Laboratory Level 6 requires **Town Hall 8**.
- Laboratory Level 7 requires **Town Hall 9**.

---

## 3. Troop Upgrade Requirements: Exact Table Rows

### A. Giant
**Source URL:** [https://clashofclans.fandom.com/wiki/Giant](https://clashofclans.fandom.com/wiki/Giant)  
**Raw Source File:** `data/raw/Giant.json`

| Level | Damage per Second | Hitpoints | Research Cost | Research Time | Laboratory Level Required | Town Hall Equivalent |
|---|---|---|---|---|---|---|
| **Level 4** | 24 | 700 | 350,000 | 8h | **5** | Town Hall 7 |
| **Level 5** | **31** | **900** | 800,000 | 12h | **6** | **Town Hall 8 (MATCHES SIM)** |
| **Level 6** | 43 | 1,100 | 1,500,000 | 1d | **7** | **Town Hall 9 (NOT TH8)** |
| **Level 7** | 55 | 1,300 | 2,400,000 | 2d | **8** | Town Hall 10 |

---

### B. Barbarian
**Source URL:** [https://clashofclans.fandom.com/wiki/Barbarian](https://clashofclans.fandom.com/wiki/Barbarian)  
**Raw Source File:** `data/raw/Barbarian.json`

| Level | Damage per Second | Hitpoints | Research Cost | Research Time | Laboratory Level Required | Town Hall Equivalent |
|---|---|---|---|---|---|---|
| **Level 4** | 18 | 85 | 120,000 | 6h | **5** | Town Hall 7 |
| **Level 5** | **23** | **105** | 300,000 | 8h | **6** | **Town Hall 8 (MATCHES SIM)** |
| **Level 6** | 26 | 125 | 800,000 | 14h | **7** | **Town Hall 9 (NOT TH8)** |
| **Level 7** | 30 | 160 | 1,400,000 | 1d 8h | **8** | Town Hall 10 |

---

### C. Archer
**Source URL:** [https://clashofclans.fandom.com/wiki/Archer](https://clashofclans.fandom.com/wiki/Archer)  
**Raw Source File:** `data/raw/Archer.json`

| Level | Damage per Second | Hitpoints | Research Cost | Research Time | Laboratory Level Required | Town Hall Equivalent |
|---|---|---|---|---|---|---|
| **Level 4** | 16 | 33 | 160,000 | 6h | **5** | Town Hall 7 |
| **Level 5** | **20** | **40** | 400,000 | 8h | **6** | **Town Hall 8 (MATCHES SIM)** |
| **Level 6** | 22 | 44 | 900,000 | 14h | **7** | **Town Hall 9 (NOT TH8)** |
| **Level 7** | 25 | 48 | 1,600,000 | 1d 8h | **8** | Town Hall 10 |

---

### D. Wall Breaker
**Source URL:** [https://clashofclans.fandom.com/wiki/Wall_Breaker](https://clashofclans.fandom.com/wiki/Wall_Breaker)  
**Raw Source File:** `data/raw/Wall_Breaker.json`

| Level | Damage vs Walls (x40) | Hitpoints | Research Cost | Research Time | Laboratory Level Required | Town Hall Equivalent |
|---|---|---|---|---|---|---|
| **Level 4** | 1,280 | 35 | 300,000 | 6h | **5** | Town Hall 7 |
| **Level 5** | **1,720** | **53** | 750,000 | 10h | **6** | **Town Hall 8 (MATCHES SIM)** |
| **Level 6** | 2,400 | 72 | 1,800,000 | 1d 12h | **8** | **Town Hall 10 (NOT TH8)** |
| **Level 7** | 3,040 | 82 | 3,000,000 | 2d 12h | **9** | Town Hall 11 |

*(Note: Level 6 Wall Breaker skips Laboratory 7 entirely and requires Laboratory 8 / TH10. Thus at TH8, Level 5 is the maximum available).*

---

### E. Goblin
**Source URL:** [https://clashofclans.fandom.com/wiki/Goblin](https://clashofclans.fandom.com/wiki/Goblin)  
**Raw Source File:** `data/raw/Goblin.json`

| Level | Damage per Second | Hitpoints | Research Cost | Research Time | Laboratory Level Required | Town Hall Equivalent |
|---|---|---|---|---|---|---|
| **Level 4** | 24 | 50 | 200,000 | 6h | **5** | Town Hall 7 |
| **Level 5** | **32** | **65** | 500,000 | 8h | **6** | **Town Hall 8 (MATCHES SIM)** |
| **Level 6** | 42 | 80 | 1,000,000 | 16h | **7** | **Town Hall 9 (NOT TH8)** |
| **Level 7** | 52 | 105 | 1,800,000 | 1d 12h | **8** | Town Hall 10 |

---

## 4. Conclusion on Stop Condition 2

- **The wiki does NOT say Level 6 for TH8.**
- The wiki explicitly, consistently, and unreservedly confirms that **Level 5** is the maximum level available for all 5 troops at Town Hall 8.
- The external dataset `clash-of-clans-data-researcher-&-csv-explorer` erroneously aligned troop level with Laboratory level (assuming Lab 6 implies Troop Level 6), whereas Supercell's actual progression unlocks Level 5 troops in Laboratory 6.
- **Stop Condition 2 is NOT triggered. Level 5 in our simulator is 100% correct.**

