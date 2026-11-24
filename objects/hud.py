from pico2d import load_image, draw_rectangle
import pico2d.pico2d as pico2d_core
from sdl2 import SDL_SetRenderDrawBlendMode, SDL_BLENDMODE_BLEND, SDL_BLENDMODE_NONE

from objects.player import ACTION_RELOAD

# 왼쪽 아래 탄약 HUD:  [탄약 아이콘] 현재탄창 / 예비탄약
# 모든 크기는 픽셀아트 원본 단위이고 화면에는 UI_SCALE배로 그린다.
UI_SCALE = 3
MARGIN = 4                  # 화면 가장자리에서 패널까지 (원본 px)
PAD = 3                     # 패널 안쪽 여백
ICON_W, ICON_H = 7, 15      # ammo_icon.png
GLYPH_W, GLYPH_H = 7, 9     # digits.png 한 칸 (5x7 글자 + 1px 외곽선)
ADVANCE = 6                 # 글자 간격 (외곽선 1px은 옆 글자와 겹침)
SPACE = 3                   # 공백 폭
GAP = 3                     # 아이콘과 숫자 사이
GLYPHS = '0123456789/'
ROW_WHITE, ROW_RED, ROW_GRAY = 0, 1, 2      # digits.png 행 (위에서부터)
LOW_AMMO_RATIO = 0.25       # 탄창이 이 비율 이하이면 현재 탄약을 빨간색으로

PANEL_COLOR = (16, 13, 11, 170)         # 반투명 배경
BORDER_COLOR = (92, 80, 66, 255)
BAR_BG_COLOR = (50, 44, 38, 255)
BAR_COLOR = (236, 182, 70, 255)         # 재장전 진행 바


class AmmoHud:
    """플레이어의 현재 탄창(ammo) / 예비 탄약(reserve_ammo)을 왼쪽 아래에 그린다.
    재장전 중에는 숫자 아래에 진행 바를 그린다. UI라서 World에 넣지 않고 main에서 직접 그린다."""

    def __init__(self, player):
        self.player = player
        self.icon = load_image('resources/images/ui/ammo_icon.png')
        self.digits = load_image('resources/images/ui/digits.png')

    @staticmethod
    def text_width(text):
        """원본 px 단위 글자열 폭."""
        w = 0
        for ch in text:
            w += SPACE if ch == ' ' else ADVANCE
        return w + (GLYPH_W - ADVANCE) if text else 0

    def draw_text(self, text, left, bottom, color_row):
        """원본 px 좌표 (left, bottom)부터 글자열을 그린다. 다음 글자를 그릴 원본 x를 반환한다."""
        s = UI_SCALE
        sheet_rows = self.digits.h // GLYPH_H
        for ch in text:
            if ch == ' ':
                left += SPACE
                continue
            idx = GLYPHS.index(ch)
            self.digits.clip_draw(idx * GLYPH_W, (sheet_rows - 1 - color_row) * GLYPH_H, GLYPH_W, GLYPH_H,
                                  (left + GLYPH_W / 2) * s, (bottom + GLYPH_H / 2) * s, GLYPH_W * s, GLYPH_H * s)
            left += ADVANCE
        return left

    @staticmethod
    def rect(l, b, r, t, color):
        """원본 px 사각형 [l, r) x [b, t)를 화면 배율로 채운다."""
        s = UI_SCALE
        draw_rectangle(l * s, b * s, r * s - 1, t * s - 1, *color, True)

    def draw(self):
        p = self.player
        cur, reserve = f'{p.ammo}', f' / {p.reserve_ammo}'
        cur_row = ROW_RED if p.ammo <= p.max_ammo * LOW_AMMO_RATIO else ROW_WHITE

        # 현재 탄창은 max_ammo 자릿수 폭에 오른쪽 정렬 (30 -> 5로 줄어도 패널이 덜컹이지 않게)
        cur_pad = (len(str(p.max_ammo)) - len(cur)) * ADVANCE if len(cur) < len(str(p.max_ammo)) else 0
        text_w = cur_pad + self.text_width(cur + reserve)
        panel_l, panel_b = MARGIN, MARGIN
        panel_r = panel_l + PAD + ICON_W + GAP + text_w + PAD
        panel_t = panel_b + PAD + ICON_H + PAD

        # 반투명 패널 (pico2d draw_rectangle은 블렌딩을 켜지 않으므로 잠깐 켠다)
        SDL_SetRenderDrawBlendMode(pico2d_core.renderer, SDL_BLENDMODE_BLEND)
        self.rect(panel_l, panel_b, panel_r, panel_t, PANEL_COLOR)
        SDL_SetRenderDrawBlendMode(pico2d_core.renderer, SDL_BLENDMODE_NONE)
        self.rect(panel_l, panel_t - 1, panel_r, panel_t, BORDER_COLOR)          # 위
        self.rect(panel_l, panel_b, panel_r, panel_b + 1, BORDER_COLOR)          # 아래
        self.rect(panel_l, panel_b, panel_l + 1, panel_t, BORDER_COLOR)          # 왼쪽
        self.rect(panel_r - 1, panel_b, panel_r, panel_t, BORDER_COLOR)          # 오른쪽

        # 아이콘
        s = UI_SCALE
        icon_l, icon_b = panel_l + PAD, panel_b + PAD
        self.icon.draw((icon_l + ICON_W / 2) * s, (icon_b + ICON_H / 2) * s, ICON_W * s, ICON_H * s)

        # 숫자: 현재 탄창(흰색/빨강) + " / 예비"(회색). 아이콘 세로 가운데보다 살짝 위
        text_l = icon_l + ICON_W + GAP
        text_b = icon_b + (ICON_H - GLYPH_H) // 2 + 1
        x = self.draw_text(cur, text_l + cur_pad, text_b, cur_row)
        self.draw_text(reserve, x, text_b, ROW_GRAY)

        # 재장전 진행 바 (숫자 아래)
        if p.action == ACTION_RELOAD:
            progress = max(0.0, min(1.0, 1.0 - p.reload_timer / p.reload_duration))
            bar_l, bar_b = text_l, icon_b
            bar_r = text_l + text_w
            self.rect(bar_l, bar_b, bar_r, bar_b + 2, BAR_BG_COLOR)
            self.rect(bar_l, bar_b, bar_l + max(1, round((bar_r - bar_l) * progress)), bar_b + 2, BAR_COLOR)


