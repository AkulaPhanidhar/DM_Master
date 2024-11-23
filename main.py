from state_manager import load_game_state, save_game_state
from ai_interactions import generate_description, initialize_game_state, generate_npc_response, generate_image_with_deepai
import random
import matplotlib.pyplot as plt
import networkx as nx

def check_player_hp():
    player_hp = game_state["player"].get("hp", 0)
    if player_hp <= 0:
        print("Your HP is too low to continue. You must start a new game.")
        while True:
            start_new = input("Would you like to start a new game? (yes/no): ").strip().lower()
            if start_new == "yes":
                start_new_game()
                return True
            elif start_new == "no":
                print("Exiting the game. Thank you for playing!")
                return False
            else:
                print("Invalid choice. Please type 'yes' or 'no'.")
    return True

def check_quest_completion():
    all_completed = True

    for quest_name, quest_data in game_state["quests"].items():
        if not quest_data.get("completed"):
            all_completed = False

            for item in game_state["player"]["inventory"]:
                if item["name"] in quest_name:
                    quest_data["completed"] = True
                    print(f"Quest completed: {quest_data['description']}!")
                    break

            for location_data in game_state["locations"].values():
                npcs = location_data.get("npcs", {})
                for npc_name, npc_data in npcs.items():
                    if npc_name in quest_name and npc_data.get("status") == "defeated":
                        quest_data["completed"] = True
                        print(f"Quest completed: {quest_data['description']}!")
                        break

    save_game_state(game_state)

    if all_completed:
        print("\n=== Game Over ===")
        print("Congratulations, adventurer! You have completed all quests and conquered the realm.")
        print("Your legacy will live on as a true hero of this land!")
        exit_game()

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

def describe_location():
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
    print(loc_data["generated_description"])

    if loc_data.get("npcs"):
        print("\n=== NPCs Here ===")
        for npc, data in loc_data["npcs"].items():
            status = "defeated" if data.get("hp", 0) <= 0 or data.get("status") == "defeated" else "active"
            print(f"- {npc.capitalize()} ({status}) - HP: {data['hp']}, Attack: {data['attack']}" if status == "active" else f"- {npc.capitalize()} ({status})")

    if loc_data.get("items"):
        print("\n=== Items Available ===")
        for item_name, item_data in loc_data["items"].items():
            description = item_data.get("description", "No description available")
            item_type = item_data.get("type", "misc")
            print(f"- {item_name.capitalize()} ({item_type}) - {description}")

    if loc_data.get("connections"):
        print("\n=== Paths Available ===")
        for direction, connected_location in loc_data["connections"].items():
            lock_status = "(locked)" if loc_data.get("locked_paths", {}).get(direction, False) else ""
            print(f"- {direction.capitalize()}: {connected_location.replace('_', ' ').title()} {lock_status}")
    
def perform_skill_check(task_description, difficulty="simple"):
    print(f"\nAttempting: {task_description}")
    roll = random.randint(1, 10)
    print(f"You rolled a {roll}!")

    if difficulty == "simple":
        success_threshold = 3
    elif difficulty == "challenging":
        success_threshold = 6
    elif difficulty == "very_challenging":
        success_threshold = 8
    else:
        raise ValueError(f"Unknown difficulty level: {difficulty}")

    if roll >= success_threshold:
        print(f"Success! You manage to complete the task: {task_description}.")
        return True
    else:
        print(f"Failure. You could not complete the task: {task_description}.")
        return False

def display_player_stats():
    player = game_state["player"]
    print("\n=== Player Stats ===")
    print(f"Level: {player['level']}")
    print(f"HP: {player['hp']}/{player['max_hp']}")
    print(f"Attack: {player['attack']}")
    print(f"XP: {player['xp']}/{player['xp_to_next_level']}")

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
            
            print(f"- {item_name.capitalize()} x{count} {additional_info}")

