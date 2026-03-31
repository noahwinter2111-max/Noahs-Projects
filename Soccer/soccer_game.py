"""
RETRO SOCCER - A 2D Pygame Soccer Game
=======================================
Controls:
  WASD or Arrow Keys - Move player
  SPACE              - Kick ball
  P                  - Pause/Resume
  ESC                - Quit

Install: pip install pygame
Run:     python soccer_game.py
"""

import pygame  
import sys
import math
import random

# ─── Constants ───────────────────────────────────────────────────────────────
SCREEN_W, SCREEN_H = 900, 600
FPS = 60

# Field dimensions
FIELD_X, FIELD_Y = 60, 80
FIELD_W, FIELD_H = 780, 440

# Goal dimensions
GOAL_W = 14
GOAL_H = 110
GOAL_Y = FIELD_Y + (FIELD_H - GOAL_H) // 2

# Colors
BLACK      = (0, 0, 0)
WHITE      = (255, 255, 255)
GREEN      = (34, 139, 34)
DARK_GREEN = (20, 100, 20)
YELLOW     = (255, 230, 0)
RED        = (220, 40, 40)
CYAN       = (0, 230, 255)
ORANGE     = (255, 140, 0)
GRAY       = (80, 80, 80)
DARK_GRAY  = (20, 20, 30)
PLAYER_BLUE = (30, 100, 255)

WIN_SCORE = 20

ENEMY_NAMES = ["NOVA FC", "BLAZE UTD", "STORM FC", "VIPER FC", "IRON FC",
               "ACID FC", "GHOST UTD", "FURY FC", "DELTA FC", "PIXEL WOLVES"]
ENEMY_COLORS = [
    (220, 40, 40), (255, 140, 0), (200, 0, 200), (0, 200, 150),
    (200, 200, 0), (255, 80, 120), (0, 200, 220), (180, 100, 20)
]


# ─── Utility helpers ─────────────────────────────────────────────────────────
def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def normalize(vx, vy):
    mag = math.hypot(vx, vy)
    if mag == 0:
        return 0.0, 0.0
    return vx / mag, vy / mag

def clamp(val, lo, hi):
    return max(lo, min(hi, val))

def beep(freq=440, duration=120):
    """Generate a simple beep using pygame.sndarray."""
    try:
        sample_rate = 44100
        n_samples = int(sample_rate * duration / 1000)
        buf = bytearray(n_samples * 2)
        for i in range(n_samples):
            val = int(32767 * math.sin(2 * math.pi * freq * i / sample_rate))
            buf[2*i]   = val & 0xFF
            buf[2*i+1] = (val >> 8) & 0xFF
        sound = pygame.mixer.Sound(buffer=bytes(buf))
        sound.set_volume(0.3)
        sound.play()
    except Exception:
        pass


# ─── Classes ─────────────────────────────────────────────────────────────────
class Ball:
    RADIUS = 10
    FRICTION = 0.985

    def __init__(self):
        self.reset()

    def reset(self):
        self.x = FIELD_X + FIELD_W // 2
        self.y = FIELD_Y + FIELD_H // 2
        self.vx = 0.0
        self.vy = 0.0

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= self.FRICTION
        self.vy *= self.FRICTION
        if abs(self.vx) < 0.05: self.vx = 0
        if abs(self.vy) < 0.05: self.vy = 0

        # Bounce off field walls (top/bottom)
        if self.y - self.RADIUS < FIELD_Y:
            self.y = FIELD_Y + self.RADIUS
            self.vy = abs(self.vy) * 0.8
        if self.y + self.RADIUS > FIELD_Y + FIELD_H:
            self.y = FIELD_Y + FIELD_H - self.RADIUS
            self.vy = -abs(self.vy) * 0.8

        # Left/right walls (only if NOT in goal area)
        if self.x - self.RADIUS < FIELD_X:
            in_goal = GOAL_Y < self.y < GOAL_Y + GOAL_H
            if not in_goal:
                self.x = FIELD_X + self.RADIUS
                self.vx = abs(self.vx) * 0.8
        if self.x + self.RADIUS > FIELD_X + FIELD_W:
            in_goal = GOAL_Y < self.y < GOAL_Y + GOAL_H
            if not in_goal:
                self.x = FIELD_X + FIELD_W - self.RADIUS
                self.vx = -abs(self.vx) * 0.8

    def draw(self, surf):
        pygame.draw.circle(surf, WHITE, (int(self.x), int(self.y)), self.RADIUS)
        pygame.draw.circle(surf, BLACK, (int(self.x), int(self.y)), self.RADIUS, 2)
        # Pentagon pattern lines
        for i in range(5):
            angle = math.radians(72 * i)
            x2 = int(self.x + self.RADIUS * 0.5 * math.cos(angle))
            y2 = int(self.y + self.RADIUS * 0.5 * math.sin(angle))
            pygame.draw.line(surf, GRAY, (int(self.x), int(self.y)), (x2, y2), 1)

    def kick(self, dx, dy, power=14):
        nx, ny = normalize(dx, dy)
        self.vx += nx * power
        self.vy += ny * power

    @property
    def pos(self):
        return (self.x, self.y)


