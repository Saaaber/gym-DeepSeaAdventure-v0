import random

class Policy(object):
    """
    Base Policy Template Class
    """
    def __init__(self):
        self._action_space_forward = [0, 1]
        self._action_space_pick = [0, 1]
        self._action_space_drop = [0, 1]

    def forward(self, state):
        """
        Return 0 to turn around or 1 to proceed forward
        """
        NotImplementedError

    def pick(self, state):
        """
        Return 0 to ignore treasure or 1 to pick it up
        """
        NotImplementedError

    def drop(self, state):
        """
        Return 0 to keep treasure(s) or 1 to drop one with smallest value
        """
        NotImplementedError


class Grabber(Policy):
    """
    Grab the first N treasures then turn around and stop grabbing
    Never drop
    """
    def __init__(self, n):
        super(Grabber).__init__()
        self._n = n

    def forward(self, state):
        return 0 if state[2] >= self._n else 1

    def pick(self, state):
        return state[3]

    def drop(self, state):
        return 0

class Randy(Policy):
    """
    Every action is random
    """
    def __init__(self):
        super(Randy).__init__()

    def forward(self, state):
        return random.randint(0, 1)

    def pick(self, state):
        return random.randint(0, 1)

    def drop(self, state):
        return random.randint(0, 1)

class Diver(Policy):
    """
    Dive to the dth treasure then turn around and grab the first n treasures
    Never drop
    """
    def __init__(self, d, n):
        super(Diver).__init__()
        self._d = d
        self._n = n

    def forward(self, state):
        return 0 if state[1] >= self._d else 1

    def pick(self, state):
        if state[1] >= self._d:
            return 1
        elif state[3] is True:
            return 0
        elif state[2] >= self._n:
            return 0
        else:
            return 1

    def drop(self, state):
        return 0

class Greedy(Policy):
    """
    Grab the first 4-dot treasure then turn around and grab nothing
    Never drop
    """
    def __init__(self):
        super(Greedy).__init__()

    def forward(self, state):
        if state[2] > 0:
            return 0
        if state[1] > 24:
            return 0
        else:
            return 1

    def pick(self, state):
        return 1 if state[1] > 24 else 0

    def drop(self, state):
        return 0
        