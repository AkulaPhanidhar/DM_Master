import random
import matplotlib.pyplot as plt
import networkx as nx
import pyttsx3
from state_manager import load_game_state, save_game_state
from ai_interactions import (
    generate_description,
    initialize_game_state,
    generate_npc_response,
    generate_image_with_deepai,
)

use_voice = True

engine = pyttsx3.init()
engine.setProperty("rate", 180)
engine.setProperty("volume", 0.8)

def speak(text):
    """
    Prints and optionally speaks the given text.
    """
    print(text)
    if use_voice:
        engine.say(text)
        engine.runAndWait()

def toggle_voice():
    """
    Toggles the voice output on or off.
    """
    global use_voice
    if use_voice:
        speak("\nVoice output is now disabled.")
        use_voice = False
    else:
        use_voice = True
        speak("\nVoice output is now enabled.")

def check_player_hp():
    """
    Checks the player's HP and handles game over conditions.
    """
    player_hp = game_state["player"].get("hp", 0)
    if player_hp <= 0:
        speak("Your HP is too low to continue. You must start a new game.")
        while True:
            start_new = input("Would you like to start a new game? (yes/no): ").strip().lower()
            if start_new == "yes":
                start_new_game()
                return True
            elif start_new == "no":
                speak("Exiting the game. Thank you for playing!")
                exit_game()
                return False
            else:
                speak("Invalid choice. Please type 'yes' or 'no'.")
    return True

def check_quest_completion():
    """
    Checks if quests are completed based on required items and defeated NPCs.
    """
    all_completed = True

    for quest_name, quest_data in game_state["quests"].items():
        if not quest_data.get("completed", False):
            is_completed = True

            required_items = quest_data.get("required_items", [])
            if required_items:
                for item in required_items:
                    if not any(
                        player_item["name"] == item for player_item in game_state["player"]["inventory"]
                    ):
                        is_completed = False
                        break

            required_npcs = quest_data.get("required_npcs", [])
            if required_npcs:
                for npc in required_npcs:
                    npc_defeated = False
                    for location_data in game_state["locations"].values():
                        npc_data = location_data.get("npcs", {}).get(npc)
                        if npc_data and npc_data.get("status") == "defeated":
                            npc_defeated = True
                            break
                    if not npc_defeated:
                        is_completed = False
                        break

            if is_completed:
                quest_data["completed"] = True
                print(f"\n=== Quest Completed: {quest_name.replace('_', ' ').title()} ===")
                speak(f"Quest completed: {quest_data['description']}!")
                save_game_state(game_state)
            else:
                all_completed = False
        else:
            all_completed = all_completed and quest_data.get("completed", False)

    if all_completed:
        print("\n=== Congratulations! You have completed all quests ===")
        speak("Congratulations! You have completed all your quests and mastered the realm.")
        exit_game()

def load_or_initialize_game():
    """
    Loads the game state or initializes it if none exists.
    """
    game_state = load_game_state()
    if game_state is None:
        game_state = initialize_game_state()
        if game_state is None:
            print("Error: Failed to initialize game state.")
            exit_game()
        save_game_state(game_state)
    return game_state

game_state = load_or_initialize_game()

def extract_locations_from_game_state(game_state):
    """
    Extracts location data from the game state for mapping.
    """
    locations = {}
    for location_name, location_data in game_state["locations"].items():
        locations[location_name] = {
            "description": location_data["description"],
            "connections": location_data["connections"],
        }
    return locations

locations = extract_locations_from_game_state(game_state)

def display_map():
    """
    Displays a visual map of the game world using NetworkX and Matplotlib.
    """
    G = nx.DiGraph()

    for location, data in game_state["locations"].items():
        G.add_node(location, label=data["description"])
        for direction, connected_location in data["connections"].items():
            G.add_edge(location, connected_location, direction=direction)

    pos = nx.spring_layout(G, seed=42)
    current_location = game_state["player"]["location"]

    plt.figure(figsize=(14, 8))
    node_colors = ["#ffa500" if node == current_location else "#87ceeb" for node in G.nodes]

    node_sizes = [max(6000, len(node.replace("_", " ").title()) * 300) for node in G.nodes]

    nx.draw(
        G,
        pos,
        node_color=node_colors,
        node_size=node_sizes,
        with_labels=False,
        edge_color="#555",
        linewidths=2,
        alpha=0.9,
        arrows=True,
        arrowsize=20,
    )

    edge_labels = {(u, v): data["direction"].capitalize() for u, v, data in G.edges(data=True)}
    nx.draw_networkx_edge_labels(
        G,
        pos,
        edge_labels=edge_labels,
        font_size=9,
        font_color="#555",
        label_pos=0.5,
    )

    node_labels = {node: node.replace('_', ' ').title() for node in G.nodes}
    for node, (x, y) in pos.items():
        text = node_labels[node]
        plt.text(
            x,
            y,
            text,
            fontsize=9,
            color="#222",
            bbox=dict(facecolor="white", edgecolor="#333", boxstyle="round,pad=0.5", lw=1),
            ha="center",
            va="center",
            clip_on=True,
        )

    plt.gca().set_facecolor("#f0f0f0")
    plt.title(
        "Game Map: Locations and Connections",
        fontsize=14,
        fontweight="bold",
        color="#333",
        pad=20,
    )
    plt.axis("off")
    plt.show()

