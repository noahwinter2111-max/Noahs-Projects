import pygame
from settings import *
from entities import Crawler, Jumper, Boss, Orb, Gem, HealthPack, Goal

_ORB_MAP = {'d': 'double_jump', 's': 'dash', 'w': 'wall_jump'}


class Level:
    def __init__(self, data, carried_abilities=None):
        self.tiles_solid  = []   # list of Rect
        self.tiles_oneway = []   # one-way platforms
        self.tiles_spike  = []   # deadly spikes
        self.enemies      = []
        self.orbs         = []
        self.gems         = []
        self.health_packs = []
        self.goal         = None
        self.spawn        = (TILE, TILE)

        self._parse(data)

        # Carry abilities from previous level
        self._carry = carried_abilities or {}

    def _parse(self, data):
        rows = data
        self.tile_rows = len(rows)
        self.tile_cols = max(len(r) for r in rows)
        self.pixel_w   = self.tile_cols * TILE
        self.pixel_h   = self.tile_rows * TILE

        for row_i, row in enumerate(rows):
            for col_i, ch in enumerate(row):
                x = col_i * TILE
                y = row_i * TILE

                if ch == '#':
                    self.tiles_solid.append(pygame.Rect(x, y, TILE, TILE))
                elif ch == '-':
                    self.tiles_oneway.append(pygame.Rect(x, y, TILE, 8))
                elif ch == '^':
                    self.tiles_spike.append(pygame.Rect(x + 4, y + TILE - 12, TILE - 8, 12))
                elif ch == 'P':
                    self.spawn = (x + TILE // 2 - 14, y)
                elif ch == 'G':
                    self.goal = Goal(x + 2, y)
                elif ch in _ORB_MAP:
                    self.orbs.append(Orb(x + TILE // 2 - 14, y + TILE // 2 - 14, _ORB_MAP[ch]))
                elif ch == '*':
                    self.gems.append(Gem(x + TILE // 2 - 8, y + TILE // 2 - 8))
                elif ch == 'h':
                    self.health_packs.append(HealthPack(x + 10, y + 10))
                elif ch == 'e':
                    self.enemies.append(Crawler(x, y))
                elif ch == 'j':
                    self.enemies.append(Jumper(x, y))
                elif ch == 'b':
                    self.enemies.append(Boss(x, y))

    # ── Spatial helpers ──────────────────────────────────────────────────────

    def solid_near(self, rect):
        """Return solid tile rects that are nearby (cheap broadphase)."""
        margin = TILE * 2
        return [t for t in self.tiles_solid
                if abs(t.centerx - rect.centerx) < rect.width  + margin and
                   abs(t.centery - rect.centery) < rect.height + margin]

    def oneway_near(self, rect):
        margin = TILE * 2
        return [t for t in self.tiles_oneway
                if abs(t.centerx - rect.centerx) < rect.width  + margin and
                   abs(t.centery - rect.centery) < rect.height + margin]

    # ── Update ───────────────────────────────────────────────────────────────

    def update(self, player):
        # Orbs
        for orb in self.orbs:
            orb.update(player)
        self.orbs = [o for o in self.orbs if not o.dead]

        # Gems
        for gem in self.gems:
            gem.update(player)
        self.gems = [g for g in self.gems if not g.dead]

        # Health packs
        for hp in self.health_packs:
            hp.update(player)
        self.health_packs = [h for h in self.health_packs if not h.dead]

        # Stomping enemies (player lands on top)
        if player.vel.y > 0:
            for en in self.enemies:
                if en.dead:
                    continue
                if (player.rect.colliderect(en.rect) and
                        player.rect.bottom <= en.rect.top + 14):
                    en.take_hit()
                    player.vel.y = JUMP_VEL * 0.5
                    player.score += 100

        # Update living enemies; update dead ones' particles until empty
        for en in self.enemies:
            if en.dead:
                en.particles.update()
            else:
                en.update(self, player)

        self.enemies = [
            e for e in self.enemies
            if not e.dead or bool(e.particles.particles)
        ]

        # Spikes
        for spike in self.tiles_spike:
            if player.rect.colliderect(spike) and player.invincible == 0:
                player.take_damage()

        # Goal
        if self.goal:
            self.goal.update(player)

    # ── Draw ─────────────────────────────────────────────────────────────────

    def draw(self, surface, camera):
        # Background parallax layers
        _draw_bg(surface, camera)

        # Solid tiles
        for tile in self.tiles_solid:
            r = camera.apply(tile)
            if -TILE < r.x < SCREEN_W + TILE and -TILE < r.y < SCREEN_H + TILE:
                pygame.draw.rect(surface, TILE_C,  r)
                pygame.draw.rect(surface, TILE_HI, r, 2)

        # One-way platforms
        for tile in self.tiles_oneway:
            r = camera.apply(tile)
            if -TILE < r.x < SCREEN_W + TILE and -TILE < r.y < SCREEN_H + TILE:
                pygame.draw.rect(surface, PLAT_C,  r)
                pygame.draw.rect(surface, PLAT_HI, pygame.Rect(r.x, r.y, r.w, 3))

        # Spikes
        for spike in self.tiles_spike:
            r = camera.apply(spike)
            if -TILE < r.x < SCREEN_W + TILE:
                # Draw triangle spikes
                n = r.w // 10
                for i in range(n):
                    bx = r.x + i * 10
                    pygame.draw.polygon(surface, SPIKE_C, [
                        (bx, r.bottom), (bx + 5, r.top), (bx + 10, r.bottom)
                    ])

        # Goal
        if self.goal:
            self.goal.draw(surface, camera)

        # Collectibles
        for orb in self.orbs:
            orb.draw(surface, camera)
        for gem in self.gems:
            gem.draw(surface, camera)
        for hp in self.health_packs:
            hp.draw(surface, camera)

        # Enemies
        for en in self.enemies:
            en.draw(surface, camera)


# ── Background ───────────────────────────────────────────────────────────────

_stars = None

def _init_stars():
    import random
    global _stars
    _stars = [(random.randint(0, 1280), random.randint(0, 720),
               random.randint(1, 3), random.uniform(0.1, 0.5))
              for _ in range(120)]

def _draw_bg(surface, camera):
    global _stars
    if _stars is None:
        _init_stars()
    surface.fill(BG)
    for sx, sy, size, parallax in _stars:
        px = int(sx - camera.offset.x * parallax) % SCREEN_W
        py = int(sy - camera.offset.y * parallax) % SCREEN_H
        brightness = 120 + size * 30
        pygame.draw.circle(surface, (brightness, brightness, brightness + 20),
                           (px, py), size)