def pick_up_item(item_name=None):
    location = game_state["player"]["location"]
    items = game_state["locations"][location].get("items", {})

    if not items:
        print("There are no items available to pick up here.")
        return

    if not item_name:
        print("\n=== Select Items to Pick Up ===")
        for idx, item in enumerate(items.keys(), start=1):
            print(f"{idx}. {item.capitalize()}")

        try:
            choice = input("Choose an item (enter the number, 'a' for all, or 0 to cancel): ").strip().lower()
            if choice == "0":
                print("Item pick-up canceled.")
                return
            elif choice == "a":
                if "ancient_artifact" in items:
                    final_boss = game_state["locations"][location]["npcs"].get("final_boss")
                    if final_boss and final_boss["status"] != "defeated":
                        print("You cannot pick up the ancient artifact without defeating the Final Boss!")
                        rest_items = {k: v for k, v in items.items() if k != "ancient_artifact"}
                        if rest_items:
                            prompt = input("\nDo you want to pick the rest of the items? (yes/no): ").strip().lower()
                            if prompt == "yes":
                                picked_items = []
                                for item_name, item_data in list(rest_items.items()):
                                    game_state["player"]["inventory"].append({"name": item_name, **item_data})
                                    picked_items.append(item_name)
                                    items.pop(item_name)
                                print(f"You picked up: {', '.join(picked_items)}.")
                                check_quest_completion()
                                save_game_state(game_state)
                            else:
                                print("Item pick-up canceled.")
                        return

                picked_items = []
                for item_name, item_data in list(items.items()):
                    game_state["player"]["inventory"].append({"name": item_name, **item_data})
                    picked_items.append(item_name)
                    items.pop(item_name)
                print(f"You picked up: {', '.join(picked_items)}.")
                check_quest_completion()
                save_game_state(game_state)
                return
            else:
                choice = int(choice)
                item_name = list(items.keys())[choice - 1]
        except (ValueError, IndexError):
            print("Invalid choice. Pick-up canceled.")
            return

    if item_name == "ancient_artifact":
        final_boss = game_state["locations"][location]["npcs"].get("final_boss")
        if final_boss and final_boss["status"] != "defeated":
            print("You cannot pick up the ancient artifact without defeating the Final Boss!")
            return

    if item_name not in items:
        print(f"No such item '{item_name}' here. Available items: {', '.join(items.keys())}")
        return

    item = items.pop(item_name)
    game_state["player"]["inventory"].append({"name": item_name, **item})
    print(f"You picked up {item_name}.")
    check_quest_completion()
    save_game_state(game_state)

def use_item(item_name):
    inventory = game_state["player"]["inventory"]
    item = next((item for item in inventory if item["name"] == item_name), None)
    
    if not item:
        available_items = ', '.join([item["name"] for item in inventory])
        print(f"You don't have '{item_name}' in your inventory. Available items: {available_items}")
        return

    item_type = item.get("type")

    if item_type == "healing":
        player_hp = game_state["player"]["hp"]
        max_hp = game_state["player"]["max_hp"]
        if player_hp >= max_hp:
            print("Your HP is already at maximum. You don't need to use a healing item now.")
            return
        healing_amount = item.get("healing_amount", 0)
        healed_amount = min(healing_amount, max_hp - player_hp)
        game_state["player"]["hp"] += healed_amount
        print(f"\n=== Item Used ===")
        print(f"You used a {item_name} and restored {healed_amount} HP.")
        inventory.remove(item)

    elif item_type == "weapon":
        weapon_attack = item.get("attack_boost", 5)
        game_state["player"]["attack"] += weapon_attack
        print(f"\n=== Item Equipped ===")
        print(f"You equipped {item_name} and permanently increased your attack by {weapon_attack}.")
        inventory.remove(item)

    elif item_type == "tool" and item_name == "torch":
        print(f"\n=== Item Used ===")
        print(f"You used a {item_name} to search for hidden items!")
        search_for_hidden_item()
        inventory.remove(item)

    elif item_type == "key":
        location = game_state["player"]["location"]
        locked_paths = game_state["locations"][location].get("locked_paths", {})
        if any(locked_paths.values()):
            for path in locked_paths:
                locked_paths[path] = False
            print(f"\n=== Item Used ===")
            print(f"You used {item_name} to unlock all locked paths in this location.")
            inventory.remove(item)
        else:
            print("There is no locked path to use the key on here.")

    else:
        print(f"The {item_name} can't be used directly.")

    save_game_state(game_state)

