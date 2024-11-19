from state_manager import load_game_state, save_game_state
from ai_interactions import generate_description, initialize_game_state, generate_npc_response
import random
import matplotlib.pyplot as plt
import networkx as nx

def check_quest_completion():
    """
    Dynamically checks and updates the status of all active quests
    based on the player's inventory and defeated NPCs.
    """
    for quest_name, quest_data in game_state["quests"].items():
        if not quest_data.get("completed"):
            for item in game_state["player"]["inventory"]:
                if item["name"] in quest_name:
                    quest_data["completed"] = True
                    print(f"Quest completed: {quest_data['description']}!")
                    break

            for location_data in game_state["locations"].items():
                npcs = location_data.get("npcs", {})
                for npc_name, npc_data in npcs.items():
                    if npc_name in quest_name and npc_data.get("status") == "defeated":
                        quest_data["completed"] = True
                        print(f"Quest completed: {quest_data['description']}!")
                        break

    save_game_state(game_state)

def load_or_initialize_game():
    game_state = load_game_state()
    if game_state is None:
        game_state = initialize_game_state()
        save_game_state(game_state)
    return game_state

game_state = load_or_initialize_game()

def extract_locations_from_game_state(game_state):
    locations = {}
    for location_name, location_data in game_state["locations"].items():
        locations[location_name] = {
            "description": location_data["description"],
            "connections": location_data["connections"]
        }
    return locations

locations = extract_locations_from_game_state(game_state)

def display_map():
    G = nx.DiGraph()

    for location, data in game_state["locations"].items():
        G.add_node(location, label=data["description"])
        for direction, connected_location in data["connections"].items():
            G.add_edge(location, connected_location, direction=direction)

    pos = nx.spring_layout(G, seed=42)
    current_location = game_state["player"]["location"]

    plt.figure(figsize=(14, 8))
    node_colors = ["#ffa500" if node == current_location else "#87ceeb" for node in G.nodes]

    node_sizes = [
        max(6000, len(node.replace("_", " ").title()) * 300) for node in G.nodes
    ]

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
        arrowsize=20
    )

    edge_labels = {(u, v): data["direction"].capitalize() for u, v, data in G.edges(data=True)}
    nx.draw_networkx_edge_labels(
        G,
        pos,
        edge_labels=edge_labels,
        font_size=9,
        font_color="#555",
        label_pos=0.5
    )

    node_labels = {node: node.replace("_", " ").title() for node in G.nodes}
    for node, (x, y) in pos.items():
        text = node_labels[node]
        plt.text(
            x,
            y,
            text,
            fontsize=9,
            color="#222",
            bbox=dict(
                facecolor="white",
                edgecolor="#333",
                boxstyle="round,pad=0.5",
                lw=1
            ),
            ha="center",
            va="center",
            clip_on=True
        )

    plt.gca().set_facecolor("#f0f0f0")
    plt.title(
        "Game Map: Locations and Connections",
        fontsize=14,
        fontweight="bold",
        color="#333",
        pad=20
    )
    plt.axis("off")
    plt.show()
    
def save_progress(message=None):
    """Saves the game state and optionally prints a checkpoint message."""
    save_game_state(game_state)
    if message:
        print(" ")
        print(message)

def describe_location(location):
    loc_data = game_state["locations"].get(location, {})
    
    print(f"\n=== Current Location ===")
    print(location.replace('_', ' ').title())

    if "generated_description" not in loc_data:
        prompt = f"{locations[location]['description']} Give a brief, atmospheric paragraph in D&D style, no more than 5 sentences."
        loc_data["generated_description"] = generate_description(prompt)
        game_state["locations"][location] = loc_data
        save_game_state(game_state)

    print("\n=== Location Description ===")
    print(loc_data["generated_description"])

    if loc_data.get("npcs"):
        print("\n=== NPCs Here ===")
        for npc, data in loc_data["npcs"].items():
            status = "defeated" if data.get("hp", 0) <= 0 or data.get("status") == "defeated" else "active"
            if status == "defeated":
                print(f"- {npc.capitalize()} ({status})")
            else:
                print(f"- {npc.capitalize()} ({status}) - HP: {data['hp']}, Attack: {data['attack']}")
    
    if loc_data.get("items"):
        print("\n=== Items Available ===")
        for item_name, item_data in loc_data["items"].items():
            description = item_data.get("description", "No description available")
            if item_data["type"] == "healing":
                print(f"- {item_name.capitalize()} (Healing) - Restores {item_data['healing_amount']} HP: {description}")
            elif item_data["type"] == "key":
                print(f"- {item_name.capitalize()} (Key) - Can unlock certain doors: {description}")
            elif item_data["type"] == "weapon":
                print(f"- {item_name.capitalize()} (Weapon) - Increases attack power: {description}")
            else:
                print(f"- {item_name.capitalize()} - {description}")
    
    if locations[location].get("connections"):
        print("\n=== Paths Available ===")
        for direction, connected_location in locations[location]["connections"].items():
            lock_status = "(locked)" if loc_data.get("locked_paths", {}).get(direction, False) else ""
            print(f"- {direction.capitalize()}: {connected_location.replace('_', ' ').title()} {lock_status}")
    
    print("\n")

