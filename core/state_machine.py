class StateMachine:
    """상태 전이 테이블에 따라 현재 상태를 관리하는 범용 상태 머신."""
    # 총기사격 구현을 위해 사용
    def __init__(self, owner, start_state, transitions):
        """소유 객체, 시작 상태, 전이 테이블을 저장하고 시작 상태의 enter를 호출한다."""
        self.owner = owner
        self.cur_state = start_state
        self.transitions = transitions
        self.cur_state.enter(owner, ('START', None))

    def update(self):
        """현재 상태의 do()를 호출한다."""
        pass

    def handle_event(self, e):
        """전이 테이블에서 조건이 맞는 이벤트를 찾아 exit -> 상태 변경 -> enter 순으로 전이한다."""
        pass

    def draw(self):
        """현재 상태의 draw()를 호출한다."""
        pass
