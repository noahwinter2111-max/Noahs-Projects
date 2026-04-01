import pygame
import math
from settings import *


def _font(size):
    return pygame.font.SysFont("monospace", size, bold=True)


class UI:
    def __init__(self, surface):
        self.surface = surface
        self.big    = _font(64)
        self.med    = _font(32)
        self.small  = _font(22)
        self.tiny   = _font(16)
        self._tick  = 0

    def tick(self):
        self._tick += 1

    # ── HUD ──────────────────────────────────────────────────────────────────

    def draw_hud(self, player, level_name, name_timer):
        s = self.surface

        # ── HP hearts ─────────────────────────────────────────────
        for i in range(PLAYER_HP):
            x = 20 + i * 32
            y = 18
            filled = i < player.hp
            col = HEALTH_C if filled else (60, 30, 40)
            _draw_heart(s, x, y, 24, col)

        # ── Ability icons ─────────────────────────────────────────
        icons = [
            (player.has_double_jump, ORB_DJ,   "2x"),
            (player.has_dash,        ORB_DASH,  ">>"),
            (player.has_wall_jump,   ORB_WJ,    "|^"),
        ]
        for i, (unlocked, col, label) in enumerate(icons):
            ix = 20 + i * 58
            iy = SCREEN_H - 52
            alpha = 255 if unlocked else 60
            glow = pygame.Surface((44, 44), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*col, alpha // 3), glow.get_rect(), border_radius=6)
            pygame.draw.rect(glow, (*col, alpha),      glow.get_rect(), 2, border_radius=6)
            s.blit(glow, (ix, iy))
            lbl = self.tiny.render(label, True, (*col, alpha) if unlocked else (80, 80, 100))
            s.blit(lbl, (ix + 8, iy + 13))

        # Dash cooldown bar
        if player.has_dash and player.dash_cooldown > 0:
            frac = 1.0 - player.dash_cooldown / DASH_COOLDOWN
            pygame.draw.rect(s, (60, 40, 20),  pygame.Rect(20, SCREEN_H - 14, 150, 8), border_radius=4)
            pygame.draw.rect(s, ORB_DASH, pygame.Rect(20, SCREEN_H - 14, int(150 * frac), 8), border_radius=4)

        # ── Gems / score ───────────────────────────────────────────
        gem_txt = self.small.render(f"★ {player.gems}", True, GEM_C)
        s.blit(gem_txt, (SCREEN_W - 120, 18))

        # ── Level name fade ────────────────────────────────────────
        if name_timer > 0:
            alpha = min(255, name_timer * 5)
            lbl = self.med.render(level_name, True, TEXT_C)
            lbl.set_alpha(alpha)
            s.blit(lbl, (SCREEN_W // 2 - lbl.get_width() // 2, 24))

    # ── Screens ──────────────────────────────────────────────────────────────

    def draw_menu(self, gems=0):
        s = self.surface
        s.fill(BG)
        t = self._tick

        # Animated title
        title_y = SCREEN_H // 3 + int(math.sin(t * 0.03) * 6)
        self._shadow_text(self.big, "LUMIA", SCREEN_W // 2, title_y, TEXT_C)

        sub = self.med.render("A platformer of light and shadow", True, (150, 140, 190))
        s.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2, title_y + 80))

        # Blinking prompt
        if (t // 30) % 2 == 0:
            prompt = self.med.render("PRESS  ENTER  TO  START", True, (200, 180, 255))
            s.blit(prompt, (SCREEN_W // 2 - prompt.get_width() // 2, SCREEN_H // 2 + 60))

        controls = [
            "WASD / Arrows  –  Move",
            "SPACE / W      –  Jump",
            "SHIFT / Z      –  Dash  (when unlocked)",
        ]
        for i, line in enumerate(controls):
            txt = self.tiny.render(line, True, (120, 110, 150))
            s.blit(txt, (SCREEN_W // 2 - txt.get_width() // 2, SCREEN_H - 140 + i * 24))

        if gems:
            gem_txt = self.small.render(f"Total gems: {gems}", True, GEM_C)
            s.blit(gem_txt, (SCREEN_W // 2 - gem_txt.get_width() // 2, SCREEN_H - 60))

    def draw_death(self, gems):
        self._overlay()
        s = self.surface
        self._shadow_text(self.big, "YOU  DIED", SCREEN_W // 2, SCREEN_H // 2 - 80, (220, 80, 80))
        sub = self.med.render(f"Gems collected: {gems}", True, GEM_C)
        s.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2, SCREEN_H // 2))
        r_txt = self.med.render("[R]  Retry     [M]  Menu", True, TEXT_C)
        s.blit(r_txt, (SCREEN_W // 2 - r_txt.get_width() // 2, SCREEN_H // 2 + 60))

    def draw_pause(self):
        self._overlay()
        s = self.surface
        self._shadow_text(self.big, "PAUSED", SCREEN_W // 2, SCREEN_H // 2 - 40, TEXT_C)
        r_txt = self.med.render("[ESC]  Resume", True, (180, 170, 220))
        s.blit(r_txt, (SCREEN_W // 2 - r_txt.get_width() // 2, SCREEN_H // 2 + 40))

    def draw_level_complete(self, has_next):
        self._overlay()
        s = self.surface
        self._shadow_text(self.big, "LEVEL  CLEAR!", SCREEN_W // 2, SCREEN_H // 2 - 60, (100, 220, 120))
        if has_next:
            p = self.med.render("[ENTER]  Next Level", True, TEXT_C)
        else:
            p = self.med.render("[ENTER]  Continue", True, TEXT_C)
        s.blit(p, (SCREEN_W // 2 - p.get_width() // 2, SCREEN_H // 2 + 30))

    def draw_win(self, total_gems):
        s = self.surface
        s.fill(BG)
        t = self._tick
        title_y = SCREEN_H // 3 + int(math.sin(t * 0.04) * 5)
        self._shadow_text(self.big, "YOU  WIN!", SCREEN_W // 2, title_y, GOAL_C)

        sub = self.med.render(f"All gems: {total_gems}   Congratulations!", True, TEXT_C)
        s.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2, title_y + 90))

        if (t // 35) % 2 == 0:
            m_txt = self.med.render("[M]  Main Menu", True, (180, 170, 220))
            s.blit(m_txt, (SCREEN_W // 2 - m_txt.get_width() // 2, SCREEN_H // 2 + 80))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _overlay(self):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.surface.blit(overlay, (0, 0))

    def _shadow_text(self, font, text, cx, cy, color):
        shadow = font.render(text, True, (0, 0, 0))
        self.surface.blit(shadow, (cx - shadow.get_width() // 2 + 3, cy + 3))
        rendered = font.render(text, True, color)
        self.surface.blit(rendered, (cx - rendered.get_width() // 2, cy))


def _draw_heart(surface, x, y, size, color):
    """Draw a simple pixel-art heart."""
    r = size // 2
    # Two circles + triangle
    pygame.draw.circle(surface, color, (x + r // 2,     y + r // 2), r // 2)
    pygame.draw.circle(surface, color, (x + r + r // 2, y + r // 2), r // 2)
    pygame.draw.polygon(surface, color, [
        (x,          y + r // 2),
        (x + r * 2,  y + r // 2),
        (x + r,      y + size),
    ])
