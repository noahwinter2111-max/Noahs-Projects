import pygame
from settings import SCREEN_W, SCREEN_H, TILE


class Camera:
    def __init__(self, level_w, level_h):
        self.offset = pygame.math.Vector2(0, 0)
        self.lw = level_w
        self.lh = level_h

    def update(self, target):
        # Centre the camera on the target
        tx = target.rect.centerx - SCREEN_W // 2
        ty = target.rect.centery - SCREEN_H // 2
        # Clamp so we never show outside the level
        self.offset.x = max(0, min(tx, self.lw - SCREEN_W))
        self.offset.y = max(0, min(ty, self.lh - SCREEN_H))

    def apply(self, rect):
        """Return a screen-space rect for a world-space rect."""
        return rect.move(-self.offset.x, -self.offset.y)

    def world_to_screen(self, x, y):
        return int(x - self.offset.x), int(y - self.offset.y)
