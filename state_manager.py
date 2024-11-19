import json

def save_game_state(state, filename="game_state.json"):
    with open(filename, "w") as file:
        json.dump(state, file, indent=4)

def load_game_state(filename="game_state.json"):
    try:
        with open(filename, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return None