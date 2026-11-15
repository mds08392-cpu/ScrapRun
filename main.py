from pico2d import *

from core.camera import camera
from core.world import World
from objects.player import Player
from objects.tile_map import TileMap

WINDOW_W, WINDOW_H = 800, 600

MAP_PATH = 'resources/images/maps/default_map.json'
TILESET_PATH = 'resources/images/tilesets/apoc_tileset.png'


def main():
    """캔버스를 열고 메인 루프(이벤트 -> update -> draw)를 실행한다."""
    open_canvas(WINDOW_W, WINDOW_H)

    # 마우스 커서를 화살표 대신 크로스헤어로 변경 (이 창 안에서만 적용)
    crosshair = SDL_CreateSystemCursor(SDL_SYSTEM_CURSOR_CROSSHAIR)
    SDL_SetCursor(crosshair)

    world = World()

    tile_map = TileMap(MAP_PATH, TILESET_PATH)
    world.add_object(tile_map, World.LAYER_BG)
    camera.set_world_size(tile_map.width, tile_map.height)

    player = Player()
    player.set_map(tile_map)  # 벽 충돌 판정 + 이동 영역
    player.x, player.y = tile_map.width // 2, tile_map.height // 2  # 맵 중앙에서 시작
    world.add_object(player, World.LAYER_PLAYER)

    show_collision = False  # F1: 벽 칸 / 충돌 박스 디버그 표시

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
            elif event.type == SDL_KEYDOWN and event.key == SDLK_F1:
                show_collision = not show_collision
            else:
                world.handle_event(event)

        world.update(dt)
        camera.follow(player.x, player.y)

        clear_canvas()
        world.draw()
        if show_collision:
            tile_map.draw_collision()
            player.draw_hitbox()
        update_canvas()
        delay(0.01)

    SDL_FreeCursor(crosshair)
    close_canvas()


if __name__ == '__main__':
    main()
