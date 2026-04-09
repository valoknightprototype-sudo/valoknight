import pygame
import sys
import random

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
pygame.display.set_caption("Atmospheric Metroidvania - Combo System")
clock = pygame.time.Clock()

# --- 2. FOREST PARTICLES ---
particles = []
for _ in range(60):
    x = random.randint(0, SCREEN_WIDTH)
    y = random.randint(0, SCREEN_HEIGHT)
    speed_x = random.uniform(0.2, 1.2)
    speed_y = random.uniform(0.5, 1.8)
    radius = random.uniform(2, 4)
    ptype = 'pollen' if random.random() > 0.3 else 'leaf'
    particles.append([x, y, speed_x, speed_y, radius, ptype])

def draw_background(surface):
    for y in range(SCREEN_HEIGHT):
        blend = y / SCREEN_HEIGHT
        r = int(COLOR_BG_TOP[0] * (1 - blend) + COLOR_BG_BOTTOM[0] * blend)
        g = int(COLOR_BG_TOP[1] * (1 - blend) + COLOR_BG_BOTTOM[1] * blend)
        b = int(COLOR_BG_TOP[2] * (1 - blend) + COLOR_BG_BOTTOM[2] * blend)
        pygame.draw.line(surface, (r, g, b), (0, y), (SCREEN_WIDTH, y))

    pygame.draw.circle(surface, COLOR_SUN, (SCREEN_WIDTH - 120, 100), 50)
    
    for p in particles:
        p[0] += p[2]
        p[1] += p[3]
        
        if p[1] > SCREEN_HEIGHT:
            p[1] = -10
            p[0] = random.randint(-100, SCREEN_WIDTH)
        if p[0] > SCREEN_WIDTH + 10:
            p[0] = -10

        color = (255, 235, 140) if p[5] == 'pollen' else (100, 200, 100)
        pygame.draw.circle(surface, color, (int(p[0]), int(p[1])), int(p[4]))

