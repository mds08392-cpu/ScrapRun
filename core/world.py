class World:
    """게임 오브젝트들을 레이어별로 보관하고 한꺼번에 update/draw/이벤트 전달을 하는 월드.

    오브젝트는 update(dt), draw() 를 가지면 되고, 이벤트를 받고 싶으면 handle_event(event)도 가진다.
    레이어 번호가 작을수록 먼저(뒤에) 그려진다. 예) 0: 배경/타일, 1: 아이템/총알, 2: 몬스터, 3: 플레이어
    """

    LAYER_COUNT = 4
    LAYER_BG, LAYER_ITEM, LAYER_MONSTER, LAYER_PLAYER = range(LAYER_COUNT)

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

    def draw(self):
        """레이어 순서대로 모든 오브젝트를 그린다."""
        for layer in self.layers:
            for obj in layer:
                obj.draw()
