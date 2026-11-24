# 총기 파츠 정의 (순수 데이터, pico2d 없음)
# 파츠마다 슬롯 하나(grip / sight / muzzle / magazine)에 들어가고, add/mul로 능력치를 바꾼다.
#   add:   {능력치: 값}  기본값에 더한다            예) 'mag_size': 10  -> 30발이 40발
#   mul:   {능력치: 값}  add 뒤에 곱한다            예) 'recoil': 0.8   -> 반동 20% 감소
#   flags: 숫자가 아닌 특수 효과 ('hide_flash' 총구 화염 숨김, 'silenced' 소음, 'laser' 레이저 표시)
# 능력치 이름은 objects/gun.py의 BASE_STATS 참고.

from objects.gun import SLOTS

# 희귀도 (HUD에서 테두리/글자 색, 추후 파밍 드롭 확률에 사용)
RARITY_COMMON, RARITY_RARE, RARITY_EPIC = 'common', 'rare', 'epic'
RARITY_COLOR = {
    RARITY_COMMON: (200, 200, 200),
    RARITY_RARE:   (90, 160, 255),
    RARITY_EPIC:   (190, 110, 255),
}


class GunPart:
    """총기 파츠 하나. 능력치 적용은 Gun.compute()가 한다."""

    def __init__(self, part_id, name, slot, rarity=RARITY_COMMON, add=None, mul=None, flags=(), desc=''):
        assert slot in SLOTS, slot
        self.id = part_id
        self.name = name
        self.slot = slot
        self.rarity = rarity
        self.add = dict(add or {})
        self.mul = dict(mul or {})
        self.flags = frozenset(flags)
        self.desc = desc

    def __repr__(self):
        return f'GunPart({self.id})'


# id -> GunPart. 슬롯별 파츠는 아래 구역에서 등록한다
PARTS = {}


def register(*parts):
    """파츠를 PARTS에 등록한다 (id 중복 불가)."""
    for part in parts:
        assert part.id not in PARTS, part.id
        PARTS[part.id] = part


def parts_for_slot(slot):
    """해당 슬롯에 들어가는 파츠 목록 (등록 순서)."""
    return [p for p in PARTS.values() if p.slot == slot]


def get_part(part_id):
    """id로 파츠를 찾는다."""
    return PARTS[part_id]


# ---------------------------------------------------------------
# 손잡이 (grip): 반동 / 탄 퍼짐 / 반동 회복 / 연사 속도
# ---------------------------------------------------------------
register(
    GunPart('grip_vertical', '수직 손잡이', 'grip', RARITY_COMMON,
            mul={'recoil': 0.8},
            desc='연사 반동 20% 감소'),
    GunPart('grip_angled', '앵글 손잡이', 'grip', RARITY_COMMON,
            mul={'spread': 0.85, 'recover': 1.2},
            desc='기본 탄 퍼짐 15% 감소, 반동 회복 20% 빠름'),
    GunPart('grip_half', '하프 손잡이', 'grip', RARITY_RARE,
            mul={'recoil': 0.9, 'recover': 1.35},
            desc='반동 10% 감소, 반동 회복 35% 빠름'),
    GunPart('grip_light', '경량 손잡이', 'grip', RARITY_RARE,
            mul={'fire_interval': 0.88, 'recoil': 1.1},
            desc='연사 속도 약 14% 증가, 반동 10% 증가'),
    GunPart('grip_thumb', '엄지 손잡이', 'grip', RARITY_EPIC,
            mul={'aim_spread': 0.8, 'recoil': 0.9, 'aim_move': 1.1},
            desc='조준 탄 퍼짐 20% 감소, 반동 10% 감소, 조준 이동 10% 빠름'),
)


# ---------------------------------------------------------------
# 배율 (sight): 조준 정확도 / 조준 시 시야(zoom) / 레이저
# zoom = 조준 중 카메라가 마우스 쪽으로 더 밀려나는 최대 거리(px). 배율이 높을수록 멀리 보지만 조준 이동이 느려진다
# ---------------------------------------------------------------
register(
    GunPart('sight_reddot', '레드 도트', 'sight', RARITY_COMMON,
            mul={'aim_spread': 0.85},
            desc='조준 탄 퍼짐 15% 감소'),
    GunPart('sight_holo', '홀로그램', 'sight', RARITY_COMMON,
            mul={'aim_spread': 0.8, 'recover': 1.1},
            desc='조준 탄 퍼짐 20% 감소, 반동 회복 10% 빠름'),
    GunPart('sight_laser', '레이저 도트', 'sight', RARITY_RARE,
            mul={'hip_spread': 0.75},
            flags=('laser',),
            desc='비조준 탄 퍼짐 25% 감소, 레이저 표시'),
    GunPart('sight_2x', '2배율', 'sight', RARITY_RARE,
            add={'zoom': 140},
            mul={'aim_spread': 0.75, 'aim_move': 0.9},
            desc='조준 시야 +140, 조준 탄 퍼짐 25% 감소, 조준 이동 10% 느림'),
    GunPart('sight_4x', '4배율', 'sight', RARITY_EPIC,
            add={'zoom': 280},
            mul={'aim_spread': 0.6, 'aim_move': 0.75, 'hip_spread': 1.15},
            desc='조준 시야 +280, 조준 탄 퍼짐 40% 감소, 조준 이동 25% 느림, 비조준 퍼짐 15% 증가'),
)


# ---------------------------------------------------------------
# 총구 (muzzle): 소음기 / 소염기 / 보정기 / 머즐 브레이크 중 하나만 장착
# ---------------------------------------------------------------
register(
    GunPart('muzzle_suppressor', '소음기', 'muzzle', RARITY_RARE,
            mul={'recoil': 0.9, 'bullet_range': 1.15},
            flags=('hide_flash', 'silenced'),
            desc='총구 화염 없음, 소음(적 감지 범위 감소 예정), 반동 10% 감소, 사거리 15% 증가'),
    GunPart('muzzle_flash_hider', '소염기', 'muzzle', RARITY_COMMON,
            mul={'recoil': 0.85, 'spread': 0.95},
            flags=('hide_flash',),
            desc='총구 화염 없음, 반동 15% 감소, 기본 탄 퍼짐 5% 감소'),
    GunPart('muzzle_compensator', '보정기', 'muzzle', RARITY_COMMON,
            mul={'recoil': 0.7, 'recover': 1.15},
            desc='반동 30% 감소, 반동 회복 15% 빠름'),
    GunPart('muzzle_brake', '머즐 브레이크', 'muzzle', RARITY_EPIC,
            mul={'recoil': 0.75, 'damage': 1.1, 'bullet_speed': 1.15},
            desc='반동 25% 감소, 데미지 10% 증가, 탄속 15% 증가'),
)
