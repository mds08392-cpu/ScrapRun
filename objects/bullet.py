import math

from pico2d import load_image

from core.camera import camera

BULLET_SPEED = 900.0    # px/초
BULLET_RANGE = 1200.0   # 이 거리를 날아가면 사라짐
BULLET_HEIGHT = 26      # 총알이 지면에서 떠 있는 높이 (플레이어 중심 ~ 발바닥 거리와 같게)
HIT_STEP = 4.0          # 벽 판정을 이 거리(px)마다 나눠서 해 착탄 위치를 정확히 잡는다

# 이펙트 시트: 한 프레임 16x16, 가로 한 줄, 오른쪽(0도)을 보는 방향 (크로스헤어_사격시스템.md 8번)
FX_FRAME = 16
FX_SCALE = 2            # 캐릭터와 같은 배율
FX_SIZE = FX_FRAME * FX_SCALE

BULLET_FRAMES, BULLET_FRAME_TIME = 4, 0.06          # 반복
MUZZLE_FRAMES, MUZZLE_FRAME_TIME = 3, 0.04          # 한 번
IMPACT_FRAMES, IMPACT_FRAME_TIME = 4, 0.05          # 한 번

_images = {}


def fx_image(name):
    """이펙트 이미지를 한 번만 로드해서 공유한다 (총알마다 load_image 하지 않도록)."""
    if name not in _images:
        _images[name] = load_image(f'resources/images/effects/{name}.png')
    return _images[name]


def spawn_shot(world, tile_map, layer, x, y, tx, ty):
    """총구(x, y)에서 (tx, ty) 방향으로 총알과 총구 화염을 함께 생성해 world에 넣는다."""
    bullet = Bullet(world, tile_map, layer, x, y, tx, ty)
    world.add_object(MuzzleFlash(world, x, y, bullet.rad), layer)
    world.add_object(bullet, layer)


class Bullet:
    """(x, y)에서 (tx, ty) 방향으로 직선 비행하는 총알 (예광탄 스프라이트, 진행 방향으로 회전).
    목표점은 목적지가 아니라 방향이라 지나쳐서 계속 날아간다.
    벽 판정과 y축 정렬은 총알 바로 밑 지면 위치(y - BULLET_HEIGHT)로 하고, 벽에 닿으면 착탄 이펙트를 남긴다."""

    def __init__(self, world, tile_map, layer, x, y, tx, ty):
        self.world, self.tile_map, self.layer = world, tile_map, layer
        self.x, self.y = x, y
        d = math.hypot(tx - x, ty - y) or 1.0
        self.vx, self.vy = (tx - x) / d, (ty - y) / d
        self.rad = math.atan2(self.vy, self.vx)   # pico2d는 y가 위라서 그대로 회전각으로 쓴다
        self.traveled = 0.0
        self.frame = 0.0

    @property
    def sort_y(self):
        """y축 정렬 피벗 = 총알 바로 밑 지면 y."""
        return self.y - BULLET_HEIGHT

    def blocked_at(self, x, y):
        """총알이 (x, y)에 있을 때 지면 위치가 벽 칸이거나 맵 밖이면 True."""
        if self.tile_map is None:
            return False
        gy = y - BULLET_HEIGHT
        return self.tile_map.is_blocked_rect(x - 1, gy - 1, x + 1, gy + 1)

    def update(self, dt):
        self.frame = (self.frame + dt / BULLET_FRAME_TIME) % BULLET_FRAMES
        remaining = BULLET_SPEED * dt
        while remaining > 0:   # 빠른 총알이 벽을 뚫거나 벽 깊숙이 박히지 않도록 잘게 나눠 이동
            step = min(HIT_STEP, remaining)
            nx, ny = self.x + self.vx * step, self.y + self.vy * step
            if self.blocked_at(nx, ny):   # 벽 바로 앞(마지막 빈 위치)에 착탄
                self.world.add_object(Impact(self.world, self.x, self.y), self.layer)
                self.world.remove_object(self)
                return
            self.x, self.y = nx, ny
            self.traveled += step
            remaining -= step
        if self.traveled >= BULLET_RANGE:
            self.world.remove_object(self)

    def draw(self):
        fx_image('bullet').clip_composite_draw(int(self.frame) * FX_FRAME, 0, FX_FRAME, FX_FRAME, self.rad, '',
                                               self.x - camera.x, self.y - camera.y, FX_SIZE, FX_SIZE)


class OneShotEffect:
    """한 번 재생하고 스스로 사라지는 이펙트 공통 부분. 높이는 총알과 같아서 정렬도 총알 기준."""
    IMAGE, FRAMES, FRAME_TIME = '', 1, 0.1

    def __init__(self, world, x, y, rad=0.0):
        self.world = world
        self.x, self.y, self.rad = x, y, rad
        self.time = 0.0

    @property
    def sort_y(self):
        return self.y - BULLET_HEIGHT

    def update(self, dt):
        self.time += dt
        if self.time >= self.FRAMES * self.FRAME_TIME:
            self.world.remove_object(self)

    def draw(self):
        frame = min(int(self.time / self.FRAME_TIME), self.FRAMES - 1)
        fx_image(self.IMAGE).clip_composite_draw(frame * FX_FRAME, 0, FX_FRAME, FX_FRAME, self.rad, '',
                                                 self.x - camera.x, self.y - camera.y, FX_SIZE, FX_SIZE)


class MuzzleFlash(OneShotEffect):
    """발사 순간 총구 화염. 그림의 왼쪽 끝이 총구라서 중심을 진행 방향으로 반 프레임만큼 민다."""
    IMAGE, FRAMES, FRAME_TIME = 'muzzle_flash', MUZZLE_FRAMES, MUZZLE_FRAME_TIME

    def __init__(self, world, muzzle_x, muzzle_y, rad):
        half = FX_SIZE / 2
        super().__init__(world, muzzle_x + math.cos(rad) * half, muzzle_y + math.sin(rad) * half, rad)
        self.muzzle_y = muzzle_y

    @property
    def sort_y(self):
        return self.muzzle_y - BULLET_HEIGHT   # 정렬은 총구 기준 (중심을 민 만큼 앞뒤가 바뀌지 않게)


class Impact(OneShotEffect):
    """벽에 맞은 자리의 착탄 이펙트 (방사형이라 회전하지 않음)."""
    IMAGE, FRAMES, FRAME_TIME = 'bullet_impact', IMPACT_FRAMES, IMPACT_FRAME_TIME
