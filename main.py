import math
import os
import sys

import pygame

from constants import *
from game import Game
from torpedo import Torpedo


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


FONT_PATH = None
_candidates = [
    resource_path('wqy-microhei.ttc'),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wqy-microhei.ttc'),
    '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
    'C:/Windows/Fonts/msyh.ttc',
    'C:/Windows/Fonts/msyhbd.ttc',
    'C:/Windows/Fonts/simhei.ttf',
    'C:/Windows/Fonts/simsun.ttc',
]
for _p in _candidates:
    if os.path.exists(_p):
        FONT_PATH = _p
        break


def make_font(size):
    if FONT_PATH:
        return pygame.font.Font(FONT_PATH, size)
    try:
        return pygame.font.SysFont(['microsoftyahei', 'simhei', 'simsun', 'stxihei'], size)
    except Exception:
        return pygame.font.Font(None, size)

floating_texts = []

EDGE_DIRS = ['SE', 'SW', 'W', 'NW', 'NE', 'E']


def same_group(t1, t2):
    if t1 is None or t2 is None:
        return False
    if t1 == 'reef' and t2 == 'reef':
        return True
    if {t1, t2} <= {'island', 'shoal'}:
        return True
    return False


def add_floating_text(text, col, row, color, size=24, duration=60):
    cx, cy = hex_center(col, row)
    floating_texts.append({
        'text': text, 'x': cx, 'y': cy,
        'start_y': cy, 'color': color, 'size': size,
        'timer': duration, 'max_timer': duration,
    })


def update_floating_texts():
    for ft in floating_texts[:]:
        ft['timer'] -= 1
        progress = 1 - ft['timer'] / ft['max_timer']
        ft['y'] = ft['start_y'] - 40 * progress
        if ft['timer'] <= 0:
            floating_texts.remove(ft)


def draw_floating_texts(screen):
    for ft in floating_texts:
        alpha = int(255 * (ft['timer'] / ft['max_timer']))
        scale = 1 + 0.15 * (1 - ft['timer'] / ft['max_timer'])
        size = int(ft['size'] * scale)
        f = make_font(size)
        surf = f.render(ft['text'], True, ft['color'])
        surf.set_alpha(alpha)
        r = surf.get_rect(center=(ft['x'], ft['y']))
        screen.blit(surf, r)


def get_ship_at(game, mx, my):
    c, r = pixel_to_hex(mx, my)
    if c is not None:
        return game.grid[r][c]
    return None


def draw_hex_borders(screen, verts, row, col, terrain):
    t = terrain[row][col]
    info = TERRAIN.get(t)
    if not info:
        return
    bdr = info['border']
    for i in range(6):
        d = EDGE_DIRS[i]
        dr, dc = HEADING_DELTA[d][row & 1]
        nr, nc = row + dr, col + dc
        if nr < 0 or nr >= ROWS or nc < 0 or nc >= COLS:
            pygame.draw.line(screen, bdr, verts[i], verts[(i + 1) % 6], 2)
        else:
            nt = terrain[nr][nc]
            if not same_group(t, nt):
                pygame.draw.line(screen, bdr, verts[i], verts[(i + 1) % 6], 2)


PREVIEW_COLOR = (255, 220, 100)