def describe_location():
    """
    Describes the current location, including NPCs, items, and available paths.
    """
    location = game_state["player"]["location"]
    loc_data = game_state["locations"].get(location)

    if not loc_data:
        print(f"Error: The location '{location}' does not exist in the game state.")
        return

    print(f"\n=== Current Location ===")
    print(location.replace('_', ' ').title())

    if "generated_description" not in loc_data:
        prompt = f"{loc_data['description']} Give a brief, atmospheric paragraph in D&D style, no more than 5 sentences."
        loc_data["generated_description"] = generate_description(prompt)
        game_state["locations"][location] = loc_data
        save_game_state(game_state)

    print("\n=== Location Description ===")
    speak(loc_data["generated_description"])

    if loc_data.get("npcs"):
        print("\n=== NPCs Here ===")
        for npc, data in loc_data["npcs"].items():
            status = "defeated" if data.get("hp", 0) <= 0 or data.get("status") == "defeated" else "active"
            if status == "active":
                print(f"- {npc.replace('_', ' ').title()} ({status}) - HP: {data['hp']}, Attack: {data['attack']}")
            else:
                print(f"- {npc.replace('_', ' ').title()} ({status})")

    if loc_data.get("items"):
        print("\n=== Items Available ===")
        for item_name, item_data in loc_data["items"].items():
            description = item_data.get("description", "No description available")
            item_type = item_data.get("type", "misc")
            print(f"- {item_name.replace('_', ' ').title()} ({item_type}) - {description}")

    if loc_data.get("connections"):
        print("\n=== Paths Available ===")
        for direction, connected_location in loc_data["connections"].items():
            lock_status = "(locked)" if loc_data.get("locked_paths", {}).get(direction, False) else ""
            print(f"- {direction.capitalize()}: {connected_location.replace('_', ' ').title()} {lock_status}")

def perform_skill_check(task_description, difficulty="simple"):
    """
    Performs a skill check based on difficulty level.
    """
    speak(f"\nAttempting: {task_description}")
    roll = random.randint(1, 10)
    speak(f"You rolled a {roll}!")

    if difficulty == "simple":
        success_threshold = 3
    elif difficulty == "challenging":
        success_threshold = 6
    elif difficulty == "very_challenging":
        success_threshold = 8
    else:
        raise ValueError(f"Unknown difficulty level: {difficulty}")

    if roll >= success_threshold:
        speak(f"Success! You manage to complete the task: {task_description}.")
        return True
    else:
        speak(f"Failure. You could not complete the task: {task_description}.")
        return False

def display_player_stats():
    """
    Displays the player's current stats.
    """
    player = game_state["player"]
    print("\n=== Player Stats ===")
    print(f"Level: {player['level']}")
    print(f"HP: {player['hp']}/{player['max_hp']}")
    print(f"Attack: {player['attack']}")
    print(f"XP: {player['xp']}/{player['xp_to_next_level']}")

def display_inventory():
    """
    Displays the player's inventory with item details.
    """
    inventory = game_state["player"]["inventory"]
    print("\n=== Inventory ===")

    if not inventory:
        speak("Your inventory is empty.")
    else:
        item_counts = {}
        for item in inventory:
            item_key = item["name"]
            if item_key in item_counts:
                item_counts[item_key]["count"] += 1
            else:
                item_counts[item_key] = {"count": 1, "data": item}

        for item_name, info in item_counts.items():
            count = info["count"]
            item_data = info["data"]
            description = item_data.get("description", "No description available.")

            if item_data["type"] == "healing":
                additional_info = f"(Healing) - Restores {item_data['healing_amount']} HP when used"
            elif item_data["type"] == "key":
                additional_info = "(Key) - Used to unlock paths."
            elif item_data["type"] == "tool":
                additional_info = f"(Tool) - {description}"
            elif item_data["type"] == "quest_item":
                additional_info = f"(Quest Item) - {description}"
            elif item_data["type"] == "weapon":
                additional_info = f"(Weapon) - Increases attack by {item_data.get('attack_boost', 0)}"
            else:
                additional_info = f"({item_data['type'].capitalize()}) - {description}"

            print(f"- {item_name.replace('_', ' ').title()} x{count} {additional_info}")