def display_player_stats():
    player = game_state["player"]
    print("\n=== Player Stats ===")
    print(f"Level: {player['level']}")
    print(f"HP: {player['hp']}/{player['max_hp']}")
    print(f"Attack: {player['attack']}")
    print(f"XP: {player['xp']}/{player['xp_to_next_level']}")
    print("\n")

def display_inventory():
    inventory = game_state["player"]["inventory"]
    print("\n=== Inventory ===")
    
    if not inventory:
        print("Your inventory is empty.")
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
            description = (
                f"(Healing) - Restores {item_data['healing_amount']} HP when used"
                if item_data["type"] == "healing" else ""
            )
            print(f"- {item_name.capitalize()} x{count} {description}")
    print("\n")

def pick_up_item(item_name):
    location = game_state["player"]["location"]
    items = game_state["locations"][location].get("items", {})

    if not items:
        print("There are no items available to pick up here.")
        return

    if item_name not in items:
        print(f"No such item '{item_name}' here. Available items: {', '.join(items.keys())}")
        return

    if item_name == "ancient_artifact":
        final_boss = game_state["locations"][location]["npcs"].get("final_boss")
        if final_boss and final_boss["status"] != "defeated":
            print("You cannot pick up the ancient artifact without defeating the Final Boss!")
            return

    item = items.pop(item_name)
    game_state["player"]["inventory"].append({"name": item_name, **item})
    save_game_state(game_state)
    print(f"You picked up {item_name}.")

def use_item(item_name):
    inventory = game_state["player"]["inventory"]

    item = next((item for item in inventory if item["name"] == item_name), None)
    
    if not item:
        available_items = ', '.join([item["name"] for item in inventory])
        print(f"You don't have '{item_name}' in your inventory. Available items: {available_items}")
        return

    if item["type"] == "healing":
        player_hp = game_state["player"]["hp"]
        max_hp = game_state["player"]["max_hp"]
        if player_hp >= max_hp:
            print("Your HP is already at maximum. You don't need to use a healing item now.")
            return
        healing_amount = item.get("healing_amount", 0)
        healed_amount = min(healing_amount, max_hp - player_hp)
        game_state["player"]["hp"] = player_hp + healed_amount
        print(f"\n=== Item Used ===")
        print(f"You used a {item_name} and gained {healed_amount} HP.")
        
        inventory.remove(item)

    elif item["type"] == "key":
        location = game_state["player"]["location"]
        locked_paths = game_state["locations"][location].get("locked_paths", {})
        
        if any(locked_paths.values()):
            for path in locked_paths:
                locked_paths[path] = False
            print(f"\n=== Item Used ===")
            print(f"You used {item_name} to unlock the path(s).")
            
            inventory.remove(item)
        else:
            print("There is no locked path to use the key on here.")
            
    elif item["type"] == "torch":
        location = game_state["player"]["location"]
        hidden_items = game_state["locations"][location].get("hidden_items", [])
        if hidden_items:
            print(f"\n=== Item Used ===")
            print(f"You used a {item_name} to reveal hidden items!")
            for hidden_item in hidden_items:
                game_state["locations"][location]["items"][hidden_item["name"]] = hidden_item
            game_state["locations"][location]["hidden_items"] = []
            inventory.remove(item)
        else:
            print("There are no hidden items to reveal here.")
            
    elif item["type"] == "shield":
        game_state["player"]["defense"] = game_state["player"].get("defense", 0) + item.get("defense_boost", 2)
        print(f"\n=== Item Used ===")
        print(f"You used a {item_name} and gained a defense boost.")
        inventory.remove(item)
        
    elif item["type"] == "magic_water":
        player_hp = game_state["player"]["hp"]
        max_hp = game_state["player"]["max_hp"]
        healing_amount = item.get("healing_amount", 20)
        healed_amount = min(healing_amount, max_hp - player_hp)
        game_state["player"]["hp"] += healed_amount
        game_state["player"]["xp"] += 10
        print(f"\n=== Item Used ===")
        print(f"You used {item_name}, gained {healed_amount} HP, and earned 10 XP.")
        inventory.remove(item)
        
    elif item["type"] == "weapon":
        weapon_attack = item.get("attack_boost", 5)
        game_state["player"]["attack"] += weapon_attack
        print(f"\n=== Item Equipped ===")
        print(f"You equipped {item_name} and permanently increased your attack by {weapon_attack}.")
        inventory.remove(item)
        
    else:
        print(f"The {item_name} can't be used directly.")

    save_game_state(game_state)

