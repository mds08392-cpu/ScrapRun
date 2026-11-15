import json

from pico2d import *

from core.camera import camera

# Tiled 타일 ID의 상위 3비트는 뒤집기 플래그이므로 실제 ID만 남길 때 사용
GID_MASK = 0x1FFFFFFF

# 이 이름의 타일 레이어는 그리지 않고 벽 충돌 판정에만 사용 (칠해진 칸 = 벽)
COLLISION_LAYER = 'collision'


class TileMap:
    """Tiled로 만든 JSON 맵(타일 레이어)을 읽어 카메라에 보이는 부분만 그린다."""

    def __init__(self, map_path, tileset_path):
        with open(map_path, encoding='utf-8') as f:
            data = json.load(f)

        self.cols, self.rows = data['width'], data['height']
        self.tile_w, self.tile_h = data['tilewidth'], data['tileheight']
        self.width, self.height = self.cols * self.tile_w, self.rows * self.tile_h
        self.firstgid = data['tilesets'][0]['firstgid']

        # 그릴 타일 레이어(보이는 것만, 아래부터 순서대로)와 충돌 레이어를 분리
        self.layers = []
        self.blocked = [False] * (self.cols * self.rows)   # 인덱스 = row * cols + col (row는 위에서부터 0)
        for layer in data['layers']:
            if layer['type'] != 'tilelayer':
                continue
            if layer['name'] == COLLISION_LAYER:
                self.blocked = [gid != 0 for gid in layer['data']]
            elif layer.get('visible', True):
                self.layers.append(layer['data'])

        self.tileset = load_image(tileset_path)
        self.tileset_cols = self.tileset.w // self.tile_w
        self.tileset_rows = self.tileset.h // self.tile_h

    def update(self, dt):
        pass

    def is_blocked_cell(self, col, row):
        """(col, row) 칸이 벽이면 True. 맵 밖도 벽으로 취급한다."""
        if not (0 <= col < self.cols and 0 <= row < self.rows):
            return True
        return self.blocked[row * self.cols + col]

    def is_blocked_rect(self, left, bottom, right, top):
        """월드 좌표 사각형(y는 위로 증가)이 걸치는 칸 중 하나라도 벽이면 True."""
        eps = 0.001  # 칸 경계에 딱 붙어 있을 때 옆 칸까지 걸치는 것으로 보지 않도록
        col_start = int(left // self.tile_w)
        col_end = int((right - eps) // self.tile_w)
        row_start = int((self.height - top) // self.tile_h)
        row_end = int((self.height - bottom - eps) // self.tile_h)
        for row in range(row_start, row_end + 1):
            for col in range(col_start, col_end + 1):
                if self.is_blocked_cell(col, row):
                    return True
        return False

    def draw_collision(self):
        """디버그용: 벽 칸을 빨간 사각형으로 표시한다."""
        for row in range(self.rows):
            for col in range(self.cols):
                if self.blocked[row * self.cols + col]:
                    left = col * self.tile_w - camera.x
                    bottom = self.height - (row + 1) * self.tile_h - camera.y
                    draw_rectangle(left, bottom, left + self.tile_w - 1, bottom + self.tile_h - 1, 255, 0, 0)

    def draw_tile(self, gid, col, row):
        """맵의 (col, row) 칸(row는 위에서부터 0)에 gid 타일을 그린다."""
        idx = (gid & GID_MASK) - self.firstgid
        src_col, src_row = idx % self.tileset_cols, idx // self.tileset_cols
        # pico2d는 이미지 아래쪽이 y=0 이므로 위에서부터 센 행을 뒤집는다
        sx = src_col * self.tile_w
        sy = (self.tileset_rows - 1 - src_row) * self.tile_h

        x = col * self.tile_w + self.tile_w // 2 - camera.x
        y = self.height - row * self.tile_h - self.tile_h // 2 - camera.y
        self.tileset.clip_draw(sx, sy, self.tile_w, self.tile_h, x, y)

    def draw(self):
        # 카메라에 보이는 칸 범위만 계산해서 그린다
        col_start = max(0, camera.x // self.tile_w)
        col_end = min(self.cols, (camera.x + camera.view_w) // self.tile_w + 1)
        row_start = max(0, (self.height - camera.y - camera.view_h) // self.tile_h)
        row_end = min(self.rows, (self.height - camera.y) // self.tile_h + 1)

        for layer in self.layers:
            for row in range(row_start, row_end):
                base = row * self.cols
                for col in range(col_start, col_end):
                    gid = layer[base + col]
                    if gid:  # 0은 빈 칸
                        self.draw_tile(gid, col, row)
