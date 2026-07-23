from constants import HEADING_DELTA, COLS, ROWS, TORPEDO_SPEED


class Torpedo:
    def __init__(self, col, row, heading, fleet_id):
        self.col = col
        self.row = row
        self.heading = heading
        self.fleet_id = fleet_id
        self.active = True
        self.movement = TORPEDO_SPEED

    def advance_one(self, grid):
        dr, dc = HEADING_DELTA[self.heading][self.row & 1]
        nr = self.row + dr
        nc = self.col + dc
        if not (0 <= nr < ROWS and 0 <= nc < COLS):
            self.active = False
            return False
        self.row = nr
        self.col = nc
        return True

    def decelerate(self):
        self.movement -= 1
        if self.movement <= 0:
            self.active = False