# --- 3. THE PLAYER CLASS ---
class Player:
    def __init__(self):
        # Assets
        self.idle_img = self.load_and_format_image('knight_idle.png')
        self.run_imgs = [
            self.load_and_format_image('knight_run1.png'),
            self.load_and_format_image('knight_run2.png')
        ]
        
        self.image = self.idle_img if self.idle_img else pygame.Surface((48, 90))
        if not self.idle_img: self.image.fill((200, 50, 50))

        self.run_index = 0
        self.anim_timer = 0
        self.ANIM_SPEED = 8
        
        # Physics Vectors
        self.pos = pygame.Vector2(SCREEN_WIDTH // 2, 100)
        self.vel = pygame.Vector2(0, 0)
        self.acc = pygame.Vector2(0, 0)
        
        self.rect = self.image.get_rect()
        self.rect.midbottom = (self.pos.x, self.pos.y) 
        
        self.facing_right = True
        self.is_moving = False

        # --- COMBO & COMBAT VARIABLES ---
        self.is_attacking = False
        self.attack_timer = 0
        self.ATTACK_DURATION = 12       # Speed of the attack
        self.attack_hitbox = pygame.Rect(0, 0, 0, 0)
        
        self.combo_step = 0             # Tracks Hit 1, Hit 2, or Hit 3
        self.combo_window_timer = 0     # How long you have to click again
        self.COMBO_WINDOW = 25          # 25 frames to click for the next hit
        # --------------------------------

        # Physics Constants
        self.HORIZONTAL_ACCEL = 0.6   
        self.FRICTION = -0.12         
        self.GRAVITY = 0.7            
        self.JUMP_FORCE = -14         
        self.MIN_JUMP_VELOCITY = -3   
        self.on_ground = False

    def load_and_format_image(self, filepath):
        try:
            raw_image = pygame.image.load(filepath).convert_alpha()
            bounding_rect = raw_image.get_bounding_rect()
            cropped_image = raw_image.subsurface(bounding_rect)
            
            orig_w, orig_h = cropped_image.get_size()
            target_height = 90
            scale = target_height / orig_h
            target_width = int(orig_w * scale)
            
            return pygame.transform.scale(cropped_image, (target_width, target_height))
        except FileNotFoundError:
            return None

    def update(self, floor_y):
        self.acc = pygame.Vector2(0, self.GRAVITY)
        keys = pygame.key.get_pressed()
        self.is_moving = False

        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.acc.x = -self.HORIZONTAL_ACCEL
            self.facing_right = False 
            self.is_moving = True
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.acc.x = self.HORIZONTAL_ACCEL
            self.facing_right = True  
            self.is_moving = True

        self.acc.x += self.vel.x * self.FRICTION
        self.vel += self.acc
        self.pos += self.vel + 0.5 * self.acc

        self.rect.midbottom = (self.pos.x, self.pos.y)

        # Floor Collision
        if self.rect.bottom > floor_y:
            self.rect.bottom = floor_y
            self.pos.y = self.rect.bottom 
            self.vel.y = 0
            self.on_ground = True
        else:
            self.on_ground = False

        # Screen Boundaries
        if self.rect.left < 0:
            self.rect.left = 0
            self.pos.x = self.rect.centerx
            self.vel.x = 0
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
            self.pos.x = self.rect.centerx
            self.vel.x = 0

        # --- COMBO WINDOW LOGIC ---
        if self.combo_window_timer > 0:
            self.combo_window_timer -= 1
            # If the timer runs out and we aren't mid-attack, reset the combo
            if self.combo_window_timer <= 0 and not self.is_attacking:
                self.combo_step = 0

        # --- COMBAT LOGIC ---
        if self.is_attacking:
            self.attack_timer += 1
            
            # Change hitbox size based on combo step
            if self.combo_step == 3:
                hitbox_width = 90  # Bigger hitbox for the finisher
                hitbox_height = 100
                duration = self.ATTACK_DURATION + 4 # Finisher lasts a bit longer
            else:
                hitbox_width = 60
                hitbox_height = 70
                duration = self.ATTACK_DURATION

            offset_x = 10 if self.facing_right else -hitbox_width - 10
            
            self.attack_hitbox = pygame.Rect(
                self.rect.centerx + offset_x, 
                self.rect.centery - hitbox_height // 2, 
                hitbox_width, 
                hitbox_height
            )

            if self.attack_timer >= duration:
                self.is_attacking = False # Attack finished
        # --------------------

        old_midbottom = self.rect.midbottom 
        
        if self.on_ground:
            if self.is_moving:
                self.anim_timer += 1
                if self.anim_timer >= self.ANIM_SPEED:
                    self.anim_timer = 0
                    self.run_index = (self.run_index + 1) % len(self.run_imgs)
                
                if self.run_imgs[self.run_index]:
                    self.image = self.run_imgs[self.run_index]
            else:
                self.anim_timer = 0
                if self.idle_img:
                    self.image = self.idle_img
        else:
            if self.idle_img:
                self.image = self.idle_img

        self.rect = self.image.get_rect()
        self.rect.midbottom = old_midbottom

    def jump(self):
        if self.on_ground:
            self.vel.y = self.JUMP_FORCE

    def cancel_jump(self):
        if self.vel.y < self.MIN_JUMP_VELOCITY:
            self.vel.y = self.MIN_JUMP_VELOCITY

    def attack(self):
        # We can only trigger the next attack if we aren't currently swinging
        if not self.is_attacking:
            self.is_attacking = True
            self.attack_timer = 0
            
            # Progress the combo
            self.combo_step += 1
            if self.combo_step > 3:
                self.combo_step = 1 # Loop back to hit 1 if we spam past 3

            # Reset the window. The player has the duration of the attack + the window size to click again
            self.combo_window_timer = self.ATTACK_DURATION + self.COMBO_WINDOW

    def draw(self, surface):
        if self.image:
            if not self.facing_right:
                flipped_image = pygame.transform.flip(self.image, True, False)
                surface.blit(flipped_image, self.rect)
            else:
                surface.blit(self.image, self.rect)

        # Draw the combo Slash Effects
        if self.is_attacking:
            slash_surf = pygame.Surface((self.attack_hitbox.width, self.attack_hitbox.height), pygame.SRCALPHA)
            
            # Customize visuals based on which combo hit we are on
            if self.combo_step == 1:
                alpha = int(255 * (1 - (self.attack_timer / self.ATTACK_DURATION)))
                color = (255, 255, 255, max(0, alpha)) # White
                pygame.draw.ellipse(slash_surf, color, (0, 0, self.attack_hitbox.width, self.attack_hitbox.height))
                
            elif self.combo_step == 2:
                alpha = int(255 * (1 - (self.attack_timer / self.ATTACK_DURATION)))
                color = (200, 230, 255, max(0, alpha)) # Light blue
                # Draw slightly lower to look like a different swing angle
                pygame.draw.ellipse(slash_surf, color, (0, 15, self.attack_hitbox.width, self.attack_hitbox.height - 30))
                
            elif self.combo_step == 3:
                # The big golden finisher
                duration = self.ATTACK_DURATION + 4
                alpha = int(255 * (1 - (self.attack_timer / duration)))
                color = (255, 220, 100, max(0, alpha)) # Golden yellow
                pygame.draw.ellipse(slash_surf, color, (0, 0, self.attack_hitbox.width, self.attack_hitbox.height))
                # Add a core to the big hit
                pygame.draw.ellipse(slash_surf, (255, 255, 255, max(0, alpha)), (10, 10, self.attack_hitbox.width - 20, self.attack_hitbox.height - 20))
            
            surface.blit(slash_surf, self.attack_hitbox.topleft)

# --- 4. MAIN GAME LOOP ---
def main():
    player = Player()
    floor_y = SCREEN_HEIGHT - 60
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            # --- KEYBOARD INPUT ---
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE or event.key == pygame.K_UP or event.key == pygame.K_w:
                    player.jump()
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE or event.key == pygame.K_UP or event.key == pygame.K_w:
                    player.cancel_jump()
            
            # --- MOUSE INPUT ---
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # 1 is the Left Mouse Button
                    player.attack()

        player.update(floor_y)

        draw_background(screen)
        pygame.draw.rect(screen, COLOR_FLOOR, (0, floor_y, SCREEN_WIDTH, SCREEN_HEIGHT - floor_y))
        pygame.draw.rect(screen, COLOR_LEDGE, (0, floor_y, SCREEN_WIDTH, 6)) 
        
        player.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()