def draw_info_panel(screen, font, font_small, ship, preview=None, game=None):
    panel_rect = pygame.Rect(PANEL_X, PANEL_Y, PANEL_W, PANEL_H)
    surf = pygame.Surface((PANEL_W, PANEL_H), pygame.SRCALPHA)
    surf.fill(PANEL_BG)
    screen.blit(surf, (PANEL_X, PANEL_Y))
    pygame.draw.rect(screen, PANEL_BORDER, panel_rect, 2)

    if ship is None:
        lines = ['─ 舰队资讯 ─', '', '鼠标悬停或点击', '船舰查看详细资料']
        y = PANEL_Y + 20
        for line in lines:
            screen.blit(font_small.render(line, True, (140, 140, 170)),
                        (PANEL_X + 10, y))
            y += 22
        return

    name_str = ship.name
    if font_small.size(name_str)[0] > PANEL_W - 20:
        name_str = name_str[:12] + '…'
    screen.blit(font_small.render(name_str, True, WHITE), (PANEL_X + 10, PANEL_Y + 10))
    type_str = f"{ship.stats['cn_name']} | {FLEET_NAMES[ship.fleet_id]}"
    screen.blit(font_small.render(type_str, True, (180, 180, 220)),
                (PANEL_X + 10, PANEL_Y + 32))

    pygame.draw.line(screen, PANEL_BORDER,
                     (PANEL_X + 10, PANEL_Y + 56),
                     (PANEL_X + PANEL_W - 10, PANEL_Y + 56), 1)

    def draw_bar(label, value, max_val, fg, bg, yp):
        label_surf = font_small.render(label, True, (200, 200, 220))
        screen.blit(label_surf, (PANEL_X + 10, yp))
        bx = PANEL_X + 55
        by = yp + 2
        bw = PANEL_W - 65
        bh = 14
        ratio = max(0, value / max_val) if max_val > 0 else 0
        pygame.draw.rect(screen, bg, (bx, by, bw, bh))
        pygame.draw.rect(screen, fg, (bx, by, int(bw * ratio), bh))
        pygame.draw.rect(screen, (100, 100, 120), (bx, by, bw, bh), 1)
        num_surf = font_small.render(f"{value}/{max_val}", True, WHITE)
        screen.blit(num_surf, (bx + 3, by + 1))

    sy = PANEL_Y + 69
    draw_bar('HP', ship.hp, ship.max_hp, HP_BAR_FG, HP_BAR_BG, sy)
    draw_bar('装甲', ship.armor, ship.max_armor, ARMOR_BAR_COLOR, ARMOR_BAR_BG, sy + 22)
    draw_bar('弹药', ship.ammo, ship.max_ammo, AMMO_BAR_COLOR, AMMO_BAR_BG, sy + 44)

    iy = sy + 78
    for label, val in [('攻击力', ship.stats['attack']),
                       ('移动力', ship.stats['max_move']),
                       ('射程',   ship.stats['attack_range'])]:
        screen.blit(font_small.render(f"{label}  {val}", True, (200, 200, 220)),
                    (PANEL_X + 10, iy))
        iy += 24

    heading_cn = HEADING_CN.get(ship.heading, ship.heading)
    screen.blit(font_small.render(f"朝向：{heading_cn}", True, (180, 200, 255)),
                (PANEL_X + 10, iy + 8))

    status = '已行动' if ship.has_moved else '待命'
    s_color = (255, 200, 50) if ship.has_moved else (100, 255, 100)
    screen.blit(font_small.render(f"状态：{status}", True, s_color),
                (PANEL_X + 10, iy + 28))

    if ship.type == 'destroyer':
        smk = '已使用' if ship.smoke_used else '可用'
        sc = (200, 100, 100) if ship.smoke_used else (100, 200, 100)
        screen.blit(font_small.render(f"烟幕：{smk}", True, sc),
                    (PANEL_X + 10, iy + 48))
        if not ship.smoke_used:
            screen.blit(font_small.render("按 S 释放", True, (200, 200, 100)),
                        (PANEL_X + 10, iy + 68))
        torp_txt = f"鱼雷：{'♥' * ship.torpedo_uses}{'♡' * (2 - ship.torpedo_uses)}"
        tc = (0, 200, 200) if ship.torpedo_uses > 0 else (100, 100, 100)
        screen.blit(font_small.render(torp_txt, True, tc),
                    (PANEL_X + 10, iy + 86))

    if id(ship) in game.flooding_ships:
        ft = game.flooding_ships[id(ship)]
        screen.blit(font_small.render(f"⚠ 进水 {ft}回合", True, (0, 200, 200)),
                    (PANEL_X + 10, iy + 106))

    ammo_type = ship.selected_ammo if hasattr(ship, 'selected_ammo') else 'APHE'
    ammo_info = AMMO_TYPES[ammo_type]
    ay = iy + 128 if ship.type == 'destroyer' else iy + 88
    if ship.type == 'destroyer' and not ship.smoke_used:
        ay += 20
    screen.blit(font_small.render(f"弹药：{ammo_info['cn']}", True, ammo_info['color']),
                (PANEL_X + 10, ay))
    screen.blit(font_small.render("1/2/3 切换", True, (200, 200, 100)),
                (PANEL_X + 10, ay + 20))

    if preview is not None:
        py = ay + 44
        pygame.draw.line(screen, PREVIEW_COLOR,
                         (PANEL_X + 10, py),
                         (PANEL_X + PANEL_W - 10, py), 1)
        py += 8
        title = font_small.render("─ 攻击预览 ─", True, PREVIEW_COLOR)
        screen.blit(title, (PANEL_X + 10, py))
        py += 24

        ammo_text = f"{preview['ammo']} {preview['arc']}"
        screen.blit(font_small.render(ammo_text, True, preview['ammo_color']),
                    (PANEL_X + 10, py))
        py += 22

        tgt_text = f"→ {preview['target_type']}  伤害 {preview['damage']}"
        screen.blit(font_small.render(tgt_text, True, (220, 220, 200)),
                    (PANEL_X + 10, py))
        py += 22

        hp_text = f"HP {preview['hp_before']}→{preview['hp_after']}"
        arm_text = f"装甲 {preview['armor_before']}→{preview['armor_after']}"
        screen.blit(font_small.render(hp_text, True, (220, 220, 200)),
                    (PANEL_X + 10, py))
        py += 22
        screen.blit(font_small.render(arm_text, True, (220, 220, 200)),
                    (PANEL_X + 10, py))
        py += 22

        if preview.get('reef_mod'):
            screen.blit(font_small.render("⚠ 礁石 ±50%", True, (255, 200, 80)),
                        (PANEL_X + 10, py))
            py += 22
        if preview.get('fire_chance'):
            screen.blit(font_small.render(f"🔥 {preview['fire_chance']}%起火", True, (255, 165, 0)),
                        (PANEL_X + 10, py))
            py += 22
        if preview.get('overmatch_note'):
            screen.blit(font_small.render(preview['overmatch_note'], True, (255, 220, 100)),
                        (PANEL_X + 10, py))


