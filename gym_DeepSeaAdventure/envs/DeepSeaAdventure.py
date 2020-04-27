import gym
from gym import error, spaces, utils
from gym.utils import seeding
import sys
import random
import math
from gym_DeepSeaAdventure.envs.policy import Grabber, Diver, Greedy, Randy
from gym_DeepSeaAdventure.envs.render import *


class DSA_env(gym.Env):
    def __init__(self):
        self._players = []
        self._next_turn_order = []
        self.action_space = gym.spaces.Discrete(2)
        self.observation_space = gym.spaces.Discrete(83)


    def reset(self):
        self._game_over = False
        self._oxygen = 25

        for i in range(len(self._players)):
            self._players[i].reset(i)
            self._players[i].points = 0


        self._generate_treasures()
        self._initialize_path()
        self._initialize_turn_order()

        self._current_player = self._turn_order[0]

        self.round = 0


    def seed(self, seed):
        random.seed(seed)

        return seed

    def state(self, idx):
        """Return the state as seen by player idx
        0:      Oxygen level [0:25]
        1:      Position of player idx [0:32].
                0 is inside the submarine. [1:32] are the treasures
        2:      Weight of player idx [0:6]
        3:      Weither player idx is going backward or forward [0, 1]
        4-8:    Positions of other players [0-32]. 
                0 is inside the submarine or no player. [1:32] are the treasures
        9-13:   Weight of other players [0:6]
        14-18:  Weither other players are going backward or forward [0, 1]
        19-50:  Dots for each treasure [0:4]. 0 means that it is an empty spot
        51-82:  Weither a position will be skipped or not [0, 1].
                A position can be skipped if there is another player or if
                the tile was removed in a previous round.
        """
        state = []
        
        state += [self._oxygen]
        state += [self._players[idx].position]
        state += [self._players[idx].weight]
        state += [int(self._players[idx].forward)]
        
        positions = []
        weights = []
        forwards = []
        skipped = 32 * [0]
        dots = []

        for pid in range(6):
            if pid >= len(self._players):
                positions += [0]
                weights += [0]
                forwards += [0]
            elif pid != idx:
                positions += [self._players[pid].position]
                weights += [self._players[pid].weight]
                forwards += [int(self._players[pid].forward)]
                if self._players[pid].position > 0:
                    skipped[self._players[pid].position - 1] = 1

        state += positions
        state += weights
        state += forwards

        for loc, t in enumerate(self._treasure_path):
            if t.removed is True:
                skipped[loc] = 1
                dots += [0]

            else:
                dots += [t.dots]

        state += dots
        state += skipped

        return state

    def step(self):
        pid = self._current_player
        pick = -1
        drop = -1
        forward = -1

        reward = 0

        force_turn = False

        if self._players[pid].done is False:
            self._oxygen -= self._players[pid].weight

            initial_state = self.state(pid)

            # Action Forward if applicable
            if self._players[pid].forward is True and self._players[pid].position != 0:
                forward = self._players[pid].policy.forward(initial_state)

                if forward == 0:
                    self._players[pid].turn()

            state = self.state(pid)

            # Roll the die and move
            steps = max(0, random.randint(1, 3) + random.randint(1, 3) - state[2])
            position = state[1]

            for _ in range(steps):
                position, force_turn = self._next_viable_position(position, state[51:83], state[3])
            
            if force_turn is True:
                self._players[pid].turn()

            self._players[pid].setposition(position)

            state = self.state(pid)

            if position == 0:
                self._players[pid].done = True
                for t in self._players[pid].treasures:
                    reward += t.hidden_value
                
                self._players[pid].points += reward

                self._next_turn_order += [pid]
            
            else:
                if state[18 + position] == 0:
                    if state[2] > 0:
                        drop = self._players[pid].policy.drop(state)

                        if drop == 1:
                            smallest_tresure = 0

                            for t, treasure in enumerate(self._players[pid].treasures):
                                if treasure.dots < self._players[pid].treasures[smallest_tresure].dots:
                                    smallest_tresure = t

                            self._treasure_path[position - 1].swap(self._players[pid].treasures[smallest_tresure])

                            del self._players[pid].treasures[smallest_tresure]

                            self._players[pid].weight -= 1
                else:
                    pick = self._players[pid].policy.pick(state)
                    
                    if pick == 1:
                        self._players[pid].treasures += [Treasure(self._treasure_path[position - 1].hidden_value,
                                                                  self._treasure_path[position - 1].dots)]

                        self._treasure_path[position - 1].hidden_value = 0
                        self._treasure_path[position - 1].dots = 0

                        self._players[pid].weight += 1

        state = self.state(pid)

        if self._oxygen <= 0 or all([p.done for p in self._players]):
            self.round += 1

            if self.round == 3:
                self._game_over = True
            else:
                self._end_of_round()

        else:
            self._next_player()

        return state, reward, self._game_over, {"last_player": self._current_player, "forward": forward, "pick": pick,"drop": drop}


    def render(self, colors=True, episode=None):
        game_top = ""
        game_bot = ""
        if colors is True:
            game_top += ESC + SUB_COLOR + END + BOLD
            game_bot += ESC + SUB_COLOR + END

        positions = [p.position for p in self._players]
        
        game_top += "["
        game_bot += " ‾‾‾‾‾‾ "

        nbplayers_in_sub = sum(map(lambda x: x==0, positions))

        game_top += " " * (6 - nbplayers_in_sub)

        for p in self._turn_order[::-1]:
            if positions[p] == 0:
                if colors is True:
                    game_top += ESC + PLAYER_COLORS[p] + END

                    game_top += ">" if self._players[p].forward is True else "<"

                else:
                    game_top += PLAYER_LETTER[p] if self._players[p].forward is True else PLAYER_LETTER[p].lower()

        if colors is True:
            game_top += ESC + SUB_COLOR + END
        
        game_top += "]"
        
        for loc, t in enumerate(self._treasure_path):
            found_player = False
            for p, pos in enumerate(positions):
                if pos == (loc + 1):
                    found_player = True
                    
                    if colors is True:
                        game_top += ESC + PLAYER_COLORS[p] + END
                        game_top += "> " if self._players[p].forward is True else "< "

                    else:
                        game_top += PLAYER_LETTER[p] if self._players[p].forward is True else PLAYER_LETTER[p].lower()
                        game_top += " "

            if found_player is False:
                game_top += "  "
                    

            if colors is True:
                if t.removed == True:
                    game_bot += ESC + "0" + END + "  "
                else:
                    game_bot += ESC + TREASURE_COLORS[t.dots] + END + "‾ "

            else:
                if t.removed == True:
                    game_bot += "- "
                else:
                    game_bot += str(t.dots) + " "
        
        if colors is True:
            game_top += ESC + SUB_COLOR + END + "  ||  Player "
            game_top += ESC + PLAYER_COLORS[self._current_player] + END + str(self._current_player + 1)
            game_top +=  ESC + SUB_COLOR + END + "'s turn"

            if episode:
                game_top += " Episode " + str(episode).zfill(5)
            
            game_top += ".\n"

            game_bot += ESC + SUB_COLOR + END + "  ||  Current O2: " + str(self._oxygen) + "\n\n"

        else:
            game_top += "  ||  Player " + PLAYER_LETTER[self._current_player] + "'s turn"

            if episode:
                game_top += " Episode " + str(episode).zfill(5)
            
            game_top += ".\n"
            game_bot += "  ||  Current O2: " + str(self._oxygen) + "\n\n"

        sys.stdout.write(game_top)
        sys.stdout.write(game_bot)

        if self._game_over is True:
            game_top = ""
            game_bot = ""
            if colors is True:
                game_top += ESC + SUB_COLOR + END + BOLD
                game_bot += ESC + SUB_COLOR + END

            game_top += "Scores: "
            game_bot += "        "
            
            for p in self._players:
                if colors is True:
                    game_top += ESC + PLAYER_COLORS[p._pid] + END + "Player " + str(p._pid + 1) + " - "
                    game_bot += ESC + PLAYER_COLORS[p._pid] + END + " " + str(p.points).zfill(2) + " pts  - "
                else:
                    game_top += "Player " + PLAYER_LETTER[p._pid] + " - "
                    game_bot += " " + str(p.points).zfill(2) + " pts  - "

            game_top += "\n"
            game_bot += "\n\n"

            sys.stdout.write(game_top)
            sys.stdout.write(game_bot)


        if colors is True:
            sys.stdout.write(RESET)


    def _generate_treasures(self):
        self._one_dots = _generate_treasure_set(1)
        self._two_dots = _generate_treasure_set(2)
        self._three_dots = _generate_treasure_set(3)
        self._four_dots = _generate_treasure_set(4)

    def _initialize_path(self):
        random.shuffle(self._one_dots)
        random.shuffle(self._two_dots)
        random.shuffle(self._three_dots)
        random.shuffle(self._four_dots)

        self._treasure_path = self._one_dots + self._two_dots + self._three_dots + self._four_dots

    def _initialize_turn_order(self):
        nb_players = len(self._players)
        self._turn_order = list(range(nb_players))

        rng = random.randint(1, nb_players)

        self._turn_order = self._turn_order[rng:] + self._turn_order[:rng]

    def _next_player(self):
        self._current_player += 1

        if self._current_player == len(self._players):
            self._current_player = 0


    def _next_viable_position(self, current_position, skipped, forward):
        step = 1 if forward==1 else -1

        next_position = current_position + step

        force_turn = False

        while True:
            if next_position < 0:
                return 0, force_turn
            elif next_position > 32:
                force_turn = True
                return current_position, force_turn
            elif skipped[next_position - 1] == 0:
                return next_position, force_turn

            next_position += step

    def _end_of_round(self):
        # Decide the next first player
        first_player = self._current_player
        
        for pid in self._turn_order:
            if self._players[pid].position > 0:
                first_player = pid

        self._current_player = first_player

        for treasure in self._treasure_path:
            if treasure.dots == 0:
                treasure.removed = True

        for player in self._players:
            player.reset(player._pid)

        self._oxygen = 25


    def add_player(self, player):
        self._players += [player]
        
