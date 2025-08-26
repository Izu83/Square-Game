import os
import sys
import math
import time
import random
import pygame

# -----------------------------
# Init
# -----------------------------
pygame.init()
pygame.joystick.init()
pygame.mixer.init()

WIDTH, HEIGHT = 1200, 760
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Controller Triangle Shooter")

# Require a controller
if pygame.joystick.get_count() == 0:
    print("No controller connected!")
    sys.exit()
joystick = pygame.joystick.Joystick(0)
joystick.init()

# Fonts
font = pygame.font.SysFont(None, 48)
title_font = pygame.font.SysFont(None, 56)
small_font = pygame.font.SysFont(None, 36)

clock = pygame.time.Clock()

# -----------------------------
# Game State
# -----------------------------
tri_x, tri_y = WIDTH // 2, HEIGHT // 2
tri_size = 60
tri_speed = 5
tri_color = (100, 200, 255)
triangle_angle = 0

paused = False
viewing_podium = False
death_screen = False
selected_option = 0
options = ["Resume Game", "Volume", "Podium", "Quit Game"]
death_options = ["Respawn", "Quit Game"]
volume = 0.5

prev_button_start = False
prev_button_a = False
prev_button_rb = False
prev_hat_y = 0

projectiles = []
enemies = []

# Healing pickups (drop from killed enemies)
heal_pickups = []
heal_pickup_duration = 10.0  # seconds
heal_pickup_radius = 15
heal_pickup_heal_amount = 20
heal_drop_chance = 0.30

# Ammo & reload
max_bullets = 12
current_bullets = max_bullets
reloading = False
reload_start_time = None
reload_duration = 0.94

# Hold-to-heal (player ability)
healing = False
heal_start_time = None
heal_duration = 5.0
heal_amount = 20

# Health
health = 100
max_health = 100

# Timer / score
start_time = time.time()
total_paused_time = 0.0
pause_start_time = None
minutes_scored = 0  # survival bonus tracker
score = 0

# Audio
try:
    pew_sound = pygame.mixer.Sound("pew.wav")
    pew_sound.set_volume(volume)
except pygame.error:
    pew_sound = None

# Podium persistence
PODIUM_FILE = "podium.txt"
MAX_PODIUM_ENTRIES = 3

def load_podium():
    if not os.path.exists(PODIUM_FILE):
        return []
    podium = []
    with open(PODIUM_FILE, "r") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) == 2:
                try:
                    s = int(parts[0])
                    t = float(parts[1])
                    podium.append((s, t))
                except ValueError:
                    pass
    # Sort by score desc, then time asc (optional tweak)
    podium.sort(key=lambda x: (-x[0], x[1]))
    return podium[:MAX_PODIUM_ENTRIES]

def update_podium(new_score, elapsed_time):
    podium = load_podium()
    podium.append((new_score, elapsed_time))
    # Sort and trim
    podium.sort(key=lambda x: (-x[0], x[1]))
    podium = podium[:MAX_PODIUM_ENTRIES]
    with open(PODIUM_FILE, "w") as f:
        for s, t in podium:
            f.write(f"{s},{t:.3f}\n")

# -----------------------------
# Drawing & Spawn Helpers
# -----------------------------
def draw_attached_triangle(surface, x, y, size, angle, color):
    cx, cy = x + size // 2, y + size // 2
    length = size * 0.6
    width = size * 0.4
    triangle = [(0, -length), (-width, width), (width, width)]
    rad = math.radians(angle)
    rotated = []
    for px, py in triangle:
        rx = px * math.cos(rad) - py * math.sin(rad)
        ry = px * math.sin(rad) + py * math.cos(rad)
        rotated.append((cx + rx, cy + ry))
    pygame.draw.polygon(surface, color, rotated)

def shoot_projectile(x, y, angle):
    rad = math.radians(angle - 90)
    dx = math.cos(rad)
    dy = math.sin(rad)
    return {
        'x': x + tri_size // 2,
        'y': y + tri_size // 2,
        'dx': dx * 10,
        'dy': dy * 10,
        'size': 12,
        'alive': True
    }

