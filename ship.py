import math
import heapq

from constants import COLS, ROWS, SHIP_TYPES, BRITISH_COLOR, ITALIAN_COLOR, \
    HEADINGS, HEADING_DELTA, HEADING_ANGLE, HEADING_CN, AMMO_ORDER, \
    hex_distance, hex_center, hex_line


class Ship:
    def __init__(self, name, ship_type, col, row, fleet_id):
        self.name = name
        self.type = ship_type
        self.col = col
        self.row = row
        self.fleet_id = fleet_id
        self.stats = SHIP_TYPES[ship_type]
        self.hp = self.stats['hp']
        self.max_hp = self.stats['hp']
        self.armor = self.stats['armor']
        self.max_armor = self.stats['armor']
        self.ammo = self.stats['ammo']
        self.max_ammo = self.stats['ammo']
        self.has_moved = False
        self.smoke_used = False
        self.heading = 'E' if fleet_id == 0 else 'W'
        self.selected_ammo = 'APHE'
        self.torpedo_uses = self.stats.get('torpedo', 0)

    @property
    def color(self):
        return BRITISH_COLOR if self.fleet_id == 0 else ITALIAN_COLOR

    def get_valid_moves(self, grid, terrain):
        max_move = self.stats['max_move']
        visited = {(self.row, self.col, self.heading)}
        pq = [(0, self.row, self.col, self.heading)]
        heads = {(self.col, self.row): self.heading}

        def can_enter(r, c):
            if grid[r][c] is not None:
                return False
            t = terrain[r][c]
            if t is None:
                return True
            if self.type == 'destroyer':
                return t in ('shoal', 'reef')
            return False

        while pq:
            d, r, c, h = heapq.heappop(pq)

            dr, dc = HEADING_DELTA[h][r & 1]
            nr, nc = r + dr, c + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS:
                cost = 2 if (terrain[nr][nc] == 'reef' and self.type == 'destroyer') else 1
                nd = d + cost
                if nd <= max_move and (nr, nc, h) not in visited and can_enter(nr, nc):
                    visited.add((nr, nc, h))
                    if (nc, nr) not in heads:
                        heads[(nc, nr)] = h
                    heapq.heappush(pq, (nd, nr, nc, h))

            nd = d + 1
            if nd <= max_move:
                for turn in (-1, 1):
                    nh = HEADINGS[(HEADINGS.index(h) + turn) % 6]
                    if (r, c, nh) not in visited:
                        visited.add((r, c, nh))
                        if (c, r) not in heads:
                            heads[(c, r)] = nh
                        heapq.heappush(pq, (nd, r, c, nh))

        self._move_headings = heads
        return list(heads.keys())

    def get_attack_targets(self, grid, terrain):
        targets = []
        atk_range = self.stats['attack_range']
        for r in range(ROWS):
            for c in range(COLS):
                if c == self.col and r == self.row:
                    continue
                if hex_distance(self.col, self.row, c, r) > atk_range:
                    continue
                if not self._has_los(self.row, self.col, r, c, terrain):
                    continue
                ship = grid[r][c]
                if ship and ship.fleet_id != self.fleet_id:
                    targets.append((c, r))
        return targets

    def get_firing_arc(self, target_row, target_col):
        if target_row == self.row and target_col == self.col:
            return 1.0, '全砲门'
        cx, cy = hex_center(self.col, self.row)
        tx, ty = hex_center(target_col, target_row)
        angle = math.atan2(ty - cy, tx - cx)
        if angle < 0:
            angle += 2 * math.pi
        ha = HEADING_ANGLE[self.heading]
        diff = angle - ha
        diff = (diff + math.pi) % (2 * math.pi) - math.pi
        deg = abs(diff) * 180 / math.pi
        if deg <= 30 or deg >= 330:
            return 0.5, '前主砲'
        elif 150 <= deg <= 210:
            return 0.5, '后主砲'
        return 1.0, '全砲门'

    @staticmethod
    def _has_los(r1, c1, r2, c2, terrain):
        if hex_distance(c1, r1, c2, r2) <= 1:
            return True
        for cc, rr in hex_line(c1, r1, c2, r2):
            if 0 <= rr < ROWS and 0 <= cc < COLS and terrain[rr][cc] == 'island':
                return False
        return True
