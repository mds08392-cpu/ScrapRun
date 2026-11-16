import math
import random

from pico2d import *

from core.camera import camera
from core.state_machine import StateMachine
from core.world import World
from objects.bullet import Bullet
from objects.player_states import *

WINDOW_W, WINDOW_H = 800, 600

FRAME_W, FRAME_H = 48, 64       # 스프라이트 한 프레임 크기
SCALE = 2                       # 화면에 그릴 배율

# 벽 충돌 박스 (발밑만 사용, 탑다운이라 상체는 벽 앞을 가려도 됨)
HIT_W, HIT_H = 24, 14           # 충돌 박스 크기 (화면 픽셀)
HIT_FOOT_OFFSET = 26            # 캐릭터 중심(y)에서 발바닥까지 거리

# 일반 걷기 시트의 행 번호 (아래에서부터 0) - 6방향
ROW = {
    'right_down': 0,
    'right_up':   1,
    'up':         2,
    'left_up':    3,
    'left_down':  4,
    'down':       5,
}

# 조준 걷기 시트의 행 번호 (아래에서부터 0) - 8방향
AIM_ROW = {
    'left':       0,
    'right':      1,
    'right_down': 2,
    'right_up':   3,
    'up':         4,
    'left_up':    5,
    'left_down':  6,
    'down':       7,
}

# 각도 45도 단위 구간 -> 방향 (0도 = 오른쪽, 반시계 방향)
AIM_DIRS = ['right', 'right_up', 'up', 'left_up', 'left', 'left_down', 'down', 'right_down']

# 서서 조준할 때 쓰는 조준 걷기 시트의 프레임 (다리가 모인 자세, 정지 화면으로 표시)
# 정지 조준 전용 시트가 없어서 Walk_while_aiming의 한 프레임을 빌려 쓴다
IDLE_AIM_FRAME = 3

# 사격 애니메이션 (총알/반동 등 사격 시스템은 추후 구현, 지금은 애니메이션만)
SHOOT_FPS = 16.0        # 서서 사격할 때 애니메이션 초당 프레임 (걷기/달리기 사격은 이동 FPS를 따름)
SHOOT_MIN_TIME = 0.25   # 좌클릭을 짧게 눌러도 사격 애니메이션을 최소한 이 시간(초)만큼 보여줌

# 각도 60도 단위 구간 -> 6방향 시트 행 이름 (Idle+AIM은 6방향 Idle_Gun 시트를 쓰므로)
AIM_DIRS_6 = ['right_up', 'up', 'left_up', 'left_down', 'down', 'right_down']


# 행동(action) 종류 - 이동 상태(StateMachine)와 별개로 Player가 가진다
ACTION_NONE, ACTION_AIM, ACTION_SHOOT, ACTION_RELOAD = 'NONE', 'AIM', 'SHOOT', 'RELOAD'

# 사격 시점 상태별 기본 탄착 반지름(spread, px) / 한 발당 반지름 증가량(recoil, px)
# 탄착 반지름 = min(spread + 누적 bloom(recoil_acc), SPREAD_MAX). 크로스헤어 눈금도 이 값으로 벌어진다
FIRE_PROFILE = {
    'idle_aim': {'spread': 4,  'recoil': 2.0},   # 서서 조준: 가장 정확
    'walk_aim': {'spread': 7,  'recoil': 2.5},
    'idle':     {'spread': 9,  'recoil': 3.5},   # 조준 없이 좌클릭
    'walk':     {'spread': 13, 'recoil': 4.5},
    'run':      {'spread': 20, 'recoil': 6.0},   # 가장 부정확
}
RECOIL_MAX = 34         # bloom(recoil_acc) 상한
SPREAD_MAX = 48         # 탄착 반지름 상한
RECOVER_DELAY = 0.12    # 마지막 발사 후 이 시간(초)이 지나야 bloom이 줄어들기 시작
RECOVER_RATE = 70.0     # bloom이 줄어드는 속도 (px/초)
FIRE_INTERVAL = 0.11    # 연사 간격(초)
MIN_AIM_DIST = 40       # 마우스가 캐릭터에 이보다 가까우면 이 거리로 밀어서 계산
MUZZLE_DIST = 20        # 캐릭터 중심에서 이만큼 앞에서 총알이 나온다


