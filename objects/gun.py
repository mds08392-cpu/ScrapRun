# 총 + 부착 파츠 -> 최종 능력치 계산
# pico2d를 import하지 않는 순수 모듈이라 창 없이 테스트할 수 있다 (test_gun_parts.py).
#
# 능력치 계산 순서: 기본값 -> 모든 파츠의 add(더하기) -> 모든 파츠의 mul(곱하기) -> STAT_MIN으로 하한 고정
# 곱하기는 파츠끼리 곱해진다 (반동 x0.8 손잡이 + 반동 x0.85 소염기 = 반동 x0.68).

SLOTS = ('grip', 'sight', 'muzzle', 'magazine')   # 손잡이 / 배율 / 총구 / 탄창
SLOT_NAMES = {'grip': '손잡이', 'sight': '배율', 'muzzle': '총구', 'magazine': '탄창'}

# 기본 소총 능력치 (파츠 없음)
BASE_STATS = {
    'damage': 20.0,         # 한 발 데미지
    'fire_interval': 0.11,  # 연사 간격(초). 작을수록 빠름
    'recoil': 1.0,          # 한 발당 bloom 증가량 배율 (FIRE_PROFILE의 recoil에 곱함)
    'spread': 1.0,          # 자세별 기본 탄착 반지름 배율 (모든 자세)
    'aim_spread': 1.0,      # 조준(우클릭) 중일 때만 추가로 곱하는 배율
    'hip_spread': 1.0,      # 조준 없이 쏠 때만 추가로 곱하는 배율
    'recover': 1.0,         # bloom 회복 속도 배율
    'mag_size': 30,         # 탄창 용량
    'reload_time': 1.2,     # 재장전 시간(초)
    'bullet_speed': 900.0,  # 총알 속도 (px/초)
    'bullet_range': 1200.0, # 총알 사거리 (px)
    'aim_move': 1.0,        # 조준하며 걸을 때 속도 배율 (AIM_SPEED_RATIO에 곱함)
    'zoom': 0.0,            # 조준 시 카메라가 마우스 쪽으로 더 볼 수 있는 거리 (px, 배율 스코프)
}

# 정수로 써야 하는 능력치
INT_STATS = ('mag_size',)

# 파츠를 많이 달아도 이 아래로는 내려가지 않는다
STAT_MIN = {
    'fire_interval': 0.05,
    'recoil': 0.3,
    'spread': 0.3,
    'aim_spread': 0.3,
    'hip_spread': 0.3,
    'mag_size': 1,
    'reload_time': 0.4,
}


class Gun:
    """기본 능력치와 슬롯별 부착 파츠를 갖고, 파츠가 반영된 최종 능력치를 계산한다."""

    def __init__(self, name='소총', base=None):
        self.name = name
        self.base = dict(BASE_STATS if base is None else base)
        self.parts = {slot: None for slot in SLOTS}
        self._cache = None

    def equip(self, part):
        """파츠를 자기 슬롯에 단다. 그 슬롯에 있던 파츠(없으면 None)를 반환한다."""
        old = self.parts[part.slot]
        self.parts[part.slot] = part
        self._cache = None
        return old

    def unequip(self, slot):
        """슬롯의 파츠를 뗀다. 떼어낸 파츠(없으면 None)를 반환한다."""
        old = self.parts[slot]
        self.parts[slot] = None
        self._cache = None
        return old

    def equipped(self):
        """달려 있는 파츠 목록 (슬롯 순서)."""
        return [self.parts[s] for s in SLOTS if self.parts[s] is not None]

    def has_flag(self, flag):
        """달려 있는 파츠 중 하나라도 flag를 가지면 True ('hide_flash', 'silenced', 'laser')."""
        return any(flag in p.flags for p in self.equipped())

    def stat(self, key):
        """파츠가 반영된 최종 능력치 하나."""
        return self.stats()[key]

    def stats(self):
        """파츠가 반영된 최종 능력치 전체 (파츠가 바뀔 때만 다시 계산)."""
        if self._cache is None:
            self._cache = self.compute()
        return self._cache

    def compute(self):
        """기본값 -> add -> mul -> 하한 고정 순서로 최종 능력치를 계산한다."""
        result = dict(self.base)
        parts = self.equipped()
        for part in parts:
            for key, value in part.add.items():
                result[key] += value
        for part in parts:
            for key, value in part.mul.items():
                result[key] *= value
        for key, value in result.items():
            if key in STAT_MIN:
                value = max(STAT_MIN[key], value)
            if key in INT_STATS:
                value = int(round(value))
            result[key] = value
        return result
