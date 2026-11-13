from pico2d import *

from core.state_machine import StateMachine
from objects.player_states import *

WINDOW_W, WINDOW_H = 800, 600

FRAME_W, FRAME_H = 48, 64       # 스프라이트 한 프레임 크기
SCALE = 2                       # 화면에 그릴 배율

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
        pass

    def facing_row(self):
        """현재 이동 입력과 마지막 방향을 바탕으로 일반 걷기 시트의 행 이름(6방향)을 반환한다."""
        pass

    def update_aim_dir(self):
        """캐릭터에서 마우스까지의 각도를 계산해 8방향 중 하나를 aim_dir에 저장한다."""
        pass

    def apply_aim_to_facing(self):
        """조준 해제 시 조준하던 방향을 일반 걷기 방향(face_x, face_y)으로 이어받는다."""
        pass

    def draw_walk_frame(self, frame):
        """조준 여부에 따라 알맞은 시트/행을 골라 걷기 프레임 한 장을 그린다."""
        pass

    def handle_mouse_event(self, event):
        """마우스 이동 좌표 갱신, 우클릭 누름/뗌에 따른 조준 시작/해제를 처리한다."""
        pass

    def handle_event(self, event):
        """마우스/WASD 입력을 처리하고 이동 시작/정지 시 상태 머신에 이벤트를 전달한다."""
        pass

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
        pass

    def draw(self):
        """상태 머신에 그리기를 위임한다."""
        pass