def gain_xp(amount):
    player = game_state["player"]
    player["xp"] += amount
    print(f"\nYou gained {amount} XP!")

    if player["xp"] >= player["xp_to_next_level"]:
        level_up()

    save_game_state(game_state)

def level_up():
    player = game_state["player"]
    player["level"] += 1
    player["xp"] -= player["xp_to_next_level"]
    player["xp_to_next_level"] = int(player["xp_to_next_level"] * 1.5)

    if player["max_hp"] < 100:
        player["max_hp"] = min(player["max_hp"] + 5, 100)

    player["hp"] = player["max_hp"]
    player["attack"] += 1

    print(f"\n=== Level Up! ===")
    print(f"You leveled up to Level {player['level']}!")
    print(f"New stats - HP: {player['hp']}, Attack: {player['attack']}, XP to next level: {player['xp_to_next_level']}")
    save_game_state(game_state)

def engage_combat(npc_name):
    print(f"\n=== Combat Initiated: {npc_name.capitalize()} ===")
    player = game_state["player"]
    npc = game_state["locations"][game_state["player"]["location"]]["npcs"][npc_name]

    while player["hp"] > 0 and npc["hp"] > 0:
        action = input("Choose your action (attack, defend, use [item], quit): ").lower().split()

        if action[0] == "attack":
            player_damage = player["attack"]
            if random.random() < 0.15:
                player_damage *= 2
                print("Critical Hit!")
            elif random.random() < 0.05:
                npc["status"] = "stunned"
                print(f"The {npc_name} is stunned and cannot attack next turn!")

            npc["hp"] -= player_damage
            print(f"You hit the {npc_name} for {player_damage} damage! {npc_name.capitalize()} HP: {max(npc['hp'], 0)}")

            if npc["hp"] <= 0:
                print(f"\nYou defeated the {npc_name}!")
                npc["status"] = "defeated"
                gain_xp(10)
                save_progress("Defeated an enemy")
                check_quest_completion()

                if npc_name == "final_boss":
                    print("\nCongratulations! You have defeated the Final Boss and completed the game!")
                    print("You retrieve the ancient artifact, marking your success as a true adventurer.")
                    save_progress("Game completed")
                return True

        elif action[0] == "defend":
            npc_damage = max(1, npc["attack"] - random.randint(1, 3))
            print(f"The {npc_name} attacks, but your defense absorbs some damage! You take {npc_damage} damage.")
            player["hp"] -= npc_damage

        elif action[0] == "use" and len(action) > 1:
            item_name = action[1]
            use_item(item_name)

        elif action[0] == "quit":
            print("You have retreated from combat.")
            return False

        else:
            print("Invalid action. Choose 'attack', 'defend', 'use [item]', or 'quit'.")
            continue
        print(f"\nYour HP: {max(player['hp'], 0)}\n")
        if npc["hp"] > 0 and npc.get("status") != "stunned":
            npc_damage = npc["attack"]
            if random.random() < 0.2:
                npc_damage *= 2
                print("The enemy lands a critical hit!")
            elif random.random() < 0.1:
                npc_damage = 0
                print("The enemy missed!")

            player["hp"] -= npc_damage
            print(f"The {npc_name} hits you for {npc_damage} damage! Your HP: {max(player['hp'], 0)}")

            if player["hp"] <= 0:
                print("\nYou have been defeated. Game Over.")
                save_progress("Player defeated")
                return True
        elif npc.get("status") == "stunned":
            print(f"The {npc_name} is stunned and cannot attack this turn.")
            npc["status"] = "active"

        save_game_state(game_state)

    return False
    