def pick_target_point(px, py, mx, my, aim_angle, radius, rand=random.random):
    """캐릭터(px, py)가 마우스 월드 좌표(mx, my)를 향해 쏠 때, 마우스를 중심으로 한
    반지름 radius 원 안에서 고르게 한 점을 뽑아 반환한다. (pico2d 없이 테스트 가능한 순수 함수)
    마우스가 캐릭터에 MIN_AIM_DIST보다 가까우면 같은 방향으로 MIN_AIM_DIST만큼 밀어낸 점을 중심으로 쓴다."""
    dx, dy = mx - px, my - py
    d = math.hypot(dx, dy)
    if d < MIN_AIM_DIST:
        ang = math.atan2(dy, dx) if d > 0 else math.radians(aim_angle)
        mx, my = px + math.cos(ang) * MIN_AIM_DIST, py + math.sin(ang) * MIN_AIM_DIST
    r = radius * math.sqrt(rand())          # sqrt가 있어야 원 안에 고르게 퍼진다
    t = 2.0 * math.pi * rand()
    return mx + r * math.cos(t), my + r * math.sin(t)


class Player:
    """플레이어 캐릭터. 입력/방향/조준 데이터를 갖고 상태 머신에 동작을 위임한다."""

    def __init__(self):
        """위치, 프레임, 키 입력, 바라보는 방향, 조준 정보, 이미지, 상태 머신을 초기화한다."""
        # 위치 / 애니메이션
        self.x, self.y = WINDOW_W // 2, WINDOW_H // 2
        self.bound_w, self.bound_h = WINDOW_W, WINDOW_H  # 이동 가능 영역 (맵 크기로 set_bounds)
        self.tile_map = None    # 벽 충돌 판정용 맵 (set_map으로 지정)
        self.world = None       # 총알을 넣을 World (set_world로 지정)
        self.frame = 0.0
        self.dt = 0.0

        # 이동 입력 (WASD)
        self.keys = {k: False for k in MOVE_KEYS}
        self.dir_x, self.dir_y = 0, 0
        self.face_x = 'right'   # 마지막 좌우 입력
        self.face_y = 'down'    # 마지막 상하 입력
        self.last_vertical_only = True  # 마지막 이동이 상/하만이었는지 (멈췄을 때 방향 유지용)
        self.run_held = False   # Shift 누르고 있는지 (달리기)

        # 대시 (Space)
        self.dash_cooldown = 0.0        # 다음 대시까지 남은 시간
        self.dash_dx, self.dash_dy = 0, 0
        self.dash_row = 'down'          # 대시 중 고정된 스프라이트 방향

        # 조준 (우클릭 유지) / 마우스 (마우스 좌표는 화면 좌표, 왼쪽 아래 원점)
        self.aiming = False         # 실제로 조준 중인지 (Run/Dash 중에는 False)
        self.aim_held = False       # 우클릭을 누르고 있는지 (Run/Dash가 끝나면 조준 재개용)
        self.mouse_x, self.mouse_y = WINDOW_W // 2, WINDOW_H // 2
        self.aim_angle = -90.0      # 캐릭터 -> 마우스 각도 (도, 0 = 오른쪽, 반시계)
        self.aim_dir = 'down'       # 8방향 (조준 걷기 시트용)
        self.aim_dir6 = 'down'      # 6방향 (Idle_Gun 시트용)

        # 행동 (이동 상태와 별개): NONE / AIM / SHOOT / RELOAD
        self.action = ACTION_NONE

        # 사격 애니메이션 (좌클릭)
        self.shoot_held = False     # 좌클릭을 누르고 있는지 (Dash가 끝나면 사격 재개용)
        self.shoot_timer = 0.0      # 최소 사격 표시 시간 남은 값
        self.shoot_frame = 0.0      # 서서 사격할 때 프레임
        self.shot_queued = False    # 클릭 후 아직 한 발도 안 나갔으면 True (짧은 클릭도 한 발은 나가게)

        # 전투 데이터
        self.hp = self.max_hp = 100
        self.ammo = self.max_ammo = 30
        self.shoot_cooldown = 0.0   # 다음 발사까지 남은 시간
        self.reload_timer = 0.0     # 재장전 남은 시간
        self.recoil_acc = 0.0       # 연사로 누적된 탄착 반지름 증가량 (bloom, px)
        self.since_shot = RECOVER_DELAY   # 마지막 발사 후 지난 시간

        # 이미지 (구현이 진행되면 사격/재장전/달리기 시트를 여기에 추가)
        self.images = {
            'idle': load_image('resources/images/characters/Idle/Normal/idle.png'),
            'walk':load_image('resources/images/characters/Walk/Normal/walk.png'),
            'walk_aim': load_image('resources/images/characters/Walk_while_Aiming - NEW/Walk_while_aiming.png'),
            'shoot': load_image('resources/images/characters/Attack/Gun/Shooting.png'),
            'walk_shoot': load_image('resources/images/characters/Walk_while_Shooting - NEW/Walk_while_Shooting.png'),
            'run_shoot': load_image('resources/images/characters/Run_while_shooting/Run_while_shooting.png'),
            'run': load_image('resources/images/characters/Run/Normal/run.png'),
            'dash': load_image('resources/images/characters/Dash/Normal/Dash.png'),
            'dash_dust': load_image('resources/images/characters/Dash/Dust/Dash_Dust.png'),
            'dash_shadow': load_image('resources/images/characters/Dash/Dash_Shadow.png'),
        }

        # 이동 상태 머신 (Death 진입 전이는 해당 상태 구현 시 추가)
        # Dash 종료는 dash_end(Idle)가 모든 DASH_END에 맞으므로 반드시 마지막에 둔다
        self.state_machine = StateMachine(self, Idle, {
            Idle: {start_moving: Walk, start_running: Run, dash_key: Dash},
            Walk: {stop_moving: Idle, start_running: Run, dash_key: Dash},
            Run: {stop_running: Walk, stop_moving: Idle, dash_key: Dash},
            Dash: {dash_end_run: Run, dash_end_walk: Walk, dash_end: Idle},
            Death: {},
        })

    def set_bounds(self, w, h):
        """플레이어가 움직일 수 있는 영역(보통 맵 크기)을 지정한다."""
        self.bound_w, self.bound_h = w, h

    def set_map(self, tile_map):
        """벽 충돌에 쓸 맵을 지정하고 이동 영역도 맵 크기로 맞춘다."""
        self.tile_map = tile_map
        self.set_bounds(tile_map.width, tile_map.height)

    def set_world(self, world):
        """총알을 생성해 넣을 World를 지정한다."""
        self.world = world

    @property
    def sort_y(self):
        """y축 정렬 피벗 = 발바닥 y (충돌 박스 아랫변과 같다)."""
        return self.y - HIT_FOOT_OFFSET

    def get_hitbox(self, x=None, y=None):
        """(x, y)에 서 있을 때의 발밑 충돌 박스 (left, bottom, right, top). 생략하면 현재 위치."""
        x = self.x if x is None else x
        y = self.y if y is None else y
        bottom = y - HIT_FOOT_OFFSET
        return x - HIT_W / 2, bottom, x + HIT_W / 2, bottom + HIT_H

    def can_move_to(self, x, y):
        """(x, y)로 옮겼을 때 충돌 박스가 벽에 걸리지 않으면 True."""
        if self.tile_map is None:
            return True
        return not self.tile_map.is_blocked_rect(*self.get_hitbox(x, y))

    def move_x(self, nx):
        """x를 nx로 옮긴다. 벽에 막히면 충돌 박스가 벽 경계에 딱 붙는 위치까지만 이동한다."""
        if nx == self.x or self.can_move_to(nx, self.y):
            self.x = nx
            return
        tw = self.tile_map.tile_w
        if nx > self.x:   # 오른쪽: 새로 걸친 칸의 왼쪽 경계에 박스 오른쪽을 맞춤
            edge = (nx + HIT_W / 2) // tw * tw
            sx = edge - HIT_W / 2
        else:             # 왼쪽: 새로 걸친 칸의 오른쪽 경계에 박스 왼쪽을 맞춤
            edge = ((nx - HIT_W / 2) // tw + 1) * tw
            sx = edge + HIT_W / 2
        if min(self.x, nx) <= sx <= max(self.x, nx) and self.can_move_to(sx, self.y):
            self.x = sx

    def move_y(self, ny):
        """y를 ny로 옮긴다. 벽에 막히면 충돌 박스가 벽 경계에 딱 붙는 위치까지만 이동한다."""
        if ny == self.y or self.can_move_to(self.x, ny):
            self.y = ny
            return
        th = self.tile_map.tile_h
        if ny > self.y:   # 위쪽: 박스 윗변을 위 칸의 아래 경계에 맞춤
            edge = (ny - HIT_FOOT_OFFSET + HIT_H) // th * th
            sy = edge - HIT_H + HIT_FOOT_OFFSET
        else:             # 아래쪽: 박스 아랫변을 아래 칸의 위 경계에 맞춤
            edge = ((ny - HIT_FOOT_OFFSET) // th + 1) * th
            sy = edge + HIT_FOOT_OFFSET
        if min(self.y, ny) <= sy <= max(self.y, ny) and self.can_move_to(self.x, sy):
            self.y = sy

    def draw_hitbox(self):
        """디버그용: 발밑 충돌 박스를 그린다."""
        l, b, r, t = self.get_hitbox()
        draw_rectangle(l - camera.x, b - camera.y, r - camera.x, t - camera.y, 0, 255, 0)

    def facing_row(self):
        """현재 이동 입력과 마지막 방향을 바탕으로 일반 걷기 시트의 행 이름(6방향)을 반환한다."""
        if self.dir_x == 0 and self.dir_y > 0:
            return 'up'
        if self.dir_x == 0 and self.dir_y < 0:
            return 'down'
        if self.dir_x == 0 and self.dir_y == 0 and self.last_vertical_only:
            return self.face_y
        # 좌/우가 들어간 경우 -> 바라보는 좌우 + 상/하 조합
        return f'{self.face_x}_{self.face_y}'

    def update_aim_dir(self):
        """캐릭터(화면 좌표)에서 마우스까지의 각도로 8방향 aim_dir, 6방향 aim_dir6을 갱신한다."""
        dx = self.mouse_x - (self.x - camera.x)
        dy = self.mouse_y - (self.y - camera.y)
        self.aim_angle = math.degrees(math.atan2(dy, dx))
        a = self.aim_angle % 360
        self.aim_dir = AIM_DIRS[int((a + 22.5) // 45) % 8]
        self.aim_dir6 = AIM_DIRS_6[int(a // 60) % 6]

    def apply_aim_to_facing(self):
        """조준 해제 시 조준하던 방향을 일반 걷기 방향(face_x, face_y)으로 이어받는다."""
        d = self.aim_dir6
        if d in ('up', 'down'):
            self.face_y = d
            self.last_vertical_only = True
        else:
            self.face_x, self.face_y = d.split('_')
            self.last_vertical_only = False

    def draw_walk_frame(self, frame):
        """사격/조준 여부에 따라 알맞은 시트/행을 골라 걷기 프레임 한 장을 그린다."""
        if self.action == ACTION_SHOOT:
            image, row = self.images['walk_shoot'], AIM_ROW[self.aim_dir]
        elif self.aiming:
            image, row = self.images['walk_aim'], AIM_ROW[self.aim_dir]
        else:
            image, row = self.images['walk'], ROW[self.facing_row()]
        image.clip_draw(frame * FRAME_W, row * FRAME_H, FRAME_W, FRAME_H,
                        self.x - camera.x, self.y - camera.y, FRAME_W * SCALE, FRAME_H * SCALE)

    def draw_run_frame(self, frame):
        """달리기 프레임 한 장을 그린다. 사격 중이면 달리며 사격 시트를 마우스 방향(8방향)으로,
        아니면 맨손 달리기 시트를 바라보는 방향(6방향)으로."""
        if self.action == ACTION_SHOOT:
            image, row = self.images['run_shoot'], AIM_ROW[self.aim_dir]
        else:
            image, row = self.images['run'], ROW[self.facing_row()]
        image.clip_draw(frame * FRAME_W, row * FRAME_H, FRAME_W, FRAME_H,
                        self.x - camera.x, self.y - camera.y, FRAME_W * SCALE, FRAME_H * SCALE)

    def draw_dash_frame(self, frame):
        """대시 고정 방향(6방향)으로 그림자, 먼지, 본체 프레임을 차례로 그린다."""
        sx, sy = self.x - camera.x, self.y - camera.y
        w, h = FRAME_W * SCALE, FRAME_H * SCALE
        row = ROW[self.dash_row] * FRAME_H
        self.images['dash_shadow'].clip_draw(frame * FRAME_W, 0, FRAME_W, FRAME_H, sx, sy, w, h)
        self.images['dash_dust'].clip_draw(frame * FRAME_W, row, FRAME_W, FRAME_H, sx, sy, w, h)
        self.images['dash'].clip_draw(frame * FRAME_W, row, FRAME_W, FRAME_H, sx, sy, w, h)

    def draw_idle_frame(self, frame):
        """Idle 프레임 한 장을 그린다. 사격 중이면 서서 사격 시트를 마우스 방향(8방향)으로,
        조준 중이면 조준 걷기 시트의 서 있는 자세 프레임을 고정해서,
        아니면 맨손 Idle 시트를 바라보는 방향으로."""
        if self.action == ACTION_SHOOT:
            image, row = self.images['shoot'], AIM_ROW[self.aim_dir]
            frame = int(self.shoot_frame)
        elif self.aiming:
            image, row = self.images['walk_aim'], AIM_ROW[self.aim_dir]
            frame = IDLE_AIM_FRAME
        else:
            image, row = self.images['idle'], ROW[self.facing_row()]
        image.clip_draw(frame * FRAME_W, row * FRAME_H, FRAME_W, FRAME_H,
                        self.x - camera.x, self.y - camera.y, FRAME_W * SCALE, FRAME_H * SCALE)

    def handle_mouse_event(self, event):
        """마우스 이동 좌표 갱신, 우클릭 누름/뗌에 따른 조준 시작/해제, 좌클릭 사격을 처리한다."""
        if event.type in (SDL_MOUSEMOTION, SDL_MOUSEBUTTONDOWN, SDL_MOUSEBUTTONUP):
            self.mouse_x, self.mouse_y = event.x, WINDOW_H - 1 - event.y  # SDL은 위가 0이라 y 반전
        if event.type in (SDL_MOUSEBUTTONDOWN, SDL_MOUSEBUTTONUP) and event.button == SDL_BUTTON_RIGHT:
            self.aim_held = event.type == SDL_MOUSEBUTTONDOWN
            if self.aim_held:
                self.start_aim()
            else:
                self.stop_aim()
        if event.type in (SDL_MOUSEBUTTONDOWN, SDL_MOUSEBUTTONUP) and event.button == SDL_BUTTON_LEFT:
            self.shoot_held = event.type == SDL_MOUSEBUTTONDOWN
            if self.shoot_held:
                self.start_shoot()
            # 뗐을 때는 update에서 최소 표시 시간이 지나면 stop_shoot

    def handle_event(self, event):
        """마우스/WASD/Shift/Space 입력을 처리하고 이동·달리기·대시 시 상태 머신에 이벤트를 전달한다.
        (사격은 애니메이션만, 총알 발사는 추후 구현)"""
        if event.type in (SDL_MOUSEMOTION, SDL_MOUSEBUTTONDOWN, SDL_MOUSEBUTTONUP):
            self.handle_mouse_event(event)
            return

        # Space: 대시 (쿨다운 중이면 무시, Dash/Death 상태에서는 전이 테이블에 없어 무시됨)
        if event.type == SDL_KEYDOWN and event.key in DASH_KEYS:
            if self.dash_cooldown <= 0:
                self.state_machine.handle_event(('DASH', None))
            return

        # Shift: 이동 중일 때만 달리기 시작/종료 (Shift만 누르면 무반응)
        if event.type in (SDL_KEYDOWN, SDL_KEYUP) and event.key in RUN_KEYS:
            self.run_held = event.type == SDL_KEYDOWN
            if self.dir_x != 0 or self.dir_y != 0:
                self.state_machine.handle_event(('START_RUN' if self.run_held else 'STOP_RUN', None))
            return

        e = ('INPUT', event)
        if not move_key_event(e):
            return

        pressed = event.type == SDL_KEYDOWN
        self.keys[event.key] = pressed

        # 새로 누른 키로 바라보는 방향 갱신
        if pressed:
            if event.key == SDLK_a:
                self.face_x = 'left'
            elif event.key == SDLK_d:
                self.face_x = 'right'
            elif event.key == SDLK_w:
                self.face_y = 'up'
            elif event.key == SDLK_s:
                self.face_y = 'down'

        was_moving = self.dir_x != 0 or self.dir_y != 0
        self.dir_x = self.keys[SDLK_d] - self.keys[SDLK_a]
        self.dir_y = self.keys[SDLK_w] - self.keys[SDLK_s]
        now_moving = self.dir_x != 0 or self.dir_y != 0

        # 멈췄을 때 마지막으로 보던 방향 유지용 (상/하만 누르다 멈춘 경우)
        if now_moving:
            self.last_vertical_only = self.dir_x == 0

        if now_moving and not was_moving:
            # Shift를 누른 채 이동을 시작하면 바로 달리기
            self.state_machine.handle_event(('START_RUN' if self.run_held else 'START_MOVE', None))
        elif was_moving and not now_moving:
            self.state_machine.handle_event(('STOP_MOVE', None))

    def can_act(self):
        """Dash/Death 중이면 False (조준/사격/재장전 불가)."""
        return self.state_machine.cur_state not in (Dash, Death)

    def start_aim(self):
        """우클릭 누름: 가능한 상태(Idle/Walk)일 때만 조준 시작, action을 AIM으로. Run/Dash면 무시."""
        if self.state_machine.cur_state not in (Idle, Walk) or self.aiming:
            return
        self.aiming = True
        if self.action == ACTION_NONE:
            self.action = ACTION_AIM
        self.update_aim_dir()

    def stop_aim(self):
        """조준 해제 (우클릭 뗌, Run/Dash 진입): 조준하던 방향을 바라보는 방향으로 이어받는다."""
        if not self.aiming:
            return
        self.aiming = False
        if self.action == ACTION_AIM:
            self.action = ACTION_NONE
        self.update_aim_dir()
        self.apply_aim_to_facing()

    def start_shoot(self):
        """좌클릭: Dash/Death/재장전 중이 아니면 action을 SHOOT로 바꿔 사격 애니메이션을 시작한다.
        실제 발사는 update에서 쿨다운/탄약을 확인한 뒤 fire()로 한다."""
        if not self.can_act() or self.action == ACTION_RELOAD:
            return
        if self.action != ACTION_SHOOT:
            self.action = ACTION_SHOOT
            self.shoot_frame = 0.0
        self.shoot_timer = SHOOT_MIN_TIME
        self.shot_queued = True
        self.update_aim_dir()

    def stop_shoot(self):
        """사격 종료: 조준 중이면 AIM으로, 아니면 NONE으로 돌아가고 사격하던 방향을 바라본다.
        (추후: 반동 회복 시작)"""
        if self.action != ACTION_SHOOT:
            return
        self.shot_queued = False
        if self.aiming:
            self.action = ACTION_AIM
        else:
            self.action = ACTION_NONE
            self.apply_aim_to_facing()

    def start_reload(self):
        """R키 또는 탄약 0: 가능한 상태에서 action을 RELOAD로, 재장전 타이머 시작."""
        pass

    def finish_reload(self):
        """재장전 시간이 끝나면 ammo를 max_ammo로 채우고 action을 NONE으로."""
        pass

    def accuracy_state(self):
        """사격 시점의 (이동 상태, AIM 여부)로 FIRE_PROFILE 키를 반환한다."""
        s = self.state_machine.cur_state
        if s is Run:
            return 'run'
        if s is Walk:
            return 'walk_aim' if self.aiming else 'walk'
        return 'idle_aim' if self.aiming else 'idle'   # Idle (Dash/Death는 사격 불가라 여기 안 옴)

    def spread_radius(self):
        """지금 쏘면 총알이 향할 수 있는 원의 반지름(px) = 자세별 기본값 + 누적 bloom."""
        base = FIRE_PROFILE[self.accuracy_state()]['spread']
        return min(base + self.recoil_acc, SPREAD_MAX)

    def pick_target(self, radius):
        """마우스 월드 좌표를 중심으로 한 반지름 radius 원 안의 한 점(총알 방향)을 고른다."""
        return pick_target_point(self.x, self.y, self.mouse_x + camera.x, self.mouse_y + camera.y,
                                 self.aim_angle, radius)

    def can_fire(self):
        """사격 중이고 (좌클릭 유지 또는 아직 한 발도 안 쏜 클릭), 쿨다운이 끝났고 탄약이 있으면 True."""
        return (self.action == ACTION_SHOOT and (self.shoot_held or self.shot_queued)
                and self.shoot_cooldown <= 0 and self.ammo > 0)

    def fire(self):
        """지금 반지름의 원 안으로 총알을 쏜 뒤 bloom을 늘린다. (쏘고 나서 벌려야 첫 발이 작은 원 안에 들어감)"""
        prof = FIRE_PROFILE[self.accuracy_state()]
        tx, ty = self.pick_target(self.spread_radius())
        if self.world is not None:
            d = math.hypot(tx - self.x, ty - self.y) or 1.0
            sx = self.x + (tx - self.x) / d * MUZZLE_DIST
            sy = self.y + (ty - self.y) / d * MUZZLE_DIST
            self.world.add_object(Bullet(self.world, self.tile_map, sx, sy, tx, ty), World.LAYER_BULLET)
        self.recoil_acc = min(self.recoil_acc + prof['recoil'], RECOIL_MAX)
        self.shoot_cooldown = FIRE_INTERVAL
        self.since_shot = 0.0
        self.shot_queued = False
        self.ammo -= 1

    def recover_recoil(self):
        """마지막 발사 후 RECOVER_DELAY가 지나면 누적 bloom을 RECOVER_RATE로 줄인다."""
        if self.since_shot >= RECOVER_DELAY:
            self.recoil_acc = max(0.0, self.recoil_acc - RECOVER_RATE * self.dt)

    def current_sheet(self):
        """(이동 상태, action) 조합으로 이미지/행 테이블에서 시트와 방향 행을 고른다."""
        pass

    def update(self, dt):
        """dt를 저장하고 상태 머신을 업데이트하며, 조준 중이면 조준 방향을 갱신한다."""
        self.dt = dt
        if self.dash_cooldown > 0:
            self.dash_cooldown -= dt
        self.state_machine.update()

        self.shoot_cooldown = max(0.0, self.shoot_cooldown - dt)
        self.since_shot += dt
        self.recover_recoil()
        if self.can_fire():
            self.update_aim_dir()
            self.fire()

        if self.action == ACTION_SHOOT:
            self.shoot_frame = (self.shoot_frame + SHOOT_FPS * dt) % FRAME_COUNT
            self.shoot_timer -= dt
            if not self.shoot_held and self.shoot_timer <= 0:
                self.stop_shoot()

        if self.aiming or self.action == ACTION_SHOOT:
            self.update_aim_dir()  # 카메라가 움직이면 마우스가 가만히 있어도 각도가 바뀜

    def draw(self):
        """상태 머신에 그리기를 위임한다."""
        self.state_machine.draw()
