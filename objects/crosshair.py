import math

from pico2d import draw_rectangle

# 크로스헤어 (마우스 위치에 십자 눈금 4개를 그린다)
# 원(탄착 범위)은 화면에 그리지 않고 눈금 위치 계산에만 쓴다.
# 눈금은 원 바깥에 붙어 있으므로 원이 커지면 눈금이 저절로 벌어진다.
RING_MIN = 3            # 내부 원 반지름 최소값
TICK_GAP = 3            # 원과 눈금 사이 간격
TICK_LEN = 6            # 눈금 길이
TICK_THICK = 2          # 눈금 두께
TICK_COLOR = (20, 20, 20)
OUTLINE_COLOR = (235, 235, 235)   # 어두운 바닥에서도 보이도록 눈금 바깥 1px 밝은 테두리

GROW_K = 40.0           # 표시 반지름이 커질 때 따라가는 속도 (빠르게)
SHRINK_K = 14.0         # 줄어들 때 따라가는 속도 (느리게)


def smooth_radius(shown, target, dt):
    """표시 반지름 shown이 target을 부드럽게 따라가도록 한 프레임 진행한 값을 반환한다."""
    k = GROW_K if target > shown else SHRINK_K
    return shown + (target - shown) * (1.0 - math.exp(-k * dt))


class Crosshair:
    """마우스 위치에 그려지는 UI 크로스헤어. World에 넣지 않고 main에서 world.draw() 뒤에 직접 그린다."""

    def __init__(self, player):
        self.player = player
        self.shown = float(RING_MIN)    # 화면에 보이는(눈금 계산용) 반지름

    def update(self, dt):
        """플레이어의 실제 탄착 반지름을 부드럽게 따라간다. (확산 모델 구현 전이라 고정)"""
        pass

    @staticmethod
    def draw_tick(l, b, r, t):
        """밝은 테두리 + 어두운 눈금 한 개를 그린다."""
        draw_rectangle(l - 1, b - 1, r + 1, t + 1, *OUTLINE_COLOR, 255, True)
        draw_rectangle(l, b, r, t, *TICK_COLOR, 255, True)

    def draw(self):
        """마우스 화면 좌표에 눈금 4개를 그린다 (카메라 보정 없음)."""
        cx, cy = int(self.player.mouse_x), int(self.player.mouse_y)
        r = max(RING_MIN, int(round(self.shown)))
        a = r + 1 + TICK_GAP          # 눈금 시작 거리 (원 바깥)
        b = a + TICK_LEN - 1          # 눈금 끝 거리
        lo = -(TICK_THICK // 2)       # 두께 방향 범위 [lo, hi]
        hi = lo + TICK_THICK - 1
        self.draw_tick(cx + a, cy + lo, cx + b, cy + hi)   # 오른쪽
        self.draw_tick(cx - b, cy + lo, cx - a, cy + hi)   # 왼쪽
        self.draw_tick(cx + lo, cy + a, cx + hi, cy + b)   # 위
        self.draw_tick(cx + lo, cy - b, cx + hi, cy - a)   # 아래