def gain_xp(amount, npc_name):
    player = game_state["player"]
    player["xp"] += amount
    print(f"You earned {amount} XP for defeating the {npc_name}!")

    if player["xp"] >= player["xp_to_next_level"]:
        level_up()

    save_game_state(game_state)

def level_up():
    player = game_state["player"]
    player["level"] += 1
    player["xp"] -= player["xp_to_next_level"]
    player["xp_to_next_level"] = int(player["xp_to_next_level"] * 1.5)

    if player["max_hp"] < 100:
        player["max_hp"] = min(player["max_hp"] + 10, 100)

    player["hp"] = player["max_hp"]
    player["attack"] += 2

    print(f"\n=== Level Up! ===")
    print(f"You leveled up to Level {player['level']}!")
    print(f"New stats - HP: {player['hp']}, Attack: {player['attack']}, XP to next level: {player['xp_to_next_level']}")
    save_game_state(game_state)

def engage_combat():
    location = game_state["player"]["location"]
    npcs = game_state["locations"][location].get("npcs", {})
    active_npcs = {npc: data for npc, data in npcs.items() if data.get("status") != "defeated"}

    if not active_npcs:
        print("No active NPCs to fight here.")
        return False

    if game_state["player"]["hp"] <= 5:
        print("You are too weak to fight. Heal yourself before engaging in combat.")
        return False

    npc_name = None
    while npc_name is None:
        if len(active_npcs) > 1:
            print("\n=== Select an NPC to Fight ===")
            for idx, npc in enumerate(active_npcs, start=1):
                print(f"{idx}. {npc.capitalize()} (HP: {active_npcs[npc]['hp']}, Attack: {active_npcs[npc]['attack']})")
            try:
                choice = input("Choose an NPC (enter the number or 0 to cancel): ").strip()
                if choice == "0":
                    print("Combat canceled.")
                    return False
                choice = int(choice)
                npc_name = list(active_npcs.keys())[choice - 1]
            except (ValueError, IndexError):
                print("Invalid choice. Let's make the chaos again. Try selecting an NPC.")
        else:
            npc_name = next(iter(active_npcs))

    print(f"\n=== Combat Initiated: {npc_name.capitalize()} ===")
    player = game_state["player"]
    npc = game_state["locations"][location]["npcs"][npc_name]

    npc.setdefault("attack", 5)
    player_base_damage = player["attack"]

    while player["hp"] > 0 and npc["hp"] > 0:
        print(f"\nYour turn! Your HP: {player['hp']}, {npc_name.capitalize()} HP: {npc['hp']}")
        action = input("Choose your action (roll, use [item], inventory, quit): ").lower().split()

        skip_npc_turn = False

        if action[0] == "roll":
            roll = random.randint(1, 6)
            critical_hit = roll == 6
            player_damage = max(1, player_base_damage + roll + (5 if critical_hit else 0))
            npc["hp"] -= player_damage
            print(f"You rolled a {roll}!")
            if critical_hit:
                print("Critical hit!")
            print(f"You hit the {npc_name} for {player_damage} damage! {npc_name.capitalize()} HP: {max(npc['hp'], 0)}")

            if npc["hp"] <= 0:
                print(f"\nYou defeated the {npc_name}!")
                npc["status"] = "defeated"

                base_xp = 10
                hp_xp = npc.get("hp_max", npc["hp"]) // 2
                attack_xp = npc["attack"] * 2
                total_xp = base_xp + hp_xp + attack_xp

                gain_xp(total_xp, npc_name)

                check_quest_completion()

                save_game_state(game_state)
                return True

        elif action[0] == "use" and len(action) > 1:
            item_name = action[1]
            use_item(item_name)
            skip_npc_turn = True

        elif action[0] == "inventory":
            display_inventory()
            skip_npc_turn = True

        elif action[0] == "quit":
            print("You retreated from the combat.")
            save_game_state(game_state)
            return False

        else:
            print("Invalid action. Choose 'roll', 'use [item]', 'inventory', or 'quit'.")
            continue

        if not skip_npc_turn and npc["hp"] > 0:
            print(f"\n{npc_name.capitalize()}'s turn!")
            roll = random.randint(1, 6)
            critical_hit = roll == 6
            npc_damage = max(1, npc["attack"] + roll + (5 if critical_hit else 0))
            player["hp"] -= npc_damage
            print(f"The {npc_name} rolled a {roll}!")
            if critical_hit:
                print(f"{npc_name.capitalize()} lands a critical hit!")
            print(f"The {npc_name} hits you for {npc_damage} damage! Your HP: {max(player['hp'], 0)}")

            if player["hp"] <= 0:
                player["hp"] = 0
                print("\nYou have been defeated. Game Over.")
                save_game_state(game_state)
                exit_game()

        save_game_state(game_state)

    return False
    
