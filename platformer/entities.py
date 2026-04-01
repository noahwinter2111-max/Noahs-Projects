import pygame
import math
import random
from settings import *
from particles import ParticleSystem


# ── Base ─────────────────────────────────────────────────────────────────────

class Entity(pygame.sprite.Sprite):
    def __init__(self, x, y, w, h, color):
        super().__init__()
        self.rect  = pygame.Rect(x, y, w, h)
        self.color = color
        self.dead  = False

    def draw(self, surface, camera):
        pass


# ── Enemies ───────────────────────────────────────────────────────────────────

class Crawler(Entity):
    """Patrols horizontally; turns at edges / walls."""
    W, H = 32, 26

    def __init__(self, x, y):
        super().__init__(x, y, self.W, self.H, ENEMY_C)
        self.vel_x  = 1.5
        self.vel_y  = 0
        self.hp     = 2
        self.hurt   = 0         # hurt flash frames
        self.particles = ParticleSystem()

    def update(self, level, player):
        self.particles.update()
        if self.hurt > 0:
            self.hurt -= 1

        # gravity
        self.vel_y = min(self.vel_y + GRAVITY, MAX_FALL)

        # move h
        self.rect.x += int(self.vel_x)
        for tile in level.solid_near(self.rect):
            if self.rect.colliderect(tile):
                if self.vel_x > 0:
                    self.rect.right = tile.left
                elif self.vel_x < 0:
                    self.rect.left = tile.right
                self.vel_x *= -1

        # move v
        on_ground = False
        self.rect.y += int(self.vel_y)
        for tile in level.solid_near(self.rect):
            if self.rect.colliderect(tile):
                if self.vel_y > 0:
                    self.rect.bottom = tile.top
                    on_ground = True
                    self.vel_y = 0
                elif self.vel_y < 0:
                    self.rect.top = tile.bottom
                    self.vel_y = 0

        # turn at ledge
        if on_ground:
            probe = pygame.Rect(
                self.rect.right if self.vel_x > 0 else self.rect.left - 2,
                self.rect.bottom + 2, 2, 2)
            at_edge = True
            for tile in level.solid_near(probe):
                if probe.colliderect(tile):
                    at_edge = False
            if at_edge:
                self.vel_x *= -1

        # hurt player
        if self.rect.colliderect(player.rect) and player.invincible == 0:
            player.take_damage()

    def take_hit(self):
        self.hp -= 1
        self.hurt = 15
        self.particles.burst(self.rect.centerx, self.rect.centery, (255, 160, 80), count=8)
        if self.hp <= 0:
            self.particles.burst(self.rect.centerx, self.rect.centery, ENEMY_C, count=16, speed=5)
            self.dead = True

    def draw(self, surface, camera):
        if self.dead:
            self.particles.draw(surface, camera.offset.x, camera.offset.y)
            return
        r = camera.apply(self.rect)
        col = (255, 200, 100) if self.hurt > 0 else self.color
        pygame.draw.rect(surface, col, r, border_radius=4)
        # eyes
        for side in (-6, 6):
            ex = r.centerx + side
            ey = r.centery - 3
            pygame.draw.circle(surface, (255, 255, 255), (ex, ey), 4)
            pygame.draw.circle(surface, (10, 8, 20), (ex, ey), 2)
        # HP bar
        bar_w = int((self.hp / 2) * self.W)
        pygame.draw.rect(surface, (200, 50, 50), pygame.Rect(r.x, r.y - 6, self.W, 4))
        pygame.draw.rect(surface, (80, 220, 80),  pygame.Rect(r.x, r.y - 6, bar_w, 4))
        self.particles.draw(surface, camera.offset.x, camera.offset.y)