def spawn_enemy():
    # (color, speed, damage, size_display) — size is overwritten to 40 later
    types = [
        ((255, 255, 255), 2, 5, 20),   # White
        ((0, 255, 255),   4, 10, 20),  # Blue
        ((255, 0, 0),     7, 15, 24),  # Red
    ]
    choice = random.choices(types, weights=[0.6, 0.3, 0.1])[0]
    color, speed, damage, size = choice
    edge = random.choice(['top', 'bottom', 'left', 'right'])
    size = 40
    if edge == 'top':
        x = random.randint(0, WIDTH)
        y = -size
    elif edge == 'bottom':
        x = random.randint(0, WIDTH)
        y = HEIGHT + size
    elif edge == 'left':
        x = -size
        y = random.randint(0, HEIGHT)
    else:
        x = WIDTH + size
        y = random.randint(0, HEIGHT)
    return {'x': x, 'y': y, 'color': color, 'speed': speed, 'damage': damage, 'size': size, 'alive': True}



spawn_timer = 0
spawn_interval = 75

running = True
while running:
    screen.fill((30, 30, 30))

    # ------------- Events -------------
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            # Save score on window close
            # Compute final elapsed_time safely
            if paused or viewing_podium:
                if pause_start_time is not None:
                    effective_elapsed_time = pause_start_time - start_time - total_paused_time
                else:
                    effective_elapsed_time = time.time() - start_time - total_paused_time
            else:
                effective_elapsed_time = time.time() - start_time - total_paused_time
            update_podium(score, effective_elapsed_time)
            running = False

    # Start button toggles pause (not in death screen, not in podium)
    button_start = joystick.get_button(7)
    if button_start and not prev_button_start:
        if death_screen:
            pass
        else:
            if not paused and not viewing_podium:
                paused = True
                pause_start_time = time.time()
            elif paused and not viewing_podium:
                paused = False
                if pause_start_time is not None:
                    total_paused_time += time.time() - pause_start_time
                    pause_start_time = None
        pygame.time.wait(150)
    prev_button_start = button_start

    # ------------- Death Screen -------------
    if death_screen:
        menu_width, menu_height = 500, 240
        menu_x = WIDTH // 2 - menu_width // 2
        menu_y = HEIGHT // 2 - menu_height // 2
        menu_surface = pygame.Surface((menu_width, menu_height), pygame.SRCALPHA)
        menu_surface.fill((80, 0, 0, 220))
        screen.blit(menu_surface, (menu_x, menu_y))

        title_text = title_font.render("You Died", True, (255, 255, 255))
        screen.blit(title_text, (WIDTH // 2 - title_text.get_width() // 2, menu_y + 20))

        for i, text in enumerate(death_options):
            color = (255, 255, 255) if i == selected_option else (180, 180, 180)
            option_text = font.render(text, True, color)
            text_x = WIDTH // 2 - option_text.get_width() // 2 + 20
            text_y = menu_y + 90 + i * 50
            screen.blit(option_text, (text_x, text_y))
            if i == selected_option:
                arrow_text = font.render("▶", True, (255, 255, 255))
                screen.blit(arrow_text, (text_x - 40, text_y))

        # Navigation
        hat_y = joystick.get_hat(0)[1]
        if hat_y == 1 and prev_hat_y != 1:
            selected_option = (selected_option - 1) % len(death_options)
            pygame.time.wait(150)
        elif hat_y == -1 and prev_hat_y != -1:
            selected_option = (selected_option + 1) % len(death_options)
            pygame.time.wait(150)
        prev_hat_y = hat_y

        # Select
        if joystick.get_button(0) and not prev_button_a:
            if death_options[selected_option] == "Respawn":
                # Reset core state
                health = 100
                current_bullets = max_bullets
                projectiles = []
                enemies = []
                heal_pickups = []
                tri_x, tri_y = WIDTH // 2, HEIGHT // 2
                # Reset timer & score
                score = 0
                start_time = time.time()
                total_paused_time = 0.0
                pause_start_time = None
                minutes_scored = 0
                death_screen = False
            else:
                # Save last run to podium before quitting
                # Compute elapsed safely
                if pause_start_time is not None:
                    elapsed_time = pause_start_time - start_time - total_paused_time
                else:
                    elapsed_time = time.time() - start_time - total_paused_time
                update_podium(score, elapsed_time)
                pygame.quit()
                sys.exit()
        prev_button_a = joystick.get_button(0)

    # ------------- Pause Menu -------------
    elif paused:
        menu_width, menu_height = 600, 360  # bigger box
        menu_x = WIDTH // 2 - menu_width // 2
        menu_y = HEIGHT // 2 - menu_height // 2
        menu_surface = pygame.Surface((menu_width, menu_height), pygame.SRCALPHA)
        menu_surface.fill((50, 50, 50, 200))
        screen.blit(menu_surface, (menu_x, menu_y))

        title_text = title_font.render("Paused", True, (255, 255, 255))
        screen.blit(title_text, (WIDTH // 2 - title_text.get_width() // 2, menu_y + 20))

        for i, text in enumerate(options):
            display_text = text
            if text == "Volume":
                display_text += f" [{int(volume * 100)}%]"
            color = (255, 255, 255) if i == selected_option else (180, 180, 180)
            option_text = font.render(display_text, True, color)
            text_x = WIDTH // 2 - option_text.get_width() // 2 + 20
            text_y = menu_y + 90 + i * 60
            screen.blit(option_text, (text_x, text_y))
            if i == selected_option:
                arrow_text = font.render("▶", True, (255, 255, 255))
                screen.blit(arrow_text, (text_x - 40, text_y))

        # Navigate
        hat_y = joystick.get_hat(0)[1]
        if hat_y == 1 and prev_hat_y != 1:
            selected_option = (selected_option - 1) % len(options)
            pygame.time.wait(150)
        elif hat_y == -1 and prev_hat_y != -1:
            selected_option = (selected_option + 1) % len(options)
            pygame.time.wait(150)
        prev_hat_y = hat_y

        # Adjust volume when "Volume" highlighted (LB/RB)
        if selected_option == 1:
            if joystick.get_button(4):  # LB
                volume = max(0, volume - 0.05)
                if pew_sound:
                    pew_sound.set_volume(volume)
                pygame.time.wait(120)
            if joystick.get_button(5):  # RB
                volume = min(1.0, volume + 0.05)
                if pew_sound:
                    pew_sound.set_volume(volume)
                pygame.time.wait(120)

        # Select option
        if joystick.get_button(0) and not prev_button_a:  # A
            choice = options[selected_option]
            if choice == "Resume Game":
                paused = False
                if pause_start_time is not None:
                    total_paused_time += time.time() - pause_start_time
                    pause_start_time = None
            elif choice == "Quit Game":
                # Save score on quit
                if pause_start_time is not None:
                    elapsed_time = pause_start_time - start_time - total_paused_time
                else:
                    elapsed_time = time.time() - start_time - total_paused_time
                update_podium(score, elapsed_time)
                pygame.quit()
                sys.exit()
            elif choice == "Podium":
                viewing_podium = True
                # ensure timer frozen
                if pause_start_time is None:
                    pause_start_time = time.time()
            # Volume is handled above
        prev_button_a = joystick.get_button(0)

    # ------------- Podium View -------------
    elif viewing_podium:
        screen.fill((20, 20, 20))
        podium_title = title_font.render("Top 3 Scores", True, (255, 255, 255))
        screen.blit(podium_title, (WIDTH // 2 - podium_title.get_width() // 2, 100))

        podium = load_podium()
        for i, (s, t) in enumerate(podium):
            mins = int(t // 60)
            secs = int(t % 60)
            ms = int((t - int(t)) * 1000)
            h = int(mins // 60)
            m = mins % 60
            time_str = f"{h:02}:{m:02}:{secs:02}:{ms:03}"
            pps = (s / t) if t > 0 else 0.0
            line = small_font.render(f"{i+1}. Score: {s}  Time: {time_str}  PPS: {pps:.2f}", True, (255, 255, 255))
            screen.blit(line, (WIDTH // 2 - line.get_width() // 2, 180 + i * 50))

        info_text = small_font.render("Press B to return", True, (150, 150, 150))
        screen.blit(info_text, (WIDTH // 2 - info_text.get_width() // 2, 400))

        # B to go back
        if joystick.get_button(1):  # B
            viewing_podium = False
            if pause_start_time is not None:
                total_paused_time += time.time() - pause_start_time
                pause_start_time = None
            pygame.time.wait(200)

    # ------------- Gameplay -------------
    else:
        # Movement (left stick)
        axis_x = joystick.get_axis(0)
        axis_y = joystick.get_axis(1)
        deadzone = 0.1
        if abs(axis_x) < deadzone: axis_x = 0
        if abs(axis_y) < deadzone: axis_y = 0

        if not healing:
            tri_x += axis_x * tri_speed
            tri_y += axis_y * tri_speed
        tri_x = max(0, min(WIDTH - tri_size, tri_x))
        tri_y = max(0, min(HEIGHT - tri_size, tri_y))

        # Aim (right stick)
        right_x = joystick.get_axis(2)
        right_y = joystick.get_axis(3)
        if abs(right_x) > 0.2 or abs(right_y) > 0.2:
            angle_rad = math.atan2(right_y, right_x)
            triangle_angle = math.degrees(angle_rad) + 90

        # Hold A to self-heal
        if joystick.get_button(0):
            if not healing:
                healing = True
                heal_start_time = time.time()
        else:
            if healing and heal_start_time:
                held_time = time.time() - heal_start_time
                if held_time >= heal_duration:
                    health = min(max_health, health + heal_amount)
                healing = False
                heal_start_time = None

        # Hold B to reload
        if joystick.get_button(1):
            if not reloading and not healing:
                reloading = True
                reload_start_time = time.time()
        else:
            if reloading and reload_start_time:
                held_time = time.time() - reload_start_time
                if held_time >= reload_duration:
                    current_bullets = max_bullets
                reloading = False
                reload_start_time = None

        # RB shoot
        button_rb = joystick.get_button(5)
        if button_rb and not prev_button_rb and current_bullets > 0 and not healing:
            projectile = shoot_projectile(tri_x, tri_y, triangle_angle)
            projectiles.append(projectile)
            if pew_sound:
                pew_sound.play()
            current_bullets -= 1
        prev_button_rb = button_rb

        # Color feedback
        if healing:
            tri_color = (0, 255, 0)
        elif reloading:
            tri_color = (255, 0, 0)
        elif joystick.get_button(3):
            tri_color = (255, 255, 0)
        elif joystick.get_button(2):
            tri_color = (0, 0, 255)
        else:
            tri_color = (100, 200, 255)

        # Draw player
        draw_attached_triangle(screen, tri_x, tri_y, tri_size, triangle_angle, tri_color)

        # Projectiles update/draw
        for proj in projectiles:
            proj['x'] += proj['dx']
            proj['y'] += proj['dy']
            pygame.draw.rect(screen, (255, 255, 255), (proj['x'], proj['y'], proj['size'], proj['size']))
        projectiles = [p for p in projectiles if 0 <= p['x'] <= WIDTH and 0 <= p['y'] <= HEIGHT and p['alive']]

        # Spawn enemies
        spawn_timer += 1
        if spawn_timer >= spawn_interval:
            enemies.append(spawn_enemy())
            spawn_timer = 0

        # Enemies move toward player
        for enemy in enemies:
            dx = tri_x + tri_size // 2 - enemy['x']
            dy = tri_y + tri_size // 2 - enemy['y']
            dist = math.hypot(dx, dy)
            if dist != 0:
                dx /= dist
                dy /= dist
            enemy['x'] += dx * enemy['speed']
            enemy['y'] += dy * enemy['speed']
            pygame.draw.rect(screen, enemy['color'], (enemy['x'], enemy['y'], enemy['size'], enemy['size']))

        # Projectile vs enemy collisions + drop heal + scoring
        for enemy in enemies:
            ex, ey, esize = enemy['x'], enemy['y'], enemy['size']
            for proj in projectiles:
                if (ex < proj['x'] < ex + esize and ey < proj['y'] < ey + esize):
                    enemy['alive'] = False
                    proj['alive'] = False

                    # scoring by enemy color
                    if enemy['color'] == (255, 255, 255):
                        score += 500
                    elif enemy['color'] == (0, 255, 255):
                        score += 1500
                    elif enemy['color'] == (255, 0, 0):
                        score += 3000

                    # heal pickup drop chance
                    if random.random() < heal_drop_chance:
                        heal_pickups.append({
                            'x': ex + esize / 2,
                            'y': ey + esize / 2,
                            'spawn_time': time.time(),
                            'radius': heal_pickup_radius,
                            'alive': True
                        })

        enemies = [e for e in enemies if e['alive']]

        # Enemy contact damage
        if not healing:
            for enemy in enemies:
                dx = (tri_x + tri_size // 2) - (enemy['x'] + enemy['size'] / 2)
                dy = (tri_y + tri_size // 2) - (enemy['y'] + enemy['size'] / 2)
                distance = math.hypot(dx, dy)
                if distance < (tri_size // 2 + enemy['size'] // 2):
                    health -= enemy['damage']
                    enemy['alive'] = False

        # Heal pickups: expire, draw, collect
        now = time.time()
        for hp in heal_pickups:
            if now - hp['spawn_time'] > heal_pickup_duration:
                hp['alive'] = False
        heal_pickups = [hp for hp in heal_pickups if hp['alive']]

        for hp in heal_pickups:
            pygame.draw.circle(screen, (0, 255, 0), (int(hp['x']), int(hp['y'])), hp['radius'])
            dx = (tri_x + tri_size / 2) - hp['x']
            dy = (tri_y + tri_size / 2) - hp['y']
            dist = math.hypot(dx, dy)
            if dist < (tri_size / 2 + hp['radius']):
                health = min(max_health, health + heal_pickup_heal_amount)
                hp['alive'] = False
        heal_pickups = [hp for hp in heal_pickups if hp['alive']]

        # Death check
        if health <= 0:
            death_screen = True
            # Save score on death
            # Compute elapsed safely
            elapsed_time = time.time() - start_time - total_paused_time
            update_podium(score, elapsed_time)

    # --------- UI common (timer/score/health/ammo/progress arcs) ----------
    # Compute elapsed time (freeze while paused or in podium)
    if paused or viewing_podium:
        if pause_start_time is not None:
            effective_elapsed_time = pause_start_time - start_time - total_paused_time
        else:
            effective_elapsed_time = time.time() - start_time - total_paused_time
    else:
        effective_elapsed_time = time.time() - start_time - total_paused_time
    elapsed_time = max(0.0, effective_elapsed_time)

    # survival bonus: award once per new minute
    new_minutes = int(elapsed_time // 60)
    if new_minutes > minutes_scored:
        score += (new_minutes - minutes_scored) * 2000
        minutes_scored = new_minutes

    # Timer display
    total_ms = int(elapsed_time * 1000)
    hours = (total_ms // (3600 * 1000)) % 100  # 2-digit hours
    minutes = (total_ms // (60 * 1000)) % 60
    seconds = (total_ms // 1000) % 60
    milliseconds = total_ms % 1000

    time_text = small_font.render(f"Time: {hours:02}:{minutes:02}:{seconds:02}:{milliseconds:03}", True, (255, 255, 255))
    time_x = WIDTH // 2 - time_text.get_width() // 2
    screen.blit(time_text, (time_x, 10))

    # Score display (below timer)
    score_text = small_font.render(f"Score: {score}", True, (255, 255, 255))
    screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, 50))

    # Ammo text
    bullet_text = small_font.render(f"Bullets: {current_bullets} / {max_bullets}", True, (255, 255, 255))
    screen.blit(bullet_text, (20, HEIGHT - 40))

    # Health bar
    health_bar_width = 200
    health_ratio = max(0, min(1, health / max_health))
    pygame.draw.rect(screen, (255, 0, 0), (20, HEIGHT - 70, health_bar_width, 20))
    pygame.draw.rect(screen, (0, 255, 0), (20, HEIGHT - 70, int(health_bar_width * health_ratio), 20))

    # Reload/Heal arcs
    if reloading and reload_start_time:
        elapsed = time.time() - reload_start_time
        progress = min(elapsed / reload_duration, 1.0)
        arc_radius = int(tri_size * 0.7)
        arc_rect = pygame.Rect(
            int(tri_x + tri_size // 2 - arc_radius),
            int(tri_y + tri_size // 2 - arc_radius),
            arc_radius * 2, arc_radius * 2
        )
        start_angle = -math.pi / 2
        end_angle = start_angle + progress * 2 * math.pi
        pygame.draw.arc(screen, (255, 0, 0), arc_rect, start_angle, end_angle, 4)

    if healing and heal_start_time:
        elapsed = time.time() - heal_start_time
        progress = min(elapsed / heal_duration, 1.0)
        arc_radius = int(tri_size * 0.7)
        arc_rect = pygame.Rect(
            int(tri_x + tri_size // 2 - arc_radius),
            int(tri_y + tri_size // 2 - arc_radius),
            arc_radius * 2, arc_radius * 2
        )
        start_angle = -math.pi / 2
        end_angle = start_angle + progress * 2 * math.pi
        pygame.draw.arc(screen, (0, 255, 0), arc_rect, start_angle, end_angle, 4)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
