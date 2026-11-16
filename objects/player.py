from pico2d import *

from core.camera import camera
from core.state_machine import StateMachine
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


# 행동(action) 종류 - 이동 상태(StateMachine)와 별개로 Player가 가진다
ACTION_NONE, ACTION_AIM, ACTION_SHOOT, ACTION_RELOAD = 'NONE', 'AIM', 'SHOOT', 'RELOAD'

# 사격 시점 상태별 퍼짐(도)/반동 - 값은 구현 시 튜닝
FIRE_PROFILE = {
    'idle_aim':  {'spread': 0, 'recoil': 0},
    'idle':      {'spread': 0, 'recoil': 0},
    'walk_aim':  {'spread': 0, 'recoil': 0},
    'walk':      {'spread': 0, 'recoil': 0},
    'run':       {'spread': 0, 'recoil': 0},
}


class Player:
    """플레이어 캐릭터. 입력/방향/조준 데이터를 갖고 상태 머신에 동작을 위임한다."""

    def __init__(self):
        """위치, 프레임, 키 입력, 바라보는 방향, 조준 정보, 이미지, 상태 머신을 초기화한다."""
        # 위치 / 애니메이션
        self.x, self.y = WINDOW_W // 2, WINDOW_H // 2
        self.bound_w, self.bound_h = WINDOW_W, WINDOW_H  # 이동 가능 영역 (맵 크기로 set_bounds)
        self.tile_map = None    # 벽 충돌 판정용 맵 (set_map으로 지정)
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

        # 조준 (우클릭 유지) / 마우스
        self.aiming = False
        self.mouse_x, self.mouse_y = self.x, self.y
        self.aim_dir = 'down'

        # 행동 (이동 상태와 별개): NONE / AIM / SHOOT / RELOAD
        self.action = ACTION_NONE

        # 전투 데이터
        self.hp = self.max_hp = 100
        self.ammo = self.max_ammo = 30
        self.shoot_cooldown = 0.0   # 다음 발사까지 남은 시간
        self.reload_timer = 0.0     # 재장전 남은 시간
        self.recoil_acc = 0.0       # 연사로 누적된 반동

        # 이미지 (구현이 진행되면 사격/재장전/달리기 시트를 여기에 추가)
        self.images = {
            'idle': load_image('resources/images/characters/Idle/Normal/idle.png'),
            'walk':load_image('resources/images/characters/Walk/Normal/walk.png'),
            'walk_aim': load_image('resources/images/characters/Walk_while_Aiming - NEW/Walk_while_aiming.png'),
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
        """캐릭터에서 마우스까지의 각도를 계산해 8방향 중 하나를 aim_dir에 저장한다."""
        pass

    def apply_aim_to_facing(self):
        """조준 해제 시 조준하던 방향을 일반 걷기 방향(face_x, face_y)으로 이어받는다."""
        pass

    def draw_walk_frame(self, frame):
        """조준 여부에 따라 알맞은 시트/행을 골라 걷기 프레임 한 장을 그린다."""
        if self.aiming:
            image, row = self.images['walk_aim'], AIM_ROW[self.aim_dir]
        else:
            image, row = self.images['walk'], ROW[self.facing_row()]
        image.clip_draw(frame * FRAME_W, row * FRAME_H, FRAME_W, FRAME_H,
                        self.x - camera.x, self.y - camera.y, FRAME_W * SCALE, FRAME_H * SCALE)

    def draw_run_frame(self, frame):
        """맨손 달리기 시트에서 바라보는 방향(6방향) 행의 프레임 한 장을 그린다."""
        self.images['run'].clip_draw(frame * FRAME_W, ROW[self.facing_row()] * FRAME_H, FRAME_W, FRAME_H,
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
        """맨손 Idle 시트에서 바라보는 방향(6방향) 행의 프레임 한 장을 그린다."""
        self.images['idle'].clip_draw(frame * FRAME_W, ROW[self.facing_row()] * FRAME_H, FRAME_W, FRAME_H,
                                      self.x - camera.x, self.y - camera.y, FRAME_W * SCALE, FRAME_H * SCALE)

    def handle_mouse_event(self, event):
        """마우스 이동 좌표 갱신, 우클릭 누름/뗌에 따른 조준 시작/해제를 처리한다."""
        pass

    def handle_event(self, event):
        """마우스/WASD/Shift 입력을 처리하고 이동·달리기 시작/정지 시 상태 머신에 이벤트를 전달한다.
        (현재는 WASD 이동 + Shift 달리기만 처리, 마우스 조준은 추후 구현)"""
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
        pass

    def start_aim(self):
        """우클릭 누름: 가능한 상태(Idle/Walk)일 때만 action을 AIM으로. Run이면 무시."""
        pass

    def stop_aim(self):
        """우클릭 뗌: AIM 해제, apply_aim_to_facing 호출."""
        pass

    def start_shoot(self):
        """좌클릭: 쿨다운/탄약/can_act 확인 후 fire() 호출, action을 SHOOT로."""
        pass

    def stop_shoot(self):
        """좌클릭 뗌: SHOOT 종료, 반동 회복 시작."""
        pass

    def start_reload(self):
        """R키 또는 탄약 0: 가능한 상태에서 action을 RELOAD로, 재장전 타이머 시작."""
        pass

    def finish_reload(self):
        """재장전 시간이 끝나면 ammo를 max_ammo로 채우고 action을 NONE으로."""
        pass

    def accuracy_state(self):
        """사격 시점의 (이동 상태, AIM 여부)로 FIRE_PROFILE 키를 반환한다."""
        pass

    def fire(self):
        """마우스 방향 + 퍼짐/누적 반동으로 총알을 발사하고 반동을 누적한다."""
        pass

    def recover_recoil(self):
        """사격을 쉬는 동안 시간에 따라 누적 반동을 감소시킨다."""
        pass

    def current_sheet(self):
        """(이동 상태, action) 조합으로 이미지/행 테이블에서 시트와 방향 행을 고른다."""
        pass

    def update(self, dt):
        """dt를 저장하고 상태 머신을 업데이트하며, 조준 중이면 조준 방향을 갱신한다."""
        self.dt = dt
        if self.dash_cooldown > 0:
            self.dash_cooldown -= dt
        self.state_machine.update()

    def draw(self):
        """상태 머신에 그리기를 위임한다."""
        self.state_machine.draw()
