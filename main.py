import pygame
import sys
import random
import os

# --- 1. SETUP & CONSTANTS ---
pygame.init()

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

COLOR_BG_TOP = (110, 190, 255)
COLOR_BG_BOTTOM = (210, 245, 170)
COLOR_FLOOR = (35, 120, 55)
COLOR_LEDGE = (130, 235, 80)
COLOR_SUN = (255, 240, 120)

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Rondo Knight - Smooth Loop Fix")
clock = pygame.time.Clock()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- 2. GLOBAL ANIMATION CACHE ---
ANIMATIONS = {}

def load_all_animations():
    def load_anim(filename, num_frames, scale=2.5):
        filepath = None
        for root, dirs, files in os.walk(BASE_DIR):
            if filename.lower() in [f.lower() for f in files]:
                actual_name = next(f for f in files if f.lower() == filename.lower())
                filepath = os.path.join(root, actual_name)
                break
                
        if not filepath:
            print(f"[Warning] Could not find: {filename}")
            surf = pygame.Surface((int(128*scale), int(128*scale)), pygame.SRCALPHA)
            surf.fill((255, 0, 128, 128))
            return [surf]
            
        sheet = pygame.image.load(filepath).convert_alpha()
        frame_width = sheet.get_width() // num_frames
        frame_height = sheet.get_height()
        
        frames = []
        for i in range(num_frames):
            frame_surf = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
            frame_surf.blit(sheet, (0, 0), (i * frame_width, 0, frame_width, frame_height))
            frame_surf = pygame.transform.scale(frame_surf, (int(frame_width * scale), int(frame_height * scale)))
            frames.append(frame_surf)
        return frames

    ANIMATIONS['idle'] = load_anim('Idle.png', 4)
    ANIMATIONS['run'] = load_anim('Run.png', 8)
    ANIMATIONS['jump'] = load_anim('Jump.png', 6)
    ANIMATIONS['attack1'] = load_anim('Attack 1.png', 5)
    ANIMATIONS['attack2'] = load_anim('Attack 2.png', 4)
    ANIMATIONS['attack3'] = load_anim('Attack 3.png', 4)
    ANIMATIONS['run_attack'] = load_anim('Run+Attack.png', 6)
    ANIMATIONS['defend'] = load_anim('Defend.png', 5)
    ANIMATIONS['hurt'] = load_anim('Hurt.png', 2)
    ANIMATIONS['dead'] = load_anim('Dead.png', 4) # Added support for Dead.png

# --- 3. PLAYER CLASS ---
class Player:
    def __init__(self):
        self.current_state = 'idle'
        self.anim_index = 0
        self.anim_timer = 0
        self.is_locked = False 
        
        self.pos = pygame.Vector2(150, 540)
        self.vel = pygame.Vector2(0, 0)
        self.acc = pygame.Vector2(0, 0)
        self.facing_right = True

        self.GRAVITY = 0.7
        self.FRICTION = -0.12
        self.WALK_ACCEL = 0.7
        self.JUMP_POWER = -14
        
    def get_hitbox(self):
        return pygame.Rect(self.pos.x - 20, self.pos.y - 70, 40, 70)
        
    def get_attack_rect(self):
        is_attacking = 'attack' in self.current_state
        if is_attacking and 1 <= self.anim_index <= 3:
            w, h = 70, 60
            return pygame.Rect(self.pos.x if self.facing_right else self.pos.x - w, self.pos.y - 70, w, h)
        return None

    def set_state(self, new_state):
        if self.current_state != new_state:
            self.current_state = new_state
            self.anim_index = 0
            self.anim_timer = 0

    def update(self, floor_y):
        self.acc = pygame.Vector2(0, self.GRAVITY)
        keys = pygame.key.get_pressed()
        mouse = pygame.mouse.get_pressed()
        
        moving_left = keys[pygame.K_a] or keys[pygame.K_LEFT]
        moving_right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
        is_moving = moving_left or moving_right
        
        # --- STATE LOGIC ---
        if not self.is_locked:
            if self.pos.y < floor_y:
                self.set_state('jump')
            elif is_moving:
                self.set_state('run')
            else:
                self.set_state('idle')
                
            # Triggers
            if mouse[0] or keys[pygame.K_j]:
                if is_moving: self.set_state('run_attack')
                else: self.set_state(random.choice(['attack1', 'attack2', 'attack3']))
                self.is_locked = True
            elif mouse[2] or keys[pygame.K_k]:
                self.set_state('defend')
                self.is_locked = True

        # --- PHYSICS ---
        if not self.is_locked or self.current_state == 'run_attack':
            if moving_left:
                self.acc.x = -self.WALK_ACCEL
                self.facing_right = False
            if moving_right:
                self.acc.x = self.WALK_ACCEL
                self.facing_right = True

        self.acc.x += self.vel.x * self.FRICTION
        self.vel += self.acc
        self.pos += self.vel + 0.5 * self.acc

        if self.pos.y >= floor_y:
            self.pos.y = floor_y
            self.vel.y = 0
            
        # --- ANIMATION SPEED ---
        self.anim_timer += 1
        # Fixed: Run animation now feels much smoother
        speeds = {'run': 5, 'idle': 8, 'jump': 6, 'defend': 7}
        anim_speed = speeds.get(self.current_state, 4)
        
        if self.anim_timer >= anim_speed:
            self.anim_timer = 0
            self.anim_index += 1
            
            if self.anim_index >= len(ANIMATIONS[self.current_state]):
                if self.is_locked:
                    if self.current_state == 'defend' and (mouse[2] or keys[pygame.K_k]):
                        self.anim_index = len(ANIMATIONS['defend']) - 1
                    else:
                        self.is_locked = False
                        self.set_state('idle')
                else:
                    self.anim_index = 0 if self.current_state != 'jump' else len(ANIMATIONS['jump']) - 1

    def draw(self, surf):
        img = ANIMATIONS[self.current_state][self.anim_index]
        if not self.facing_right: img = pygame.transform.flip(img, True, False)
        surf.blit(img, img.get_rect(midbottom=(int(self.pos.x), int(self.pos.y))))

