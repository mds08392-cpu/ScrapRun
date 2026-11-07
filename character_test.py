import math

from pico2d import *

# ---------------------------------------------------------------
# 테스트용 설정값
# ---------------------------------------------------------------
WINDOW_W, WINDOW_H = 800, 600

FRAME_W, FRAME_H = 48, 64       # 스프라이트 한 프레임 크기
FRAME_COUNT = 8                 # 한 방향당 프레임 수
SCALE = 2                       # 화면에 그릴 배율

WALK_SPEED = 200.0              # 픽셀/초
WALK_FPS = 10.0                 # 애니메이션 초당 프레임
AIM_SPEED_RATIO = 0.6           # 조준하며 걸을 때 속도 배율

# 스프라이트 시트의 행 번호 (아래에서부터 0)
ROW = {
    'right_down': 0,
    'right_up':   1,
    'up':         2,
    'left_up':    3,
    'left_down':  4,
    'down':       5,
}

# 조준 걷기 시트(Walk_while_aiming.png)의 행 번호 (아래에서부터 0) - 8방향
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

# ---------------------------------------------------------------
# 이벤트 판별 함수
# ---------------------------------------------------------------
MOVE_KEYS = (SDLK_w, SDLK_a, SDLK_s, SDLK_d)


def move_key_event(e):
    return e[0] == 'INPUT' and e[1].type in (SDL_KEYDOWN, SDL_KEYUP) and e[1].key in MOVE_KEYS


def start_moving(e):
    return e[0] == 'START_MOVE'


def stop_moving(e):
    return e[0] == 'STOP_MOVE'


# ---------------------------------------------------------------
# 상태들
# ---------------------------------------------------------------
class Idle:
    @staticmethod
    def enter(p, e):
        p.frame = 0

    @staticmethod
    def exit(p, e):
        pass

    @staticmethod
    def do(p):
        pass

    @staticmethod
    def draw(p):
        # Idle 은 아직 미구현 -> 걷기(조준) 시트의 첫 프레임으로 서있는 모습만 표시
        p.draw_walk_frame(0)


class Walk:
    @staticmethod
    def enter(p, e):
        pass

    @staticmethod
    def exit(p, e):
        pass

    @staticmethod
    def do(p):
        dt = p.dt
        dx, dy = p.dir_x, p.dir_y
        if dx and dy:  # 대각선 속도 보정
            dx *= 0.7071
            dy *= 0.7071
        speed = WALK_SPEED * (AIM_SPEED_RATIO if p.aiming else 1.0)
        p.x += dx * speed * dt
        p.y += dy * speed * dt

        half_w, half_h = FRAME_W * SCALE // 2, FRAME_H * SCALE // 2
        p.x = clamp(half_w, p.x, WINDOW_W - half_w)
        p.y = clamp(half_h, p.y, WINDOW_H - half_h)

        p.frame = (p.frame + WALK_FPS * dt) % FRAME_COUNT

    @staticmethod
    def draw(p):
        p.draw_walk_frame(int(p.frame))


class Run:
    @staticmethod
    def enter(p, e): pass
    @staticmethod
    def exit(p, e): pass
    @staticmethod
    def do(p): pass
    @staticmethod
    def draw(p): pass


class Dash:
    @staticmethod
    def enter(p, e): pass
    @staticmethod
    def exit(p, e): pass
    @staticmethod
    def do(p): pass
    @staticmethod
    def draw(p): pass


class Jump:
    @staticmethod
    def enter(p, e): pass
    @staticmethod
    def exit(p, e): pass
    @staticmethod
    def do(p): pass
    @staticmethod
    def draw(p): pass


class Attack:
    @staticmethod
    def enter(p, e): pass
    @staticmethod
    def exit(p, e): pass
    @staticmethod
    def do(p): pass
    @staticmethod
    def draw(p): pass


class Death:
    @staticmethod
    def enter(p, e): pass
    @staticmethod
    def exit(p, e): pass
    @staticmethod
    def do(p): pass
    @staticmethod
    def draw(p): pass


# ---------------------------------------------------------------
# 상태 머신
# ---------------------------------------------------------------
class StateMachine:
    def __init__(self, owner, start_state, transitions):
        self.owner = owner
        self.cur_state = start_state
        self.transitions = transitions
        self.cur_state.enter(owner, ('START', None))

    def update(self):
        self.cur_state.do(self.owner)

    def handle_event(self, e):
        for check, next_state in self.transitions.get(self.cur_state, {}).items():
            if check(e):
                self.cur_state.exit(self.owner, e)
                self.cur_state = next_state
                next_state.enter(self.owner, e)
                return

    def draw(self):
        self.cur_state.draw(self.owner)