def draw_ship_shape(screen, cx, cy, length, width, angle, color):
    shape = [
        (length * 0.5, 0),
        (length * 0.15, -width * 0.5),
        (-length * 0.35, -width * 0.4),
        (-length * 0.5, 0),
        (-length * 0.35, width * 0.4),
        (length * 0.15, width * 0.5),
    ]
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    pts = []
    for x, y in shape:
        rx = x * cos_a - y * sin_a
        ry = x * sin_a + y * cos_a
        pts.append((cx + rx, cy + ry))
    pygame.draw.polygon(screen, color, pts)
    pygame.draw.polygon(screen, WHITE, pts, 2)

    arrow = [
        (length * 0.55, 0),
        (length * 0.4, -4),
        (length * 0.4, 4),
    ]
    apts = []
    for x, y in arrow:
        rx = x * cos_a - y * sin_a
        ry = x * sin_a + y * cos_a
        apts.append((cx + rx, cy + ry))
    pygame.draw.polygon(screen, (255, 255, 200), apts)


def draw(screen, game, font, font_small, font_big, hovered_ship, hovered_cell=None):
    screen.fill(DARK_BLUE)

    info = TERRAIN

    for r in range(ROWS):
        for c in range(COLS):
            cx, cy = hex_center(c, r)
            verts = hex_vertices(cx, cy)
            t = game.terrain[r][c]

            base_color = GRID_COLOR_1 if (r + c) % 2 == 0 else GRID_COLOR_2

            if t is None:
                pygame.draw.polygon(screen, base_color, verts)
                if (r * 17 + c * 31) % 7 > 3:
                    seed = r * 11 + c * 7
                    wx = cx + ((seed + 5) % 11 - 5) * 2
                    wy = cy + ((seed + 3) % 9 - 4) * 2
                    for wi in range(2):
                        dx = wi * 3
                        dy = int(2 * math.sin(wi * 1.5))
                        pygame.draw.circle(screen, (100, 165, 215), (wx + dx, wy + dy), 1)
            elif t == 'island':
                clr = info['island']['color']
                pygame.draw.polygon(screen, clr, verts)
                draw_hex_borders(screen, verts, r, c, game.terrain)
                if (r + c) % 3 == 0:
                    off = (r * 7 + c * 3) % 8 - 4
                    tx = cx + off
                    ty = cy - HEX_SIZE * 0.3
                    pygame.draw.line(screen, (100, 60, 20), (tx, ty + 4), (tx, ty - 8), 3)
                    pygame.draw.circle(screen, (50, 130, 40), (tx, ty - 12), 5)
                bush_clr = (clr[0] - 10, clr[1] + 15, clr[2] - 5)
                for vi in range(2):
                    sx = cx + ((r + 1) * (vi + 7) + c * 11) % 12 - 6
                    sy = cy + ((c + 1) * (vi + 5) + r * 13) % 10 - 5
                    pygame.draw.circle(screen, bush_clr, (sx, sy), 2)
                rock_x = cx + (r * 7 + c * 3) % 10 - 5
                rock_y = cy + (r * 5 + c * 11) % 10 - 5
                pygame.draw.circle(screen, (120, 100, 70), (rock_x, rock_y), 2)
            elif t == 'shoal':
                clr = info['shoal']['color']
                bdr = info['shoal']['border']
                pygame.draw.polygon(screen, clr, verts)
                for i in range(6):
                    d = EDGE_DIRS[i]
                    dr, dc = HEADING_DELTA[d][r & 1]
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < ROWS and 0 <= nc < COLS and game.terrain[nr][nc] == 'island':
                        v1 = verts[i]
                        v2 = verts[(i + 1) % 6]
                        mx = (v1[0] + v2[0]) / 2
                        my = (v1[1] + v2[1]) / 2
                        strip_pts = [v1]
                        for s in range(5):
                            t = s / 4
                            px = v1[0] + (v2[0] - v1[0]) * t
                            py = v1[1] + (v2[1] - v1[1]) * t
                            dx = px - cx
                            dy = py - cy
                            dist = math.hypot(dx, dy)
                            if dist > 0:
                                nx = dx / dist
                                ny = dy / dist
                            else:
                                nx, ny = 0, 0
                            inward = cx + nx * (dist - HEX_SIZE * 0.35)
                            inwy = cy + ny * (dist - HEX_SIZE * 0.35)
                            sw = 4 * math.sin(s * 1.2)
                            strip_pts.append((inward + sw * ny, inwy - sw * nx))
                        strip_pts.append(v2)
                        if len(strip_pts) > 2:
                            pygame.draw.polygon(screen, clr, strip_pts)
                            pygame.draw.polygon(screen, bdr, strip_pts, 1)
                draw_hex_borders(screen, verts, r, c, game.terrain)
            elif t == 'reef':
                clr = info['reef']['color']
                bdr = info['reef']['border']
                pygame.draw.polygon(screen, clr, verts)
                for sx, sy, sr in [(cx - 7, cy - 5, 4), (cx + 6, cy - 6, 3),
                                   (cx - 3, cy + 4, 5), (cx + 5, cy + 3, 3),
                                   (cx - 6, cy + 1, 3), (cx + 1, cy - 2, 4)]:
                    pygame.draw.circle(screen, bdr, (sx, sy), sr)
                    pygame.draw.circle(screen, tuple(min(255, c + 40) for c in clr),
                                       (sx, sy), sr - 2)
                    if sr >= 3:
                        hlt = tuple(min(255, c + 55) for c in clr)
                        pygame.draw.circle(screen, hlt, (sx - 1, sy - 1), sr // 3)

    for col, row in game.valid_moves:
        cx, cy = hex_center(col, row)
        verts = hex_vertices(cx, cy)
        s = pygame.Surface((HEX_SIZE * 2, HEX_SIZE * 2), pygame.SRCALPHA)
        pygame.draw.polygon(s, MOVE_HIGHLIGHT, [(x - cx + HEX_SIZE * 2 / 2, y - cy + HEX_SIZE * 2 / 2) for x, y in verts])
        screen.blit(s, (cx - HEX_SIZE, cy - HEX_SIZE))

    for col, row in game.valid_targets:
        cx, cy = hex_center(col, row)
        verts = hex_vertices(cx, cy)
        s = pygame.Surface((HEX_SIZE * 2, HEX_SIZE * 2), pygame.SRCALPHA)
        pygame.draw.polygon(s, ATTACK_HIGHLIGHT, [(x - cx + HEX_SIZE, y - cy + HEX_SIZE) for x, y in verts])
        screen.blit(s, (cx - HEX_SIZE, cy - HEX_SIZE))
        pygame.draw.polygon(screen, (255, 50, 50), verts, 3)

    if game.selected_ship:
        s = game.selected_ship
        cx, cy = hex_center(s.col, s.row)
        verts = hex_vertices(cx, cy)
        pygame.draw.polygon(screen, SELECTED_COLOR, verts, 3)
        ammo_clr = AMMO_TYPES[s.selected_ammo]['color']
        pygame.draw.circle(screen, ammo_clr, (cx, cy - HEX_SIZE + 6), 4)

    if game.phase == 'torpedo_aim' and game.selected_ship:
        s = game.selected_ship
        cx, cy = hex_center(s.col, s.row)
        for heading in HEADINGS:
            dr, dc = HEADING_DELTA[heading][s.row & 1]
            nr, nc = s.row + dr, s.col + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS:
                tx, ty = hex_center(nc, nr)
                verts = hex_vertices(tx, ty)
                ov = pygame.Surface((HEX_SIZE * 2, HEX_SIZE * 2), pygame.SRCALPHA)
                pygame.draw.polygon(ov, (0, 200, 200, 60), [(x - tx + HEX_SIZE, y - ty + HEX_SIZE) for x, y in verts])
                screen.blit(ov, (tx - HEX_SIZE, ty - HEX_SIZE))
                pygame.draw.polygon(screen, (0, 200, 200), verts, 2)
                mid_x = (cx + tx) / 2
                mid_y = (cy + ty) / 2
                end_angle = math.atan2(ty - cy, tx - cx)
                for da in (0.4, -0.4):
                    ax = mid_x - 8 * math.cos(end_angle + da)
                    ay = mid_y - 8 * math.sin(end_angle + da)
                    pygame.draw.line(screen, (0, 200, 200), (mid_x, mid_y), (ax, ay), 3)
                lbl = font_small.render(HEADING_CN[heading], True, (0, 200, 200))
                lr = lbl.get_rect(center=(tx, ty - HEX_SIZE))
                screen.blit(lbl, lr)

    for ship in game.ships:
        cx, cy = hex_center(ship.col, ship.row)
        angle = HEADING_ANGLE[ship.heading]
        l = ship.stats['shape_len']
        w = ship.stats['shape_wid']

        if ship.has_moved and ship != game.selected_ship:
            color = tuple(min(255, int(c * 0.5)) for c in ship.color)
        else:
            color = ship.color
        draw_ship_shape(screen, cx, cy, l, w, angle, color)

        label = font_small.render(ship.stats['label'], True, WHITE)
        lr = label.get_rect(center=(cx, cy - HEX_SIZE - 4))
        screen.blit(label, lr)

        bar_w = 26
        bar_h = 3
        bx = cx - bar_w // 2
        hp_r = max(0, ship.hp / ship.max_hp)
        by = cy + HEX_SIZE * 0.65
        pygame.draw.rect(screen, HP_BAR_BG, (bx, by, bar_w, bar_h))
        pygame.draw.rect(screen, HP_BAR_FG, (bx, by, int(bar_w * hp_r), bar_h))
        arm_r = max(0, ship.armor / ship.max_armor)
        by2 = by + bar_h + 1
        pygame.draw.rect(screen, ARMOR_BAR_BG, (bx, by2, bar_w, bar_h))
        pygame.draw.rect(screen, ARMOR_BAR_COLOR, (bx, by2, int(bar_w * arm_r), bar_h))

    SMOKE_OVERLAY = (140, 140, 160, 90)
    for sc in game.smoke_clouds:
        r, c = sc['row'], sc['col']
        cx, cy = hex_center(c, r)
        verts = hex_vertices(cx, cy)
        s = pygame.Surface((HEX_SIZE * 2, HEX_SIZE * 2), pygame.SRCALPHA)
        pygame.draw.polygon(s, SMOKE_OVERLAY, [(x - cx + HEX_SIZE, y - cy + HEX_SIZE) for x, y in verts])
        screen.blit(s, (cx - HEX_SIZE, cy - HEX_SIZE))
        pygame.draw.polygon(screen, (200, 200, 220), verts, 1)

    for torpedo in game.torpedoes:
        cx, cy = hex_center(torpedo.col, torpedo.row)
        pygame.draw.circle(screen, (0, 200, 200), (int(cx), int(cy)), 8)
        pygame.draw.circle(screen, (100, 255, 255), (int(cx), int(cy)), 5)
        angle = HEADING_ANGLE[torpedo.heading]
        tip_x = cx + 10 * math.cos(angle)
        tip_y = cy + 10 * math.sin(angle)
        pygame.draw.line(screen, (0, 200, 200), (cx, cy), (tip_x, tip_y), 3)

    draw_info_panel(screen, font, font_small,
                    game.selected_ship or hovered_ship, game.preview, game)

    fleet_name = FLEET_NAMES[game.current_fleet]
    turn_text = f"第 {game.turn} 回合  |  {fleet_name} 舰队"
    screen.blit(font.render(turn_text, True, WHITE), (20, 15))
    screen.blit(
        font_small.render(
            f"英国：{game.british_count} 艘  |  意大利：{game.italian_count} 艘",
            True, WHITE),
        (20, 45),
    )

    bar_r = pygame.Rect(20, 68, PANEL_X - 30, 22)
    pygame.draw.rect(screen, (10, 15, 40), bar_r)
    pygame.draw.rect(screen, (60, 80, 130), bar_r, 1)

    if hovered_cell is not None:
        c, r = hovered_cell
        t_type = game.terrain[r][c]
        if t_type is not None:
            t_info = TERRAIN[t_type]
            color = t_info['color']
            cn = t_info['cn']
            m = t_info['move']
            co = t_info['combat']
            pygame.draw.rect(screen, color, (24, 72, 14, 14))
            bar_text = f"{cn}  |  移动: {m}  |  战斗: {co}"
            screen.blit(font_small.render(bar_text, True, (200, 200, 220)), (44, 70))

    help_y = SCREEN_HEIGHT - 62
    for text in [
        "左键：选取/移动/攻击    S：烟幕    T：鱼雷    1/2/3：弹药    右键：取消    空格：结束回合",
    ]:
        screen.blit(font_small.render(text, True, (160, 160, 190)),
                    (20, help_y))
        help_y += 20

    screen.blit(font.render(game.message, True, WHITE),
                (20, SCREEN_HEIGHT - 35))

    draw_floating_texts(screen)

    if game.phase == 'turn_end_delay':
        t = pygame.time.get_ticks()
        pulse = 0.5 + 0.5 * abs(math.sin(t * 0.004))
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(100 + 80 * pulse)))
        screen.blit(overlay, (0, 0))

        txt = font_big.render("回合切换中...", True, (255, 255, 100))
        sr = txt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20))
        screen.blit(txt, sr)

        sub = font.render(game.message, True, (255, 255, 200))
        sr2 = sub.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30))
        screen.blit(sub, sr2)

        hint = font_small.render("按空格键立即切换", True, (200, 200, 200))
        sr3 = hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 65))
        screen.blit(hint, sr3)


