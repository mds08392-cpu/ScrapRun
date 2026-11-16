from pico2d import *

WINDOW_W, WINDOW_H = 960, 720
FRAME_W, FRAME_H = 48, 64
FRAME_COUNT = 8                 # 한 방향당 프레임 수
SCALE = 2

WALK_SPEED = 200.0              # 픽셀/초
WALK_FPS = 10.0                 # 애니메이션 초당 프레임
IDLE_FPS = 8.0                  # Idle(숨쉬기) 애니메이션 초당 프레임
AIM_SPEED_RATIO = 0.6           # 조준하며 걸을 때 속도 배율
RUN_SPEED = 300.0               # 달리기 속도 (픽셀/초)
RUN_FPS = 14.0                  # 달리기 애니메이션 초당 프레임
DASH_SPEED = 500.0              # 대시 이동 속도 (픽셀/초)
DASH_FPS = 24.0                 # 대시 애니메이션 초당 프레임 (8프레임 / 24 = 약 0.33초 동안 대시)
DASH_COOLDOWN = 0.5             # 대시가 끝난 뒤 다시 대시할 수 있을 때까지 대기 시간 (초)

MOVE_KEYS = (SDLK_w, SDLK_a, SDLK_s, SDLK_d)
RUN_KEYS = (SDLK_LSHIFT, SDLK_RSHIFT)
DASH_KEYS = (SDLK_SPACE,)

# 6방향 행 이름 -> 대시 방향 벡터 (이동 입력 없이 대시할 때 바라보는 방향으로)
FACING_VECTOR = {
    'up': (0, 1), 'down': (0, -1),
    'right_up': (1, 1), 'right_down': (1, -1),
    'left_up': (-1, 1), 'left_down': (-1, -1),
}


# ---------------------------------------------------------------
# 이벤트 판별 함수
# ---------------------------------------------------------------
def move_key_event(e):
    """e가 WASD 키 입력(KEYDOWN/KEYUP) 이벤트인지 판별한다."""
    return e[0] == 'INPUT' and e[1].type in (SDL_KEYDOWN, SDL_KEYUP) and e[1].key in MOVE_KEYS


def start_moving(e):
    """e가 이동 시작('START_MOVE') 이벤트인지 판별한다."""
    return e[0] == 'START_MOVE'


def start_running(e):
    """e가 달리기 시작(이동 중 Shift 누름, 또는 Shift 누른 채 이동 시작) 이벤트인지 판별한다."""
    return e[0] == 'START_RUN'


def stop_running(e):
    """e가 달리기 종료(Shift 뗌) 이벤트인지 판별한다. 이동 키를 모두 떼면 stop_moving으로 Idle 전환."""
    return e[0] == 'STOP_RUN'


def dash_key(e):
    """e가 대시 키(Space) 입력인지 판별한다."""
    return e[0] == 'DASH'


def dash_end(e):
    """e가 대시 종료('DASH_END') 이벤트인지 판별한다. (이동 입력 없음 -> Idle, 전이 테이블에서 마지막에 검사)"""
    return e[0] == 'DASH_END'


def dash_end_walk(e):
    """대시 종료 시 이동 입력이 있으면 Walk로."""
    return e[0] == 'DASH_END' and e[1] == 'WALK'


def dash_end_run(e):
    """대시 종료 시 이동 입력 + Shift 유지 중이면 Run으로."""
    return e[0] == 'DASH_END' and e[1] == 'RUN'


def player_dead(e):
    """e가 사망('DEAD', HP 0) 이벤트인지 판별한다."""
    pass


def stop_moving(e):
    """e가 이동 정지('STOP_MOVE') 이벤트인지 판별한다."""
    return e[0] == 'STOP_MOVE'


# ---------------------------------------------------------------
# 공용 이동 함수 (Walk / Run)
# ---------------------------------------------------------------
def move_player(p, speed, dx=None, dy=None):
    """(dx, dy) 방향(생략하면 현재 이동 입력)으로 speed만큼 이동한다.
    대각선 속도 보정, 맵 경계 클램프, 벽에 막힌 축만 멈춘다."""
    if dx is None:
        dx, dy = p.dir_x, p.dir_y
    if dx and dy:  # 대각선 속도 보정
        dx *= 0.7071
        dy *= 0.7071

    # 맵(없으면 화면) 경계 밖으로 스프라이트가 나가지 않도록 클램프한 목표 위치
    half_w, half_h = FRAME_W * SCALE // 2, FRAME_H * SCALE // 2
    nx = clamp(half_w, p.x + dx * speed * p.dt, p.bound_w - half_w)
    ny = clamp(half_h, p.y + dy * speed * p.dt, p.bound_h - half_h)

    # x, y 축을 따로 이동해서 벽에 막힌 축만 벽에 딱 붙여 멈춘다 (대각선이면 벽을 따라 미끄러짐)
    p.move_x(nx)
    p.move_y(ny)


