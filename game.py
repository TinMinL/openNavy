import random

from constants import COLS, ROWS, FLEET_NAMES, TERRAIN, AMMO_TYPES, \
    HEADINGS, HEADING_CN, HEADING_DELTA, hex_distance, hex_neighbors, \
    TORPEDO_DAMAGE, FLOODING_DAMAGE, FLOODING_TURNS
from ship import Ship
from torpedo import Torpedo


class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        self.grid = [[None] * COLS for _ in range(ROWS)]
        self.ships = []
        self.terrain = [[None] * COLS for _ in range(ROWS)]
        self.current_fleet = 0
        self.selected_ship = None
        self.valid_moves = []
        self.valid_targets = []
        self.turn = 1
        self.phase = 'select'
        self.delay_frames = 0
        self.preview = None
        self.last_attack = None
        self.smoke_clouds = []
        self.fire_ships = {}
        self.torpedoes = []
        self.flooding_ships = {}
        self._torpedo_hit_ship = None
        self._torpedo_hit_movement = 0
        self._torpedo_from_ship_move = False
        self._pending_torpedo_hits = []
        self._pending_floating_texts = []
        self.message = "英国舰队的回合 — 请选择一艘船舰"
        self._init_terrain()
        self._init_fleets()

    def update(self):
        if self.phase == 'turn_end_delay':
            self.delay_frames -= 1
            if self.delay_frames <= 0:
                self.end_turn()

    def _init_fleets(self):
        configs = [
            [
                Ship("HMS Warspite",   'battleship', 0, 1, 0),
                Ship("HMS Valiant",    'battleship', 0, 4, 0),
                Ship("HMS Jervis",     'destroyer',  1, 0, 0),
                Ship("HMS Belfast",    'cruiser',    1, 3, 0),
                Ship("HMS Kelvin",     'destroyer',  1, 6, 0),
            ],
            [
                Ship("RN Vittorio Veneto",    'battleship', COLS - 1, 1, 1),
                Ship("RN Littorio",           'battleship', COLS - 1, 4, 1),
                Ship("RN Alpino",             'destroyer',  COLS - 2, 0, 1),
                Ship("RN Giuseppe Garibaldi", 'cruiser',    COLS - 2, 3, 1),
                Ship("RN Carabiniere",        'destroyer',  COLS - 2, 6, 1),
            ],
        ]
        for fleet in configs:
            for ship in fleet:
                self.ships.append(ship)
                self.grid[ship.row][ship.col] = ship

    def _init_terrain(self):
        self.terrain = [[None] * COLS for _ in range(ROWS)]

        margin = 2

        def free(r, c):
            return (0 <= r < ROWS and 0 <= c < COLS and
                    self.terrain[r][c] is None)

        def not_start(nc):
            return margin <= nc < COLS - margin

        seeds = []
        for _ in range(random.randint(4, 6)):
            for _ in range(30):
                cr = random.randint(2, ROWS - 3)
                cc = random.randint(margin + 1, COLS - margin - 1)
                if free(cr, cc):
                    seeds.append((cr, cc))
                    self.terrain[cr][cc] = 'island'
                    break

        all_islands = list(seeds)
        target = random.randint(16, 24)
        stagnant = 0
        while len(all_islands) < target and stagnant < 5:
            new_cells = []
            for r, c in all_islands:
                adj = []
                for nr, nc in hex_neighbors(r, c):
                    if free(nr, nc) and not_start(nc) and (nr, nc) not in new_cells:
                        adj.append((nr, nc))
                if adj and random.random() < 0.5:
                    nc = random.choice(adj)
                    new_cells.append(nc)
            if not new_cells:
                stagnant += 1
                continue
            stagnant = 0
            for r, c in new_cells:
                self.terrain[r][c] = 'island'
                all_islands.append((r, c))

        shoal_candidates = []
        for r in range(ROWS):
            for c in range(COLS):
                if self.terrain[r][c] != 'island':
                    continue
                for nr, nc in hex_neighbors(r, c):
                    if free(nr, nc) and not_start(nc) and (nr, nc) not in shoal_candidates:
                        shoal_candidates.append((nr, nc))
        random.shuffle(shoal_candidates)
        for _ in range(min(random.randint(3, 6), len(shoal_candidates))):
            r, c = shoal_candidates.pop()
            self.terrain[r][c] = 'shoal'

        for _ in range(random.randint(6, 10)):
            for _ in range(30):
                c = random.randint(margin, COLS - margin - 1)
                r = random.randint(1, ROWS - 2)
                if free(r, c):
                    self.terrain[r][c] = 'reef'
                    break

    def select_ship(self, col, row):
        if self.phase != 'select':
            return False
        ship = self.grid[row][col]
        if ship and ship.fleet_id == self.current_fleet and not ship.has_moved:
            self.selected_ship = ship
            self.valid_moves = ship.get_valid_moves(self.grid, self.terrain)
            self.phase = 'move'
            self.message = f"{ship.name} 已选取 — 点击高亮格子移动"
            if ship.type == 'destroyer' and not ship.smoke_used:
                self.message += "  （S 释放烟幕）"
            return True
        return False

    def move_ship(self, col, row):
        if self.phase != 'move' or (col, row) not in self.valid_moves:
            return False
        ship = self.selected_ship
        if (col, row) != (ship.col, ship.row):
            self.grid[ship.row][ship.col] = None
            ship.col = col
            ship.row = row
            self.grid[row][col] = ship
        if hasattr(ship, '_move_headings') and (col, row) in ship._move_headings:
            ship.heading = ship._move_headings[(col, row)]
        ship.has_moved = True
        self.valid_moves = []

        # Check for enemy torpedo at destination
        for t in self.torpedoes[:]:
            if t.col == ship.col and t.row == ship.row and t.fleet_id != ship.fleet_id:
                hit_movement = t.movement
                t.active = False
                self.torpedoes.remove(t)
                self._torpedo_hit_ship = ship
                self._torpedo_hit_movement = hit_movement
                self._torpedo_from_ship_move = True
                self.phase = 'torpedo_evade'
                p, a = self._torpedo_evade_probs(hit_movement)
                self.message = (
                    f"{ship.name} 驶入鱼雷区域！"
                    f" 主动{a*100:.0f}% / 被动{p*100:.0f}%  Y / N"
                )
                return True

        return self._post_move_attack_phase(ship)

    def _post_move_attack_phase(self, ship):
        has_ammo = ship.ammo > 0
        has_torpedo = ship.torpedo_uses > 0

        if not has_ammo and not has_torpedo:
            self.message = f"{ship.name} 已移动（弹药耗尽）"
            self.selected_ship = None
            self.phase = 'select'
            self._check_turn_end()
            return True

        targets = ship.get_attack_targets(self.grid, self.terrain) if has_ammo else []
        targets = [(c, r) for c, r in targets if not self._in_smoke(r, c)]
        self.valid_targets = targets
        self.phase = 'attack'

        parts = [f"{ship.name} 已移动"]
        if targets:
            parts.append("— 点击红色目标攻击")
        if has_torpedo:
            parts.append("T 鱼雷")
        if not targets and not has_torpedo:
            parts.append("— 范围内无敌军")
        parts.append("（右键跳过）")
        self.message = "  ".join(parts)
        return True

    def _calculate_damage(self, attacker, target):
        distance = hex_distance(attacker.col, attacker.row, target.col, target.row)
        max_range = attacker.stats['attack_range']
        base = attacker.stats['attack']

        range_factor = 0.5 + 0.5 * max(0, (max_range - distance) / max_range)

        effective_armor = target.armor * random.uniform(0.6, 1.0)
        raw = max(base * 0.15, base - effective_armor)
        damage = max(1, int(raw * range_factor * random.uniform(0.9, 1.1)))

        arc_mult, arc_name = attacker.get_firing_arc(target.row, target.col)
        damage = max(1, int(damage * arc_mult))

        if target.type == 'destroyer' and self.terrain[target.row][target.col] == 'reef':
            damage = max(1, int(damage * random.uniform(0.5, 1.5)))

        ammo = attacker.selected_ammo
        is_critical = False
        caused_fire = False
        ammo_color = (255, 255, 255)

        if ammo == 'APHE':
            ammo_color = (255, 255, 255)
            is_critical = False
            mag_hit = False

            hit_result = '击穿'

            if random.random() < 0.03:
                mag_hit = True
                ammo_color = (255, 255, 0)
                damage = max(1, int(damage * 3.0))
                hit_result = '殉爆'
            else:
                if target.armor > 40:
                    pen_chance = max(0.25, 1.0 - (target.armor - 40) / 30)
                    if random.random() > pen_chance:
                        damage = max(1, int(damage * 0.15))
                        hit_result = '未击穿'
                    elif random.random() < 0.15:
                        damage = max(1, int(damage * 0.15))
                        hit_result = '跳弹'

                if hit_result == '击穿':
                    overmatch = base / max(1, target.armor)
                    if overmatch >= 6:
                        op = random.random() < 0.75
                    elif overmatch >= 4:
                        op = random.random() < 0.45
                    elif overmatch >= 2.5:
                        op = random.random() < 0.20
                    else:
                        op = False
                    if op:
                        damage = max(1, int(damage * 0.15))
                        hit_result = '过穿'

                if hit_result == '击穿' and random.random() < 0.10:
                    is_critical = True
                    ammo_color = (255, 255, 0)
                    damage = int(damage * 1.5)

        elif ammo == 'HE':
            ammo_color = (255, 165, 0)
            if target.type != 'destroyer':
                damage = max(1, int(damage * 0.4))
            if random.random() < 0.30:
                caused_fire = True
                self.fire_ships[id(target)] = {'turns': 2}
                if self.fire_ships[id(target)]['turns'] > 0:
                    pass

        elif ammo == 'SAP':
            ammo_color = (180, 100, 220)
            damage = max(1, int(damage * 0.75))
            if target.armor < 30:
                pass
            elif target.armor > 40:
                damage = max(1, int(damage * 0.10))

        details = {
            'base': base,
            'range_factor': range_factor,
            'distance': distance,
            'effective_armor': effective_armor,
            'raw': raw,
            'crit': is_critical,
            'hp_before': target.hp,
            'ammo': ammo,
            'ammo_color': ammo_color,
            'fire': caused_fire,
            'mag_hit': mag_hit if ammo == 'APHE' else False,
            'hit_result': hit_result if ammo == 'APHE' else None,
        }
        return max(1, damage), details

    def _calculate_preview(self, attacker, target):
        distance = hex_distance(attacker.col, attacker.row, target.col, target.row)
        max_range = attacker.stats['attack_range']
        base = attacker.stats['attack']
        range_factor = 0.5 + 0.5 * max(0, (max_range - distance) / max_range)
        effective_armor = target.armor * 0.8
        raw = max(base * 0.15, base - effective_armor)
        damage = max(1, int(raw * range_factor))
        arc_mult, arc_name = attacker.get_firing_arc(target.row, target.col)
        damage = max(1, int(damage * arc_mult))

        ammo = attacker.selected_ammo
        ammo_info = AMMO_TYPES.get(ammo, AMMO_TYPES['APHE'])
        fire_chance = 0
        overmatch_note = ''

        if ammo == 'APHE':
            if target.armor > 40:
                damage = max(1, int(damage * 0.15))
            overmatch = base / max(1, target.armor)
            if overmatch >= 6:
                overmatch_note = '高过穿风险 3%殉爆'
            elif overmatch >= 4:
                overmatch_note = '过穿风险 3%殉爆'
            elif overmatch >= 2.5:
                overmatch_note = '低过穿风险 3%殉爆'
        elif ammo == 'HE':
            if target.type != 'destroyer':
                damage = max(1, int(damage * 0.4))
            fire_chance = 30
        elif ammo == 'SAP':
            damage = max(1, int(damage * 0.75))
            if target.armor > 40:
                damage = max(1, int(damage * 0.10))

        armor_lost = max(1, damage // 5)
        p = {
            'target_name': target.name,
            'target_type': target.stats['cn_name'],
            'damage': damage,
            'armor_before': target.armor,
            'armor_after': max(0, target.armor - armor_lost),
            'hp_before': target.hp,
            'hp_after': max(0, target.hp - damage),
            'arc': f'{arc_name}({int(arc_mult*100)}%)',
            'ammo': ammo_info['cn'],
            'ammo_color': ammo_info['color'],
            'fire_chance': fire_chance,
            'overmatch_note': overmatch_note,
        }
        if target.type == 'destroyer' and self.terrain[target.row][target.col] == 'reef':
            p['reef_mod'] = True
        return p

    def update_preview(self, col, row):
        if self.phase != 'attack' or not self.selected_ship:
            self.preview = None
            return
        if not (0 <= col < COLS and 0 <= row < ROWS):
            self.preview = None
            return
        target = self.grid[row][col]
        if not target or (col, row) not in self.valid_targets:
            self.preview = None
            return
        self.preview = self._calculate_preview(self.selected_ship, target)

    def attack_target(self, col, row):
        if self.phase != 'attack':
            return False
        if (col, row) not in self.valid_targets:
            return False
        target = self.grid[row][col]
        if not target or target.fleet_id == self.current_fleet:
            return False

        ship = self.selected_ship
        ship.ammo = max(0, ship.ammo - 1)
        damage, details = self._calculate_damage(ship, target)
        target.hp -= damage

        old_armor = target.armor
        armor_lost = max(1, damage // 5)
        target.armor = max(0, target.armor - armor_lost)

        hit_tag = ""
        if details.get('hit_result'):
            hit_tag = f"  {details['hit_result']}"
            if details['hit_result'] == '殉爆':
                hit_tag += '！'
        crit_tag = "  暴击！" if details['crit'] else ""
        sunk_tag = ""
        if target.hp <= 0:
            self.grid[target.row][target.col] = None
            self.ships.remove(target)
            sunk_tag = f"  {target.name} 沉没！"

        self.message = (
            f"{ship.name} → {target.name}  伤害 {damage}{hit_tag}{crit_tag}"
            f"  |  装甲 {old_armor}→{target.armor}  HP {details['hp_before']}→{max(0, target.hp)}"
            f"{sunk_tag}"
        )

        self.last_attack = {
            'col': target.col, 'row': target.row,
            'damage': damage, 'crit': details['crit'],
            'sunk': target.hp <= 0,
            'ammo_color': details['ammo_color'],
            'fire': details.get('fire', False),
            'hit_result': details.get('hit_result'),
        }

        self.selected_ship = None
        self.valid_targets = []
        self.phase = 'select'
        self._check_turn_end()
        return True

    def skip_attack(self):
        if self.phase != 'attack':
            return False
        self.message = f"{self.selected_ship.name} 跳过攻击"
        self.selected_ship = None
        self.valid_targets = []
        self.phase = 'select'
        self._check_turn_end()
        return True

    def _in_smoke(self, row, col):
        return any(c['row'] == row and c['col'] == col for c in self.smoke_clouds)

    def use_smoke(self):
        ship = self.selected_ship
        if not ship or ship.type != 'destroyer' or ship.smoke_used:
            return False
        ship.smoke_used = True
        ship.has_moved = True
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                r, c = ship.row + dr, ship.col + dc
                if 0 <= r < ROWS and 0 <= c < COLS:
                    existing = [s for s in self.smoke_clouds if s['row'] == r and s['col'] == c]
                    if existing:
                        existing[0]['turns'] = max(existing[0]['turns'], 2)
                    else:
                        self.smoke_clouds.append({'row': r, 'col': c, 'turns': 2})
        self.message = f"{ship.name} 释放了烟幕！"
        self.selected_ship = None
        self.valid_moves = []
        has_ammo = ship.ammo > 0
        has_torpedo = ship.torpedo_uses > 0
        if has_ammo:
            targets = ship.get_attack_targets(self.grid, self.terrain)
            targets = [(c, r) for c, r in targets if not self._in_smoke(r, c)]
        else:
            targets = []
        if targets or has_torpedo:
            self.valid_targets = targets
            self.phase = 'attack'
            parts = [f"{ship.name} 释放了烟幕"]
            if targets:
                parts.append("— 点击红色目标攻击")
            if has_torpedo:
                parts.append("T 鱼雷")
            parts.append("（右键跳过）")
            self.message = "  ".join(parts)
            return True
        self.phase = 'select'
        self._check_turn_end()
        return True

    # --- Torpedo system ---

    def enter_torpedo_aim(self):
        ship = self.selected_ship
        if not ship or ship.torpedo_uses <= 0:
            return False
        self.phase = 'torpedo_aim'
        self.message = f"{ship.name} 选择鱼雷发射方向（剩余{ship.torpedo_uses}枚）"
        return True

    def fire_torpedo(self, heading):
        ship = self.selected_ship
        dr, dc = HEADING_DELTA[heading][ship.row & 1]
        tr = ship.row + dr
        tc = ship.col + dc
        if not (0 <= tr < ROWS and 0 <= tc < COLS):
            return False
        if self.grid[tr][tc] is not None:
            self.message = "发射位置被占用！"
            return False

        torpedo = Torpedo(tc, tr, heading, ship.fleet_id)
        self.torpedoes.append(torpedo)
        ship.torpedo_uses -= 1

        self.last_attack = {
            'col': tc, 'row': tr, 'damage': 0, 'crit': False, 'sunk': False,
            'ammo_color': (0, 200, 200), 'torpedo': True,
        }

        self.message = f"{ship.name} 发射了鱼雷！方向{HEADING_CN[heading]}"
        self.selected_ship = None
        self.valid_targets = []
        self.phase = 'select'
        self._check_turn_end()
        return True

    @staticmethod
    def _torpedo_evade_probs(movement):
        probs = {
            3: (0.10, 0.30),
            2: (0.25, 0.35),
            1: (0.45, 0.40),
        }
        return probs.get(movement, (0.50, 0.40))

    def resolve_torpedo_evade(self, evade):
        ship = self._torpedo_hit_ship
        if not ship or ship not in self.ships:
            self._torpedo_hit_ship = None
            if self._torpedo_from_ship_move:
                self._torpedo_from_ship_move = False
                self.phase = 'select'
                self._check_turn_end()
            else:
                self._process_next_torpedo_hit()
            return

        passive_prob, active_bonus = self._torpedo_evade_probs(self._torpedo_hit_movement)
        evaded = False

        if evade:
            # Active evade — higher chance, but no second chance on failure
            if random.random() < active_bonus:
                evaded = True
                self.message = f"{ship.name} 主动规避了鱼雷！"
                self._pending_floating_texts.append({
                    'text': '主动规避!', 'col': ship.col, 'row': ship.row,
                    'color': (100, 255, 100), 'size': 26,
                })
        else:
            # Passive evade — lower chance
            if random.random() < passive_prob:
                evaded = True
                self.message = f"{ship.name} 被动规避了鱼雷！"
                self._pending_floating_texts.append({
                    'text': '规避!', 'col': ship.col, 'row': ship.row,
                    'color': (100, 255, 100), 'size': 26,
                })

        if evaded:
            self._torpedo_hit_ship = None
            if self._torpedo_from_ship_move:
                self._torpedo_from_ship_move = False
                self._post_move_attack_phase(ship)
            else:
                self._process_next_torpedo_hit()
            return

        # Hit — apply damage
        ship.hp -= TORPEDO_DAMAGE
        idx = HEADINGS.index(ship.heading)
        ship.heading = HEADINGS[(idx + 3) % 6]

        self.last_attack = {
            'col': ship.col, 'row': ship.row,
            'damage': TORPEDO_DAMAGE, 'crit': False, 'sunk': ship.hp <= 0,
            'ammo_color': (0, 200, 200), 'torpedo': True,
        }
        self._pending_floating_texts.append({
            'text': f"鱼雷 {TORPEDO_DAMAGE}",
            'col': ship.col, 'row': ship.row,
            'color': (0, 200, 200), 'size': 28,
        })

        if ship.hp <= 0:
            self.grid[ship.row][ship.col] = None
            self.ships.remove(ship)
            self.message = f"{ship.name} 被鱼雷击沉！"
            self._pending_floating_texts.append({
                'text': '沉没!', 'col': ship.col, 'row': ship.row,
                'color': (255, 100, 100), 'size': 30,
            })
            self._torpedo_hit_ship = None
            if self._torpedo_from_ship_move:
                self._torpedo_from_ship_move = False
                self.selected_ship = None
                self.phase = 'select'
                self._check_turn_end()
            else:
                self._process_next_torpedo_hit()
            return

        self.flooding_ships[id(ship)] = FLOODING_TURNS
        self._pending_floating_texts.append({
            'text': '进水!', 'col': ship.col, 'row': ship.row,
            'color': (0, 200, 200), 'size': 26,
        })
        self.message = f"{ship.name} 被鱼雷命中！进水！"
        self._torpedo_hit_ship = None
        if self._torpedo_from_ship_move:
            self._torpedo_from_ship_move = False
            self._post_move_attack_phase(ship)
        else:
            self._process_next_torpedo_hit()

    def _check_win(self):
        opp = 1 - self.current_fleet
        if not any(s for s in self.ships if s.fleet_id == opp):
            winner = FLEET_NAMES[self.current_fleet]
            self.message = f"游戏结束 — {winner} 舰队获胜！按 R 重新开始 / M 返回菜单"
            self.phase = 'game_over'
            return True
        return False

    def _check_turn_end(self):
        if self._check_win():
            return
        my_ships = [s for s in self.ships if s.fleet_id == self.current_fleet]
        for s in my_ships:
            if not s.has_moved and s.ammo <= 0:
                s.has_moved = True
        if all(s.has_moved for s in my_ships) and self.phase != 'turn_end_delay':
            self.phase = 'turn_end_delay'
            self.delay_frames = 90
            self.message = "所有船舰已行动！即将切换至敌方回合..."

    def end_turn(self):
        if self.phase == 'game_over':
            return
        if self._check_win():
            return

        # Move torpedoes step by step, checking each hex for ships
        self._pending_torpedo_hits = []
        for torpedo in self.torpedoes[:]:
            if not torpedo.active:
                self.torpedoes.remove(torpedo)
                continue
            hit = False
            for _ in range(torpedo.movement):
                if not torpedo.advance_one(self.grid):
                    break
                ship = self.grid[torpedo.row][torpedo.col]
                if ship and ship.fleet_id != torpedo.fleet_id:
                    self._pending_torpedo_hits.append(
                        (torpedo, ship, torpedo.movement)
                    )
                    hit = True
                    break

            if hit:
                continue

            torpedo.decelerate()
            if not torpedo.active:
                self.torpedoes.remove(torpedo)

        if self._pending_torpedo_hits:
            self._process_next_torpedo_hit()
            return

        self._complete_end_turn()

    def _process_next_torpedo_hit(self):
        if not self._pending_torpedo_hits:
            self._complete_end_turn()
            return

        torpedo, ship, hit_movement = self._pending_torpedo_hits.pop(0)
        self.torpedoes.remove(torpedo)

        if ship not in self.ships:
            self._process_next_torpedo_hit()
            return

        self._torpedo_hit_ship = ship
        self._torpedo_hit_movement = hit_movement
        self._torpedo_from_ship_move = False
        self.phase = 'torpedo_evade'
        p, a = self._torpedo_evade_probs(hit_movement)
        self.message = (
            f"{ship.name} 被鱼雷锁定！"
            f" 主动{a*100:.0f}% / 被动{p*100:.0f}%  Y / N"
        )

    def _complete_end_turn(self):
        # Smoke dissipation
        for cloud in self.smoke_clouds[:]:
            cloud['turns'] -= 1
            if cloud['turns'] <= 0:
                self.smoke_clouds.remove(cloud)

        # Fire damage
        for ship_id in list(self.fire_ships.keys()):
            ship = next((s for s in self.ships if id(s) == ship_id), None)
            if ship:
                ship.hp -= 10
                self.fire_ships[ship_id]['turns'] -= 1
                if self.fire_ships[ship_id]['turns'] <= 0 or ship.hp <= 0:
                    del self.fire_ships[ship_id]
                if ship.hp <= 0:
                    self.grid[ship.row][ship.col] = None
                    if ship in self.ships:
                        self.ships.remove(ship)

        # Flooding damage
        for ship_id in list(self.flooding_ships.keys()):
            ship = next((s for s in self.ships if id(s) == ship_id), None)
            if ship:
                ship.hp -= FLOODING_DAMAGE
                self.flooding_ships[ship_id] -= 1
                if self.flooding_ships[ship_id] <= 0 or ship.hp <= 0:
                    del self.flooding_ships[ship_id]
                if ship.hp <= 0:
                    self.grid[ship.row][ship.col] = None
                    if ship in self.ships:
                        self.ships.remove(ship)

        for ship in self.ships:
            if ship.fleet_id == self.current_fleet:
                ship.has_moved = False
        self.current_fleet = 1 - self.current_fleet
        if self.current_fleet == 0:
            self.turn += 1
        name = FLEET_NAMES[self.current_fleet]
        self.message = f"{name} 舰队的回合（第 {self.turn} 回合）— 请选择船舰"
        self.phase = 'select'

    @property
    def british_count(self):
        return len([s for s in self.ships if s.fleet_id == 0])

    @property
    def italian_count(self):
        return len([s for s in self.ships if s.fleet_id == 1])