def move_player(direction=None):
    location = game_state["player"]["location"]
    location_data = game_state["locations"][location]

    if not direction:
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
                return
            direction = available_directions[choice - 1]
        except (ValueError, IndexError):
            print("Invalid choice. Move action canceled.")
            return

    if direction in location_data["connections"]:
        new_location = location_data["connections"][direction]

        if location_data.get("locked_paths", {}).get(direction, False):
            print(f"The path to {new_location.replace('_', ' ').title()} is locked.")
            key_item = next((item for item in game_state["player"]["inventory"] if item["name"] == "key"), None)
            if not key_item:
                print("You don't have a key to attempt unlocking this door.")
                return

            while True:
                action = input("What would you like to do? (unlock, inventory, quit): ").lower()

                if action == "unlock":
                    if unlock_door(location, direction):
                        print(f"You successfully unlocked the path to {new_location.replace('_', ' ').title()}!")
                        break
                    else:
                        print("The path remains locked.")
                        return
                elif action == "inventory":
                    display_inventory()
                elif action == "quit":
                    print("You chose to not unlock the door and remain in your current location.")
                    return
                else:
                    print("Invalid action. Try again.")

        game_state["player"]["location_history"].append(location)
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

def talk_to_npc():
    location = game_state["player"]["location"]
    npcs = game_state["locations"][location].get("npcs", {})

    active_npcs = {npc: data for npc, data in npcs.items() if data.get("status") != "defeated"}

    if not active_npcs:
        print("There are no active NPCs here to talk to.")
        return

    if len(active_npcs) > 1:
        print("\n=== Select an NPC to Talk ===")
        for idx, npc in enumerate(active_npcs, start=1):
            print(f"{idx}. {npc.capitalize()}")
        try:
            choice = int(input("Choose an NPC to talk to (enter the number or 0 to cancel): ").strip())
            if choice == 0:
                print("Conversation canceled.")
                return
            npc_name = list(active_npcs.keys())[choice - 1]
        except (ValueError, IndexError):
            print("Invalid choice. Conversation canceled.")
            return
    else:
        npc_name = next(iter(active_npcs))

    npc = game_state["locations"][location]["npcs"][npc_name]

    if npc["status"] == "defeated":
        print(f"{npc_name.capitalize()} is defeated and cannot respond.")
        print(f"{npc_name.capitalize()}: 'I have nothing left to say...'")
        return

    print(f"\nYou start a conversation with {npc_name.capitalize()}.")

    has_previous_conversation = "conversation_history" in npc and npc["conversation_history"]
    if has_previous_conversation:
        print(f"\n=== Previous Conversation with {npc_name.capitalize()} ===")
        for dialogue in npc["conversation_history"]:
            print(f"You: {dialogue['player']}")
            print(f"{npc_name.capitalize()}: {dialogue['npc']}")

    if "conversation_history" not in npc:
        npc["conversation_history"] = []

    if has_previous_conversation:
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

