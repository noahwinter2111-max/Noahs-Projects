import pygame
import sys

from settings import *
from player  import Player
from level   import Level
from camera  import Camera
from ui      import UI
from levels  import ALL_LEVELS


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("LUMIA")
        self.clock  = pygame.time.Clock()
        self.ui     = UI(self.screen)
        self.state  = "menu"
        self.current_level_idx = 0
        self.total_gems = 0
        self._shake  = 0       # screen-shake frames
        self._shake_dx = 0
        self._shake_dy = 0
        self.player  = None
        self.level   = None
        self.camera  = None
        self.name_timer = 0

    # ── Level loading ─────────────────────────────────────────────────────────

    def _load_level(self, idx):
        data = ALL_LEVELS[idx]

        # Carry over abilities from previous player
        carried = {}
        if self.player:
            carried = {
                'double_jump': self.player.has_double_jump,
                'dash':        self.player.has_dash,
                'wall_jump':   self.player.has_wall_jump,
            }

        self.level  = Level(data)
        self.player = Player(*self.level.spawn)

        # Restore carried abilities
        if carried.get('double_jump'):
            self.player.has_double_jump = True
        if carried.get('dash'):
            self.player.has_dash = True
        if carried.get('wall_jump'):
            self.player.has_wall_jump = True

        self.camera = Camera(self.level.pixel_w, self.level.pixel_h)
        self.name_timer = 200

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        while True:
            self.clock.tick(FPS)
            self.ui.tick()
            self._handle_events()
            self._update()
            self._draw()

    # ── Events ────────────────────────────────────────────────────────────────

    def _handle_events(self):
        keys = pygame.key.get_pressed()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                if self.state == "menu":
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.current_level_idx = 0
                        self.total_gems = 0
                        self._load_level(0)
                        self.state = "playing"

                elif self.state == "playing":
                    if event.key == pygame.K_ESCAPE:
                        self.state = "paused"
                    else:
                        self.player.handle_keydown(event.key, keys)

                elif self.state == "paused":
                    if event.key == pygame.K_ESCAPE:
                        self.state = "playing"

                elif self.state == "dead":
                    if event.key == pygame.K_r:
                        self._load_level(self.current_level_idx)
                        self.state = "playing"
                    elif event.key == pygame.K_m:
                        self.state = "menu"

                elif self.state == "level_complete":
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.current_level_idx += 1
                        if self.current_level_idx >= len(ALL_LEVELS):
                            self.state = "win"
                        else:
                            self._load_level(self.current_level_idx)
                            self.state = "playing"

                elif self.state == "win":
                    if event.key == pygame.K_m:
                        self.player = None
                        self.state = "menu"

    # ── Update ────────────────────────────────────────────────────────────────

    def _update(self):
        if self.state != "playing":
            return

        keys = pygame.key.get_pressed()
        self.player.update(self.level, keys)
        self.level.update(self.player)
        self.camera.update(self.player)

        if self.name_timer > 0:
            self.name_timer -= 1

        # Screen shake from player
        if self.player.shake > 0:
            self._shake = self.player.shake
            self.player.shake = 0

        if self._shake > 0:
            self._shake -= 1
            import random
            self._shake_dx = random.randint(-4, 4) * (self._shake / 10)
            self._shake_dy = random.randint(-4, 4) * (self._shake / 10)
        else:
            self._shake_dx = 0
            self._shake_dy = 0

        # State transitions
        if self.player.dead:
            self.total_gems += self.player.gems
            self.state = "dead"
        elif self.player.reached_goal:
            self.total_gems += self.player.gems
            self.state = "level_complete"

    # ── Draw ─────────────────────────────────────────────────────────────────

    def _draw(self):
        if self.state == "menu":
            self.ui.draw_menu(self.total_gems)

        elif self.state in ("playing", "paused", "dead", "level_complete"):
            # 1. Render world to a temp surface so we can apply screen shake
            world = pygame.Surface((SCREEN_W, SCREEN_H))
            self.level.draw(world, self.camera)
            self.player.draw(world, self.camera)

            # 2. Blit world to screen with shake offset
            self.screen.fill(BG)
            self.screen.blit(world, (int(self._shake_dx), int(self._shake_dy)))

            # 3. HUD drawn on top of screen (no shake)
            self.ui.draw_hud(
                self.player,
                LEVEL_NAMES[self.current_level_idx],
                self.name_timer,
            )

            # 4. Full-screen overlays
            if self.state == "paused":
                self.ui.draw_pause()
            elif self.state == "dead":
                self.ui.draw_death(self.total_gems)
            elif self.state == "level_complete":
                has_next = self.current_level_idx + 1 < len(ALL_LEVELS)
                self.ui.draw_level_complete(has_next)

        elif self.state == "win":
            self.ui.draw_win(self.total_gems)

        pygame.display.flip()


if __name__ == "__main__":
    game = Game()
    game.run()