def draw_menu(screen, font, font_small, font_big, mouse_pos):
    screen.fill((5, 10, 30))

    for i in range(0, SCREEN_WIDTH, 40):
        for j in range(0, SCREEN_HEIGHT, 40):
            if (i // 40 + j // 40) % 2 == 0:
                pygame.draw.circle(screen, (15, 25, 50), (i, j), 2)

    title = font_big.render("二战海军舰队战术模拟器", True, (220, 230, 255))
    tr = title.get_rect(center=(SCREEN_WIDTH // 2, 130))
    screen.blit(title, tr)

    sub = font.render("WWII Naval Fleet Tactical Simulator", True, (120, 140, 180))
    sr = sub.get_rect(center=(SCREEN_WIDTH // 2, 175))
    screen.blit(sub, sr)

    pygame.draw.line(screen, (60, 80, 130),
                     (SCREEN_WIDTH // 2 - 180, 205),
                     (SCREEN_WIDTH // 2 + 180, 205), 1)

    buttons = []
    for i, (text, action) in enumerate([
        ('开始游戏', 'start'),
        ('退出', 'quit'),
    ]):
        bw, bh = 220, 50
        bx = SCREEN_WIDTH // 2 - bw // 2
        by = 270 + i * 75
        rect = pygame.Rect(bx, by, bw, bh)
        buttons.append({'rect': rect, 'action': action})
        hovered = rect.collidepoint(mouse_pos)
        color = (70, 110, 180) if hovered else (40, 70, 130)
        border_color = (140, 180, 240) if hovered else (80, 110, 170)
        pygame.draw.rect(screen, color, rect, border_radius=6)
        pygame.draw.rect(screen, border_color, rect, 2, border_radius=6)
        lbl = font.render(text, True, WHITE)
        lr = lbl.get_rect(center=rect.center)
        screen.blit(lbl, lr)

    credits = font_small.render("左键点击选择    S烟幕    T鱼雷    1/2/3切换弹药    空格结束回合    右键取消", True, (100, 110, 140))
    cr = credits.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 40))
    screen.blit(credits, cr)
    return buttons


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("二战海军舰队战术模拟器")
    clock = pygame.time.Clock()
    font = make_font(26)
    font_small = make_font(18)
    font_big = make_font(42)

    state = 'menu'
    game = None
    running = True
    hovered_ship = None
    hovered_cell = None
    menu_buttons = []

    while running:
        if state == 'menu':
            mouse_pos = pygame.mouse.get_pos()
            menu_buttons = draw_menu(screen, font, font_small, font_big, mouse_pos)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for btn in menu_buttons:
                        if btn['rect'].collidepoint(event.pos):
                            if btn['action'] == 'start':
                                state = 'game'
                                floating_texts.clear()
                                game = Game()
                                hovered_ship = None
                                hovered_cell = None
                            elif btn['action'] == 'quit':
                                running = False

        elif state == 'game':
            game.update()
            update_floating_texts()

            for ft in game._pending_floating_texts:
                add_floating_text(ft['text'], ft['col'], ft['row'], ft['color'], ft.get('size', 24), 70)
            game._pending_floating_texts.clear()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1 and game.phase in ('move', 'attack'):
                        if game.selected_ship:
                            game.selected_ship.selected_ammo = 'APHE'
                            if hovered_cell:
                                game.update_preview(*hovered_cell)
                    elif event.key == pygame.K_2 and game.phase in ('move', 'attack'):
                        if game.selected_ship:
                            game.selected_ship.selected_ammo = 'HE'
                            if hovered_cell:
                                game.update_preview(*hovered_cell)
                    elif event.key == pygame.K_3 and game.phase in ('move', 'attack'):
                        if game.selected_ship:
                            game.selected_ship.selected_ammo = 'SAP'
                            if hovered_cell:
                                game.update_preview(*hovered_cell)
                    elif event.key == pygame.K_s and game.phase == 'move':
                        game.use_smoke()
                    elif event.key == pygame.K_t and game.phase == 'attack':
                        game.enter_torpedo_aim()
                    elif event.key == pygame.K_y and game.phase == 'torpedo_evade':
                        if game._torpedo_hit_ship is None:
                            game.phase = 'select'
                            game._check_turn_end()
                        else:
                            game.resolve_torpedo_evade(True)
                    elif event.key == pygame.K_n and game.phase == 'torpedo_evade':
                        if game._torpedo_hit_ship is None:
                            game.phase = 'select'
                            game._check_turn_end()
                        else:
                            game.resolve_torpedo_evade(False)
                    elif event.key == pygame.K_SPACE:
                        if game.phase == 'turn_end_delay':
                            game.delay_frames = 1
                        else:
                            game.end_turn()
                    elif event.key == pygame.K_r and game.phase == 'game_over':
                        game.reset()
                    elif event.key == pygame.K_m and game.phase == 'game_over':
                        state = 'menu'
                        game = None
                elif event.type == pygame.MOUSEMOTION:
                    mx, my = event.pos
                    c, r = pixel_to_hex(mx, my)
                    if c is not None:
                        hovered_ship = game.grid[r][c]
                        hovered_cell = (c, r)
                        game.update_preview(c, r)
                    else:
                        hovered_ship = None
                        hovered_cell = None
                        game.preview = None
                elif event.type == pygame.MOUSEBUTTONDOWN and game.phase in ('select', 'move', 'attack', 'torpedo_aim'):
                    mx, my = event.pos
                    c, r = pixel_to_hex(mx, my)
                    if c is None:
                        continue
                    if event.button == 1:
                        if game.phase == 'select':
                            game.select_ship(c, r)
                        elif game.phase == 'move':
                            game.move_ship(c, r)
                        elif game.phase == 'torpedo_aim':
                            s = game.selected_ship
                            for heading in HEADINGS:
                                dr, dc = HEADING_DELTA[heading][s.row & 1]
                                nr, nc = s.row + dr, s.col + dc
                                if nr == r and nc == c:
                                    if game.fire_torpedo(heading) and game.last_attack:
                                        a = game.last_attack
                                        add_floating_text("鱼雷发射!", a['col'], a['row'], (0, 200, 200), 26, 60)
                                        game.last_attack = None
                                    break
                        elif game.phase == 'attack':
                            if game.attack_target(c, r) and game.last_attack:
                                a = game.last_attack
                                txt = str(a['damage'])
                                if a.get('hit_result'):
                                    txt = a['hit_result'] + ' ' + txt
                                if a['crit']:
                                    txt += ' 暴击!'
                                if a['sunk']:
                                    txt += ' 沉没!'
                                if a.get('fire'):
                                    txt += ' 🔥'
                                clr = a.get('ammo_color', (255, 220, 80))
                                add_floating_text(txt, a['col'], a['row'], clr, 28, 70)
                                game.last_attack = None
                    elif event.button == 3:
                        if game.phase == 'attack':
                            game.skip_attack()
                        elif game.phase == 'torpedo_aim':
                            game.phase = 'attack'
                            game.message = f"{game.selected_ship.name} 已移动 — 点击红色目标攻击（右键跳过）  T 鱼雷"
                        elif game.phase == 'move':
                            game.selected_ship = None
                            game.valid_moves = []
                            game.phase = 'select'
                            name = FLEET_NAMES[game.current_fleet]
                            game.message = f"{name} 舰队的回合 — 请选择船舰"

            draw(screen, game, font, font_small, font_big, hovered_ship, hovered_cell)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()