class Jumper(Entity):
    """Bounces around the platform."""
    W, H = 24, 24

    def __init__(self, x, y):
        super().__init__(x, y, self.W, self.H, (220, 100, 180))
        self.vel_x  = random.choice([-1.5, 1.5])
        self.vel_y  = 0
        self.hp     = 1
        self.hurt   = 0
        self.jump_t = random.randint(30, 80)
        self.particles = ParticleSystem()

    def update(self, level, player):
        self.particles.update()
        if self.hurt > 0:
            self.hurt -= 1
        self.jump_t -= 1

        self.vel_y = min(self.vel_y + GRAVITY, MAX_FALL)

        self.rect.x += int(self.vel_x)
        for tile in level.solid_near(self.rect):
            if self.rect.colliderect(tile):
                if self.vel_x > 0:
                    self.rect.right = tile.left
                elif self.vel_x < 0:
                    self.rect.left = tile.right
                self.vel_x *= -1

        on_ground = False
        self.rect.y += int(self.vel_y)
        for tile in level.solid_near(self.rect):
            if self.rect.colliderect(tile):
                if self.vel_y > 0:
                    self.rect.bottom = tile.top
                    on_ground = True
                    self.vel_y = 0
                elif self.vel_y < 0:
                    self.rect.top = tile.bottom
                    self.vel_y = 0

        if on_ground and self.jump_t <= 0:
            self.vel_y = JUMP_VEL * 0.85
            self.jump_t = random.randint(40, 90)
            self.particles.burst(self.rect.centerx, self.rect.bottom, (220, 100, 180), count=6)

        if self.rect.colliderect(player.rect) and player.invincible == 0:
            player.take_damage()

    def take_hit(self):
        self.hp -= 1
        self.hurt = 15
        self.particles.burst(self.rect.centerx, self.rect.centery, (255, 160, 200), count=8)
        if self.hp <= 0:
            self.particles.burst(self.rect.centerx, self.rect.centery, (220, 100, 180), count=14, speed=5)
            self.dead = True

    def draw(self, surface, camera):
        if self.dead:
            self.particles.draw(surface, camera.offset.x, camera.offset.y)
            return
        r = camera.apply(self.rect)
        col = (255, 200, 100) if self.hurt > 0 else self.color
        pygame.draw.ellipse(surface, col, r)
        self.particles.draw(surface, camera.offset.x, camera.offset.y)


# ── Boss ─────────────────────────────────────────────────────────────────────

class Boss(Entity):
    """Multi-phase boss: charges + shoots projectiles."""
    W, H = 64, 64
    MAX_HP = 12

    def __init__(self, x, y):
        super().__init__(x, y, self.W, self.H, BOSS_C)
        self.hp      = self.MAX_HP
        self.vel_x   = 0
        self.vel_y   = 0
        self.hurt    = 0
        self.phase   = 1           # 1 or 2 (phase 2 below half HP)
        self.timer   = 0
        self.state   = "idle"      # idle | charge | shoot | rest
        self.projectiles = []
        self.particles   = ParticleSystem()
        self.spawn_x = x           # home position
        self._next_action()

    # ── AI ───────────────────────────────────────────────────────────────────

    def _next_action(self):
        self.timer = 90
        if self.phase == 1:
            self.state = random.choice(["charge", "shoot"])
        else:
            self.state = random.choice(["charge", "shoot", "shoot"])

    def update(self, level, player):
        self.particles.update()
        for p in self.projectiles:
            p.update()
        self.projectiles = [p for p in self.projectiles if p.alive]

        if self.hurt > 0:
            self.hurt -= 1

        # Phase 2 threshold
        if self.hp <= self.MAX_HP // 2:
            self.phase = 2

        self.timer -= 1
        if self.timer <= 0:
            self._execute_action(player)
            self._next_action()

        # Gravity
        self.vel_y = min(self.vel_y + GRAVITY * 0.8, MAX_FALL)

        # Move
        if self.state == "charge":
            spd = 4 if self.phase == 1 else 6
            dx = player.rect.centerx - self.rect.centerx
            self.vel_x = spd if dx > 0 else -spd
        else:
            # drift back home
            dx = self.spawn_x - self.rect.x
            self.vel_x = max(-2, min(2, dx * 0.05))

        self.rect.x += int(self.vel_x)
        for tile in level.solid_near(self.rect):
            if self.rect.colliderect(tile):
                if self.vel_x > 0:
                    self.rect.right = tile.left
                elif self.vel_x < 0:
                    self.rect.left = tile.right
                self.vel_x = 0

        self.rect.y += int(self.vel_y)
        for tile in level.solid_near(self.rect):
            if self.rect.colliderect(tile):
                if self.vel_y > 0:
                    self.rect.bottom = tile.top
                    self.vel_y = 0
                elif self.vel_y < 0:
                    self.rect.top = tile.bottom
                    self.vel_y = 0

        # Hurt player contact
        if self.rect.colliderect(player.rect) and player.invincible == 0:
            player.take_damage()

        # Projectile hit player
        for p in self.projectiles:
            if p.rect.colliderect(player.rect) and player.invincible == 0:
                player.take_damage()
                p.alive = False

    def _execute_action(self, player):
        if self.state == "shoot":
            count = 3 if self.phase == 1 else 5
            cx, cy = self.rect.centerx, self.rect.centery
            spread = math.tau / count
            for i in range(count):
                angle = i * spread
                spd = 4 + self.phase
                vx = math.cos(angle) * spd
                vy = math.sin(angle) * spd
                self.projectiles.append(Projectile(cx, cy, vx, vy))
        elif self.state == "charge":
            # jump toward player
            if self.rect.bottom >= self.rect.bottom:  # always true; just jump
                self.vel_y = JUMP_VEL * 0.8

    def take_hit(self):
        self.hp -= 1
        self.hurt = 20
        self.particles.burst(self.rect.centerx, self.rect.centery, (255, 160, 80), count=12, speed=6)
        if self.hp <= 0:
            self.dead = True
            self.particles.burst(self.rect.centerx, self.rect.centery, BOSS_C, count=30, speed=8)

    def draw(self, surface, camera):
        if self.dead:
            self.particles.draw(surface, camera.offset.x, camera.offset.y)
            for p in self.projectiles:
                p.draw(surface, camera)
            return

        r = camera.apply(self.rect)
        col = (255, 200, 100) if self.hurt > 0 else (self.color if self.phase == 1 else (255, 80, 20))
        pygame.draw.rect(surface, col, r, border_radius=8)

        # Crown / horns
        for side in (-20, 20):
            hx = r.centerx + side
            pygame.draw.rect(surface, col,
                             pygame.Rect(hx - 5, r.top - 16, 10, 18), border_radius=3)

        # Eyes
        for side in (-14, 14):
            ex = r.centerx + side
            ey = r.centery - 8
            pygame.draw.circle(surface, (255, 240, 50), (ex, ey), 7)
            pygame.draw.circle(surface, (10, 8, 20), (ex, ey), 3)

        # HP bar (full width)
        bar_y = r.bottom + 6
        bw    = self.W * 2
        bx    = r.centerx - bw // 2
        pygame.draw.rect(surface, (100, 30, 30), pygame.Rect(bx, bar_y, bw, 8))
        fill_w = int((self.hp / self.MAX_HP) * bw)
        pygame.draw.rect(surface, (220, 50, 50), pygame.Rect(bx, bar_y, fill_w, 8))
        pygame.draw.rect(surface, (255, 100, 100), pygame.Rect(bx, bar_y, bw, 8), 1)

        for p in self.projectiles:
            p.draw(surface, camera)
        self.particles.draw(surface, camera.offset.x, camera.offset.y)


