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
    is_defense: bool = False
    is_wall: bool = False
    is_town_hall: bool = False

    @property
    def alive(self):
        return self.hp > 0

    @property
    def cx(self):
        return self.x + self.size / 2

    @property
    def cy(self):
        return self.y + self.size / 2


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
    target: "Building | None" = field(default=None, repr=False)
    path: list = field(default_factory=list, repr=False)
    path_wall_ver: int = -1
    path_target_id: int = -1

    @property
    def alive(self):
        return self.hp > 0
