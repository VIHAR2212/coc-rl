from dataclasses import dataclass, field


@dataclass
class Building:
    kind: str
    x: float          # top-left tile
    y: float
    size: int
    hp: float
    max_hp: float
    dps: float = 0.0
    range_tiles: float = 0.0
    attack_speed: float = 1.0
    min_range_tiles: float = 0.0
    splash_radius: float = 0.0
    targets: str = "ground"
    projectile_delay: float = 0.0
    cooldown: float = 0.0
    is_defense: bool = False
    is_wall: bool = False
    is_town_hall: bool = False
    cx: float = 0.0
    cy: float = 0.0

    def __post_init__(self):
        half = self.size / 2
        self.cx = self.x + half
        self.cy = self.y + half

    @property
    def alive(self):
        return self.hp > 0


@dataclass
class Troop:
    name: str
    x: float
    y: float
    hp: float
    dps: float
    attack_speed: float
    range_tiles: float
    speed: float
    favorite: str
    housing: int
    damage_vs_walls: float = 0.0
    splash_radius: float = 0.0
    is_flying: bool = False
    wall_jumper: bool = False
    whirlwind: bool = False
    death_damage: float = 0.0
    death_splash_radius: float = 0.0
    splits_into: int = 0
    split_troop: str = ""
    max_hp: float = 0.0
    target: "Building | None" = field(default=None, repr=False)
    path: list = field(default_factory=list, repr=False)
    path_wall_ver: int = -1
    path_target_id: int = -1

    def __post_init__(self):
        if self.max_hp <= 0.0:
            self.max_hp = self.hp

    @property
    def alive(self):
        return self.hp > 0


@dataclass
class PendingProjectile:
    x: float
    y: float
    damage: float
    splash_radius: float
    targets: str
    delay_left: float
    target: "Troop | None" = field(default=None, repr=False)