def pick_up_item(item_name=None):
    """
    Allows the player to pick up an item from the current location.
    """
    location = game_state["player"]["location"]
    items = game_state["locations"][location].get("items", {})

    if not items:
        print("There are no items to pick up here.")
        return

    if item_name:
        if item_name in items:
            pick_specific_item(item_name, items, location)
            check_quest_completion()
        else:
            print(f"There is no {item_name} here to pick up.")
    else:
        print("\n=== Select Items to Pick Up ===")
        for idx, item in enumerate(items.keys(), start=1):
            print(f"{idx}. {item.replace('_', ' ').title()}")
        print("Choose an item (enter the number, 'a' for all, or 0 to cancel): ", end="")
        choice = input().strip()

        if choice == '0':
            print("Cancelled picking up items.")
            return
        elif choice.lower() == 'a':
            for item in list(items.keys()):
                pick_specific_item(item, items, location)
            check_quest_completion()
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(items):
                    item_name = list(items.keys())[idx]
                    pick_specific_item(item_name, items, location)
                    check_quest_completion()
                else:
                    print("Invalid selection.")
            except ValueError:
                print("Invalid input.")

def pick_specific_item(item_name, items, location):
    """
    Picks up a specific item from the location.
    """
    if item_name == "ancient_artifact":
        final_boss = game_state["locations"][location]["npcs"].get("final_boss")
        if final_boss and final_boss["status"] != "defeated":
            speak("You cannot pick up the Ancient Artifact without defeating the Final Boss!")
            return

    if item_name not in items:
        print(f"No such item '{item_name}' here. Available items: {', '.join(items.keys())}")
        return

    item = items.pop(item_name)
    game_state["player"]["inventory"].append({"name": item_name, **item})
    print(f"You picked up {item_name.replace('_', ' ').title()}.")
    save_game_state(game_state)

def use_item(item_name):
    """
    Uses an item from the player's inventory.
    """
    inventory = game_state["player"]["inventory"]
    item = next((item for item in inventory if item["name"] == item_name), None)

    if not item:
        available_items = ', '.join([item["name"] for item in inventory])
        print(f"You don't have '{item_name}' in your inventory. Available items: {available_items}")
        return

    item_type = item.get("type")

    if item_type == "healing":
        use_healing_item(item, inventory, item_name)
    elif item_type == "weapon":
        use_weapon_item(item, inventory, item_name)
    elif item_type == "tool" and item_name == "torch":
        use_torch_item(item, inventory, item_name)
    elif item_type == "key":
        speak("You can use keys to unlock doors when you encounter them.")
    else:
        speak(f"The {item_name} can't be used directly.")

    save_game_state(game_state)

def use_healing_item(item, inventory, item_name):
    """
    Uses a healing item to restore player's HP.
    """
    player_hp = game_state["player"]["hp"]
    max_hp = game_state["player"]["max_hp"]
    if player_hp >= max_hp:
        speak("Your HP is already at maximum. You don't need to use a healing item now.")
        return
    healing_amount = item.get("healing_amount", 0)
    healed_amount = min(healing_amount, max_hp - player_hp)
    game_state["player"]["hp"] += healed_amount
    print(f"\n=== Item Used ===")
    speak(f"You used a {item_name.replace('_', ' ').title()} and restored {healed_amount} HP.")
    inventory.remove(item)

def use_weapon_item(item, inventory, item_name):
    """
    Equips a weapon item to increase player's attack.
    """
    weapon_attack = item.get("attack_boost", 5)
    game_state["player"]["attack"] += weapon_attack
    print(f"\n=== Item Equipped ===")
    speak(f"You equipped {item_name.replace('_', ' ').title()} and permanently increased your attack by {weapon_attack}.")
    inventory.remove(item)

def use_torch_item(item, inventory, item_name):
    """
    Uses a torch to search for hidden items.
    """
    print(f"\n=== Item Used ===")
    speak(f"You used a {item_name.replace('_', ' ').title()} to search for hidden items!")
    search_for_hidden_item()
    inventory.remove(item)

