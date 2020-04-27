from gym.envs.registration import register

register(
    id='DeepSeaAdventure-v0',
    entry_point='gym_DeepSeaAdventure.envs:DSA_env',
)