class Player:
    RADIUS = 14
    BASE_SPEED = 4.5
    KICK_RANGE = 28

    def __init__(self, x, y, color, name="P1", is_human=True):
        self.x = float(x)
        self.y = float(y)
        self.color = color
        self.name = name
        self.is_human = is_human
        self.speed = self.BASE_SPEED

    def reset(self, x, y):
        self.x = float(x)
        self.y = float(y)

    def move(self, dx, dy):
        nx, ny = normalize(dx, dy)
        self.x = clamp(self.x + nx * self.speed,
                       FIELD_X + self.RADIUS, FIELD_X + FIELD_W - self.RADIUS)
        self.y = clamp(self.y + ny * self.speed,
                       FIELD_Y + self.RADIUS, FIELD_Y + FIELD_H - self.RADIUS)

    def draw(self, surf, font_small):
        # Shadow
        pygame.draw.circle(surf, (0, 0, 0, 100),
                           (int(self.x) + 3, int(self.y) + 3), self.RADIUS)
        # Body
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.RADIUS)
        pygame.draw.circle(surf, WHITE, (int(self.x), int(self.y)), self.RADIUS, 2)
        # Name label
        label = font_small.render(self.name[:3], True, WHITE)
        surf.blit(label, (int(self.x) - label.get_width()//2,
                          int(self.y) - self.RADIUS - 14))

    @property
    def pos(self):
        return (self.x, self.y)


class AIPlayer(Player):
    def __init__(self, x, y, color, name, index=0):
        super().__init__(x, y, color, name, is_human=False)
        self.index = index          # 0 = main forward, 1 = mid, 2 = defender
        self.reaction_timer = 0
        self.reaction_delay = 12    # frames between decisions

    def update(self, ball, difficulty_factor, player_pos):
        """AI logic — chases ball and shoots toward left goal."""
        self.reaction_timer += 1
        if self.reaction_timer < self.reaction_delay:
            return

        self.reaction_timer = 0

        bx, by = ball.x, ball.y
        cx = FIELD_X + FIELD_W // 2
        cy = FIELD_Y + FIELD_H // 2

        # Role-based target
        if self.index == 0:          # Forward: chase ball aggressively
            tx, ty = bx, by
        elif self.index == 1:        # Mid: stay between ball and center
            tx = (bx + cx) / 2
            ty = (by + cy) / 2
        else:                        # Defender: hang back
            tx = cx + (FIELD_W * 0.2)
            ty = by

        dx = tx - self.x
        dy = ty - self.y
        self.move(dx, dy)

    def try_kick(self, ball, difficulty_factor):
        """Kick toward the left goal (player's goal)."""
        if dist(self.pos, ball.pos) < self.KICK_RANGE:
            # Target: center of left goal
            goal_x = FIELD_X
            goal_y = GOAL_Y + GOAL_H // 2
            # Add inaccuracy based on difficulty
            spread = (1.0 - difficulty_factor) * 80
            goal_y += random.uniform(-spread, spread)
            dx = goal_x - ball.x
            dy = goal_y - ball.y
            power = 10 + difficulty_factor * 8
            ball.kick(dx, dy, power)
            return True
        return False