def gain_xp(amount, npc_name):
    """
    Adds experience points to the player and checks for level up.
    """
    player = game_state["player"]
    player["xp"] += amount
    speak(f"You earned {amount} XP for defeating the {npc_name.replace('_', ' ').title()}!")

    if player["xp"] >= player["xp_to_next_level"]:
        level_up()

    save_game_state(game_state)

def level_up():
    """
    Increases player's level and stats when enough XP is accumulated.
    """
    player = game_state["player"]
    player["level"] += 1
    player["xp"] -= player["xp_to_next_level"]
    player["xp_to_next_level"] = int(player["xp_to_next_level"] * 1.5)

    player["max_hp"] += 10
    player["hp"] = player["max_hp"]
    player["attack"] += 2

    print(f"\n=== Level Up! ===")
    speak(f"You leveled up to Level {player['level']}!")
    print(
        f"New stats - HP: {player['hp']}/{player['max_hp']}, Attack: {player['attack']}, XP to next level: {player['xp_to_next_level']}"
    )
    save_game_state(game_state)

def engage_combat():
    """
    Initiates combat with an NPC in the current location.
    """
    location = game_state["player"]["location"]
    npcs = game_state["locations"][location].get("npcs", {})
    active_npcs = {npc: data for npc, data in npcs.items() if data.get("status") != "defeated"}

    if not active_npcs:
        speak("No active NPCs to fight here.")
        return False

    if game_state["player"]["hp"] <= 5:
        speak("You are too weak to fight. Heal yourself before engaging in combat.")
        return False

    npc_name = select_npc_for_combat(active_npcs)
    if not npc_name:
        return False

    return combat_loop(npc_name)

def select_npc_for_combat(active_npcs):
    """
    Allows the player to select an NPC to fight.
    """
    if len(active_npcs) > 1:
        print("\n=== Select an NPC to Fight ===")
        for idx, npc in enumerate(active_npcs, start=1):
            npc_data = active_npcs[npc]
            print(f"{idx}. {npc.replace('_', ' ').title()} (HP: {npc_data['hp']}/{npc_data['max_hp']}, Attack: {npc_data['attack']})")
        try:
            choice = input("Choose an NPC (enter the number or 0 to cancel): ").strip()
            if choice == "0":
                print("Combat canceled.")
                return None
            choice = int(choice)
            npc_name = list(active_npcs.keys())[choice - 1]
        except (ValueError, IndexError):
            speak("Invalid choice. Try selecting an NPC.")
            return None
    else:
        npc_name = next(iter(active_npcs))
    return npc_name

def combat_loop(npc_name):
    """
    Handles the combat loop between the player and the NPC.
    """
    npc = game_state["locations"][game_state["player"]["location"]]["npcs"][npc_name]
    player = game_state["player"]

    speak(f"\nYou engage in combat with {npc_name.replace('_', ' ').title()}!")

    while player["hp"] > 0 and npc["hp"] > 0:
        print(f"\nYour HP: {player['hp']}/{player['max_hp']}")
        print(f"{npc_name.replace('_', ' ').title()}'s HP: {npc['hp']}/{npc['max_hp']}")

        action_input = input("\nChoose your action (roll, use [item], inventory, quit): ").lower().strip()
        action = action_input.split()

        skip_npc_turn = False

        if not action:
            print("No action entered. Please choose an action.")
            continue

        if action[0] == "roll":
            roll = random.randint(1, 6)
            critical_hit = roll == 6
            damage = player["attack"] + roll + (5 if critical_hit else 0)
            npc["hp"] -= damage
            print(f"\nYou rolled a {roll}!")
            if critical_hit:
                print("Critical hit!")
            speak(f"You attack {npc_name.replace('_', ' ').title()} for {damage} damage.")
        elif action[0] == "use" and len(action) > 1:
            item_name = action[1]
            use_item(item_name)
            skip_npc_turn = True
        elif action[0] == "inventory":
            display_inventory()
            skip_npc_turn = True
        elif action[0] == "quit":
            speak("\nYou retreated from the combat.")
            save_game_state(game_state)
            return False
        else:
            print("\nInvalid action. Choose 'roll', 'use [item]', 'inventory', or 'quit'.")
            continue

        if npc["hp"] <= 0:
            npc["hp"] = 0
            npc["status"] = "defeated"
            speak(f"\nYou have defeated {npc_name.replace('_', ' ').title()}!")
            xp_gained = npc.get("xp", 20)
            gain_xp(xp_gained, npc_name)
            save_game_state(game_state)
            check_quest_completion()
            return True

        if not skip_npc_turn:
            print(f"\n{npc_name.replace('_', ' ').title()}'s turn!")
            roll = random.randint(1, 6)
            critical_hit = roll == 6
            npc_damage = npc.get("attack", 5) + roll + (5 if critical_hit else 0)
            player["hp"] -= npc_damage
            print(f"{npc_name.replace('_', ' ').title()} rolled a {roll}!")
            if critical_hit:
                print("Critical hit!")
            speak(f"{npc_name.replace('_', ' ').title()} attacks you for {npc_damage} damage.")

            if player["hp"] <= 0:
                player["hp"] = 0
                speak("\nYou have been defeated. Game over.")
                save_game_state(game_state)
                exit_game()
        else:
            skip_npc_turn = False

    return True

