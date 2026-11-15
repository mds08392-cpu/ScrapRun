from pico2d import *

WINDOW_W, WINDOW_H = 800, 600
FRAME_W, FRAME_H = 48, 64
FRAME_COUNT = 8                 # 한 방향당 프레임 수
SCALE = 2

WALK_SPEED = 200.0              # 픽셀/초
WALK_FPS = 10.0                 # 애니메이션 초당 프레임
IDLE_FPS = 8.0                  # Idle(숨쉬기) 애니메이션 초당 프레임
AIM_SPEED_RATIO = 0.6           # 조준하며 걸을 때 속도 배율

MOVE_KEYS = (SDLK_w, SDLK_a, SDLK_s, SDLK_d)


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
    pass


def stop_running(e):
    """e가 달리기 종료(Shift 뗌) 이벤트인지 판별한다. 이동 키를 모두 떼면 stop_moving으로 Idle 전환."""
    pass


def dash_key(e):
    """e가 대시 키(Ctrl) 입력인지 판별한다."""
    pass


def dash_end(e):
    """e가 대시 종료('DASH_END') 이벤트인지 판별한다."""
    pass


def player_dead(e):
    """e가 사망('DEAD', HP 0) 이벤트인지 판별한다."""
    pass


def stop_moving(e):
    """e가 이동 정지('STOP_MOVE') 이벤트인지 판별한다."""
    return e[0] == 'STOP_MOVE'


# ---------------------------------------------------------------
# 상태들 (모두 enter / exit / do / draw 를 가진다)
# ---------------------------------------------------------------
class Idle:
    """서있는 상태. 맨손 Idle 시트(6방향 x 8프레임)를 반복 재생한다."""

    @staticmethod
    def enter(p, e):
        """진입 시 프레임을 0으로 초기화한다."""
        p.frame = 0

    @staticmethod
    def exit(p, e):
        pass

    @staticmethod
    def do(p):
        """Idle 애니메이션 프레임을 진행한다."""
        p.frame = (p.frame + IDLE_FPS * p.dt) % FRAME_COUNT

    @staticmethod
    def draw(p):
        """맨손 Idle 시트의 현재 프레임을 바라보는 방향으로 그린다."""
        p.draw_idle_frame(int(p.frame))


class Walk:
    """WASD 이동 상태 (조준 중이면 속도 감소, 조준 시트 사용)."""

    @staticmethod
    def enter(p, e):
        pass

    @staticmethod
    def exit(p, e):
        pass

    @staticmethod
    def do(p):
        """대각선 속도 보정, 조준 속도 배율 적용 이동, 맵 경계 클램프, 프레임 진행."""
        dt = p.dt
        dx, dy = p.dir_x, p.dir_y
        if dx and dy:  # 대각선 속도 보정
            dx *= 0.7071
            dy *= 0.7071
        speed = WALK_SPEED * (AIM_SPEED_RATIO if p.aiming else 1.0)

        # 맵(없으면 화면) 경계 밖으로 스프라이트가 나가지 않도록 클램프한 목표 위치
        half_w, half_h = FRAME_W * SCALE // 2, FRAME_H * SCALE // 2
        nx = clamp(half_w, p.x + dx * speed * dt, p.bound_w - half_w)
        ny = clamp(half_h, p.y + dy * speed * dt, p.bound_h - half_h)

        # x, y 축을 따로 이동해서 벽에 막힌 축만 벽에 딱 붙여 멈춘다 (대각선이면 벽을 따라 미끄러짐)
        p.move_x(nx)
        p.move_y(ny)

        p.frame = (p.frame + WALK_FPS * dt) % FRAME_COUNT

    @staticmethod
    def draw(p):
        """현재 프레임을 그린다."""
        p.draw_walk_frame(int(p.frame))


class Run:
    """달리기 상태 (미구현)."""

    @staticmethod
    def enter(p, e): pass
    @staticmethod
    def exit(p, e): pass
    @staticmethod
    def do(p): pass
    @staticmethod
    def draw(p): pass


class Dash:
    """대시 상태 (미구현)."""

    @staticmethod
    def enter(p, e): pass
    @staticmethod
    def exit(p, e): pass
    @staticmethod
    def do(p): pass
    @staticmethod
    def draw(p): pass


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