def move_player(direction):
    current_location = game_state["player"]["location"]
    location_data = game_state["locations"][current_location]

    if direction in location_data["connections"]:
        new_location = location_data["connections"][direction]
        
        if location_data.get("locked_paths", {}).get(direction, False):
            has_key = any(item["name"] == "key" and not item.get("used", False) for item in game_state["player"]["inventory"])
            if has_key:
                use_key = input(f"The path to {new_location.replace('_', ' ').title()} is locked. Do you want to use a key to unlock it? (yes/no): ").lower()
                if use_key == "yes":
                    location_data["locked_paths"][direction] = False
                    for item in game_state["player"]["inventory"]:
                        if item["name"] == "key" and not item.get("used", False):
                            item["used"] = True
                            break
                    print(f"You used a key to unlock the path to {new_location.replace('_', ' ').title()}!")
                else:
                    print("You chose not to use the key. The path remains locked.")
                    return
            else:
                print(f"The path to {new_location.replace('_', ' ').title()} is locked and you have no key to unlock it.")
                return

        game_state["player"]["location_history"].append(current_location)
        game_state["player"]["location"] = new_location
        print(f"\nYou move {direction} to {new_location.replace('_', ' ').title()}.")
        save_game_state(game_state)
    else:
        print("You can't go that way. Here are the directions you can go:")
        for available_direction, connected_location in location_data["connections"].items():
            print(f"- {available_direction.capitalize()}: {connected_location.replace('_', ' ').title()}")
        
def move_back():
    if game_state["player"]["location_history"]:
        previous_location = game_state["player"]["location_history"].pop()
        game_state["player"]["location"] = previous_location
        print(f"\nYou move back to {previous_location.replace('_', ' ').title()}.")
        save_game_state(game_state)
    else:
        print("You can't go back any further.")

def talk_to_npc(npc_name):
    location = game_state["player"]["location"]
    npc = game_state["locations"][location]["npcs"].get(npc_name)

    if not npc:
        print("No such NPC to talk to here.")
        return

    if npc["status"] == "defeated":
        print(f"{npc_name.capitalize()} is defeated and cannot respond.")
        print(f"{npc_name.capitalize()}: 'I have nothing left to say...'")
        return

    print(f"\nYou start a conversation with {npc_name.capitalize()}.")

    if "conversation_history" in npc and npc["conversation_history"]:
        print(f"\n=== Previous Conversation with {npc_name.capitalize()} ===")
        for dialogue in npc["conversation_history"]:
            print(f"You: {dialogue['player']}")
            print(f"{npc_name.capitalize()}: {dialogue['npc']}")

    if "conversation_history" not in npc:
        npc["conversation_history"] = []

    print(f"\n=== Current Conversation with {npc_name.capitalize()} ===")
    npc_initial_response = generate_npc_response(npc_name, "start")
    print(f"{npc_name.capitalize()}: {npc_initial_response}")
    npc["conversation_history"].append({"player": "start", "npc": npc_initial_response})

    while True:
        player_input = input("You: ").strip()

        if player_input.lower() == "stop":
            print(f"\nYou ended the conversation with {npc_name.capitalize()}.")
            break

        npc_response = generate_npc_response(npc_name, player_input)
        print(f"{npc_name.capitalize()}: {npc_response}")

        npc["conversation_history"].append({"player": player_input, "npc": npc_response})

    save_game_state(game_state)
        
def skill_check(difficulty):
    roll = random.randint(1, 10)
    if difficulty == "simple" and roll >= 3:
        return "success"
    elif difficulty == "challenging" and roll >= 6:
        return "success"
    return "failure"

