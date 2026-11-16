from pico2d import load_image, draw_rectangle
import pico2d.pico2d as pico2d_core
from sdl2 import SDL_SetRenderDrawBlendMode, SDL_BLENDMODE_BLEND, SDL_BLENDMODE_NONE

from objects.player import ACTION_RELOAD, RELOAD_TIME

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
            progress = max(0.0, min(1.0, 1.0 - p.reload_timer / RELOAD_TIME))
            bar_l, bar_b = text_l, icon_b
            bar_r = text_l + text_w
            self.rect(bar_l, bar_b, bar_r, bar_b + 2, BAR_BG_COLOR)
            self.rect(bar_l, bar_b, bar_l + max(1, round((bar_r - bar_l) * progress)), bar_b + 2, BAR_COLOR)
