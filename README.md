# AI Dungeon Master Adventure Game

A Dungeons & Dragons-inspired interactive text-based adventure game where players explore a mystical world, battle NPCs, complete quests, and uncover hidden treasures. The game features a dynamic map, conversational NPCs, and rich, procedurally generated game states.

---

## Features

### **Core Features**

- **Dynamic Gameplay**: Explore various interconnected locations with NPCs, quests, and items.
- **Rich World**: Locations, quests, and NPCs are procedurally generated at the start of a new game.
- **Combat System**: Engage in battles with NPCs using a dice-based combat system influenced by player stats, critical hits, and NPC special abilities.
- **NPC Conversations**: Interact with NPCs, receiving context-aware responses based on the current game state.
- **Dynamic Map**: Visualize the game world with an interactive, auto-updating map.
- **Quests**: Complete quests such as retrieving mystical items or defeating powerful bosses.
- **Inventory Management**: Collect, use, and drop items such as potions, keys, and weapons.
- **State Persistence**: Game state is saved and loaded automatically for continuity.

---

## Recent Updates

### **Image Generation**

- **DALL-E Integration**: Generate location-based images dynamically using AI prompts.
- **DeepAI Integration**: High-resolution image generation for detailed location visuals.
- **Persistent Images**: Once generated, images are saved and reused for revisited locations.

### **Combat System Enhancements**

- **Critical Hits**: Added critical hit mechanics for both players and NPCs.
- **Special Abilities**: NPCs and players now have unique abilities impacting combat outcomes.
- **Refined Damage System**: Damage calculations now consider player level, attributes, and dynamic dice rolls.

### **Quest Management**

- **Quest Display**: Added a `display_quest` function to show active quests, descriptions, and statuses.
- **Quest State Tracking**: Automatic updates to quests upon completion or progress.

### **Gameplay Enhancements**

- **Hidden Item Search**: Introduced a skill-check-based system for discovering hidden treasures, requiring a torch.
- **Locked Path Handling**: Clear prompts and validation when attempting to move to locked locations.
- **Improved Movement System**: Added feedback for locked and unlocked path navigation.

### **NPC Interaction**

- **Dynamic Responses**: NPCs provide tailored replies based on current quests, inventory, and player stats.
- **Combat Conversations**: Integrated NPC dialogues during battles.

### **General Fixes and Improvements**

- **Game State Validation**: Ensures all `generated_image` fields are properly formatted.
- **Bug Fixes**:
  - Resolved issues with invalid inventory items.
  - Addressed errors in locked path handling.
  - Fixed HP and item usage inconsistencies.

---

### **Game Commands**

- **new**:  
  Start a new game, erasing current progress.

- **look**:  
  Describe your current surroundings, including NPCs, items, and possible paths.

- **image**:  
  Generate an image for the current location using AI.

- **stats**:  
  Show your current stats, including HP, level, attack power, and XP.

- **inventory**:  
  Display the items you are carrying with details.

- **pick [item]**:  
  Pick up an item from your current location (e.g., `pick potion`).

- **use [item]**:  
  Use an item from your inventory (e.g., `use potion`).

- **drop [item]**:  
  Remove an item from your inventory (e.g., `drop potion`).

- **move [direction]**:  
  Move to a new location in a specified direction (e.g., `move north`).

- **back**:  
  Return to the previous location.

- **unlock**:  
  Attempt to unlock a locked path if you have a key.

- **talk [npc]**:  
  Start a conversation with an NPC in your location (e.g., `talk goblin`).

- **fight [npc]**:  
  Engage in combat with an NPC (e.g., `fight goblin`).

- **goal**:  
  Display the current quest and progress of the game.

- **map**:  
  Display the visual map of the game's world.

- **quit**:  
  Exit the game. Progress will be saved.

---

### **Acknowledgements**

This project leverages:

- **OpenAI GPT-4o**:  
  For generating:

  - Location Discription.
  - Context-aware NPC interactions.
  - World map generatiion.

- **DeepAI**:  
  For dynamic image generation.

---

## Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/AkulaPhanidhar/DM_Master.git
   cd DM_Master
   ```

2. **Create a Virtual Envirnoment**:

```bash
python3 -m venv <env Name>
```

```bash
source <env Name>/bin/activate
```

3. install requit=rement.txt

4. run python main.py
