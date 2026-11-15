import json
import os
import xml.etree.ElementTree as ET

from pico2d import *

from core.camera import camera

# ---------------------------------------------------------------
# 맵 레이어 규칙 (Tiled 레이어 이름으로 역할을 정한다 -> 새 맵도 코드 수정 없이 동작)
#   ground*      타일 레이어   바닥. 정렬 없이 가장 먼저 그린다 (ground, ground_deco ...)
#   objects*     타일 레이어   건물/소품. 캐릭터와 y축 정렬해서 그린다 (objects, objects_2 ...)
#   sort_groups  오브젝트 레이어  사각형 안의 objects 타일을 한 덩어리로 묶고, 사각형 밑변을 피벗으로 사용
#                               (사각형 밖 objects 타일은 자기 칸 밑변이 피벗)
#   interiors    오브젝트 레이어  플레이어 발이 이 사각형 안에 있으면 겹치는 덩어리(건물)를 실내에 있는
#                               것들(플레이어, 나중의 파밍 아이템 등) 뒤로 보낸다 -> 건물 위에 그려짐
#   collision    타일 레이어   충돌 전용 (칠해진 칸 = 벽), 그리지 않음
# ---------------------------------------------------------------
GROUND_PREFIX = 'ground'
OBJECTS_PREFIX = 'objects'
SORT_GROUP_LAYER = 'sort_groups'
INTERIOR_LAYER = 'interiors'
COLLISION_LAYER = 'collision'

# Tiled 타일 ID의 상위 3비트는 뒤집기 플래그이므로 실제 ID만 남길 때 사용
GID_MASK = 0x1FFFFFFF


class Tileset:
    """타일셋 이미지 한 장. 맵에 포함(embed)된 것과 외부 .tsx/.tsj 파일 모두 지원한다."""

    def __init__(self, info, map_dir):
        self.firstgid = info['firstgid']
        base_dir = map_dir
        if 'source' in info:  # 외부 타일셋 파일
            src = os.path.normpath(os.path.join(map_dir, info['source']))
            base_dir = os.path.dirname(src)
            info = self.load_external(src)

        self.tile_w, self.tile_h = info['tilewidth'], info['tileheight']
        self.image = load_image(os.path.normpath(os.path.join(base_dir, info['image'])))
        self.cols = self.image.w // self.tile_w
        self.rows = self.image.h // self.tile_h
        self.count = self.cols * self.rows

    @staticmethod
    def load_external(path):
        if path.endswith('.tsx'):
            root = ET.parse(path).getroot()
            img = root.find('image')
            return {'tilewidth': int(root.get('tilewidth')), 'tileheight': int(root.get('tileheight')),
                    'image': img.get('source')}
        with open(path, encoding='utf-8') as f:  # .tsj / .json
            return json.load(f)

    def draw(self, gid, x, y):
        """gid 타일을 화면 좌표 (x, y)를 중심으로 그린다."""
        idx = gid - self.firstgid
        src_col, src_row = idx % self.cols, idx // self.cols
        # pico2d는 이미지 아래쪽이 y=0 이므로 위에서부터 센 행을 뒤집는다
        self.image.clip_draw(src_col * self.tile_w, (self.rows - 1 - src_row) * self.tile_h,
                             self.tile_w, self.tile_h, x, y)


class MapObject:
    """objects 레이어 타일의 덩어리(건물 하나 또는 1칸 소품). World 정렬 레이어에 넣어 y축 정렬된다."""

    def __init__(self, tile_map, left, bottom, right, top):
        self.tile_map = tile_map
        self.left, self.bottom, self.right, self.top = left, bottom, right, top
        self.x = (left + right) / 2
        self.base_sort_y = bottom     # 피벗 = 덩어리 밑변
        self.sort_y = bottom          # 실제 정렬에 쓰는 값 (건물 안에 있을 때 바뀜)
        self.tiles = []               # (gid, col, row), 레이어 순서대로 쌓임

    def update(self, dt):
        pass

    def overlaps(self, left, bottom, right, top):
        return self.left < right and left < self.right and self.bottom < top and bottom < self.top

    def is_visible(self):
        return self.overlaps(camera.x, camera.y, camera.x + camera.view_w, camera.y + camera.view_h)

    def draw(self):
        if not self.is_visible():
            return
        for gid, col, row in self.tiles:
            self.tile_map.draw_tile(gid, col, row)