def trigger_trap(trap_name, trap_data):
    """
    Applies the trap's effects to the player.
    """
    speak(f"\nOh no! You've triggered a trap: {trap_name.replace('_', ' ').title()}!")
    speak(trap_data.get("description", "A trap activates!"))
    damage = trap_data.get("damage", 10)
    speak(f"You take {damage} damage.")
    game_state["player"]["hp"] -= damage

    if game_state["player"]["hp"] <= 0:
        game_state["player"]["hp"] = 0
        print("You have succumbed to your injuries from the trap. Game over.")
        save_game_state(game_state)
        exit_game()
    else:
        print(f"Your current HP: {game_state['player']['hp']}/{game_state['player']['max_hp']}")

    trap_data["triggered"] = True

def check_for_traps(location):
    """
    Checks for traps in the specified location and handles player interaction.
    """
    location_data = game_state["locations"].get(location, {})
    traps = location_data.get("traps", {})

    for trap_name, trap_data in traps.items():
        if not trap_data.get("triggered", False):
            print(f"\nAs you enter {location.replace('_', ' ').title()}, you feel that something is amiss...")
            print("What would you like to do?")
            print("1. Proceed carefully")
            print("2. Search for traps")
            print("3. Do nothing")
            action = input("Enter 1, 2, or 3: ").strip()

            if action == "1":
                success = perform_skill_check("Trying to avoid any traps", trap_data["disarm_difficulty"])
                if success:
                    print("You proceed carefully and avoid triggering any traps.")
                else:
                    trigger_trap(trap_name, trap_data)
            elif action == "2":
                success = perform_skill_check("Searching for traps", trap_data["disarm_difficulty"])
                if success:
                    print(f"You have found and disarmed a trap: {trap_name.replace('_', ' ').title()}.")
                    trap_data["triggered"] = True
                else:
                    print("You failed to find any traps.")
                    trigger_trap(trap_name, trap_data)
            else:
                trigger_trap(trap_name, trap_data)

            location_data["traps"][trap_name] = trap_data
            game_state["locations"][location] = location_data
            save_game_state(game_state)
            break

def move_player(direction=None):
    """
    Moves the player to a new location based on the given direction.
    """
    location = game_state["player"]["location"]
    location_data = game_state["locations"][location]

    if not direction:
        direction = select_direction_to_move(location_data)
        if not direction:
            return

    if direction in location_data["connections"]:
        new_location = location_data["connections"][direction]

        if location_data.get("locked_paths", {}).get(direction, False):
            handle_locked_path(location, direction, new_location)
            return

        game_state["player"]["location_history"].append(location)
        game_state["player"]["location"] = new_location
        print(f"\nYou move {direction} to {new_location.replace('_', ' ').title()}.")
        check_for_traps(new_location)
        save_game_state(game_state)
    else:
        speak("You can't go that way. Here are the directions you can go:")
        for available_direction, connected_location in location_data["connections"].items():
            print(f"- {available_direction.capitalize()}: {connected_location.replace('_', ' ').title()}")

def select_direction_to_move(location_data):
    """
    Allows the player to select a direction to move.
    """
    print("\n=== Select a Direction to Move ===")
    available_directions = list(location_data["connections"].keys())
    for idx, available_direction in enumerate(available_directions, start=1):
        connected_location = location_data["connections"][available_direction]
        locked_status = " (Locked)" if location_data.get("locked_paths", {}).get(available_direction, False) else ""
        print(f"{idx}. {available_direction.capitalize()} -> {connected_location.replace('_', ' ').title()}{locked_status}")

    try:
        choice = int(input("Choose a direction (enter the number or 0 to cancel): "))
        if choice == 0:
            print("Move action canceled.")
            return None
        return available_directions[choice - 1]
    except (ValueError, IndexError):
        print("Invalid choice. Move action canceled.")
        return None

