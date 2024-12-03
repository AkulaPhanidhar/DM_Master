import json

def save_game_state(state, filename="game_state.json"):
    """
    Saves the current game state to a JSON file.
    """
    with open(filename, "w") as file:
        json.dump(state, file, indent=4)

def load_game_state(filename="game_state.json"):
    """
    Loads the game state from a JSON file.
    """
    try:
        with open(filename, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return None