class TileMap:
    """Tiled JSON 맵을 읽어 바닥은 직접 그리고, 건물/소품은 MapObject로 만들어 World에 넘긴다."""

    def __init__(self, map_path):
        with open(map_path, encoding='utf-8') as f:
            data = json.load(f)
        map_dir = os.path.dirname(map_path)

        self.cols, self.rows = data['width'], data['height']
        self.tile_w, self.tile_h = data['tilewidth'], data['tileheight']
        self.width, self.height = self.cols * self.tile_w, self.rows * self.tile_h

        # firstgid 큰 것부터 찾도록 정렬 (여러 타일셋 지원)
        self.tilesets = sorted((Tileset(info, map_dir) for info in data['tilesets']),
                               key=lambda ts: -ts.firstgid)

        self.ground_layers = []                            # 바닥 타일 레이어 데이터
        object_layers = []                                 # objects 타일 레이어 데이터
        self.blocked = [False] * (self.cols * self.rows)   # 인덱스 = row * cols + col (row는 위에서부터 0)
        self.group_rects = []                              # sort_groups 사각형 (월드 좌표)
        self.interior_rects = []                           # interiors 사각형 (월드 좌표)

        for layer in data['layers']:
            name, kind = layer['name'], layer['type']
            if kind == 'tilelayer':
                if name == COLLISION_LAYER:
                    self.blocked = [gid != 0 for gid in layer['data']]
                elif not layer.get('visible', True):
                    continue
                elif name.startswith(OBJECTS_PREFIX):
                    object_layers.append(layer['data'])
                elif name.startswith(GROUND_PREFIX):
                    self.ground_layers.append(layer['data'])
                else:
                    print(f'[TileMap] 알 수 없는 타일 레이어 "{name}" -> 바닥으로 그림')
                    self.ground_layers.append(layer['data'])
            elif kind == 'objectgroup' and name == SORT_GROUP_LAYER:
                self.group_rects = [self.tiled_rect(o) for o in layer['objects']]
            elif kind == 'objectgroup' and name == INTERIOR_LAYER:
                self.interior_rects = [self.tiled_rect(o) for o in layer['objects']]

        self.map_objects = self.build_map_objects(object_layers)

    # ---------------- 생성 ----------------
    def tiled_rect(self, obj):
        """Tiled 오브젝트(왼쪽 위 기준, y 아래로 증가)를 월드 좌표 (left, bottom, right, top)로 변환한다."""
        left, top = obj['x'], self.height - obj['y']
        return left, top - obj['height'], left + obj['width'], top

    def cell_rect(self, col, row):
        left = col * self.tile_w
        bottom = self.height - (row + 1) * self.tile_h
        return left, bottom, left + self.tile_w, bottom + self.tile_h

    def build_map_objects(self, object_layers):
        """objects 타일을 sort_groups 사각형 단위(없으면 칸 단위)의 MapObject로 묶는다."""
        groups = [MapObject(self, *rect) for rect in self.group_rects]
        singles = {}   # (col, row) -> 덩어리에 속하지 않은 칸의 MapObject
        for data in object_layers:
            for row in range(self.rows):
                for col in range(self.cols):
                    gid = data[row * self.cols + col]
                    if not gid:
                        continue
                    cx = col * self.tile_w + self.tile_w / 2
                    cy = self.height - row * self.tile_h - self.tile_h / 2
                    group = next((g for g in groups
                                  if g.left <= cx < g.right and g.bottom <= cy < g.top), None)
                    if group is None:
                        group = singles.get((col, row))
                        if group is None:
                            group = singles[(col, row)] = MapObject(self, *self.cell_rect(col, row))
                    group.tiles.append((gid, col, row))
        return [g for g in groups if g.tiles] + list(singles.values())

    # ---------------- 갱신 ----------------
    def update(self, dt):
        pass

    def update_occlusion(self, foot_x, foot_y):
        """플레이어 발(foot_x, foot_y)이 interiors 사각형 안이면, 그 사각형과 겹치는 건물 뒤쪽 덩어리
        (지붕/뒷벽)의 정렬 피벗을 실내 사각형 윗변으로 올린다. 실내에 있는 것(플레이어, 아이템)은 피벗이
        그보다 아래라 뒤쪽 덩어리 위에 그려진다.
        앞벽 덩어리(피벗이 실내 사각형 밑변 이하)는 그대로 두므로, 앞벽 바로 뒤에 서면 앞벽에 가려진다.
        밖으로 나오면 원래 피벗으로 돌아가 건물 뒤에서는 다시 가려진다."""
        inside = [r for r in self.interior_rects
                  if r[0] <= foot_x < r[2] and r[1] <= foot_y < r[3]]
        for obj in self.map_objects:
            tops = [r[3] for r in inside
                    if r[1] < obj.base_sort_y < r[3] and obj.overlaps(*r)]
            obj.sort_y = max(tops) if tops else obj.base_sort_y

    # ---------------- 충돌 ----------------
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

    # ---------------- 그리기 ----------------
    def draw_tile(self, gid, col, row):
        """맵의 (col, row) 칸(row는 위에서부터 0)에 gid 타일을 그린다."""
        gid &= GID_MASK
        x = col * self.tile_w + self.tile_w // 2 - camera.x
        y = self.height - row * self.tile_h - self.tile_h // 2 - camera.y
        for ts in self.tilesets:
            if gid >= ts.firstgid:
                ts.draw(gid, x, y)
                return

    def draw(self):
        """바닥 레이어만 그린다 (건물/소품은 MapObject가 World에서 정렬되어 그려짐)."""
        col_start = max(0, camera.x // self.tile_w)
        col_end = min(self.cols, (camera.x + camera.view_w) // self.tile_w + 1)
        row_start = max(0, (self.height - camera.y - camera.view_h) // self.tile_h)
        row_end = min(self.rows, (self.height - camera.y) // self.tile_h + 1)

        for layer in self.ground_layers:
            for row in range(row_start, row_end):
                base = row * self.cols
                for col in range(col_start, col_end):
                    gid = layer[base + col]
                    if gid:  # 0은 빈 칸
                        self.draw_tile(gid, col, row)

    def draw_debug(self):
        """디버그용: 벽 칸(빨강), 덩어리 사각형(파랑), 실내 영역(하늘색), 정렬 피벗(노랑)."""
        for row in range(self.rows):
            for col in range(self.cols):
                if self.blocked[row * self.cols + col]:
                    l, b, r, t = self.cell_rect(col, row)
                    draw_rectangle(l - camera.x, b - camera.y, r - camera.x - 1, t - camera.y - 1, 255, 0, 0)
        for l, b, r, t in self.group_rects:
            draw_rectangle(l - camera.x, b - camera.y, r - camera.x - 1, t - camera.y - 1, 0, 0, 255)
        for l, b, r, t in self.interior_rects:
            draw_rectangle(l - camera.x + 2, b - camera.y + 2, r - camera.x - 3, t - camera.y - 3, 0, 255, 255)
        for obj in self.map_objects:
            y = obj.base_sort_y - camera.y
            draw_rectangle(obj.left - camera.x, y, obj.right - camera.x - 1, y + 1, 255, 255, 0)