def handle_locked_path(location, direction, new_location):
    """
    Handles the scenario when the player encounters a locked path.
    """
    print(f"The path to {new_location.replace('_', ' ').title()} is locked.")
    key_item = next((item for item in game_state["player"]["inventory"] if item["type"] == "key"), None)
    if not key_item:
        speak("You don't have a key to attempt unlocking this door.")
        return

    while True:
        action = input("What would you like to do? (unlock, inventory, quit): ").lower()

        if action == "unlock":
            if unlock_door(location, direction):
                speak(f"You successfully unlocked the path to {new_location.replace('_', ' ').title()}!")
                move_player(direction)
                break
            else:
                speak("The path remains locked.")
                return
        elif action == "inventory":
            display_inventory()
        elif action == "quit":
            speak("You chose to not unlock the door and remain in your current location.")
            return
        else:
            speak("Invalid action. Try again.")

def move_back():
    """
    Moves the player back to the previous location.
    """
    if game_state["player"]["location_history"]:
        previous_location = game_state["player"]["location_history"].pop()
        game_state["player"]["location"] = previous_location
        print(f"\nYou move back to {previous_location.replace('_', ' ').title()}.")
        save_game_state(game_state)
    else:
        print("You can't go back any further.")

def talk_to_npc():
    """
    Initiates a conversation with an NPC in the current location.
    """
    location = game_state["player"]["location"]
    npcs = game_state["locations"][location].get("npcs", {})

    active_npcs = {npc: data for npc, data in npcs.items() if data.get("status") != "defeated"}

    if not active_npcs:
        print("There are no active NPCs here to talk to.")
        return

    npc_name = select_npc_to_talk(active_npcs)
    if not npc_name:
        return

    npc = game_state["locations"][location]["npcs"][npc_name]

    if npc["status"] == "defeated":
        print(f"{npc_name.replace('_', ' ').title()} is defeated and cannot respond.")
        print(f"{npc_name.replace('_', ' ').title()}: 'I have nothing left to say...'")
        return

    speak(f"\nYou start a conversation with {npc_name.replace('_', ' ').title()}.")

    initiate_conversation(npc_name, npc)

def select_npc_to_talk(active_npcs):
    """
    Allows the player to select an NPC to talk to.
    """
    if len(active_npcs) > 1:
        print("\n=== Select an NPC to Talk ===")
        for idx, npc in enumerate(active_npcs, start=1):
            print(f"{idx}. {npc.replace('_', ' ').title()}")
        try:
            choice = int(input("Choose an NPC to talk to (enter the number or 0 to cancel): ").strip())
            if choice == 0:
                print("Conversation canceled.")
                return None
            return list(active_npcs.keys())[choice - 1]
        except (ValueError, IndexError):
            print("Invalid choice. Conversation canceled.")
            return None
    else:
        return next(iter(active_npcs))

def initiate_conversation(npc_name, npc):
    """
    Manages the conversation loop with an NPC.
    """
    has_previous_conversation = "conversation_history" in npc and npc["conversation_history"]
    if has_previous_conversation:
        print(f"\n=== Previous Conversation with {npc_name.replace('_', ' ').title()} ===\n")
        for dialogue in npc["conversation_history"]:
            print(f"{npc_name.replace('_', ' ').title()}: {dialogue['npc']}")
            print(f"You: {dialogue['player']}\n")

    if "conversation_history" not in npc:
        npc["conversation_history"] = []

    print(f"\n=== Current Conversation with {npc_name.replace('_', ' ').title()} ===\n")
    npc_initial_response = generate_npc_response(npc_name, "start")
    speak(f"{npc_name.replace('_', ' ').title()}: {npc_initial_response}")
    npc["conversation_history"].append({"player": "start", "npc": npc_initial_response})

    while True:
        player_input = input("You: ").strip()

        if player_input.lower() == "stop":
            speak(f"\nYou ended the conversation with {npc_name.replace('_', ' ').title()}.")
            break

        npc_response = generate_npc_response(npc_name, player_input)
        speak(f"{npc_name.replace('_', ' ').title()}: {npc_response}\n")

        npc["conversation_history"].append({"player": player_input, "npc": npc_response})

    save_game_state(game_state)

