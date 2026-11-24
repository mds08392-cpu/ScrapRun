import math

import pico2d.pico2d as pico2d_core
from pico2d import draw_line, draw_rectangle
from sdl2 import SDL_SetRenderDrawBlendMode, SDL_BLENDMODE_BLEND, SDL_BLENDMODE_NONE

from core.camera import camera
from objects.bullet import BULLET_HEIGHT

# 레이저 도트 파츠('laser' 플래그)를 달면 총구에서 마우스 방향으로 빨간 레이저를 그린다.
# 총알이 실제로 날아가는 높이(지면 + BULLET_HEIGHT)로 그리고, 벽에 닿으면 거기서 끊고 점을 찍는다.
LASER_COLOR = (255, 40, 40)
LASER_ALPHA = 150           # 선 투명도 (0~255)
DOT_ALPHA = 230             # 끝 점 투명도
DOT_SIZE = 2                # 끝 점 반 크기 (px)
LASER_MAX = 900.0           # 레이저 최대 길이 (px)
LASER_STEP = 6.0            # 벽 판정 간격 (px)


class LaserSight:
    """레이저 도트 표시. UI가 아니라 월드 좌표에 그리지만 y축 정렬 없이 world.draw() 뒤에 main에서 그린다
    (가늘어서 건물에 가려질 필요가 없고, 가려지면 레이저를 단 의미가 없다)."""

    def __init__(self, player):
        self.player = player

    def visible(self):
        """레이저 파츠를 달았고, 총을 들고 있을 수 있는 상태(Dash/Death/재장전 아님)일 때만."""
        p = self.player
        return p.gun.has_flag('laser') and p.can_act() and not p.is_reloading()

    def end_point(self, sx, sy, ux, uy):
        """총구(sx, sy)에서 (ux, uy) 방향으로 벽이나 최대 길이까지 간 끝 점 (월드 좌표)."""
        tile_map = self.player.tile_map
        d = 0.0
        while d < LASER_MAX:
            nd = min(d + LASER_STEP, LASER_MAX)
            nx, ny = sx + ux * nd, sy + uy * nd
            gy = ny - BULLET_HEIGHT
            if tile_map is not None and tile_map.is_blocked_rect(nx - 1, gy - 1, nx + 1, gy + 1):
                break
            d = nd
        return sx + ux * d, sy + uy * d

    def draw(self):
        if not self.visible():
            return
        p = self.player
        sx, sy, ux, uy = p.muzzle_point()
        ex, ey = self.end_point(sx, sy, ux, uy)
        x1, y1 = sx - camera.x, sy - camera.y
        x2, y2 = ex - camera.x, ey - camera.y

        SDL_SetRenderDrawBlendMode(pico2d_core.renderer, SDL_BLENDMODE_BLEND)
        draw_line(x1, y1, x2, y2, *LASER_COLOR, LASER_ALPHA)
        # 기울기에 따라 옆으로 한 줄 더 그어 2px 두께로
        if abs(uy) > abs(ux):
            draw_line(x1 + 1, y1, x2 + 1, y2, *LASER_COLOR, LASER_ALPHA)
        else:
            draw_line(x1, y1 + 1, x2, y2 + 1, *LASER_COLOR, LASER_ALPHA)
        draw_rectangle(x2 - DOT_SIZE, y2 - DOT_SIZE, x2 + DOT_SIZE, y2 + DOT_SIZE, *LASER_COLOR, DOT_ALPHA, True)
        SDL_SetRenderDrawBlendMode(pico2d_core.renderer, SDL_BLENDMODE_NONE)