# --- 4. ENEMY CLASS ---
class Enemy:
    def __init__(self, x):
        self.current_state = 'idle'
        self.anim_index = 0
        self.anim_timer = 0
        self.pos = pygame.Vector2(x, 540)
        self.health = 3
        self.iframes = 0
        self.is_dead = False

    def take_damage(self):
        if self.iframes <= 0 and not self.is_dead:
            self.health -= 1
            self.iframes = 30
            if self.health <= 0:
                self.is_dead = True
                self.current_state = 'dead'
            else:
                self.current_state = 'hurt'
            self.anim_index = 0

    def update(self):
        if self.iframes > 0: self.iframes -= 1
        
        self.anim_timer += 1
        if self.anim_timer >= 7:
            self.anim_timer = 0
            self.anim_index += 1
            if self.anim_index >= len(ANIMATIONS[self.current_state]):
                if self.current_state == 'dead':
                    self.anim_index = len(ANIMATIONS['dead']) - 1 # Stay dead
                elif self.current_state == 'hurt':
                    self.current_state = 'idle'
                    self.anim_index = 0
                else:
                    self.anim_index = 0

    def draw(self, surf):
        img = ANIMATIONS[self.current_state][self.anim_index]
        # Always face the player (assume player is on the left initially)
        surf.blit(img, img.get_rect(midbottom=(int(self.pos.x), int(self.pos.y))))

# --- 5. BACKGROUND DRAWING ---
def draw_background(surf):
    # Draw gradient sky
    for y in range(SCREEN_HEIGHT):
        ratio = y / SCREEN_HEIGHT
        r = int(COLOR_BG_TOP[0] * (1 - ratio) + COLOR_BG_BOTTOM[0] * ratio)
        g = int(COLOR_BG_TOP[1] * (1 - ratio) + COLOR_BG_BOTTOM[1] * ratio)
        b = int(COLOR_BG_TOP[2] * (1 - ratio) + COLOR_BG_BOTTOM[2] * ratio)
        pygame.draw.line(surf, (r, g, b), (0, y), (SCREEN_WIDTH, y))
    
    # Draw sun
    pygame.draw.circle(surf, COLOR_SUN, (700, 80), 50)

# --- 6. MAIN LOOP ---
def main():
    load_all_animations()
    player = Player()
    enemy = Enemy(600)
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_SPACE, pygame.K_UP, pygame.K_w]: player.jump()

        player.update(SCREEN_HEIGHT - 60)
        enemy.update()
        
        # Combat Check
        atk_rect = player.get_attack_rect()
        if atk_rect and atk_rect.colliderect(pygame.Rect(enemy.pos.x - 20, enemy.pos.y - 70, 40, 70)):
            enemy.take_damage()

        draw_background(screen)
        pygame.draw.rect(screen, COLOR_FLOOR, (0, SCREEN_HEIGHT - 60, SCREEN_WIDTH, 60))
        player.draw(screen)
        enemy.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()