class Projectile:
    def __init__(self, x, y, vx, vy):
        self.rect  = pygame.Rect(x - 6, y - 6, 12, 12)
        self.vx    = vx
        self.vy    = vy
        self.alive = True
        self.life  = 180

    def update(self):
        self.rect.x += int(self.vx)
        self.rect.y += int(self.vy)
        self.life -= 1
        if self.life <= 0:
            self.alive = False

    def draw(self, surface, camera):
        r = camera.apply(self.rect)
        t = self.life / 180
        c = (int(255 * t), int(100 * t), int(20 * t))
        pygame.draw.circle(surface, c, r.center, 6)
        pygame.draw.circle(surface, (255, 255, 200), r.center, 3)


# ── Collectibles ─────────────────────────────────────────────────────────────

class Orb(Entity):
    """Ability-unlock orb."""
    R = 14

    def __init__(self, x, y, kind):
        super().__init__(x, y, self.R * 2, self.R * 2, _orb_color(kind))
        self.kind      = kind     # 'double_jump' | 'dash' | 'wall_jump'
        self.timer     = 0
        self.collected = False
        self.particles = ParticleSystem()

    def update(self, player):
        self.timer += 1
        self.particles.update()
        if self.collected:
            return
        # Bob
        self.rect.y = self.rect.y  # position managed in level parse; we just bob visually
        if self.rect.colliderect(player.rect):
            self._collect(player)

    def _collect(self, player):
        self.collected = True
        self.dead = True
        if self.kind == 'double_jump':
            player.has_double_jump = True
        elif self.kind == 'dash':
            player.has_dash = True
        elif self.kind == 'wall_jump':
            player.has_wall_jump = True
        player.particles.burst(self.rect.centerx, self.rect.centery, self.color, count=20, speed=6)

    def draw(self, surface, camera):
        if self.dead:
            self.particles.draw(surface, camera.offset.x, camera.offset.y)
            return
        sx, sy = camera.world_to_screen(self.rect.x, self.rect.y)
        cx = sx + self.R
        cy = sy + self.R + int(math.sin(self.timer * 0.05) * 4)
        # Glow
        glow_surf = pygame.Surface((self.R * 4, self.R * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*self.color, 60), (self.R * 2, self.R * 2), self.R * 2)
        surface.blit(glow_surf, (cx - self.R * 2, cy - self.R * 2))
        # Core
        pygame.draw.circle(surface, self.color, (cx, cy), self.R)
        pygame.draw.circle(surface, (255, 255, 255), (cx - 4, cy - 4), 5)
        self.particles.draw(surface, camera.offset.x, camera.offset.y)


