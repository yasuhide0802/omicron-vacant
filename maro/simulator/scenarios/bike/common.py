from enum import Enum

class Trip:
    def __init__(self, date: int, start_cell: int, end_cell: int, end_tick: int, usertype: int = 0, gendor: int = 0, num: int = 1):
        self.date = date
        self.from_cell = start_cell
        self.to_cell = end_cell
        self.number = num
        self.end_tick = end_tick
        self.usertype = usertype
        self.gendor = gendor

    @property
    def weekday(self):
        return self.date.weekday()

    def __repr__(self):
        return f"(Trip start cell: {self.from_cell}, end cell: {self.to_cell}, end tick: {self.end_tick})"


class BikeTransferPayload:
    def __init__(self, from_cell: int, to_cell: int, number: int):
        self.from_cell = from_cell
        self.to_cell = to_cell
        self.number = number


class BikeReturnPayload:
    def __init__(self, from_cell: int, to_cell: int, num: int = 1):
        self.from_cell = from_cell
        self.to_cell = to_cell
        self.number = num

    def __repr__(self):
        return f"(Bike return payload, target cell: {self.to_cell}, number: {self.number})"

class DecisionType(Enum):
    Supply = 'supply' # current cell has too more bikes, need transfer to others
    Demand = 'demand' # current cell has no enough bikes, need neighobors transfer bikes to it

class DecisionEvent:
    def __init__(self, cell_idx: int, tick: int, frame_index: int, action_scope_func: callable, decision_type: DecisionType):
        self.cell_idx = cell_idx
        self.tick = tick
        self.frame_index = frame_index
        self.type = decision_type
        self._action_scope = None
        self._action_scope_func = action_scope_func

    @property
    def action_scope(self):
        if self._action_scope is None:
            self._action_scope = self._action_scope_func(self.cell_idx, self.type)

        return self._action_scope

    def __repr__(self):
        return f"DecisionEvent(cell: {self.cell_idx}, action scope: {self.action_scope}, type: {self.type})"


class Action:
    def __init__(self, from_cell: int, to_cell: int, number: int):
        self.from_cell = from_cell
        self.to_cell = to_cell
        self.number = number

    def __repr__(self):
        return f"Action(from cell: {self.from_cell}, to cell: {self.to_cell}, number: {self.number})"


class ExtraCostMode(Enum):
    Source = "source"
    Target = "target"
    TargetNeighbors = "target_neighbors"
