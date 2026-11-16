class Camera:
    """화면에 보이는 영역의 왼쪽 아래 좌표(x, y)를 관리한다.

    월드 좌표 -> 화면 좌표: (wx - camera.x, wy - camera.y)
    """

    def __init__(self, view_w, view_h):
        self.x, self.y = 0, 0
        self.view_w, self.view_h = view_w, view_h
        self.world_w, self.world_h = view_w, view_h

    def set_world_size(self, w, h):
        """카메라가 움직일 수 있는 월드(맵) 크기를 지정한다."""
        self.world_w, self.world_h = w, h

    def follow(self, tx, ty):
        """대상(tx, ty)이 화면 중앙에 오도록 이동하되 맵 밖은 보이지 않게 클램프한다."""
        self.x = int(max(0, min(tx - self.view_w / 2, self.world_w - self.view_w)))
        self.y = int(max(0, min(ty - self.view_h / 2, self.world_h - self.view_h)))


# 모든 오브젝트가 함께 쓰는 카메라 (main에서 맵 크기를 지정한다)
camera = Camera(960, 720)
