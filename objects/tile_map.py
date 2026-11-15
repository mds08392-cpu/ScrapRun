import json

from pico2d import *

from core.camera import camera

# Tiled 타일 ID의 상위 3비트는 뒤집기 플래그이므로 실제 ID만 남길 때 사용
GID_MASK = 0x1FFFFFFF


class TileMap:
    """Tiled로 만든 JSON 맵(타일 레이어)을 읽어 카메라에 보이는 부분만 그린다."""

    def __init__(self, map_path, tileset_path):
        with open(map_path, encoding='utf-8') as f:
            data = json.load(f)

        self.cols, self.rows = data['width'], data['height']
        self.tile_w, self.tile_h = data['tilewidth'], data['tileheight']
        self.width, self.height = self.cols * self.tile_w, self.rows * self.tile_h
        self.firstgid = data['tilesets'][0]['firstgid']

        # 보이는 타일 레이어만 아래(먼저 그릴 것)부터 순서대로 보관
        self.layers = [layer['data'] for layer in data['layers']
                       if layer['type'] == 'tilelayer' and layer.get('visible', True)]

        self.tileset = load_image(tileset_path)
        self.tileset_cols = self.tileset.w // self.tile_w
        self.tileset_rows = self.tileset.h // self.tile_h

    def update(self, dt):
        pass

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
