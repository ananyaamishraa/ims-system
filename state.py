class BaseState:
    allowed = []

    def can_transition(self, new_state: str):
        return new_state in self.allowed


class OpenState(BaseState):
    allowed = ["INVESTIGATING"]


class InvestigatingState(BaseState):
    allowed = ["RESOLVED"]


class ResolvedState(BaseState):
    allowed = ["CLOSED"]


class ClosedState(BaseState):
    allowed = [] 
