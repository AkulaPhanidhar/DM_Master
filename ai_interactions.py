import requests
import json
import os
import re
import ast
from openai import OpenAI
from dotenv import load_dotenv
from state_manager import load_game_state

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPAI_API_KEY = os.getenv("DEEPAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

game_state = load_game_state()

def generate_description(prompt):
    """
    Generates a location description using OpenAI's GPT model.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a Dungeon Master."},
                {
                    "role": "user",
                    "content": f"{prompt} Provide a brief, engaging paragraph, no more than 3 sentences.",
                },
            ],
            max_tokens=200,
            temperature=0.7,
        )
        description_text = response.choices[0].message.content.strip()
        return description_text
    except Exception as e:
        print(f"Error generating description: {e}")
        return "An intriguing scene unfolds before you."

def generate_npc_response(npc_name, player_input):
    """
    Generates an NPC's response to the player's input using OpenAI's GPT model.
    """
    try:
        location = game_state["player"]["location"]
        npc_data = game_state["locations"][location]["npcs"].get(npc_name, {})
        inventory = game_state["player"]["inventory"]
        quests = game_state.get("quests", {})
        current_hp = game_state["player"]["hp"]
        max_hp = game_state["player"]["max_hp"]

        context = (
            f"You are an NPC named {npc_name.capitalize()} in a Dungeons & Dragons game. "
            f"You are located at {location.replace('_', ' ').title()}, which is described as: '{game_state['locations'][location]['description']}'. "
            f"Your status is '{npc_data.get('status', 'unknown')}'. "
            f"The player has {current_hp}/{max_hp} HP and the following inventory: "
            f"{', '.join(item['name'] for item in inventory)}. "
            f"The active quests are: {', '.join(f'{q}: {data['description']}' for q, data in quests.items() if not data['completed'])}. "
            "Respond to the player's input in a way that reflects the current game state, being helpful, cryptic, or lore-focused. "
            "Keep your responses concise and limited to no more than two sentences."
        )

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": player_input},
            ],
            max_tokens=150,
            temperature=0.7,
        )
        npc_response = response.choices[0].message.content.strip()

        sentences = re.split(r'(?<=[.!?]) +', npc_response)
        if len(sentences) > 2:
            npc_response = ' '.join(sentences[:2])
            if not npc_response.endswith('.'):
                npc_response += '.'

        return npc_response
    except Exception as e:
        print(f"Error generating NPC response: {e}")
        return "I have nothing to say right now."

def generate_image_with_deepai(description, location_name, folder="generated_images"):
    """
    Generates an image using the DeepAI API based on the location description.
    """
    try:
        url = "https://api.deepai.org/api/text2img"
        headers = {"api-key": DEEPAI_API_KEY}
        data = {"text": f"{description}. Make it in a Dungeons & Dragons style, with a cave environment."}

        response = requests.post(url, headers=headers, data=data)
        response_data = response.json()

        if "output_url" not in response_data:
            print(f"Error: 'output_url' not found in API response.")
            return None

        if not os.path.exists(folder):
            os.makedirs(folder)

        image_url = response_data["output_url"]
        image_path = os.path.join(folder, f"{location_name}_image.png")
        image_data = requests.get(image_url).content

        with open(image_path, "wb") as img_file:
            img_file.write(image_data)

        return {"file_path": image_path, "url": image_url}
    except Exception as e:
        print(f"Error during image generation: {e}")
        return None

def validate_game_state(game_state):
    """
    Validates the game state structure and required keys.
    """
    required_player_keys = {
        "location",
        "location_history",
        "hp",
        "max_hp",
        "attack",
        "xp",
        "level",
        "xp_to_next_level",
        "inventory",
    }
    required_quest_keys = {"description", "completed", "required_items", "required_npcs"}
    required_location_keys = {
        "description",
        "npcs",
        "items",
        "connections",
        "locked_paths",
        "hidden_items",
        "traps",
    }

    if "player" not in game_state:
        raise ValueError("Missing 'player' section in game state.")
    if not required_player_keys.issubset(game_state["player"].keys()):
        missing = required_player_keys - game_state["player"].keys()
        raise ValueError(f"Player state is missing required keys: {missing}")

    if "quests" not in game_state:
        raise ValueError("Missing 'quests' section in game state.")
    for quest_name, quest_data in game_state["quests"].items():
        if not required_quest_keys.issubset(quest_data.keys()):
            missing = required_quest_keys - quest_data.keys()
            raise ValueError(f"Quest '{quest_name}' is missing required keys: {missing}")

    if "locations" not in game_state:
        raise ValueError("Missing 'locations' section in game state.")
    for location_name, location_data in game_state["locations"].items():
        if not required_location_keys.issubset(location_data.keys()):
            missing = required_location_keys - location_data.keys()
            raise ValueError(f"Location '{location_name}' is missing required keys: {missing}")

        traps = location_data.get("traps", {})
        for trap_name, trap_data in traps.items():
            required_trap_keys = {"description", "damage", "disarm_difficulty", "triggered"}
            if not required_trap_keys.issubset(trap_data.keys()):
                missing = required_trap_keys - trap_data.keys()
                raise ValueError(f"Trap '{trap_name}' in location '{location_name}' is missing keys: {missing}")

    return True

def generate_initial_game_state(attempts=3):
    """
    Generates the initial game state using OpenAI's GPT model.
    """
    prompt = """
    Generate a structured game state for a Dungeons & Dragons-inspired game in JSON format. The structure should include the following elements:

    {
        "player": {
            "location": "starting_location",
            "location_history": [],
            "hp": 120,
            "max_hp": 120,
            "attack": 10,
            "xp": 0,
            "level": 1,
            "xp_to_next_level": 75,
            "inventory": [
                {
                    "name": "healing_potion",
                    "type": "healing",
                    "healing_amount": 25,
                    "description": "A potion that restores 25 HP."
                },
                {
                    "name": "silver_key",
                    "type": "key",
                    "description": "A shiny silver key with intricate engravings."
                }
            ]
        },
        "quests": {
            "retrieve_ancient_artifact": {
                "description": "Retrieve the Ancient Artifact protected by the Shadow Lord in the Cursed Castle.",
                "completed": false,
                "required_items": ["ancient_artifact"],
                "required_npcs": []
            },
            "find_mystic_gem": {
                "description": "Locate the Mystic Gem concealed in the Crystal Caves.",
                "completed": false,
                "required_items": ["mystic_gem"],
                "required_npcs": []
            },
            "vanquish_final_boss": {
                "description": "Slay the Shadow Lord in the Cursed Castle.",
                "completed": false,
                "required_items": [],
                "required_npcs": ["final_boss"]
            }
        },
        "locations": {
            "starting_location": {
                "description": "A peaceful village surrounded by lush forests and rolling hills.",
                "npcs": {
                    "village_elder": {
                        "hp": 50,
                        "max_hp": 50,
                        "attack": 5,
                        "status": "active"
                    }
                },
                "items": {
                    "healing_potion": {
                        "type": "healing",
                        "healing_amount": 25,
                        "description": "A potion that restores 25 HP."
                    },
                    "silver_key": {
                        "type": "key",
                        "description": "A shiny silver key with intricate engravings."
                    }
                },
                "connections": {
                    "north": "dark_forest",
                    "east": "mystic_lake",
                    "south": "abandoned_mine",
                    "west": "ancient_ruins"
                },
                "locked_paths": {
                    "west": true,
                    "north": true,
                },
                "hidden_items": {
                    "golden_key": {
                        "type": "key",
                        "description": "A golden key glinting in the sunlight, it might unlock something important."
                    }
                },
                "traps": {
                    "avalanche": {
                        "description": "A sudden avalanche triggered by a footstep, it's fast and deadly.",
                        "damage": 30,
                        "disarm_difficulty": "very_challenging",
                        "triggered": false
                    }
                }
            }
        }
    }

    **Instructions:**
    - **Use the Same Quests:**
        - Do not change the quests from the example.
        - Ensure the quests are exactly as defined in the example, including the quest names and descriptions.
    - **Quest Structure:**
        - Each quest should have the following fields:
            - `description`: As provided.
            - `completed`: Set to **false**.
            - `required_items`: A list of item names required to complete the quest.
            - `required_npcs`: A list of NPC names that need to be defeated to complete the quest.
    - **Placement:**
        - **Final Boss NPC and Ancient Artifact:**
            - Place both the `final_boss` NPC and the `ancient_artifact` item (type: `scroll`) in the **same location**.
            - For the `vanquish_final_boss` quest, set `required_npcs` to `["final_boss"]`.
            - For the `retrieve_ancient_artifact` quest, set `required_items` to `["ancient_artifact"]`.
        - **Mystic Gem:**
            - Place the `mystic_gem` (type: `healing` with full heal capacity) in a **different location**.
            - For the `find_mystic_gem` quest, set `required_items` to `["mystic_gem"]`.
    - **Complete All Entries:**
        - Define between **8 to 12** unique locations without using placeholders like `{...}`.
        - Ensure all necessary fields (`description`, `npcs`, `items`, `connections`, `locked_paths`, `hidden_items`, `traps`) are present for each location.
    - **Maintain Consistency:**
        - Follow the same JSON structure as the example above.
        - Ensure that locations, items, and NPCs are interconnected logically.
    - **Include Traps in Locations:**
        - **Trap Definition:** Each location may include a `traps` key with traps defined as:
            - `description`: A description of the trap.
            - `damage`: The amount of HP the player loses if the trap is triggered.
            - `disarm_difficulty`: Difficulty level for disarming the trap (`"simple"`, `"challenging"`, `"very_challenging"`).
            - `triggered`: Set to `false`.
        - **Distribution:** Include between **0 to 2** traps per location, with most locations having **0 or 1** traps.
    - **Configure Locked Paths and Keys:**
        - **Locked Paths:** lock **4 to 6** paths in total across all locations.
        - **Locked Paths:** All paths leading to the final boss location must be **locked**.
        - **Keys Availability:** Provide **more keys** (e.g., 2 times the number of locked paths) to ensure players can progress through the game.
    - **Include Hidden Items:**
        - **Quantity:** Add **0 to 2** hidden items per location, with most locations having **0**.
        - **Placement:** Strategically place hidden items to enhance gameplay and exploration.
    - **Logical Location Connections:**
        - **Connectivity:** Ensure that all locations are connected logically, allowing smooth navigation.
        - **Final Boss Location:** Design the final boss location (e.g., `cursed_castle`) to be the **most challenging to reach**, requiring multiple keys or steps.
    - **Distribute Item Types Based on Probabilities:**
        - **Item Type Distribution:**
            - **Tool:** 10%
            - **Weapon:** 20%
            - **Healing:** 50%
            - **Key:** 30%
        - **Implementation:** Ensure that the distribution of item types across all locations adheres to these probabilities.
    - **Player Statistics Configuration:**
        - **Player Stats:**
            - `max_hp`: Range between **80 to 140**.
            - `attack`: Range between **6 to 14**.
            - `xp`: Set to **0**.
            - `level`: Set to **1**.
            - `xp_to_next_level`: Choose from **50, 75, or 100**.
            - `inventory`: Include between **2 to 4** items.
    - **JSON Formatting and Validation:**
        - **Format:** Ensure the game state is a **well-structured** and **error-free** JSON object.
        - **Syntax:** Properly use commas, quotes, braces, and brackets.
        - **Validation:** The JSON must pass standard JSON validation checks without errors.
    - **Output Requirements:**
        - **Content Only:** Return **only** the JSON object without any variable assignments, explanations, or additional text.
        - **No Extra Messages:** The output should be clean, containing solely the JSON structure.
    """

    for attempt in range(1, attempts + 1):
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a Dungeon Master."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=3500,
                temperature=0.7,
                n=1,
                stop=None,
            )

            game_state_text = response.choices[0].message.content.strip()
            game_state_text = re.sub(r"```(?:python|json)?|```", "", game_state_text).strip()
            game_state_text = re.sub(r'^game_state\s*=\s*', '', game_state_text, flags=re.MULTILINE)

            try:
                game_state = json.loads(game_state_text)
                validate_game_state(game_state)
                return game_state
            except json.JSONDecodeError:
                print("Error: Received invalid JSON from AI.")
            except ValueError as ve:
                print(f"Validation Error: {ve}")

            try:
                game_state = ast.literal_eval(game_state_text)
                validate_game_state(game_state)
                return game_state
            except Exception:
                print("Error: Failed to parse game_state as Python dict.")
        except Exception as e:
            print(f"Error during API call: {e}")

        print(f"Retrying... ({attempt}/{attempts})")

    print("Failed to generate a valid game state after multiple attempts.")
    return None

def initialize_game_state():
    """
    Initializes the game state by generating it if not present.
    """
    return generate_initial_game_state()
