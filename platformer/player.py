import pygame
from settings import *
from particles import ParticleSystem


class Player(pygame.sprite.Sprite):
    W, H = 28, 36

    def __init__(self, x, y):
        super().__init__()
        self.rect = pygame.Rect(x, y, self.W, self.H)
        self.vel  = pygame.math.Vector2(0, 0)

        # State
        self.on_ground  = False
        self.on_wall    = 0      # -1 left wall, +1 right wall, 0 none
        self.wall_slide = False
        self.dead       = False
        self.reached_goal = False
        self.invincible = 0      # invincibility frames after hit
        self.hp         = PLAYER_HP

        # Abilities (unlocked by collecting orbs)
        self.has_double_jump = False
        self.has_dash        = False
        self.has_wall_jump   = False

        # Jump state
        self.jumps_left   = 1
        self.coyote_timer = 0
        self.jump_buffer  = 0

        # Dash state
        self.dashing       = False
        self.dash_timer    = 0
        self.dash_cooldown = 0
        self.dash_dir      = 1

        # Animation
        self.facing     = 1
        self.anim_timer = 0
        self.squish_y   = 1.0   # landing squish
        self.squish_x   = 1.0

        # Particles
        self.particles = ParticleSystem()
        self.gems       = 0
        self.score      = 0

        # Screen-shake request
        self.shake = 0

    # ── Input ────────────────────────────────────────────────────────────────

    def handle_keydown(self, key, keys):
        jump_keys  = (pygame.K_SPACE, pygame.K_UP, pygame.K_w)
        dash_keys  = (pygame.K_LSHIFT, pygame.K_z)

        if key in jump_keys:
            self.jump_buffer = JUMP_BUFFER

        if key in dash_keys:
            self._try_dash(keys)

    def _try_dash(self, keys):
        if not self.has_dash:
            return
        if self.dash_cooldown > 0:
            return
        # direction
        left  = keys[pygame.K_LEFT]  or keys[pygame.K_a]
        right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        if left:
            self.dash_dir = -1
        elif right:
            self.dash_dir = 1
        else:
            self.dash_dir = self.facing
        self.dashing     = True
        self.dash_timer  = DASH_FRAMES
        self.dash_cooldown = DASH_COOLDOWN
        self.vel.y = 0
        self.particles.burst(self.rect.centerx, self.rect.centery, ORB_DASH, count=8, speed=5)

    # ── Update ───────────────────────────────────────────────────────────────

    def update(self, level, keys):
        if self.dead or self.reached_goal:
            self.particles.update()
            return

        self.anim_timer += 1
        if self.invincible > 0:
            self.invincible -= 1
        if self.dash_cooldown > 0:
            self.dash_cooldown -= 1

        # Squish decay
        self.squish_y += (1.0 - self.squish_y) * 0.25
        self.squish_x += (1.0 - self.squish_x) * 0.25

        # ── Horizontal input ─────────────────────────────────────────────────
        left  = keys[pygame.K_LEFT]  or keys[pygame.K_a]
        right = keys[pygame.K_RIGHT] or keys[pygame.K_d]

        if self.dashing:
            self.vel.x = self.dash_dir * DASH_SPEED
            self.vel.y = 0
            self.dash_timer -= 1
            if self.dash_timer <= 0:
                self.dashing = False
                self.vel.x *= 0.3
            self.particles.trail(self.rect.centerx, self.rect.centery, ORB_DASH)
        else:
            if right:
                self.vel.x = PLAYER_SPEED
                self.facing = 1
            elif left:
                self.vel.x = -PLAYER_SPEED
                self.facing = -1
            else:
                self.vel.x *= 0.75  # friction

        # ── Wall slide ───────────────────────────────────────────────────────
        self.wall_slide = False
        if self.has_wall_jump and not self.on_ground and self.on_wall != 0:
            if (self.on_wall == 1 and right) or (self.on_wall == -1 and left):
                self.wall_slide = True
                if self.vel.y > 2:
                    self.vel.y = 2          # slide slowly

        # ── Gravity ──────────────────────────────────────────────────────────
        if not self.dashing:
            self.vel.y += GRAVITY
            if self.vel.y > MAX_FALL:
                self.vel.y = MAX_FALL

        # ── Jump (coyote + buffer) ────────────────────────────────────────────
        if self.on_ground:
            self.jumps_left   = 2 if self.has_double_jump else 1
            self.coyote_timer = COYOTE
        else:
            if self.coyote_timer > 0:
                self.coyote_timer -= 1

        if self.jump_buffer > 0:
            self.jump_buffer -= 1
            can_coyote    = self.coyote_timer > 0
            can_walljump  = self.has_wall_jump and self.on_wall != 0 and not self.on_ground
            can_doublejump= self.jumps_left > 0 and not self.on_ground and not can_coyote

            if can_walljump:
                self.vel.y = WALL_JUMP_VY
                self.vel.x = -self.on_wall * WALL_JUMP_VX
                self.facing = -self.on_wall
                self.jumps_left = max(0, self.jumps_left - 1)
                self.coyote_timer = 0
                self.jump_buffer  = 0
                self.particles.burst(self.rect.centerx, self.rect.bottom, ORB_WJ, count=8, speed=3)
            elif can_coyote or self.on_ground:
                self.vel.y = JUMP_VEL
                self.jumps_left = max(0, self.jumps_left - 1)
                self.coyote_timer = 0
                self.jump_buffer  = 0
                # Landing squish
                self.squish_y = 0.6
                self.squish_x = 1.4
                self.particles.burst(self.rect.centerx, self.rect.bottom, PLAYER_C, count=6, speed=3)
            elif can_doublejump:
                self.vel.y = JUMP_VEL * 0.9
                self.jumps_left -= 1
                self.jump_buffer = 0
                self.particles.burst(self.rect.centerx, self.rect.centery, ORB_DJ, count=10, speed=4)

        # ── Move & collide ───────────────────────────────────────────────────
        self.on_ground = False
        self.on_wall   = 0

        # Horizontal
        self.rect.x += int(self.vel.x)
        self._collide_h(level)

        # Vertical
        self.rect.y += int(self.vel.y)
        self._collide_v(level)

        # Level bounds – kill if fallen off
        if self.rect.top > level.pixel_h + 200:
            self._die()

        self.particles.update()

    def _collide_h(self, level):
        for tile in level.solid_near(self.rect):
            if self.rect.colliderect(tile):
                if self.vel.x > 0:
                    self.rect.right = tile.left
                    self.on_wall = 1
                elif self.vel.x < 0:
                    self.rect.left = tile.right
                    self.on_wall = -1
                self.vel.x = 0

    def _collide_v(self, level):
        for tile in level.solid_near(self.rect):
            if self.rect.colliderect(tile):
                if self.vel.y > 0:
                    self.rect.bottom = tile.top
                    self.on_ground = True
                    if self.vel.y > 8:
                        # landing squish
                        self.squish_y = 0.55
                        self.squish_x = 1.45
                    self.vel.y = 0
                elif self.vel.y < 0:
                    self.rect.top = tile.bottom
                    self.vel.y = 0
        # One-way platforms
        for tile in level.oneway_near(self.rect):
            if self.vel.y > 0 and self.rect.bottom - self.vel.y <= tile.top + 2:
                if self.rect.colliderect(tile):
                    self.rect.bottom = tile.top
                    self.on_ground = True
                    self.vel.y = 0

    # ── Damage / death ───────────────────────────────────────────────────────

    def take_damage(self, amount=1):
        if self.invincible > 0:
            return
        self.hp -= amount
        self.invincible = 60
        self.shake = 8
        self.particles.burst(self.rect.centerx, self.rect.centery, HEALTH_C, count=14, speed=5)
        if self.hp <= 0:
            self._die()

    def _die(self):
        self.dead = True
        self.particles.burst(self.rect.centerx, self.rect.centery, PLAYER_C, count=20, speed=6)

    # ── Draw ─────────────────────────────────────────────────────────────────

    def draw(self, surface, camera):
        if self.dead:
            self.particles.draw(surface, camera.offset.x, camera.offset.y)
            return

        sx, sy = camera.world_to_screen(self.rect.x, self.rect.y)
        w, h = self.W, self.H

        # Squish / stretch
        draw_w = int(w * self.squish_x)
        draw_h = int(h * self.squish_y)
        dx = (w - draw_w) // 2
        dy = h - draw_h

        body_rect = pygame.Rect(sx + dx, sy + dy, draw_w, draw_h)

        # Flash when invincible
        if self.invincible > 0 and (self.invincible // 4) % 2 == 0:
            self.particles.draw(surface, camera.offset.x, camera.offset.y)
            return

        # Shadow
        pygame.draw.ellipse(surface, SHADOW_C,
                            pygame.Rect(sx + 2, sy + h - 6, w - 4, 8))

        # Body
        pygame.draw.rect(surface, PLAYER_C, body_rect, border_radius=5)

        # Eye
        eye_x = sx + (w // 2) + self.facing * 5
        eye_y = sy + dy + draw_h // 3
        pygame.draw.circle(surface, (255, 255, 255), (eye_x, eye_y), 4)
        pygame.draw.circle(surface, (10, 8, 20),     (eye_x + self.facing, eye_y), 2)

        # Dash glow
        if self.dashing:
            glow = pygame.Surface((draw_w + 16, draw_h + 16), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*ORB_DASH, 80),
                             glow.get_rect(), border_radius=8)
            surface.blit(glow, (sx + dx - 8, sy + dy - 8))

        # Wall-slide sparkle
        if self.wall_slide:
            self.particles.trail(self.rect.centerx, self.rect.centery, ORB_WJ)

        self.particles.draw(surface, camera.offset.x, camera.offset.y)