# ---------------------------------------------------------------
# 오른쪽 아래 총기 파츠 HUD: 슬롯별 장착 파츠(희귀도 색) + 기본 총 대비 능력치 변화
# 글자는 시스템 한글 폰트로 그린다 (폰트가 없으면 패널을 그리지 않는다)
# ---------------------------------------------------------------
FONT_CANDIDATES = ('C:/Windows/Fonts/malgun.ttf', 'C:/Windows/Fonts/gulim.ttc',
                   '/System/Library/Fonts/AppleSDGothicNeo.ttc')
PARTS_FONT_SIZE = 14
PARTS_LINE_H = 18           # 줄 간격 (화면 px)
PARTS_PANEL_W = 250
PARTS_PAD = 8
PARTS_MARGIN = 12
PARTS_LABEL_W = 62          # 왼쪽 이름 칸 폭

TEXT_TITLE = (236, 182, 70)
TEXT_LABEL = (170, 160, 145)
TEXT_NONE = (110, 104, 96)
TEXT_VALUE = (235, 235, 235)
TEXT_GOOD = (110, 220, 110)
TEXT_BAD = (235, 95, 80)


def _load_font(size):
    """후보 폰트 중 처음 열리는 것을 반환한다. 하나도 없으면 None."""
    from pico2d import load_font
    for path in FONT_CANDIDATES:
        try:
            return load_font(path, size)
        except (IOError, OSError):
            continue
    return None


