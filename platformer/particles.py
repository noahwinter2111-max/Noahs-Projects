import pygame
import random
import math


class Particle:
    def __init__(self, x, y, color, vx=None, vy=None, life=None, size=None):
        self.x = float(x)
        self.y = float(y)
        self.color = color
        self.vx = vx if vx is not None else random.uniform(-3, 3)
        self.vy = vy if vy is not None else random.uniform(-4, -1)
        self.life = life if life is not None else random.randint(15, 35)
        self.max_life = self.life
        self.size = size if size is not None else random.randint(3, 6)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.15          # gravity on particles
        self.life -= 1

    def draw(self, surface, offset_x, offset_y):
        alpha = self.life / self.max_life
        r = int(self.color[0] * alpha + 10 * (1 - alpha))
        g = int(self.color[1] * alpha + 8  * (1 - alpha))
        b = int(self.color[2] * alpha + 20 * (1 - alpha))
        s = max(1, int(self.size * alpha))
        sx = int(self.x - offset_x)
        sy = int(self.y - offset_y)
        pygame.draw.circle(surface, (r, g, b), (sx, sy), s)

    @property
    def alive(self):
        return self.life > 0


class ParticleSystem:
    def __init__(self):
        self.particles = []

    def burst(self, x, y, color, count=12, speed=4):
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            spd = random.uniform(1, speed)
            self.particles.append(Particle(
                x, y, color,
                vx=math.cos(angle) * spd,
                vy=math.sin(angle) * spd,
                life=random.randint(20, 40),
                size=random.randint(3, 7),
            ))

    def trail(self, x, y, color, count=3):
        for _ in range(count):
            self.particles.append(Particle(
                x + random.uniform(-6, 6),
                y + random.uniform(-4, 4),
                color,
                vx=random.uniform(-1, 1),
                vy=random.uniform(-2, 0),
                life=random.randint(8, 18),
                size=random.randint(2, 4),
            ))

    def update(self):
        self.particles = [p for p in self.particles if p.alive]
        for p in self.particles:
            p.update()

    def draw(self, surface, offset_x, offset_y):
        for p in self.particles:
            p.draw(surface, offset_x, offset_y)
