from pico2d import *

WINDOW_W, WINDOW_H = 800, 600
FRAME_W, FRAME_H = 48, 64
FRAME_COUNT = 8                 # 한 방향당 프레임 수
SCALE = 2

WALK_SPEED = 200.0              # 픽셀/초
WALK_FPS = 10.0                 # 애니메이션 초당 프레임
AIM_SPEED_RATIO = 0.6           # 조준하며 걸을 때 속도 배율

MOVE_KEYS = (SDLK_w, SDLK_a, SDLK_s, SDLK_d)


# ---------------------------------------------------------------
# 이벤트 판별 함수
# ---------------------------------------------------------------
def move_key_event(e):
    """e가 WASD 키 입력(KEYDOWN/KEYUP) 이벤트인지 판별한다."""
    pass


def start_moving(e):
    """e가 이동 시작('START_MOVE') 이벤트인지 판별한다."""
    pass


def start_running(e):
    """e가 달리기 시작(Shift 누름) 이벤트인지 판별한다."""
    pass


def stop_running(e):
    """e가 달리기 종료(Shift 뗌) 이벤트인지 판별한다."""
    pass


def jump_key(e):
    """e가 스페이스바 입력인지 판별한다."""
    pass


def jump_end(e):
    """e가 점프 종료('JUMP_END') 이벤트인지 판별한다."""
    pass


def dash_key(e):
    """e가 대시 키 입력인지 판별한다."""
    pass


def dash_end(e):
    """e가 대시 종료('DASH_END') 이벤트인지 판별한다."""
    pass


def player_dead(e):
    """e가 사망('DEAD', HP 0) 이벤트인지 판별한다."""
    pass


def stop_moving(e):
    """e가 이동 정지('STOP_MOVE') 이벤트인지 판별한다."""
    pass


# ---------------------------------------------------------------
# 상태들 (모두 enter / exit / do / draw 를 가진다)
# ---------------------------------------------------------------
class Idle:
    """서있는 상태. (아직 Idle 시트 미구현 -> 걷기 첫 프레임 표시 예정)"""

    @staticmethod
    def enter(p, e):
        """진입 시 프레임을 0으로 초기화한다."""
        pass

    @staticmethod
    def exit(p, e):
        pass

    @staticmethod
    def do(p):
        pass

    @staticmethod
    def draw(p):
        """걷기 시트의 첫 프레임으로 서있는 모습을 그린다."""
        pass


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
        """대각선 속도 보정, 조준 속도 배율 적용 이동, 화면 경계 클램프, 프레임 진행."""
        pass

    @staticmethod
    def draw(p):
        """현재 프레임을 그린다."""
        pass


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


class Jump:
    """점프 상태 - 스페이스바 입력 (미구현)."""

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