def search_for_hidden_item():
    torch_item = next((item for item in game_state["player"]["inventory"] if item["name"] == "torch"), None)
    if not torch_item:
        print("You need a torch to search for hidden items in the dark.")
        return

    print("You carefully search the area for hidden items...")

    if perform_skill_check("Searching for hidden items", "challenging"):
        possible_items = [
            {"name": "magic_amulet", "type": "healing", "healing_amount": 30, "description": "A powerful amulet of protection."},
            {"name": "potion", "type": "healing", "healing_amount": 15, "description": "Restores health."},
            {"name": "ancient_scroll", "type": "quest", "description": "A scroll with mysterious symbols."},
            {"name": "silver_dagger", "type": "weapon", "attack" : 5, "description": "A finely crafted silver dagger."},
            {"name": "key", "type": "key", "description": "A rusty key that seems to fit old locks."},
            {"name": "torch", "type": "tool", "description": "A flickering torch that illuminates the darkness."}
        ]
        found_item = random.choice(possible_items)

        game_state["player"]["inventory"].append(found_item)
        print(f"Success! You found a hidden item: {found_item['name'].capitalize()}!")
        save_game_state(game_state)
    else:
        print("Despite your best efforts, you couldn't find anything hidden.")
        
def skill_check(difficulty):
    roll = random.randint(1, 10)
    if difficulty == "simple" and roll >= 3:
        return "success"
    elif difficulty == "challenging" and roll >= 6:
        return "success"
    return "failure"

def unlock_door(location, direction):
    current_location = game_state["locations"].get(location)
    locked_paths = current_location.get("locked_paths", {})

    if not locked_paths.get(direction, False):
        print(f"There is no locked path in the {direction} direction.")
        return False

    print("You use a key to attempt unlocking the door.")
    game_state["player"]["inventory"] = [
        item for item in game_state["player"]["inventory"] if item["name"] != "key"
    ]

    task_description = f"unlocking the door to {direction}"
    difficulty = "challenging" if "north" in direction else "simple"
    success = perform_skill_check(task_description, difficulty)

    if success:
        current_location["locked_paths"][direction] = False
        save_game_state(game_state)
        print(f"The door to {direction} unlocks with a satisfying click!")
        return True
    else:
        print("Despite your efforts, the door remains locked.")
        return False

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
        print("A new game has started!")
    else:
        print("\nNew game canceled. Continuing with the current progress.")
        
def generate_location_image():
    location = game_state["player"]["location"]
    loc_data = game_state["locations"].get(location)

    if not loc_data:
        print(f"Error: The location '{location}' does not exist in the game state.")
        return

    if "generated_image" in loc_data:
        generated_data = loc_data["generated_image"]

        if isinstance(generated_data, dict) and "file_path" in generated_data and "url" in generated_data:
            print(f"Image already generated for {location}:")
            print(f" - Local File: {generated_data['file_path']}")
            print(f" - URL: {generated_data['url']}")
        else:
            print(f"Error: The 'generated_image' field for {location} is invalid. Regenerating...")
            description = loc_data.get("generated_description", loc_data["description"])
            generated_data = generate_image_with_deepai(description, location)
            if generated_data:
                loc_data["generated_image"] = generated_data
                game_state["locations"][location] = loc_data
                save_game_state(game_state)
                print(f"Image regenerated for {location}:")
                print(f" - Local File: {generated_data['file_path']}")
                print(f" - URL: {generated_data['url']}")
            else:
                print("Failed to regenerate an image for this location.")
    else:
        print(f"Generating an image for {location}...")
        description = loc_data.get("generated_description", loc_data["description"])
        generated_data = generate_image_with_deepai(description, location)
        if generated_data:
            loc_data["generated_image"] = generated_data
            game_state["locations"][location] = loc_data
            save_game_state(game_state)
            print(f"Image regenerated for {location}:")
            print(f" - Local File: {generated_data['file_path']}")
            print(f" - URL: {generated_data['url']}")
        else:
            print("Failed to generate an image for this location.")