def _generate_treasure_set(dots):
    base_values = [0, 4, 8, 12]
    
    treasures_ix = list(range(0, 8))

    treasures = [Treasure(base_values[dots - 1] + math.floor(ix / 2) , dots) for ix in treasures_ix]

    return treasures

def f_col(hex_color):
    return "\x1b[38;5;" + str(hex_color) + "m"


class Treasure(object):
    def __init__(self, hidden_value, dots):
        self.dots = dots
        self.hidden_value = hidden_value
        self.removed = False

    def swap(self, treasure):
        self.dots = treasure.dots
        self.hidden_value = treasure.hidden_value

class Player(object):
    def __init__(self, policy):
        self.policy = policy
        self.points = 0

    def reset(self, pid):
        self._pid = pid
        self.position = 0
        self.weight = 0
        self.treasures = []
        self.forward = True
        self.done = False

    def setposition(self, pos):
        self.position = pos

    def turn(self):
        self.forward = False



if __name__ == "__main__":
    env = DSA_env()
    env.seed(42)
    
    player1 = Player(Grabber(1))
    player2 = Player(Diver(16, 1))
    player3 = Player(Greedy())
    player4 = Player(Randy())
    player5 = Player(Grabber(2))
    player6 = Player(Diver(8, 2))

    env.add_player(player1)
    env.add_player(player2)
    env.add_player(player3)
    env.add_player(player4)
    env.add_player(player5)
    env.add_player(player6)

    env.reset()

    env.render()

    done = False

    while done is False:
        state, reward, done, info = env.step()
        env.render()