# ---------------------------------------------------------------
# 플레이어
# ---------------------------------------------------------------
class Player:
    def __init__(self):
        self.x, self.y = WINDOW_W // 2, WINDOW_H // 2
        self.frame = 0.0
        self.dt = 0.0

        self.keys = {k: False for k in MOVE_KEYS}
        self.dir_x, self.dir_y = 0, 0
        self.face_x = 'right'   # 마지막 좌우 입력
        self.face_y = 'down'    # 마지막 상하 입력
        self.last_vertical_only = True  # 마지막 이동이 상/하만이었는지 (멈췄을 때 방향 유지용)

        # 조준 (우클릭 유지)
        self.aiming = False
        self.mouse_x, self.mouse_y = self.x, self.y
        self.aim_dir = 'down'

        self.walk_image = load_image('resources/images/characters/Walk/Normal/walk.png')
        self.aim_image = load_image('resources/images/characters/Walk_while_Aiming - NEW/Walk_while_aiming.png')

        self.state_machine = StateMachine(self, Idle, {
            Idle: {start_moving: Walk},
            Walk: {stop_moving: Idle},
            Run: {}, Dash: {}, Jump: {}, Attack: {}, Death: {},
        })

    def facing_row(self):
        if self.dir_x == 0 and self.dir_y > 0:
            return 'up'
        if self.dir_x == 0 and self.dir_y < 0:
            return 'down'
        if self.dir_x == 0 and self.dir_y == 0 and self.last_vertical_only:
            return self.face_y
        # 좌/우가 들어간 경우 -> 바라보는 좌우 + 상/하 조합
        return f'{self.face_x}_{self.face_y}'

    def update_aim_dir(self):
        dx, dy = self.mouse_x - self.x, self.mouse_y - self.y
        if dx == 0 and dy == 0:
            return
        idx = round(math.degrees(math.atan2(dy, dx)) / 45) % 8
        self.aim_dir = AIM_DIRS[idx]

    def apply_aim_to_facing(self):
        # 조준 해제 시 조준하던 방향을 일반 걷기 방향(6방향)으로 이어받음
        d = self.aim_dir
        if d in ('up', 'down'):
            self.face_y = d
            self.last_vertical_only = True
        else:
            x, _, y = d.partition('_')
            self.face_x = x
            if y:
                self.face_y = y
            self.last_vertical_only = False

    def draw_walk_frame(self, frame):
        if self.aiming:
            image, row = self.aim_image, AIM_ROW[self.aim_dir]
        else:
            image, row = self.walk_image, ROW[self.facing_row()]
        image.clip_draw(frame * FRAME_W, row * FRAME_H, FRAME_W, FRAME_H,
                        self.x, self.y, FRAME_W * SCALE, FRAME_H * SCALE)

    def handle_mouse_event(self, event):
        if event.type == SDL_MOUSEMOTION:
            self.mouse_x, self.mouse_y = event.x, WINDOW_H - 1 - event.y
        elif event.type in (SDL_MOUSEBUTTONDOWN, SDL_MOUSEBUTTONUP) and event.button == SDL_BUTTON_RIGHT:
            self.mouse_x, self.mouse_y = event.x, WINDOW_H - 1 - event.y
            self.aiming = event.type == SDL_MOUSEBUTTONDOWN
            if self.aiming:
                self.update_aim_dir()
            else:
                self.apply_aim_to_facing()

    def handle_event(self, event):
        if event.type in (SDL_MOUSEMOTION, SDL_MOUSEBUTTONDOWN, SDL_MOUSEBUTTONUP):
            self.handle_mouse_event(event)
            return

        e = ('INPUT', event)
        if not move_key_event(e):
            return

        pressed = event.type == SDL_KEYDOWN
        self.keys[event.key] = pressed

        # 새로 누른 키로 바라보는 방향 갱신
        if pressed:
            if event.key == SDLK_a:
                self.face_x = 'left'
            elif event.key == SDLK_d:
                self.face_x = 'right'
            elif event.key == SDLK_w:
                self.face_y = 'up'
            elif event.key == SDLK_s:
                self.face_y = 'down'

        was_moving = self.dir_x != 0 or self.dir_y != 0
        self.dir_x = self.keys[SDLK_d] - self.keys[SDLK_a]
        self.dir_y = self.keys[SDLK_w] - self.keys[SDLK_s]
        now_moving = self.dir_x != 0 or self.dir_y != 0

        # 멈췄을 때 마지막으로 보던 방향 유지용 (상/하만 누르다 멈춘 경우)
        if now_moving:
            self.last_vertical_only = self.dir_x == 0

        if now_moving and not was_moving:
            self.state_machine.handle_event(('START_MOVE', None))
        elif was_moving and not now_moving:
            self.state_machine.handle_event(('STOP_MOVE', None))

    def update(self, dt):
        self.dt = dt
        self.state_machine.update()
        if self.aiming:  # 캐릭터가 움직여도 마우스 쪽을 계속 바라보도록 매 프레임 갱신
            self.update_aim_dir()

    def draw(self):
        self.state_machine.draw()


# ---------------------------------------------------------------
# 메인 루프
# ---------------------------------------------------------------
def main():
    open_canvas(WINDOW_W, WINDOW_H)

    # 마우스 커서를 화살표 대신 크로스헤어로 변경 (이 창 안에서만 적용)
    crosshair = SDL_CreateSystemCursor(SDL_SYSTEM_CURSOR_CROSSHAIR)
    SDL_SetCursor(crosshair)

    player = Player()

    running = True
    prev_time = get_time()
    while running:
        now = get_time()
        dt = now - prev_time
        prev_time = now

        for event in get_events():
            if event.type == SDL_QUIT:
                running = False
            elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
                running = False
            else:
                player.handle_event(event)

        player.update(dt)

        clear_canvas()
        player.draw()
        update_canvas()
        delay(0.01)

    SDL_FreeCursor(crosshair)
    close_canvas()


if __name__ == '__main__':
    main()
