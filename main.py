from pico2d import *

from core.camera import camera
from core.world import World
from objects.crosshair import Crosshair
from objects.player import Player
from objects.tile_map import TileMap

WINDOW_W, WINDOW_H = 800, 600

# 맵 목록 (F2로 순서대로 바꿔 가며 확인). 타일셋은 맵 JSON에 포함되어 있거나 tilesets/*.tsx를 참조한다
MAPS = [
    ('farm', 'resources/images/maps/farm_maps.json'),
    ('default', 'resources/images/maps/default_map.json'),
]
START_MAP = 0   # 시작 맵 (MAPS 인덱스)


def load_map(world, player, path, old_map=None):
    """맵을 읽어 World에 넣고(이전 맵과 총알은 제거) 플레이어를 맵 중앙 근처 빈 곳에 세운다."""
    if old_map is not None:
        world.remove_object(old_map)
        for obj in old_map.map_objects:
            world.remove_object(obj)
    world.layers[World.LAYER_BULLET].clear()

    tile_map = TileMap(path)
    world.add_object(tile_map, World.LAYER_BG)                    # 바닥
    world.add_objects(tile_map.map_objects, World.LAYER_ITEM)     # 건물/소품/파밍 상자 (y축 정렬)
    camera.set_world_size(tile_map.width, tile_map.height)

    player.set_map(tile_map)  # 벽 충돌 판정 + 이동 영역
    player.x, player.y = find_spawn(tile_map, player)
    return tile_map


def find_spawn(tile_map, player):
    """맵 중앙에서 가장 가까운, 플레이어 충돌 박스가 벽에 걸리지 않는 칸 중심을 찾는다."""
    cx, cy = tile_map.width // 2, tile_map.height // 2
    tw, th = tile_map.tile_w, tile_map.tile_h
    for ring in range(max(tile_map.cols, tile_map.rows)):
        for dc in range(-ring, ring + 1):
            for dr in range(-ring, ring + 1):
                if max(abs(dc), abs(dr)) != ring:
                    continue
                x, y = cx + dc * tw, cy + dr * th
                if 0 < x < tile_map.width and 0 < y < tile_map.height and player.can_move_to(x, y):
                    return x, y
    return cx, cy


def main():
    """캔버스를 열고 메인 루프(이벤트 -> update -> draw)를 실행한다."""
    open_canvas(WINDOW_W, WINDOW_H)

    hide_cursor()   # 시스템 커서 대신 Crosshair를 직접 그린다

    world = World()

    player = Player()
    player.set_world(world)   # 총알 생성용
    world.add_object(player, World.LAYER_PLAYER)

    map_index = START_MAP
    tile_map = load_map(world, player, MAPS[map_index][1])

    crosshair = Crosshair(player)   # UI라서 World(y축 정렬)에 넣지 않고 맨 마지막에 직접 그린다

    show_collision = False  # F1: 벽 칸 / 덩어리 / 실내 영역 / 피벗 / 파밍 지점 / 충돌 박스 디버그 표시

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
            elif event.type == SDL_KEYDOWN and event.key == SDLK_F2:
                map_index = (map_index + 1) % len(MAPS)
                tile_map = load_map(world, player, MAPS[map_index][1], tile_map)
            else:
                world.handle_event(event)

        world.update(dt)
        tile_map.update_occlusion(player.x, player.sort_y)  # 건물 안이면 플레이어를 건물 위에 그림
        camera.follow(player.x, player.y)
        crosshair.update(dt)

        clear_canvas()
        world.draw()
        if show_collision:
            tile_map.draw_debug()
            player.draw_hitbox()
        crosshair.draw()
        update_canvas()
        delay(0.01)

    close_canvas()


if __name__ == '__main__':
    main()
