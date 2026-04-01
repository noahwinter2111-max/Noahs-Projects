SCREEN_W = 1280
SCREEN_H = 720
FPS      = 60
TILE     = 40

# Physics
GRAVITY      = 0.65
MAX_FALL     = 18
PLAYER_SPEED = 5
JUMP_VEL     = -16
DASH_SPEED   = 15
DASH_FRAMES  = 14
DASH_COOLDOWN= 45
WALL_JUMP_VX = 6
WALL_JUMP_VY = -15
COYOTE       = 8   # coyote-time frames
JUMP_BUFFER  = 8   # jump-buffering frames

# HP
PLAYER_HP = 5

# Palette
BG       = (10,  8,  20)
TILE_C   = (55, 50,  75)
TILE_HI  = (85, 80, 105)
PLAT_C   = (40, 85,  55)
PLAT_HI  = (65,125,  75)
SPIKE_C  = (160, 50,  50)
PLAYER_C = (210,190, 255)
SHADOW_C = (140,120, 190)
ENEMY_C  = (190, 75,  75)
BOSS_C   = (220, 45,  45)
ORB_DJ   = ( 70,160, 255)   # double-jump  – blue
ORB_DASH = (255,150,  40)   # dash         – orange
ORB_WJ   = ( 70,220, 120)   # wall-jump    – green
GEM_C    = (255,210,  50)
HEALTH_C = (255,100, 120)
GOAL_C   = (255,240, 100)
HUD_C    = (200,180, 255)
TEXT_C   = (240,230, 255)
DIM      = (  0,  0,   0, 160)

LEVEL_NAMES = [
    "The Hollow",
    "Forest Path",
    "Rocky Cliffs",
    "The Depths",
    "The Summit",
]
