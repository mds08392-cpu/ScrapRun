import math

from pico2d import draw_line, draw_rectangle

from core.camera import camera

BULLET_SPEED = 900.0    # px/초
BULLET_RANGE = 1200.0   # 이 거리를 날아가면 사라짐
BULLET_HEIGHT = 26      # 총알이 지면에서 떠 있는 높이 (플레이어 중심 ~ 발바닥 거리와 같게)
TRAIL_LEN = 10          # 꼬리 길이
BULLET_COLOR = (255, 220, 90)
TRAIL_COLOR = (255, 170, 40)


class Bullet:
    """(x, y)에서 (tx, ty) 방향으로 직선 비행하는 총알.
    목표점은 목적지가 아니라 방향이라 지나쳐서 계속 날아간다.
    벽 판정과 y축 정렬은 총알 바로 밑 지면 위치(y - BULLET_HEIGHT)로 한다."""

    def __init__(self, world, tile_map, x, y, tx, ty):
        self.world, self.tile_map = world, tile_map
        self.x, self.y = x, y
        d = math.hypot(tx - x, ty - y) or 1.0
        self.vx, self.vy = (tx - x) / d, (ty - y) / d
        self.traveled = 0.0

    @property
    def sort_y(self):
        """y축 정렬 피벗 = 총알 바로 밑 지면 y."""
        return self.y - BULLET_HEIGHT

    def hit_wall(self):
        """지면 위치가 벽 칸이거나 맵 밖이면 True."""
        if self.tile_map is None:
            return False
        gx, gy = self.x, self.sort_y
        return self.tile_map.is_blocked_rect(gx - 1, gy - 1, gx + 1, gy + 1)

    def update(self, dt):
        step = BULLET_SPEED * dt
        self.x += self.vx * step
        self.y += self.vy * step
        self.traveled += step
        if self.traveled >= BULLET_RANGE or self.hit_wall():
            self.world.remove_object(self)

    def draw(self):
        sx, sy = self.x - camera.x, self.y - camera.y
        draw_line(int(sx - self.vx * TRAIL_LEN), int(sy - self.vy * TRAIL_LEN), int(sx), int(sy), *TRAIL_COLOR)
        draw_rectangle(int(sx) - 1, int(sy) - 1, int(sx) + 1, int(sy) + 1, *BULLET_COLOR, 255, True)