def search_for_hidden_item():
    """
    Allows the player to search for hidden items in the current location.
    """
    speak("You carefully search the area for hidden items...")

    if perform_skill_check("Searching for hidden items", "challenging"):
        possible_items = [
            {"name": "magic_amulet", "type": "healing", "healing_amount": 30, "description": "A powerful amulet of protection."},
            {"name": "potion", "type": "healing", "healing_amount": 15, "description": "Restores health."},
            {"name": "ancient_scroll", "type": "quest_item", "description": "A scroll with mysterious symbols."},
            {"name": "silver_dagger", "type": "weapon", "attack_boost": 5, "description": "A finely crafted silver dagger."},
            {"name": "key", "type": "key", "description": "A rusty key that seems to fit old locks."},
            {"name": "torch", "type": "tool", "description": "A flickering torch that illuminates the darkness."},
        ]
        found_item = random.choice(possible_items)

        game_state["player"]["inventory"].append(found_item)
        speak(f"Success! You found a hidden item: {found_item['name'].replace('_', ' ').title()}!")
        save_game_state(game_state)
    else:
        speak("Despite your best efforts, you couldn't find anything hidden.")

def unlock_door(location, direction):
    """
    Attempts to unlock a locked door in the specified direction.
    """
    current_location = game_state["locations"].get(location)
    locked_paths = current_location.get("locked_paths", {})

    if not locked_paths.get(direction, False):
        print(f"There is no locked path in the {direction} direction.")
        return False

    speak("You use a key to attempt unlocking the door.")
    key_item = next((item for item in game_state["player"]["inventory"] if item["type"] == "key"), None)
    if key_item:
        game_state["player"]["inventory"].remove(key_item)
    else:
        speak("You don't have a key to attempt unlocking this door.")
        return False

    task_description = f"unlocking the door to {direction}"
    difficulty = "challenging" if "north" in direction else "simple"
    success = perform_skill_check(task_description, difficulty)

    if success:
        current_location["locked_paths"][direction] = False
        save_game_state(game_state)
        speak(f"The door to {direction} unlocks with a satisfying click!")
        return True
    else:
        speak("Despite your efforts, the door remains locked.")
        return False

def drop_item(item_name):
    """
    Drops an item from the player's inventory into the current location.
    """
    inventory = game_state["player"]["inventory"]

    item = next((item for item in inventory if item["name"] == item_name), None)

    if not item:
        speak(f"You don't have '{item_name}' in your inventory.")
        return

    inventory.remove(item)
    speak(f"You dropped {item_name.replace('_', ' ').title()}.")

    current_location = game_state["player"]["location"]
    game_state["locations"][current_location].setdefault("items", {})[item_name] = item

    save_game_state(game_state)

def start_new_game():
    """
    Starts a new game, resetting the game state.
    """
    global game_state
    confirm = input(
        "\nAre you sure you want to start a new game? This will erase your current progress. (yes/no): "
    ).strip().lower()

    if confirm == "yes":
        game_state = initialize_game_state()
        if game_state is None:
            print("Error: Failed to initialize game state.")
            exit_game()
        save_game_state(game_state)
        speak("\nA new game has started!")
    else:
        speak("\nNew game canceled. Continuing with the current progress.")

def generate_location_image():
    """
    Generates an AI image for the current location.
    """
    location = game_state["player"]["location"]
    loc_data = game_state["locations"].get(location)

    if not loc_data:
        print(f"Error: The location '{location}' does not exist in the game state.")
        return

    if "generated_image" in loc_data and isinstance(loc_data["generated_image"], dict):
        generated_data = loc_data["generated_image"]
        if "file_path" in generated_data and "url" in generated_data:
            print(f"Image already generated for {location}:")
            print(f" - Local File: {generated_data['file_path']}")
            print(f" - URL: {generated_data['url']}")
            return
        else:
            print(f"Error: The 'generated_image' field for {location} is invalid. Regenerating...")

    print(f"Generating an image for {location}...")
    description = loc_data.get("generated_description", loc_data["description"])
    generated_data = generate_image_with_deepai(description, location)
    if generated_data:
        loc_data["generated_image"] = generated_data
        game_state["locations"][location] = loc_data
        save_game_state(game_state)
        print(f"Image generated for {location}:")
        print(f" - Local File: {generated_data['file_path']}")
        print(f" - URL: {generated_data['url']}")
    else:
        print("Failed to generate an image for this location.")

def display_goal():
    """
    Displays the player's current quests and their statuses.
    """
    quests = game_state.get("quests", {})
    if not quests:
        print("No active quests available.")
        return

    print("\n=== Quest Details ===")
    for quest_name, quest_data in quests.items():
        status = "Completed" if quest_data.get("completed", False) else "Not Completed"
        print(f"- Quest Name: {quest_name.replace('_', ' ').title()}")
        print(f"  Description: {quest_data.get('description', 'No description available.')}")
        print(f"  Status: {status}")
        print("-" * 40)