def display_quest():
    quests = game_state.get("quests", {})
    if not quests:
        print("No active quests available.")
        return

    print("\n=== Quest Details ===")
    for quest_name, quest_data in quests.items():
        status = "Completed" if quest_data.get("completed", False) else "Not Completed"
        print(f"- Quest Name: {quest_name.capitalize()}")
        print(f"  Description: {quest_data.get('description', 'No description available.')}")
        print(f"  Status: {status}")
        print("-" * 40)
        
def exit_game():
    print("Exiting the game. Thank you for playing!\n")
    exit()
    
def show_help():
    print("\n=== Available Commands ===")
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
    print("  goal                - Display the current quest and progress of the game.")
    print("  map                 - Display the visual map of the game's world.")
    print("  quit                - Exit the game. Progress will be saved.")
    print("\nType 'help' anytime to see this list again.")

def game_loop():
    print("Welcome to the AI Dungeon Master Adventure Game!")
    print("Embark on a journey through dark forests, mystical lakes, and ancient ruins in search of hidden treasures and legendary artifacts.")
    print("Face challenging enemies, level up your skills, and strategically use items to survive the dangers that await.")
    print("\nType 'help' to see available commands. Good luck, adventurer!")
    
    if not check_player_hp():
        return

    in_combat = False

    while True:
        command = input("\n> ").lower().split()
        action = command[0]
        
        if action == "new":
            start_new_game()
            continue
        if action == "quit":
            print("Thanks for playing!")
            break
        elif action == "look" and not in_combat:
            describe_location()
        elif action == "stats" and not in_combat:
            display_player_stats()
        elif action == "inventory" and not in_combat:
            display_inventory()
        elif action == "goal" and not in_combat:
            display_quest()
        elif action == "back" and not in_combat:
            move_back()
        elif action == "help" and not in_combat:
            show_help()
        elif action == "image" and not in_combat:
            generate_location_image()
        elif action == "talk" and not in_combat:
            talk_to_npc()
        elif action == "fight" and not in_combat:
            engage_combat()
        elif action == "map":
            display_map()
        elif action == "pick" and not in_combat:
            if len(command) > 1:
                print("Invalid action. Use 'pick' without specifying an item to select items from the menu.")
            else:
                pick_up_item()
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
                move_player()
        elif action == "unlock":
            current_location = game_state["player"]["location"]
            if len(command) == 1:
                locked_paths = {
                    direction: locked
                    for direction, locked in game_state["locations"][current_location].get("locked_paths", {}).items()
                    if locked
                }
                if not locked_paths:
                    print("There are no locked paths here.")
                    continue
                print("\nThe following paths are locked:")
                for idx, direction in enumerate(locked_paths.keys(), start=1):
                    print(f"{idx}. {direction.capitalize()}")
                try:
                    choice = int(input("Select a path to unlock (enter the number): "))
                    direction = list(locked_paths.keys())[choice - 1]
                except (ValueError, IndexError):
                    print("Invalid selection. Try again.")
                    continue
            else:
                direction = command[1]
            if direction in game_state["locations"][current_location]["connections"]:
                unlock_door(current_location, direction)
            else:
                print(f"There is no door in the {direction} direction.")
        else:
            print("Unknown command. Type 'help' to see available actions.")

if __name__ == "__main__":
    game_loop()