# ─── Main Game ───────────────────────────────────────────────────────────────
class SoccerGame:
    def __init__(self):
        pygame.init()
        pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("⚽ RETRO SOCCER")
        self.clock = pygame.time.Clock()

        # Fonts — try retro-ish pygame font
        self.font_big   = pygame.font.SysFont("Courier", 52, bold=True)
        self.font_mid   = pygame.font.SysFont("Courier", 30, bold=True)
        self.font_small = pygame.font.SysFont("Courier", 16, bold=True)
        self.font_tiny  = pygame.font.SysFont("Courier", 13)

        self.state = "menu"   # menu | game | paused | goal | win
        self.difficulty = 1   # 0=Easy, 1=Medium, 2=Hard
        self.diff_names = ["EASY", "MEDIUM", "HARD"]

        self.enemy_name  = random.choice(ENEMY_NAMES)
        self.enemy_color = random.choice(ENEMY_COLORS)

        self.player_score = 0
        self.enemy_score  = 0
        self.game_time    = 0       # frames elapsed
        self.paused       = False
        self.goal_timer   = 0
        self.goal_msg     = ""
        self.win_flash    = 0

        self.ball = Ball()
        self._init_players()

    # ── Initialise / reset players ──────────────────────────────────────────
    def _init_players(self):
        mid_x = FIELD_X + FIELD_W // 2
        mid_y = FIELD_Y + FIELD_H // 2

        self.player = Player(mid_x - 120, mid_y, PLAYER_BLUE, "YOU")

        # Number of AI players based on difficulty
        n_ai = self.difficulty + 1   # 1/2/3
        self.ai_players = []
        positions = [
            (mid_x + 120, mid_y),
            (mid_x + 220, mid_y - 80),
            (mid_x + 220, mid_y + 80),
        ]
        for i in range(n_ai):
            ai = AIPlayer(positions[i][0], positions[i][1],
                          self.enemy_color, self.enemy_name[:3], index=i)
            self.ai_players.append(ai)

    def _reset_positions(self):
        mid_x = FIELD_X + FIELD_W // 2
        mid_y = FIELD_Y + FIELD_H // 2
        self.ball.reset()
        self.player.reset(mid_x - 120, mid_y)
        positions = [
            (mid_x + 120, mid_y),
            (mid_x + 220, mid_y - 80),
            (mid_x + 220, mid_y + 80),
        ]
        for i, ai in enumerate(self.ai_players):
            ai.reset(positions[i][0], positions[i][1])

    # ── Difficulty scaling ───────────────────────────────────────────────────
    @property
    def difficulty_factor(self):
        """0.0 (easy) → 1.0 (max hard) rising over ~5 minutes."""
        base = [0.2, 0.45, 0.7][self.difficulty]
        time_bonus = min(self.game_time / (FPS * 300), 0.3)   # max +0.3 after 5 min
        return min(base + time_bonus, 1.0)

    def _apply_difficulty(self):
        df = self.difficulty_factor
        for ai in self.ai_players:
            ai.speed = Player.BASE_SPEED * (0.7 + df * 0.9)
            ai.reaction_delay = max(2, int(18 - df * 15))

    # ── Goal detection ──────────────────────────────────────────────────────
    def _check_goals(self):
        bx, by = self.ball.x, self.ball.y
        in_goal_y = GOAL_Y < by < GOAL_Y + GOAL_H

        # Ball went into left goal (enemy scores)
        if bx - Ball.RADIUS < FIELD_X - 2 and in_goal_y:
            self.enemy_score += 1
            self.goal_msg = f"⚽ {self.enemy_name} SCORES!"
            self._trigger_goal()

        # Ball went into right goal (player scores)
        if bx + Ball.RADIUS > FIELD_X + FIELD_W + 2 and in_goal_y:
            self.player_score += 1
            self.goal_msg = "⚽ FC PIXEL SCORES!"
            self._trigger_goal()

    def _trigger_goal(self):
        beep(523, 150)
        pygame.time.delay(80)
        beep(659, 150)
        self.state = "goal"
        self.goal_timer = FPS * 2   # 2 second pause
        if self.player_score >= WIN_SCORE or self.enemy_score >= WIN_SCORE:
            self.state = "win"
            self.win_flash = 0

    # ── Input handling ───────────────────────────────────────────────────────
    def _handle_input_menu(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.difficulty = (self.difficulty - 1) % 3
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self.difficulty = (self.difficulty + 1) % 3
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.enemy_name  = random.choice(ENEMY_NAMES)
                self.enemy_color = random.choice(ENEMY_COLORS)
                self.player_score = 0
                self.enemy_score  = 0
                self.game_time    = 0
                self._init_players()
                self._reset_positions()
                self.state = "game"

    def _handle_input_game(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                self.state = "paused"
            if event.key == pygame.K_ESCAPE:
                self.state = "menu"
            if event.key == pygame.K_SPACE:
                # Kick!
                if dist(self.player.pos, self.ball.pos) < Player.KICK_RANGE:
                    dx = self.ball.x - self.player.x
                    dy = self.ball.y - self.player.y
                    self.ball.kick(dx, dy, 16)
                    beep(300, 60)

    def _handle_input_paused(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                self.state = "game"
            if event.key == pygame.K_ESCAPE:
                self.state = "menu"

    # ── Update ───────────────────────────────────────────────────────────────
    def _update_game(self, keys):
        self.game_time += 1
        self._apply_difficulty()

        # Player movement
        dx, dy = 0, 0
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: dx -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx += 1
        if keys[pygame.K_UP]    or keys[pygame.K_w]: dy -= 1
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]: dy += 1
        if dx or dy:
            self.player.move(dx, dy)

        # Continuous kick near ball
        if keys[pygame.K_SPACE]:
            if dist(self.player.pos, self.ball.pos) < Player.KICK_RANGE:
                dx2 = self.ball.x - self.player.x
                dy2 = self.ball.y - self.player.y
                self.ball.kick(dx2, dy2, 12)

        # AI update
        for ai in self.ai_players:
            ai.update(self.ball, self.difficulty_factor, self.player.pos)
            ai.try_kick(self.ball, self.difficulty_factor)

        # Ball
        self.ball.update()

        # Push players away from ball (basic collision)
        for p in [self.player] + self.ai_players:
            d = dist(p.pos, self.ball.pos)
            if d < Player.RADIUS + Ball.RADIUS and d > 0:
                nx = (self.ball.x - p.x) / d
                ny = (self.ball.y - p.y) / d
                overlap = Player.RADIUS + Ball.RADIUS - d
                self.ball.x += nx * overlap * 0.5
                self.ball.y += ny * overlap * 0.5
                self.ball.vx += nx * 1.5
                self.ball.vy += ny * 1.5

        self._check_goals()

    # ── Drawing ──────────────────────────────────────────────────────────────
    def _draw_field(self):
        s = self.screen
        s.fill(DARK_GRAY)

        # Field
        pygame.draw.rect(s, DARK_GREEN, (FIELD_X, FIELD_Y, FIELD_W, FIELD_H))

        # Stripes
        stripe_w = FIELD_W // 10
        for i in range(10):
            if i % 2 == 0:
                pygame.draw.rect(s, GREEN,
                                 (FIELD_X + i * stripe_w, FIELD_Y, stripe_w, FIELD_H))

        # Border
        pygame.draw.rect(s, WHITE, (FIELD_X, FIELD_Y, FIELD_W, FIELD_H), 3)

        # Center line
        cx = FIELD_X + FIELD_W // 2
        pygame.draw.line(s, WHITE, (cx, FIELD_Y), (cx, FIELD_Y + FIELD_H), 2)

        # Center circle
        cy = FIELD_Y + FIELD_H // 2
        pygame.draw.circle(s, WHITE, (cx, cy), 60, 2)
        pygame.draw.circle(s, WHITE, (cx, cy), 4)

        # Penalty boxes
        pb_w, pb_h = 100, 200
        pb_y = FIELD_Y + (FIELD_H - pb_h) // 2
        pygame.draw.rect(s, WHITE, (FIELD_X, pb_y, pb_w, pb_h), 2)
        pygame.draw.rect(s, WHITE, (FIELD_X + FIELD_W - pb_w, pb_y, pb_w, pb_h), 2)

        # Goals (left = enemy scores on, right = player scores on)
        pygame.draw.rect(s, WHITE,
                         (FIELD_X - GOAL_W, GOAL_Y, GOAL_W, GOAL_H), 0)
        pygame.draw.rect(s, WHITE,
                         (FIELD_X + FIELD_W, GOAL_Y, GOAL_W, GOAL_H), 0)
        # Goal nets
        for i in range(0, GOAL_H, 10):
            pygame.draw.line(s, GRAY,
                             (FIELD_X - GOAL_W, GOAL_Y + i),
                             (FIELD_X, GOAL_Y + i), 1)
            pygame.draw.line(s, GRAY,
                             (FIELD_X + FIELD_W, GOAL_Y + i),
                             (FIELD_X + FIELD_W + GOAL_W, GOAL_Y + i), 1)

    def _draw_hud(self):
        s = self.screen
        df = self.difficulty_factor

        # Score bar background
        pygame.draw.rect(s, (10, 10, 20), (0, 0, SCREEN_W, 72))
        pygame.draw.line(s, CYAN, (0, 72), (SCREEN_W, 72), 2)

        # FC PIXEL score (left)
        label = self.font_mid.render("FC PIXEL", True, PLAYER_BLUE)
        s.blit(label, (20, 8))
        score = self.font_big.render(str(self.player_score), True, WHITE)
        s.blit(score, (20 + label.get_width() + 12, 2))

        # VS
        vs = self.font_mid.render("VS", True, YELLOW)
        s.blit(vs, (SCREEN_W // 2 - vs.get_width() // 2, 20))

        # Enemy score (right)
        e_label = self.font_mid.render(self.enemy_name, True, self.enemy_color)
        e_score = self.font_big.render(str(self.enemy_score), True, WHITE)
        e_score_x = SCREEN_W - 20 - e_label.get_width() - 12 - e_score.get_width()
        s.blit(e_label, (SCREEN_W - 20 - e_label.get_width(), 8))
        s.blit(e_score, (e_score_x, 2))

        # Danger meter
        meter_x = SCREEN_W // 2 - 100
        meter_y = 50
        meter_w = 200
        meter_h = 14
        pygame.draw.rect(s, GRAY, (meter_x, meter_y, meter_w, meter_h))
        fill = int(meter_w * df)
        danger_color = (int(50 + 205 * df), int(200 - 160 * df), 20)
        pygame.draw.rect(s, danger_color, (meter_x, meter_y, fill, meter_h))
        pygame.draw.rect(s, WHITE, (meter_x, meter_y, meter_w, meter_h), 1)
        danger_txt = self.font_tiny.render(f"DANGER {int(df*100)}%", True, WHITE)
        s.blit(danger_txt, (meter_x + meter_w // 2 - danger_txt.get_width() // 2,
                             meter_y + 1))

        # Difficulty tag
        diff_txt = self.font_tiny.render(
            f"[{self.diff_names[self.difficulty]}]  P=PAUSE  SPC=KICK  WASD/ARROWS=MOVE",
            True, GRAY)
        s.blit(diff_txt, (SCREEN_W // 2 - diff_txt.get_width() // 2, SCREEN_H - 22))

        # Win target
        win_txt = self.font_tiny.render(f"FIRST TO {WIN_SCORE} WINS", True, YELLOW)
        s.blit(win_txt, (SCREEN_W // 2 - win_txt.get_width() // 2, 75))

    def _draw_menu(self):
        s = self.screen
        s.fill(DARK_GRAY)

        # Flashing title
        tick = pygame.time.get_ticks() // 500
        title_color = CYAN if tick % 2 == 0 else YELLOW
        title = self.font_big.render("⚽ RETRO SOCCER", True, title_color)
        s.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 100))

        sub = self.font_mid.render("FIRST TO 20 GOALS WINS", True, WHITE)
        s.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2, 175))

        # Difficulty
        diff_label = self.font_mid.render("SELECT DIFFICULTY:", True, GRAY)
        s.blit(diff_label, (SCREEN_W // 2 - diff_label.get_width() // 2, 250))

        for i, name in enumerate(self.diff_names):
            selected = i == self.difficulty
            color = YELLOW if selected else GRAY
            prefix = "► " if selected else "  "
            txt = self.font_mid.render(f"{prefix}{name}", True, color)
            s.blit(txt, (SCREEN_W // 2 - txt.get_width() // 2, 295 + i * 40))

        # Controls reminder
        ctrl = self.font_small.render(
            "↑↓ SELECT   ENTER/SPACE START", True, WHITE)
        s.blit(ctrl, (SCREEN_W // 2 - ctrl.get_width() // 2, 420))

        ctrl2 = self.font_small.render(
            "WASD/ARROWS MOVE   SPACE KICK   P PAUSE", True, GRAY)
        s.blit(ctrl2, (SCREEN_W // 2 - ctrl2.get_width() // 2, 450))

        # Enemy preview
        preview = self.font_small.render(
            f"YOUR OPPONENT: {self.enemy_name}", True, self.enemy_color)
        s.blit(preview, (SCREEN_W // 2 - preview.get_width() // 2, 495))

        hint = self.font_tiny.render(
            "(opponent randomises each game)", True, GRAY)
        s.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, 520))

    def _draw_pause(self):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))

        tick = pygame.time.get_ticks() // 400
        color = CYAN if tick % 2 == 0 else YELLOW
        txt = self.font_big.render("⏸ PAUSED", True, color)
        self.screen.blit(txt,
            (SCREEN_W // 2 - txt.get_width() // 2, SCREEN_H // 2 - 40))
        sub = self.font_mid.render("P to Resume   ESC for Menu", True, WHITE)
        self.screen.blit(sub,
            (SCREEN_W // 2 - sub.get_width() // 2, SCREEN_H // 2 + 30))

    def _draw_goal_flash(self):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        self.screen.blit(overlay, (0, 0))

        tick = pygame.time.get_ticks() // 200
        color = YELLOW if tick % 2 == 0 else ORANGE
        txt = self.font_big.render("GOAL!", True, color)
        self.screen.blit(txt,
            (SCREEN_W // 2 - txt.get_width() // 2, SCREEN_H // 2 - 60))

        sub = self.font_mid.render(self.goal_msg, True, WHITE)
        self.screen.blit(sub,
            (SCREEN_W // 2 - sub.get_width() // 2, SCREEN_H // 2 + 10))

    def _draw_win(self):
        self.win_flash += 1
        s = self.screen
        s.fill(DARK_GRAY)

        if self.player_score >= WIN_SCORE:
            winner = "FC PIXEL"
            w_color = PLAYER_BLUE
        else:
            winner = self.enemy_name
            w_color = self.enemy_color

        tick = self.win_flash // 15
        colors = [YELLOW, CYAN, ORANGE, WHITE, RED]
        c = colors[tick % len(colors)]

        title = self.font_big.render("GAME OVER!", True, c)
        s.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 140))

        win_txt = self.font_big.render(f"{winner} WINS!", True, w_color)
        s.blit(win_txt, (SCREEN_W // 2 - win_txt.get_width() // 2, 220))

        # Final score
        score_txt = self.font_mid.render(
            f"FC PIXEL  {self.player_score} - {self.enemy_score}  {self.enemy_name}",
            True, WHITE)
        s.blit(score_txt, (SCREEN_W // 2 - score_txt.get_width() // 2, 310))

        # Confetti
        for _ in range(30):
            rx = random.randint(0, SCREEN_W)
            ry = random.randint(150, SCREEN_H - 100)
            rc = random.choice([YELLOW, CYAN, ORANGE, RED, WHITE])
            rw = random.randint(4, 10)
            rh = random.randint(4, 10)
            pygame.draw.rect(s, rc, (rx, ry, rw, rh))

        restart = self.font_mid.render("PRESS ENTER to Play Again", True, YELLOW)
        s.blit(restart, (SCREEN_W // 2 - restart.get_width() // 2, 430))
        esc = self.font_small.render("ESC for Menu", True, GRAY)
        s.blit(esc, (SCREEN_W // 2 - esc.get_width() // 2, 480))

    # ── Main loop ────────────────────────────────────────────────────────────
    def run(self):
        while True:
            keys = pygame.key.get_pressed()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if self.state == "menu":
                    self._handle_input_menu(event)
                elif self.state == "game":
                    self._handle_input_game(event)
                elif self.state == "paused":
                    self._handle_input_paused(event)
                elif self.state == "goal":
                    pass  # handled by timer
                elif self.state == "win":
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_RETURN:
                            self.player_score = 0
                            self.enemy_score  = 0
                            self.game_time    = 0
                            self.enemy_name   = random.choice(ENEMY_NAMES)
                            self.enemy_color  = random.choice(ENEMY_COLORS)
                            self._init_players()
                            self._reset_positions()
                            self.state = "game"
                        if event.key == pygame.K_ESCAPE:
                            self.state = "menu"

            # Update
            if self.state == "game":
                self._update_game(keys)
            elif self.state == "goal":
                self.goal_timer -= 1
                if self.goal_timer <= 0:
                    self._reset_positions()
                    self.state = "game"

            # Draw
            if self.state == "menu":
                self._draw_menu()
            elif self.state in ("game", "goal", "paused"):
                self._draw_field()
                self.ball.draw(self.screen)
                for ai in self.ai_players:
                    ai.draw(self.screen, self.font_tiny)
                self.player.draw(self.screen, self.font_small)
                self._draw_hud()
                if self.state == "goal":
                    self._draw_goal_flash()
                elif self.state == "paused":
                    self._draw_pause()
            elif self.state == "win":
                self._draw_win()

            pygame.display.flip()
            self.clock.tick(FPS)


if __name__ == "__main__":
    game = SoccerGame()
    game.run()