def stat_lines(gun):
    """패널에 표시할 능력치 줄 목록 [(이름, 값 글자, 기본 대비 변화 글자, 색)].
    변화 글자는 기본 총과 같으면 ''이고, 플레이어에게 좋은 쪽이면 초록, 나쁜 쪽이면 빨강."""
    s, b = gun.stats(), gun.base

    def delta(key, lower_is_better=False):
        if b[key] == 0 or abs(s[key] - b[key]) < 1e-9:
            return '', TEXT_VALUE
        pct = (s[key] / b[key] - 1.0) * 100
        good = (pct < 0) if lower_is_better else (pct > 0)
        return f'{pct:+.0f}%', (TEXT_GOOD if good else TEXT_BAD)

    rpm = 60.0 / s['fire_interval']
    lines = []
    d, c = delta('damage');                          lines.append(('데미지', f'{s["damage"]:.1f}', d, c))
    d, c = delta('fire_interval', True)
    d = '' if not d else f'{(b["fire_interval"] / s["fire_interval"] - 1) * 100:+.0f}%'
    lines.append(('연사', f'{rpm:.0f} RPM', d, c))
    d, c = delta('recoil', True);                    lines.append(('반동', f'x{s["recoil"]:.2f}', d, c))
    aim = s['spread'] * s['aim_spread']
    hip = s['spread'] * s['hip_spread']
    c = TEXT_GOOD if aim < 1 - 1e-9 else (TEXT_BAD if aim > 1 + 1e-9 else TEXT_VALUE)
    lines.append(('조준 퍼짐', f'x{aim:.2f}', f'{(aim - 1) * 100:+.0f}%' if c != TEXT_VALUE else '', c))
    c = TEXT_GOOD if hip < 1 - 1e-9 else (TEXT_BAD if hip > 1 + 1e-9 else TEXT_VALUE)
    lines.append(('비조준 퍼짐', f'x{hip:.2f}', f'{(hip - 1) * 100:+.0f}%' if c != TEXT_VALUE else '', c))
    d, c = delta('recover');                         lines.append(('반동 회복', f'x{s["recover"]:.2f}', d, c))
    d, c = delta('mag_size');                        lines.append(('탄창', f'{s["mag_size"]}발', d, c))
    d, c = delta('reload_time', True);               lines.append(('재장전', f'{s["reload_time"]:.2f}초', d, c))
    if s['zoom'] > 0:
        lines.append(('조준 시야', f'+{s["zoom"]:.0f}', '', TEXT_GOOD))
    return lines


class GunPartsHud:
    """오른쪽 아래에 장착 파츠와 능력치를 그린다. F3으로 켜고 끈다. UI라서 main에서 직접 그린다."""

    def __init__(self, player, view_w, view_h):
        self.player = player
        self.view_w, self.view_h = view_w, view_h
        self.font = _load_font(PARTS_FONT_SIZE)
        self.shown = True

    def toggle(self):
        self.shown = not self.shown

    def draw(self):
        if not self.shown or self.font is None:
            return
        from objects.gun import SLOTS, SLOT_NAMES
        from objects.gun_parts import RARITY_COLOR
        gun = self.player.gun
        stats = stat_lines(gun)
        n_lines = 1 + len(SLOTS) + 1 + len(stats)          # 제목 + 슬롯 + 구분 + 능력치
        h = PARTS_PAD * 2 + n_lines * PARTS_LINE_H
        r = self.view_w - PARTS_MARGIN
        l = r - PARTS_PANEL_W
        b = PARTS_MARGIN
        t = b + h

        SDL_SetRenderDrawBlendMode(pico2d_core.renderer, SDL_BLENDMODE_BLEND)
        draw_rectangle(l, b, r, t, *PANEL_COLOR, True)
        SDL_SetRenderDrawBlendMode(pico2d_core.renderer, SDL_BLENDMODE_NONE)
        draw_rectangle(l, b, r, t, *BORDER_COLOR)

        x = l + PARTS_PAD
        y = t - PARTS_PAD - PARTS_LINE_H / 2
        self.font.draw(x, y, f'{gun.name} 파츠  (F5~F8 교체, F3 숨김)', TEXT_TITLE)
        y -= PARTS_LINE_H
        for slot in SLOTS:
            part = gun.parts[slot]
            self.font.draw(x, y, SLOT_NAMES[slot], TEXT_LABEL)
            if part is None:
                self.font.draw(x + PARTS_LABEL_W, y, '-', TEXT_NONE)
            else:
                self.font.draw(x + PARTS_LABEL_W, y, part.name, RARITY_COLOR[part.rarity])
            y -= PARTS_LINE_H

        draw_rectangle(x, y + 2, r - PARTS_PAD, y + 2, *BORDER_COLOR)   # 구분선
        y -= PARTS_LINE_H
        for name, value, change, color in stats:
            self.font.draw(x, y, name, TEXT_LABEL)
            self.font.draw(x + 80, y, value, TEXT_VALUE)
            if change:
                self.font.draw(x + 170, y, change, color)
            y -= PARTS_LINE_H
