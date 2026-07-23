import math

SCREEN_WIDTH = 960
SCREEN_HEIGHT = 640
FPS = 60

COLS = 16
ROWS = 10

HEX_SIZE = 24
HEX_W = HEX_SIZE * math.sqrt(3)
HEX_H = HEX_SIZE * 2

GRID_LEFT = 55
GRID_TOP = 134

PANEL_X = 780
PANEL_Y = 65
PANEL_W = 170
PANEL_H = 470
PANEL_BG = (15, 20, 50, 220)
PANEL_BORDER = (100, 130, 200)

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK_BLUE = (10, 15, 40)
GRID_COLOR_1 = (15, 40, 90)
GRID_COLOR_2 = (20, 55, 110)
SELECTED_COLOR = (0, 255, 100)
MOVE_HIGHLIGHT = (255, 255, 0, 80)
ATTACK_HIGHLIGHT = (255, 30, 30, 100)
BRITISH_COLOR = (60, 130, 230)
ITALIAN_COLOR = (210, 130, 30)
HP_BAR_BG = (80, 0, 0)
HP_BAR_FG = (0, 210, 60)

FLEET_NAMES = {0: '英国', 1: '意大利'}

ARMOR_BAR_COLOR = (160, 160, 180)
ARMOR_BAR_BG = (60, 60, 80)

SHIP_TYPES = {
    'battleship': {
        'name': 'Battleship', 'cn_name': '战舰',
        'hp': 100, 'armor': 8, 'max_move': 2,
        'attack_range': 4, 'attack': 35, 'ammo': 10, 'label': 'BB',
        'shape_len': 20, 'shape_wid': 12,
    },
    'cruiser': {
        'name': 'Light Cruiser', 'cn_name': '轻巡洋舰',
        'hp': 65, 'armor': 5, 'max_move': 3,
        'attack_range': 3, 'attack': 26, 'ammo': 12, 'label': 'CL',
        'shape_len': 16, 'shape_wid': 10,
    },
    'destroyer': {
        'name': 'Destroyer', 'cn_name': '驱逐舰',
        'hp': 40, 'armor': 3, 'max_move': 4,
        'attack_range': 2, 'attack': 20, 'ammo': 15, 'label': 'DD',
        'shape_len': 13, 'shape_wid': 8,
        'torpedo': 2,
    },
}

TERRAIN = {
    'island': {'color': (55, 115, 50), 'border': (80, 150, 70), 'cn': '岛屿',
               'move': '不可通行', 'combat': '遮蔽视线'},
    'shoal':  {'color': (80, 170, 145), 'border': (120, 200, 175), 'cn': '浅滩',
               'move': '仅驱逐舰', 'combat': '无修正'},
    'reef':   {'color': (145, 105, 55), 'border': (175, 135, 80), 'cn': '礁石',
               'move': '仅驱逐舰(双倍)', 'combat': '伤害±50%'},
}

HEADINGS = ['E', 'SE', 'SW', 'W', 'NW', 'NE']
HEADING_CN = {'E': '东', 'SE': '东南', 'SW': '西南', 'W': '西', 'NW': '西北', 'NE': '东北'}
HEADING_ANGLE = {
    'E': 0, 'SE': math.pi / 3, 'SW': 2 * math.pi / 3,
    'W': math.pi, 'NW': 4 * math.pi / 3, 'NE': 5 * math.pi / 3,
}
HEADING_DELTA = {
    'E':  ((0, 1), (0, 1)),
    'NE': ((-1, 0), (-1, 1)),
    'NW': ((-1, -1), (0, -1)),
    'W':  ((0, -1), (0, -1)),
    'SW': ((1, -1), (1, 0)),
    'SE': ((1, 0), (1, 1)),
}

AMMO_TYPES = {
    'APHE': {'cn': '穿甲弹', 'color': (255, 255, 255), 'crit_color': (255, 255, 0)},
    'HE':   {'cn': '高爆弹', 'color': (255, 165, 0)},
    'SAP':  {'cn': '半穿甲弹','color': (180, 100, 220)},
}
AMMO_ORDER = ['APHE', 'HE', 'SAP']

AMMO_BAR_COLOR = (220, 200, 80)
AMMO_BAR_BG = (80, 70, 20)

TORPEDO_SPEED = 3
TORPEDO_DAMAGE = 50
TORPEDO_MAX_USES = 2
TORPEDO_COLOR = (0, 200, 200)
FLOODING_DAMAGE = 10
FLOODING_TURNS = 3


def hex_center(col, row):
    q = col - (row - (row & 1)) // 2
    r = row
    cx = GRID_LEFT + HEX_SIZE + HEX_SIZE * math.sqrt(3) * (q + r / 2)
    cy = GRID_TOP + HEX_SIZE + HEX_SIZE * 1.5 * r
    return cx, cy


def hex_vertices(cx, cy):
    verts = []
    for i in range(6):
        angle = math.pi / 6 + i * math.pi / 3
        verts.append((cx + HEX_SIZE * math.cos(angle), cy + HEX_SIZE * math.sin(angle)))
    return verts


def hex_distance(col1, row1, col2, row2):
    q1 = col1 - (row1 - (row1 & 1)) // 2
    r1 = row1
    q2 = col2 - (row2 - (row2 & 1)) // 2
    r2 = row2
    s1 = -q1 - r1
    s2 = -q2 - r2
    return max(abs(q1 - q2), abs(r1 - r2), abs(s1 - s2))


def pixel_to_hex(px, py):
    x = (px - GRID_LEFT - HEX_SIZE) / HEX_SIZE
    y = (py - GRID_TOP - HEX_SIZE) / HEX_SIZE
    q = math.sqrt(3) / 3 * x - 1 / 3 * y
    r = 2 / 3 * y
    s = -q - r
    qr, rr, sr = round(q), round(r), round(s)
    if abs(qr - q) > abs(rr - r) and abs(qr - q) > abs(sr - s):
        qr = -rr - sr
    elif abs(rr - r) > abs(sr - s):
        rr = -qr - sr
    col = qr + (rr - (rr & 1)) // 2
    row = rr
    if 0 <= col < COLS and 0 <= row < ROWS:
        return col, row
    return None, None


def hex_line(col1, row1, col2, row2):
    q1 = col1 - (row1 - (row1 & 1)) // 2
    r1 = row1
    q2 = col2 - (row2 - (row2 & 1)) // 2
    r2 = row2
    s1 = -q1 - r1
    s2 = -q2 - r2
    dist = hex_distance(col1, row1, col2, row2)
    if dist <= 1:
        return [(col2, row2)]
    cells = []
    for i in range(1, dist):
        t = i / dist
        q = q1 + (q2 - q1) * t
        ra = r1 + (r2 - r1) * t
        s = s1 + (s2 - s1) * t
        qr, rr, sr = round(q), round(ra), round(s)
        if abs(qr - q) > abs(rr - ra) and abs(qr - q) > abs(sr - s):
            qr = -rr - sr
        elif abs(rr - ra) > abs(sr - s):
            rr = -qr - sr
        cc = qr + (rr - (rr & 1)) // 2
        cells.append((cc, rr))
    return cells


def hex_neighbors(row, col):
    nbs = []
    for deltas in HEADING_DELTA.values():
        dr, dc = deltas[row & 1]
        nr, nc = row + dr, col + dc
        if 0 <= nr < ROWS and 0 <= nc < COLS:
            nbs.append((nr, nc))
    return nbs