def unlock_door():
    if not any(item["name"] == "key" for item in game_state["player"]["inventory"]):
        print("You need a key to unlock any door.")
        return

    current_location = game_state["player"]["location"]
    location_data = game_state["locations"].get(current_location, {})
    locked_paths = location_data.get("locked_paths", {})

    locked_directions = [direction for direction, is_locked in locked_paths.items() if is_locked]

    if not locked_directions:
        print("There are no locked paths here.")
        return

    if len(locked_directions) == 1:
        direction = locked_directions[0]
        use_key_for_unlock()
        locked_paths[direction] = False
        print(f"The door to the {direction} has been unlocked!")
        return

    print("Multiple paths are locked. Choose a direction to unlock:")
    for direction in locked_directions:
        print(f"- {direction.capitalize()}")

    chosen_direction = input("Enter direction to unlock: ").lower()

    if chosen_direction in locked_directions:
        use_key_for_unlock()
        locked_paths[chosen_direction] = False
        print(f"The door to the {chosen_direction} has been unlocked!")
    else:
        print("Invalid direction. Please try again.")

def use_key_for_unlock():
    inventory = game_state["player"]["inventory"]
    for item in inventory:
        if item["name"] == "key":
            inventory.remove(item)
            save_game_state(game_state)
            return True
    return False

def perform_action_with_skill_check(action_type):
    if action_type == "find_hidden_item":
        result = skill_check("challenging")
        if result == "success":
            location = game_state["player"]["location"]
            hidden_item = game_state["locations"][location].get("hidden_item", None)
            
            if hidden_item:
                print(f"You found a hidden item: {hidden_item['name']}!")
                game_state["player"]["inventory"].append(hidden_item)
                del game_state["locations"][location]["hidden_item"]
                save_game_state(game_state)
            else:
                print("There seems to be nothing hidden here.")
        else:
            print("You search around but find nothing of interest.")

def select_npc():
    location = game_state["player"]["location"]
    npcs = game_state["locations"][location].get("npcs", {})

    active_npcs = {npc: data for npc, data in npcs.items() if data.get("status") != "defeated"}

    if not active_npcs:
        print("No active NPCs to fight here.")
        return None

    print("\n=== Select NPC to Fight ===")
    for i, npc in enumerate(active_npcs, 1):
        print(f"{i}. {npc.capitalize()} (HP: {active_npcs[npc]['hp']}, Attack: {active_npcs[npc]['attack']})")

    choice = input("Enter the number of the NPC you want to fight: ").strip()
    
    try:
        selected_index = int(choice) - 1
        selected_npc = list(active_npcs.keys())[selected_index]
        return selected_npc
    except (ValueError, IndexError):
        print("Invalid choice. No NPC selected.")
        return None

def drop_item(item_name):
    inventory = game_state["player"]["inventory"]

    item = next((item for item in inventory if item["name"] == item_name), None)
    
    if not item:
        print(f"You don't have '{item_name}' in your inventory.")
        return

    inventory.remove(item)
    print(f"You dropped {item_name}.")
    
    current_location = game_state["player"]["location"]
    if item_name not in game_state["locations"][current_location].get("items", {}):
        game_state["locations"][current_location].setdefault("items", {})[item_name] = item

    save_game_state(game_state)
        
def start_new_game():
    global game_state
    confirm = input("Are you sure you want to start a new game? This will erase your current progress. (yes/no): ").strip().lower()
    
    if confirm == "yes":
        game_state = initialize_game_state()
        save_game_state(game_state)
        save_progress("A new game has started!")
    else:
        print("\nNew game canceled. Continuing with the current progress.")
    
def show_help():
    print("\n=== Available Commands ===")
    print("\nNon-Combat Commands:")
    print("  new                 - Start a new game, erasing current progress.")
    print("  look                - Describe your current surroundings, including NPCs, items, and possible paths.")
    print("  stats               - Show your current stats including HP, level, attack power, and XP.")
    print("  inventory           - Display the items you are carrying with details.")
    print("  pick [item]         - Pick up an item from your current location (e.g., 'pick potion').")
    print("  use [item]          - Use an item from your inventory (e.g., 'use potion').")
    print("  drop [item]         - Remove an item from your inventory (e.g., 'drop potion').")
    print("  move [direction]    - Move to a new location in a specified direction (e.g., 'move north').")
    print("  back                - Return to the previous location.")
    print("  unlock_door         - Attempt to unlock a locked path if you have a key.")
    print("  search              - Search for hidden items in the area.")
    print("  talk [npc]          - Start a conversation with an NPC in your location (e.g., 'talk goblin').")
    print("                        Type 'stop' during a conversation to end it.")
    print("  map                 - Display the visual map of the game's world.")
    print("  quit                - Exit the game. Progress will be saved.")

    print("\nCombat Commands:")
    print("  fight [npc]         - Engage in combat with an NPC (e.g., 'fight goblin').")
    print("  attack              - Attack the enemy during combat.")
    print("  defend              - Defend against the enemy's next attack, reducing incoming damage.")
    print("  use [item]          - Use an item from your inventory during combat (e.g., 'use potion').")
    print("  quit                - Retreat from combat, exiting the combat mode.")

    print("\n=== Goal ===")
    print("Your objective is to defeat the final boss and retrieve the ancient artifact.")
    print("Survive the enemies, gather items, and explore all areas to complete the game.")

    print("\nType 'help' anytime to see this list again.")

