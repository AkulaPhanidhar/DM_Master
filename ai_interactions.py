from openai import OpenAI
from dotenv import load_dotenv
import os
import re
import requests
from state_manager import load_game_state

game_state = load_game_state()

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

def generate_description(prompt):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a Dungeon Master."},
            {"role": "user", "content": f"{prompt} Provide a brief, engaging paragraph, no more than 3 sentences."}
        ],
    )
    description_text = response.choices[0].message.content.strip()
    return description_text

def generate_npc_response(npc_name, player_input):
    """Generate an NPC response dynamically based on player input and the current game state."""
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
        model="gpt-4o",
        messages=[
            {"role": "system", "content": context},
            {"role": "user", "content": player_input}
        ]
    )
    npc_response = response.choices[0].message.content.strip()

    sentences = npc_response.split(". ")
    if len(sentences) > 2:
        npc_response = ". ".join(sentences[:2]).strip() + ("" if npc_response.endswith(".") else ".")
    
    return npc_response

def generate_image_with_deepai(description, location_name, folder="generated_images"):
    try:
        url = "https://api.deepai.org/api/text2img"
        headers = {"api-key": os.getenv("DEEPAI_API_KEY")}
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

def generate_initial_game_state():
    prompt = """
    Generate a structured game state for a Dungeons & Dragons-inspired game. The structure should include the following elements:
    
    First, focus on the given examples and then create your own unique content based on the examples provided, and make sure to follow the same structure as the examples.

    1. **Player Information**:
       - `location`: The player's starting location, with a descriptive name.
       - `hp`: Player's starting health points (e.g., 100).
       - `max_hp`: Maximum health points (e.g., 100).
       - `attack`: Player's attack power (e.g., 5).
       - `xp`: Starting experience points (e.g., 0).
       - `level`: Starting level (e.g., 1).
       - `xp_to_next_level`: Experience points needed to level up (e.g., 50).
       - `inventory`: A list of starting items, including examples like:
         - A "potion" that restores health when used.
         - A "key" used to unlock certain paths.
         - add only any 2 items in the inventory, the abive is the example.

    2. **Quests**:
       - Generate at least two quests for the player to complete. Example quests might include:
         - Finding a valuable item, such as a "mystic_gem."
         - Defeating a challenging opponent or "final boss" to retrieve a special item, like an "ancient_artifact."
       - For each quest, include:
         - `description`: A short description of the quest.
         - `completed`: A boolean to track if the quest is completed.

    3. **Locations**:
       Create a set of unique locations (at least 8 and max 12) that players can explore and your own no of of locations. Each location should include:
       - `name`: A descriptive name for the location.
       - `description`: A vivid description that highlights the setting and any notable features.
       - `npcs`: A list of NPCs in the location. Examples of NPCs include:
         - Hostile creatures (e.g., "goblin," "wolf") with attributes such as `hp`, `attack`, and `status` only active.
         - Place a powerful final boss as one of the npc with higher difficulty and a unique setting, marking it as a climactic area.
         generate the npcs in this example formate only:
         "npcs": {
                    "goblin": {"hp": 10, "attack": 2, "status": "active"},
                    "troll": {"hp": 20, "attack": 4, "status": "inactive"}
                },
       - `items`: List of items found in the location, such as:
         - Healing items like "potion" or "magic_water."
         - Quest items like "mystic_gem" or "ancient_artifact."
         - Equipment like "sword" (boosts attack) or "shield" (boosts defense).
         - Have the final boss guard a special item, such as an "ancient_artifact, and place it as an item in the location where the final boss is present" which the player must retrieve to complete a quest.
         - these are the list of items you can add in total (use any item name but use only these item types which are key, shield, healing, tool, weapon, etc, only one mystic_gem of type healing), add these as many as you want but only one ancient_artifac in the location where the final boss is present.
         - make sure there are more keys than the locked paths and able to find enought no of keys before a door.
         - add atleast one item in 80 percentage of the locations and maximum 4 items in one location.
       - `connections`: Possible directions that lead to other locations (e.g., north, south, east, west), make the connections little comple, and make sure connections are properly connected to each other, example: from one location to other is connected as south, both should be south and no overlapping.
       - `locked_paths`: Indicate if any paths are locked, requiring an item (e.g., "key") to access, look at least 3 paths from any location to any location.

       here is an example formate: do it in the same formate, but change everything else in the sence of content.
       
       "player": {
            "location": "cave_entrance",
            "location_history": [],
            "hp": 100,
            "max_hp": 100,
            "attack": 5,
            "xp": 0,
            "level": 1,
            "xp_to_next_level": 50,
            "inventory": [
                {"name": "potion", "type": "healing", "healing_amount": 10, "description": "A small bottle filled with a liquid that restores 10 HP."},
                {"name": "key", "type": "key", "description": "A simple iron key, used to unlock certain doors."}
            ]
        },
        "quests": {
            "collect_mystic_gem": {
                "description": "Collect the Mystic Gem from the Hidden Clearing.",
                "completed": False
            },
            "defeat_final_boss": {
                "description": "Defeat the Final Boss in the Enchanted Valley and retrieve the ancient artifact.",
                "completed": False
            }
        },
        "locations": {
            "cave_entrance": {
                "description": "The entrance to a cave with a gloomy atmosphere.",
                "npcs": {
                    "goblin": {"hp": 10, "attack": 2, "status": "active"},
                    "troll": {"hp": 20, "attack": 4, "status": "inactive"}
                },
                "items": {
                    "potion": {"type": "healing", "healing_amount": 10, "description": "A small bottle that restores 10 HP."}
                },
                "connections": {
                    "north": "river_bank",
                    "south": "dark_forest"
                },
                "locked_paths": {"north": True}
            },
            "dark_forest": {
                "description": "A misty, eerie forest with twisted trees and strange sounds.",
                "npcs": {
                    "wolf": {"hp": 15, "attack": 3, "status": "active"},
                    "bat": {"hp": 5, "attack": 1, "status": "active"},
                    "owlbear": {"hp": 20, "attack": 4, "status": "active"}
                },
                "items": {},
                "connections": {
                    "south": "cave_entrance",
                    "west": "mystic_lake",
                    "north": "mountain_pass"
                }
            },
            "river_bank": {
                "description": "A calm river bank with water flowing gently.",
                "npcs": {},
                "items": {
                    "torch": {"type": "tool", "description": "A torch to illuminate hidden paths and items."},
                    "shield": {"type": "defense", "defense_boost": 3, "description": "A sturdy shield that grants +3 defense when equipped."},
                    "key": {"type": "key", "description": "A key that may unlock doors in nearby areas."},
                },
                "connections": {
                    "north": "cave_entrance",
                    "east": "mystic_lake"
                },
                "hidden_item": {
                    "name": "herb_bundle",
                    "type": "healing",
                    "healing_amount": 15,
                    "description": "A bundle of rare herbs that restores 15 HP when used."
                }
            },
            "mystic_lake": {
                "description": "A lake with shimmering water, radiating a magical aura.",
                "npcs": {
                    "water_spirit": {"hp": 20, "attack": 4, "status": "active"}
                },
                "items": {
                    "magic_water": {"type": "healing", "healing_amount": 25, "description": "A mystical water that restores 25 HP."},
                    "sword": {"type": "weapon", "attack_boost": 7, "description": "A sharp sword that grants +7 attack when wielded."},
                    "key": {"type": "key", "description": "A small key for opening locked paths."}
                },
                "connections": {
                    "north": "ancient_ruins",
                    "west": "dark_forest",
                    "south": "enchanted_valley"
                },
                "locked_paths": {"south": True, "west": True}
            },
            "ancient_ruins": {
                "description": "Forgotten ruins with broken pillars and overgrown vines.",
                "npcs": {
                    "skeleton": {"hp": 18, "attack": 3, "status": "active"}
                },
                "items": {
                    "key": {"type": "key", "description": "A tarnished key found in the ruins."}
                },
                "connections": {
                    "north": "mystic_lake",
                    "south": "hidden_clearing",
                }
            },
            "hidden_clearing": {
                "description": "A small, tranquil clearing that seems to be untouched by time.",
                "npcs": {},
                "items": {
                    "mystic_gem": {"type": "quest_item", "description": "A radiant gem pulsating with energy, essential for completing a quest."},
                    "potion": {"type": "healing", "healing_amount": 15, "description": "A potent potion that restores 15 HP."}
                },
                "connections": {
                    "south": "ancient_ruins",
                    "north": "river_bank",
                    "east": "mountain_pass"
                }
            },
            "mountain_pass": {
                "description": "A narrow mountain pass with steep cliffs on both sides.",
                "npcs": {
                    "eagle": {"hp": 12, "attack": 2, "status": "active"}
                },
                "items": {
                    "key": {"type": "key", "description": "A simple key likely used for unlocking a nearby path."}
                },
                "connections": {
                    "north": "dark_forest",
                    "east": "enchanted_valley"
                },
                "locked_paths": {"east": True}
            },
            "enchanted_valley": {
                "description": "A hidden valley filled with vibrant flora and mystical energies.",
                "npcs": {
                    "final_boss": {"hp": 60, "attack": 8, "status": "active"}
                },
                "items": {
                    "ancient_artifact": {
                        "type": "quest_item",
                        "description": "A powerful artifact, obtainable only by defeating the final boss."
                    },
                    "potion": {"type": "healing", "healing_amount": 25, "description": "A healing potion that restores 25 HP."}
                },
                "connections": {
                    "west": "mountain_pass",
                    "south": "mystic_lake"
                }
            }
        }
        
    make sure there are more keys than the locked paths and able to find enought no of keys before a door.

    Format the response as a Python dictionary ready for integration into a JSON-based game state. Ensure the structure is nested and consistent, capturing all these elements in a structured and playable format.
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a Dungeon Master."},
            {"role": "user", "content": prompt}
        ],
    )
    
    game_state_text = response.choices[0].message.content.strip()
    game_state_text = re.sub(r"```(?:python)?|```", "", game_state_text).strip()

    game_state = eval(game_state_text)
    return game_state

def initialize_game_state():
    return generate_initial_game_state()
