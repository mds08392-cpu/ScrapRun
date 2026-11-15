class World:
    """게임 오브젝트들을 레이어별로 보관하고 한꺼번에 update/draw/이벤트 전달을 하는 월드.

    오브젝트는 update(dt), draw() 를 가지면 되고, 이벤트를 받고 싶으면 handle_event(event)도 가진다.
    LAYER_BG(배경/바닥)는 정렬 없이 가장 먼저 그리고, 나머지 레이어(건물·소품/아이템, 몬스터, 플레이어)는
    하나로 모아 y축 정렬해서 그린다. 정렬 기준(피벗)은 오브젝트의 sort_y(캐릭터는 발밑 y, 건물은 밑변 y)이며,
    pico2d는 y가 위로 증가하므로 sort_y가 큰(화면 위쪽, 더 먼) 것부터 그린다.
    """

    LAYER_COUNT = 4
    LAYER_BG, LAYER_ITEM, LAYER_MONSTER, LAYER_PLAYER = range(LAYER_COUNT)
    SORTED_LAYERS = (LAYER_ITEM, LAYER_MONSTER, LAYER_PLAYER)  # y축 정렬해서 그릴 레이어

    def __init__(self):
        self.layers = [[] for _ in range(self.LAYER_COUNT)]

    def add_object(self, obj, layer):
        """오브젝트를 지정한 레이어에 추가한다."""
        self.layers[layer].append(obj)

    def add_objects(self, objs, layer):
        """여러 오브젝트를 한 번에 추가한다."""
        self.layers[layer].extend(objs)

    def remove_object(self, obj):
        """오브젝트를 월드에서 제거한다. 없으면 무시한다."""
        for layer in self.layers:
            if obj in layer:
                layer.remove(obj)
                return

    def clear(self):
        """모든 오브젝트를 제거한다."""
        for layer in self.layers:
            layer.clear()

    def all_objects(self):
        """모든 오브젝트를 레이어 순서대로 순회한다."""
        for layer in self.layers:
            yield from layer

    def handle_event(self, event):
        """handle_event 를 가진 모든 오브젝트에 이벤트를 전달한다."""
        for obj in list(self.all_objects()):
            if hasattr(obj, 'handle_event'):
                obj.handle_event(event)

    def update(self, dt):
        """모든 오브젝트를 업데이트한다. (순회 중 제거되어도 안전하도록 복사본 사용)"""
        for obj in list(self.all_objects()):
            obj.update(dt)

    @staticmethod
    def sort_y_of(obj):
        """정렬 기준 y. sort_y가 없으면 y를 사용한다."""
        return getattr(obj, 'sort_y', getattr(obj, 'y', 0))

    def sorted_objects(self):
        """정렬 레이어의 오브젝트를 그릴 순서(먼 것 -> 가까운 것)로 반환한다.
        sort_y가 같으면 레이어 번호가 큰(플레이어 쪽) 것을, 같은 레이어면 먼저 추가된 것을 먼저 그린다."""
        items = [(obj, layer_no) for layer_no in self.SORTED_LAYERS for obj in self.layers[layer_no]]
        items.sort(key=lambda t: (-self.sort_y_of(t[0]), t[1]))   # 안정 정렬이라 추가 순서 유지
        return [obj for obj, _ in items]

    def draw(self):
        """배경 레이어를 먼저 그리고, 나머지는 y축 정렬 순서로 그린다."""
        for obj in self.layers[self.LAYER_BG]:
            obj.draw()
        for obj in self.sorted_objects():
            obj.draw()