def game_loop():
    print("Welcome to the Dungeon Master Adventure Game!")
    print("Embark on a journey through dark forests, mystical lakes, and ancient ruins in search of hidden treasures and legendary artifacts.")
    print("Face challenging enemies, level up your skills, and strategically use items to survive the dangers that await.")
    print("To complete the game, seek out and defeat the Final Boss guarding the ancient artifact.")
    print("\nType 'help' to see available commands. Good luck, adventurer!")

    in_combat = False
    combat_target = None

    while True:
        command = input("\n> ").lower().split()
        action = command[0]
        
        if action == "new":
            start_new_game()
            continue

        if in_combat:
            if action == "attack":
                result = engage_combat(combat_target)
                if result:
                    in_combat = False
                continue
            elif action == "defend":
                result = engage_combat(combat_target, defend=True)
                if result:
                    in_combat = False
                continue
            elif action == "use" and len(command) > 1:
                item_name = command[1]
                use_item(item_name)
                result = engage_combat(combat_target)
                if result:
                    in_combat = False
                continue
            elif action == "quit":
                print("You have retreated from combat.")
                in_combat = False
                continue
            else:
                print("You are in combat! Use 'attack', 'defend', 'use [item]', or 'quit' to continue.")
                continue

        if action == "quit":
            print("Thanks for playing!")
            break
        elif action == "look" and not in_combat:
            describe_location(game_state["player"]["location"])
        elif action == "stats" and not in_combat:
            display_player_stats()
        elif action == "inventory" and not in_combat:
            display_inventory()
        elif action == "pick" and not in_combat:
            if len(command) > 1:
                pick_up_item(command[1])
            else:
                print("Specify an item to pick up.")
        elif action == "use":
            if len(command) > 1:
                use_item(command[1])
            else:
                print("Specify an item to use. For example, 'use potion'.")
        elif action == "drop" and not in_combat:
            if len(command) > 1:
                drop_item(command[1])
            else:
                print("Specify an item to drop. For example, 'drop potion'.")
        elif action == "move" and not in_combat:
            if len(command) > 1:
                direction = command[1]
                move_player(direction)
            else:
                print("Specify a direction to move (e.g., 'move north').")
        elif action == "back" and not in_combat:
            move_back()
        elif action == "fight":
            location = game_state["player"]["location"]
            npcs = game_state["locations"][location].get("npcs", {})
            active_npcs = {npc: data for npc, data in npcs.items() if data.get("status") != "defeated"}
            if not active_npcs:
                print("No active NPCs to fight here.")
                continue
            if len(active_npcs) == 1:
                combat_target = next(iter(active_npcs))
                engage_combat(combat_target)
            else:
                combat_target = select_npc()
                if combat_target:
                    print(f"\n=== Combat Initiated: {combat_target.capitalize()} ===")
                    engage_combat(combat_target)
        elif action == "map":
            display_map()
        elif action == "unlock_door" and not in_combat:
            unlock_door()
        elif action == "search" and not in_combat:
            perform_action_with_skill_check("find_hidden_item")
        elif action == "help":
            show_help()
        elif action == "talk":
            location = game_state["player"]["location"]
            npcs = game_state["locations"][location].get("npcs", {})

            active_npcs = {npc: data for npc, data in npcs.items() if data.get("status") != "defeated"}
            if not active_npcs:
                print("There are no active NPCs here to talk to.")
                continue

            if len(active_npcs) == 1:
                npc_name = next(iter(active_npcs))
                talk_to_npc(npc_name)
            else:
                npc_name = select_npc(active_npcs)
                if npc_name:
                    talk_to_npc(npc_name)
                else:
                    print("No NPC selected to talk to.")

if __name__ == "__main__":
    game_loop()