class Gem(Entity):
    R = 8

    def __init__(self, x, y):
        super().__init__(x, y, self.R * 2, self.R * 2, GEM_C)
        self.timer = 0
        self.particles = ParticleSystem()

    def update(self, player):
        self.timer += 1
        self.particles.update()
        if self.rect.colliderect(player.rect):
            player.gems += 1
            player.score += 50
            self.particles.burst(self.rect.centerx, self.rect.centery, GEM_C, count=8, speed=4)
            self.dead = True

    def draw(self, surface, camera):
        if self.dead:
            self.particles.draw(surface, camera.offset.x, camera.offset.y)
            return
        sx, sy = camera.world_to_screen(self.rect.x, self.rect.y)
        cx = sx + self.R
        cy = sy + self.R + int(math.sin(self.timer * 0.07 + 1.0) * 3)
        pygame.draw.polygon(surface, GEM_C, [
            (cx, cy - self.R), (cx + self.R, cy),
            (cx, cy + self.R), (cx - self.R, cy),
        ])
        pygame.draw.circle(surface, (255, 255, 200), (cx - 2, cy - 3), 3)
        self.particles.draw(surface, camera.offset.x, camera.offset.y)


class HealthPack(Entity):
    W, H = 20, 20

    def __init__(self, x, y):
        super().__init__(x, y, self.W, self.H, HEALTH_C)
        self.timer = 0
        self.particles = ParticleSystem()

    def update(self, player):
        self.timer += 1
        self.particles.update()
        if self.rect.colliderect(player.rect):
            if player.hp < PLAYER_HP:
                player.hp = min(PLAYER_HP, player.hp + 1)
                self.particles.burst(self.rect.centerx, self.rect.centery, HEALTH_C, count=10, speed=4)
                self.dead = True

    def draw(self, surface, camera):
        if self.dead:
            self.particles.draw(surface, camera.offset.x, camera.offset.y)
            return
        r = camera.apply(self.rect)
        pulse = 1.0 + 0.15 * math.sin(self.timer * 0.1)
        pw = int(self.W * pulse)
        ph = int(self.H * pulse)
        pr = pygame.Rect(r.centerx - pw // 2, r.centery - ph // 2, pw, ph)
        pygame.draw.rect(surface, HEALTH_C, pr, border_radius=4)
        # cross
        pygame.draw.rect(surface, (255, 255, 255),
                         pygame.Rect(pr.centerx - 2, pr.y + 4, 4, ph - 8))
        pygame.draw.rect(surface, (255, 255, 255),
                         pygame.Rect(pr.x + 4, pr.centery - 2, pw - 8, 4))
        self.particles.draw(surface, camera.offset.x, camera.offset.y)


class Goal(Entity):
    W, H = 36, 48

    def __init__(self, x, y):
        super().__init__(x, y, self.W, self.H, GOAL_C)
        self.timer = 0

    def update(self, player):
        self.timer += 1
        if self.rect.colliderect(player.rect):
            player.reached_goal = True
            player.score += 500

    def draw(self, surface, camera):
        sx, sy = camera.world_to_screen(self.rect.x, self.rect.y)
        cx = sx + self.W // 2
        t  = self.timer

        # Glowing portal ring
        for i in range(4, 0, -1):
            alpha = 40 * i
            radius = self.W // 2 + i * 5 + int(math.sin(t * 0.05) * 3)
            glow = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*GOAL_C, alpha),
                               (radius + 2, radius + 2), radius, 3)
            surface.blit(glow, (cx - radius - 2, sy + self.H // 2 - radius - 2))

        pygame.draw.circle(surface, GOAL_C, (cx, sy + self.H // 2), self.W // 2 - 2)
        pygame.draw.circle(surface, (255, 255, 255), (cx, sy + self.H // 2), self.W // 2 - 6)

        # Arrow inside
        ay = sy + self.H // 2 + int(math.sin(t * 0.07) * 4)
        pygame.draw.polygon(surface, GOAL_C, [
            (cx, ay - 8), (cx + 8, ay + 4), (cx - 8, ay + 4),
        ])


# ── Helpers ──────────────────────────────────────────────────────────────────

def _orb_color(kind):
    return {'double_jump': ORB_DJ, 'dash': ORB_DASH, 'wall_jump': ORB_WJ}.get(kind, (200, 200, 200))