def exit_game():
    """
    Exits the game gracefully.
    """
    save_game_state(game_state)
    speak("Exiting the game. Thank you for playing!\n")
    exit()

def show_help():
    """
    Displays a list of available commands to the player.
    """
    print("\n=== Available Commands ===\n")
    print("  new                 - Start a new game, erasing current progress.")
    print("  look                - Describe your current surroundings, including NPCs, items, and possible paths.")
    print("  image               - Generate an image for the current location using AI.")
    print("  stats               - Show your current stats including HP, level, attack power, and XP.")
    print("  inventory           - Display the items you are carrying with details.")
    print("  pick                - Pick up an item from your current location.")
    print("  use                 - Use an item from your inventory (e.g., 'use potion').")
    print("  drop                - Remove an item from your inventory (e.g., 'drop potion').")
    print("  move                - Move to a new location in a specified direction (e.g., 'move north').")
    print("  back                - Return to the previous location.")
    print("  unlock              - Attempt to unlock a locked path if you have a key.")
    print("  talk                - Start a conversation with an NPC in your location.")
    print("  fight               - Engage in combat with an NPC.")
    print("  voice               - Enable or disable voice output for game text.")
    print("  goal                - Display the current quest and progress of the game.")
    print("  map                 - Display the visual map of the game's world.")
    print("  quit                - Exit the game. Progress will be saved.")
    print("\nType 'help' anytime to see this list again.")

def game_loop():
    """
    Main game loop that processes player commands and updates the game state.
    """
    speak("\nWelcome to the AI Dungeon Master Adventure Game!")
    speak("Embark on a journey through dark forests, mystical lakes, and ancient ruins in search of hidden treasures and legendary artifacts.")
    speak("Face challenging enemies, level up your skills, and strategically use items to survive the dangers that await.")
    speak("\nType 'help' to see available commands. Good luck, adventurer!")

    if not check_player_hp():
        return

    while True:
        command = input("\n> ").lower().split()
        if not command:
            continue
        action = command[0]

        if action == "new":
            start_new_game()
        elif action == "quit":
            exit_game()
        elif action == "look":
            describe_location()
        elif action == "stats":
            display_player_stats()
        elif action == "inventory":
            display_inventory()
        elif action == "goal":
            display_goal()
        elif action == "back":
            move_back()
        elif action == "help":
            show_help()
        elif action == "voice":
            toggle_voice()
        elif action == "image":
            generate_location_image()
        elif action == "talk":
            talk_to_npc()
        elif action == "fight":
            engage_combat()
        elif action == "map":
            display_map()
        elif action == "pick":
            if len(command) > 1:
                print("Invalid action. Use 'pick' without specifying an item to select items from the menu.")
            else:
                pick_up_item()
        elif action == "use":
            if len(command) > 1:
                use_item(command[1])
            else:
                print("Specify an item to use. For example, 'use potion'.")
        elif action == "drop":
            if len(command) > 1:
                drop_item(command[1])
            else:
                print("Specify an item to drop. For example, 'drop potion'.")
        elif action == "move":
            if len(command) > 1:
                direction = command[1]
                move_player(direction)
            else:
                move_player()
        elif action == "unlock":
            handle_unlock_command(command)
        else:
            print("Unknown command. Type 'help' to see available actions.")

def handle_unlock_command(command):
    """
    Handles the unlock command to attempt unlocking a path.
    """
    current_location = game_state["player"]["location"]
    if len(command) == 1:
        locked_paths = {
            direction: locked
            for direction, locked in game_state["locations"][current_location].get("locked_paths", {}).items()
            if locked
        }
        if not locked_paths:
            print("There are no locked paths here.")
            return
        print("\nThe following paths are locked:")
        for idx, direction in enumerate(locked_paths.keys(), start=1):
            print(f"{idx}. {direction.capitalize()}")
        try:
            choice = int(input("Select a path to unlock (enter the number): "))
            direction = list(locked_paths.keys())[choice - 1]
        except (ValueError, IndexError):
            print("Invalid selection. Try again.")
            return
    else:
        direction = command[1]
    if direction in game_state["locations"][current_location]["connections"]:
        unlock_door(current_location, direction)
    else:
        print(f"There is no door in the {direction} direction.")

if __name__ == "__main__":
    game_loop()