# ---------------------------------------------------------------
# 상태들 (모두 enter / exit / do / draw 를 가진다)
# ---------------------------------------------------------------
class Idle:
    """서있는 상태. 맨손 Idle 시트(6방향 x 8프레임)를 반복 재생한다."""

    @staticmethod
    def enter(p, e):
        """진입 시 프레임을 0으로 초기화하고, 우클릭을 누르고 있었다면 조준을 다시 시작한다."""
        p.frame = 0
        if p.aim_held:
            p.start_aim()
        if p.shoot_held:
            p.start_shoot()

    @staticmethod
    def exit(p, e):
        pass

    @staticmethod
    def do(p):
        """Idle 애니메이션 프레임을 진행한다."""
        p.frame = (p.frame + IDLE_FPS * p.dt) % FRAME_COUNT

    @staticmethod
    def draw(p):
        """Idle 시트의 현재 프레임을 그린다 (조준 중이면 총 든 Idle 시트를 마우스 방향으로)."""
        p.draw_idle_frame(int(p.frame))


class Walk:
    """WASD 이동 상태 (조준 중이면 속도 감소, 조준 시트 사용)."""

    @staticmethod
    def enter(p, e):
        """Run/Dash에서 돌아왔을 때 우클릭/좌클릭을 누르고 있었다면 조준/사격을 다시 시작한다."""
        if p.aim_held:
            p.start_aim()
        if p.shoot_held:
            p.start_shoot()

    @staticmethod
    def exit(p, e):
        pass

    @staticmethod
    def do(p):
        """조준 속도 배율을 적용해 이동하고 걷기 프레임을 진행한다."""
        move_player(p, WALK_SPEED * (AIM_SPEED_RATIO if p.aiming else 1.0))
        p.frame = (p.frame + WALK_FPS * p.dt) % FRAME_COUNT

    @staticmethod
    def draw(p):
        """현재 프레임을 그린다."""
        p.draw_walk_frame(int(p.frame))


class Run:
    """달리기 상태 (이동 중 Shift 유지). 조준 불가: 진입 시 AIM 해제."""

    @staticmethod
    def enter(p, e):
        """Run 중에는 조준·재장전할 수 없으므로 조준을 해제하고 재장전을 취소한다 (우클릭 유지 여부는 기억).
        사격은 가능하므로 Dash 뒤에 좌클릭을 누르고 있었다면 다시 시작한다."""
        p.stop_aim()
        p.cancel_reload()   # Run 중에는 재장전 불가
        if p.shoot_held:
            p.start_shoot()

    @staticmethod
    def exit(p, e):
        pass

    @staticmethod
    def do(p):
        """달리기 속도로 이동하고 달리기 프레임을 진행한다."""
        move_player(p, RUN_SPEED)
        p.frame = (p.frame + RUN_FPS * p.dt) % FRAME_COUNT

    @staticmethod
    def draw(p):
        """맨손 달리기 시트의 현재 프레임을 그린다."""
        p.draw_run_frame(int(p.frame))


class Dash:
    """대시 상태 (Space). 진입 순간의 방향으로 고정된 채 빠르게 이동하고, 8프레임이 끝나면 종료.
    대시 중에는 조준/사격/재장전 불가 (action 잠금), 이동/Shift 입력은 끝날 때만 반영."""

    @staticmethod
    def enter(p, e):
        """대시 방향/스프라이트 방향을 고정하고 조준·행동을 해제한다."""
        p.frame = 0
        p.stop_aim()
        p.cancel_reload()
        p.action = 'NONE'

        p.dash_row = p.facing_row()
        if p.dir_x or p.dir_y:      # 이동 중이면 입력 방향으로
            p.dash_dx, p.dash_dy = p.dir_x, p.dir_y
        else:                       # 서 있으면 바라보는 방향으로
            p.dash_dx, p.dash_dy = FACING_VECTOR[p.dash_row]

    @staticmethod
    def exit(p, e):
        """쿨다운을 시작한다."""
        p.dash_cooldown = DASH_COOLDOWN

    @staticmethod
    def do(p):
        """고정된 방향으로 이동하고, 애니메이션이 한 바퀴 끝나면 다음 상태로 전이한다."""
        move_player(p, DASH_SPEED, p.dash_dx, p.dash_dy)
        p.frame += DASH_FPS * p.dt
        if p.frame >= FRAME_COUNT:
            if not (p.dir_x or p.dir_y):
                nxt = 'IDLE'
            elif p.run_held:
                nxt = 'RUN'
            else:
                nxt = 'WALK'
            p.state_machine.handle_event(('DASH_END', nxt))

    @staticmethod
    def draw(p):
        """그림자 -> 먼지 -> 본체 순으로 그린다."""
        p.draw_dash_frame(min(int(p.frame), FRAME_COUNT - 1))


class SpearAttack:
    """창 근접 공격 (사용하지 않음, 껍데기만 유지)."""

    @staticmethod
    def enter(p, e): pass
    @staticmethod
    def exit(p, e): pass
    @staticmethod
    def do(p): pass
    @staticmethod
    def draw(p): pass


class Death:
    """사망 상태 - HP가 0이 되었을 때 (미구현)."""

    @staticmethod
    def enter(p, e): pass
    @staticmethod
    def exit(p, e): pass
    @staticmethod
    def do(p): pass
    @staticmethod
    def draw(p): pass
