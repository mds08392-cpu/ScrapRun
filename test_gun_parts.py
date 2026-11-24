# 총기 파츠 능력치 계산 테스트 (pico2d/창 없이 실행)
# 실행: ScrapRun 폴더에서 python test_gun_parts.py   (pytest가 있으면 pytest test_gun_parts.py 도 가능)
import math

from objects.gun import BASE_STATS, SLOTS, STAT_MIN, Gun
from objects.gun_parts import PARTS, RARITY_COLOR, GunPart, get_part, parts_for_slot

KNOWN_FLAGS = {'hide_flash', 'silenced', 'laser'}


def close(a, b):
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)


def test_no_parts_is_base():
    assert Gun().stats() == BASE_STATS


def test_part_data_valid():
    for part in PARTS.values():
        assert part.slot in SLOTS, part
        assert part.rarity in RARITY_COLOR, part
        assert set(part.add) <= set(BASE_STATS), part
        assert set(part.mul) <= set(BASE_STATS), part
        assert part.flags <= KNOWN_FLAGS, part
        assert all(v > 0 for v in part.mul.values()), part
        assert part.desc, part


def test_every_slot_has_parts():
    for slot in SLOTS:
        assert parts_for_slot(slot), slot


def test_mul_stacks_across_slots():
    g = Gun()
    g.equip(get_part('grip_vertical'))        # recoil x0.8
    g.equip(get_part('muzzle_compensator'))   # recoil x0.7
    assert close(g.stat('recoil'), 0.56)


def test_add_then_mul():
    g = Gun()
    g.equip(GunPart('t_add', 't', 'grip', add={'damage': 10}))
    g.equip(GunPart('t_mul', 't', 'muzzle', mul={'damage': 2.0}))
    assert close(g.stat('damage'), (BASE_STATS['damage'] + 10) * 2.0)


def test_min_clamp_and_int():
    g = Gun()
    g.equip(GunPart('t_low', 't', 'grip', mul={'recoil': 0.01, 'fire_interval': 0.01}))
    g.equip(GunPart('t_mag', 't', 'magazine', add={'mag_size': 0.6}))
    assert g.stat('recoil') == STAT_MIN['recoil']
    assert g.stat('fire_interval') == STAT_MIN['fire_interval']
    assert isinstance(g.stat('mag_size'), int) and g.stat('mag_size') == 31


def test_equip_replaces_and_unequip():
    g = Gun()
    assert g.equip(get_part('mag_extended')) is None
    assert g.stat('mag_size') == 40
    assert g.equip(get_part('mag_drum')) is get_part('mag_extended')
    assert g.stat('mag_size') == 60                   # 캐시가 갱신되어야 함
    assert g.unequip('magazine') is get_part('mag_drum')
    assert g.stat('mag_size') == BASE_STATS['mag_size']
    assert g.unequip('magazine') is None


def test_flags():
    g = Gun()
    assert not g.has_flag('hide_flash')
    g.equip(get_part('muzzle_flash_hider'))
    assert g.has_flag('hide_flash') and not g.has_flag('silenced')
    g.equip(get_part('muzzle_suppressor'))
    assert g.has_flag('hide_flash') and g.has_flag('silenced')
    g.equip(get_part('sight_laser'))
    assert g.has_flag('laser')


def test_requested_effects_exist():
    """요청한 방향(반동 감소, 연사 증가, 데미지 증가)을 주는 파츠가 각각 하나 이상 있다."""
    def effect(stat):
        g = Gun()
        out = []
        for part in PARTS.values():
            g.equip(part)
            out.append(g.stat(stat))
            g.unequip(part.slot)
        return out
    assert min(effect('recoil')) < BASE_STATS['recoil']
    assert min(effect('fire_interval')) < BASE_STATS['fire_interval']
    assert max(effect('damage')) > BASE_STATS['damage']


if __name__ == '__main__':
    tests = [(name, fn) for name, fn in sorted(globals().items()) if name.startswith('test_') and callable(fn)]
    for name, fn in tests:
        fn()
        print('ok  ', name)
    print(f'{len(tests)} passed')
