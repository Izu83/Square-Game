# Triangle Shooter  

A simple but fun arcade-style game built with **Pygame**.  
You control a **triangle** with a controller, shoot **squares** as enemies, manage limited ammo, and heal with **green circle potions** that drop during the game.  

---

## 🎮 Features  
- **Controller support only** – play using an Xbox or compatible gamepad.  
- **Triangle player**  
  - Move with the **left stick**  
  - Aim/rotate with the **right stick**  
  - Shoot with limited ammo (**12 bullets**)  
  - Reload when out of bullets  
- **Enemies:** squares you must shoot to survive  
- **Healing system:** pick up **green circle potions** to restore health  
- **Score system:** based on time survived and kills  
- **Pause menu:** adjust volume and manage game state  

---

## 🕹️ Controls  
| Action         | Controller Input |
|----------------|------------------|
| Move           | Left stick       |
| Rotate / Aim   | Right stick      |
| Shoot          | Right trigger (RT) |
| Reload         | X button (or equivalent) |
| Pause / Resume | Start button     |

---

## 🔫 Gameplay  
1. Survive as long as possible.  
2. Manage your **12 bullet magazine** – reload when empty.  
3. Pick up **green circles** to heal.  
4. Kill squares to increase your score.  
5. Try to beat your high score by lasting longer and defeating more enemies!  

---

## 📦 Requirements  
- Python 3.10+  
- [Pygame](https://www.pygame.org/)  

Install dependencies with:  
```bash
pip install pygame
```  

---

## ▶️ Running the Game  
```bash
python main.py
```  

(Make sure your controller is connected before starting.)  

---

## 📝 Notes  
- Keyboard/mouse is **not supported**. A controller is required.  
- Tested with Xbox controller; other XInput-compatible controllers should work.  
