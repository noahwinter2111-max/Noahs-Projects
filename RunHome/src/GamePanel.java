import javax.swing.*;
import java.awt.*;
import java.awt.event.*;
import java.awt.geom.*;
import java.awt.image.BufferedImage;
import java.util.*;
import java.util.List;

/**
 * RUN HOME — GamePanel
 * All game logic lives here via inner classes.
 * City is a tile grid; cops use steering + pathfinding toward player.
 */
public class GamePanel extends JPanel implements ActionListener {

    // ── Constants ──────────────────────────────────────────────────────────────
    static final int TILE   = 40;
    static final int GCOLS  = 56;
    static final int GROWS  = 56;
    static final int WW     = TILE * GCOLS;   // world width  px
    static final int WH     = TILE * GROWS;   // world height px
    static final int BLOCK  = 8;              // street grid period (tiles)
    static final int ROAD_W = 2;              // road width in tiles

    // Tile types
    static final int T_ROAD  = 0;
    static final int T_SIDE  = 1;
    static final int T_BLDG  = 2;
    static final int T_HOME  = 3;
    static final int T_ALLEY = 4;

    // Game states
    static final int S_MENU = 0, S_PLAY = 1, S_PAUSE = 2, S_DEAD = 3, S_WIN = 4, S_OVER = 5;

    // ── World ──────────────────────────────────────────────────────────────────
    final int[][] grid = new int[GROWS][GCOLS];
    final Color[] bldgCol = new Color[GROWS * GCOLS];
    float homeWx, homeWy;   // home centre world coords
    float spawnWx, spawnWy; // player spawn world coords

    // ── Camera ────────────────────────────────────────────────────────────────
    float camX, camY;       // world-space top-left
    float shakeAmt;

    // ── Game state ────────────────────────────────────────────────────────────
    int    state     = S_MENU;
    int    score     = 0;
    int    round     = 1;
    int    wantedLvl = 1;
    int    coins     = 0;
    long   tick      = 0;
    int    diff      = 1;     // 0=easy 1=med 2=hard
    int    charIdx   = 0;     // selected character index
    int    menuSel   = -1;    // hover tracking
    float  roundTimer = 0;
    boolean roundComplete = false;

    // Character definitions (inline)
    static final String[] CHAR_NAME  = {"Ziggy","Volt","Phantom","Brick"};
    static final String[] CHAR_ROLE  = {"Runner","Speedster","Ghost","Brawler"};
    static final String[] CHAR_SPEC  = {"Powerful sprint","Tiny hitbox · ultra fast","2 dashes · phase thru","Dash stuns · 3 lives"};
    static final float[]  CHAR_SPD   = {3.2f, 4.0f, 2.8f, 2.6f}; // base speed (tiles/frame at 60fps)
    static final float[]  CHAR_STAM  = {100,  140,   85,  130};
    static final float[]  CHAR_DRAIN = {1.1f, 0.7f, 1.5f, 0.7f};
    static final int[]    CHAR_RAD   = {12, 9, 11, 14};
    static final int[]    CHAR_LIVES = {2, 2, 2, 3};
    static final int[]    CHAR_DASH  = {1, 1, 2, 1};
    static final Color[]  CHAR_CLR   = {new Color(0x3a86ff),new Color(0xffbe0b),new Color(0x8338ec),new Color(0xff6b35)};
    static final Color[]  CHAR_ACC   = {new Color(0xffbe0b),new Color(0xfb5607),new Color(0x3a86ff),new Color(0x2ec4b6)};

    // ── Player ────────────────────────────────────────────────────────────────
    float px, py;       // world position
    float pvx, pvy;     // velocity
    float stamina;
    int   lives, maxLives;
    int   dashCharges, dashCdMs;
    long  dashCdTimer;
    boolean dashing;
    float dashVx, dashVy;
    int   dashTicks;
    int   ghostTicks;       // Phantom ability: invincibility frames
    int   hitCooldown;      // invincibility after getting hit
    float speed;            // base move speed px/frame
    int   playerRad;

    // ── Cops ──────────────────────────────────────────────────────────────────
    List<Cop> cops = new ArrayList<>();

    // ── Power-ups ─────────────────────────────────────────────────────────────
    List<PowerUp> powerups = new ArrayList<>();
    int   shieldTicks, rushTicks, freezeTicks, smokeTicks, magnetTicks;
    long  pupSpawnTimer;

    // ── Coins ─────────────────────────────────────────────────────────────────
    List<float[]> coinItems = new ArrayList<>();  // {wx, wy}
    int   totalCoins = 0;  // session earned

    // ── Particles ─────────────────────────────────────────────────────────────
    List<Particle> particles = new ArrayList<>();

    // ── Floating text ─────────────────────────────────────────────────────────
    List<FloatText> floatTexts = new ArrayList<>();

    // ── Score multiplier ──────────────────────────────────────────────────────
    float mult = 1f;
    int   multTimer = 0;
    int   combo = 0;

    // ── Save data ─────────────────────────────────────────────────────────────
    SaveManager save;
    int bestScore = 0;
    int totalCash = 0;

    // ── Input ─────────────────────────────────────────────────────────────────
    final Set<Integer> held    = new HashSet<>();
    final Set<Integer> pressed = new HashSet<>();
    float mouseX, mouseY;
    boolean mouseDown;
    float clickX, clickY;
    boolean clickConsumed;

    // ── Timer ─────────────────────────────────────────────────────────────────
    final Timer gameTimer;

    // ── Colors / fonts ────────────────────────────────────────────────────────
    static final Color C_BG      = new Color(0x1a1a2e);
    static final Color C_ROAD    = new Color(0x3d3d3d);
    static final Color C_ROAD_MK = new Color(0x555555);
    static final Color C_SIDE    = new Color(0x555555);
    static final Color C_HOME    = new Color(0x1a4a1a);
    static final Color C_ALLEY   = new Color(0x292929);
    static final Color C_COP     = new Color(0x1155dd);
    static final Color C_COP_HL  = new Color(0x88aaff);
    static final Color C_COIN    = new Color(0xffd700);
    static final Font  FONT_BIG  = new Font("Monospaced", Font.BOLD, 36);
    static final Font  FONT_MED  = new Font("Monospaced", Font.BOLD, 20);
    static final Font  FONT_SM   = new Font("Monospaced", Font.PLAIN, 14);
    static final Font  FONT_HUD  = new Font("Monospaced", Font.BOLD, 16);

    static final Color[] BLDG_PAL = {
        new Color(0x1e3a5f), new Color(0x3d1e1e), new Color(0x1e3d1e),
        new Color(0x3d2a0f), new Color(0x2a1e3d), new Color(0x1e2d3d)
    };

    static final Random RNG = new Random();

    // ══════════════════════════════════════════════════════════════════════════
    // Inner classes
    // ══════════════════════════════════════════════════════════════════════════

    static class Cop {
        float x, y, vx, vy;
        float angle;
        int   state;      // 0=patrol 1=chase 2=alerted
        float alertTimer; // ticks remaining alert
        float patrolAngle, patrolTimer;
        boolean confused;
        int confusedTicks;
        // light flash
        int lightTick;
        static final int PATROL=0, CHASE=1, ALERTED=2;

        Cop(float x, float y) {
            this.x = x; this.y = y;
            this.patrolAngle = (float)(RNG.nextDouble() * Math.PI * 2);
        }
    }

    static class PowerUp {
        float x, y;
        int type; // 0=shield 1=rush 2=smoke 3=freeze 4=magnet
        int bobTick;
        PowerUp(float x, float y, int type) { this.x=x; this.y=y; this.type=type; }
        static final String[] NAMES = {"SHIELD","RUSH","SMOKE","FREEZE","MAGNET"};
        static final Color[]  COLS  = {
            new Color(0x33aaff), new Color(0xffe040),
            new Color(0xaaaaaa), new Color(0x88ddff), new Color(0xff8a00)
        };
        static final String[] ICONS = {"⛉","⚡","💨","❄","⊕"};
    }

    static class Particle {
        float x, y, vx, vy;
        int life, maxLife;
        Color color;
        float size;
        Particle(float x, float y, float vx, float vy, int life, Color c, float size) {
            this.x=x; this.y=y; this.vx=vx; this.vy=vy;
            this.life=life; this.maxLife=life; this.color=c; this.size=size;
        }
    }

    static class FloatText {
        float x, y;
        int life;
        String text;
        Color color;
        FloatText(float x, float y, String t, Color c) { this.x=x; this.y=y; this.text=t; this.color=c; life=60; }
    }

    // ══════════════════════════════════════════════════════════════════════════
    // Constructor
    // ══════════════════════════════════════════════════════════════════════════

    public GamePanel() {
        setPreferredSize(new Dimension(RunHome.W, RunHome.H));
        setBackground(C_BG);
        setFocusable(true);

        save = new SaveManager();
        bestScore = save.bestScore;
        totalCash = save.cash;

        generateCity();

        // Input
        addKeyListener(new KeyAdapter() {
            @Override public void keyPressed(KeyEvent e) {
                held.add(e.getKeyCode()); pressed.add(e.getKeyCode());
            }
            @Override public void keyReleased(KeyEvent e) { held.remove(e.getKeyCode()); }
        });
        addMouseListener(new MouseAdapter() {
            @Override public void mousePressed(MouseEvent e) {
                mouseDown=true; clickX=e.getX(); clickY=e.getY(); clickConsumed=false;
            }
            @Override public void mouseReleased(MouseEvent e) { mouseDown=false; }
        });
        addMouseMotionListener(new MouseMotionAdapter() {
            @Override public void mouseMoved(MouseEvent e)   { mouseX=e.getX(); mouseY=e.getY(); }
            @Override public void mouseDragged(MouseEvent e) { mouseX=e.getX(); mouseY=e.getY(); }
        });

        gameTimer = new Timer(16, this);
    }

    public void start() { gameTimer.start(); requestFocusInWindow(); }

    // ══════════════════════════════════════════════════════════════════════════
    // World generation
    // ══════════════════════════════════════════════════════════════════════════

    void generateCity() {
        // Default everything to building
        for (int[] row : grid) Arrays.fill(row, T_BLDG);

        // Carve road grid
        for (int r = 0; r < GROWS; r++) {
            for (int c = 0; c < GCOLS; c++) {
                int mr = r % BLOCK, mc = c % BLOCK;
                if (mr < ROAD_W || mc < ROAD_W) grid[r][c] = T_ROAD;
                else if (mr == ROAD_W || mc == ROAD_W) grid[r][c] = T_SIDE;
            }
        }

        // Carve some alleys (mid-block horizontals)
        for (int br = 1; br * BLOCK < GROWS - BLOCK; br++) {
            for (int bc = 0; bc * BLOCK < GCOLS; bc++) {
                if ((br + bc) % 2 == 0) {
                    int midR = br * BLOCK + BLOCK / 2;
                    for (int c = bc * BLOCK + ROAD_W + 1; c < (bc+1) * BLOCK - 1 && c < GCOLS; c++)
                        if (midR < GROWS) grid[midR][c] = T_ALLEY;
                }
            }
        }

        // Assign colours per building block
        for (int r = 0; r < GROWS; r++) {
            for (int c = 0; c < GCOLS; c++) {
                int bi = (r / BLOCK) * (GCOLS / BLOCK) + (c / BLOCK);
                bldgCol[r * GCOLS + c] = BLDG_PAL[bi % BLDG_PAL.length];
            }
        }

        // Home near top-right corner (on a road tile)
        int hc = GCOLS - BLOCK, hr = BLOCK;
        for (int dr = 0; dr < 4; dr++)
            for (int dc = 0; dc < 4; dc++)
                if (hr+dr < GROWS && hc+dc < GCOLS) grid[hr+dr][hc+dc] = T_HOME;
        homeWx = (hc + 2f) * TILE;
        homeWy = (hr + 2f) * TILE;

        // Spawn near bottom-left corner
        spawnWx = (BLOCK + 2f) * TILE;
        spawnWy = (GROWS - BLOCK * 2f) * TILE;
    }

    boolean isSolid(int col, int row) {
        if (col<0||col>=GCOLS||row<0||row>=GROWS) return true;
        return grid[row][col] == T_BLDG;
    }

    float[] resolveWall(float wx, float wy, float r) {
        int c0=(int)((wx-r)/TILE), c1=(int)((wx+r)/TILE);
        int r0=(int)((wy-r)/TILE), r1=(int)((wy+r)/TILE);
        for (int row=r0; row<=r1; row++) {
            for (int col=c0; col<=c1; col++) {
                if (isSolid(col, row)) {
                    float bx=col*TILE, by=row*TILE;
                    float cx=clamp(wx, bx, bx+TILE);
                    float cy=clamp(wy, by, by+TILE);
                    float dx=wx-cx, dy=wy-cy;
                    float d=(float)Math.sqrt(dx*dx+dy*dy);
                    if (d<r && d>0.001f) { float p=(r-d)/d; wx+=dx*p; wy+=dy*p; }
                }
            }
        }
        return new float[]{wx, wy};
    }

    boolean losBlocked(float x1,float y1,float x2,float y2) {
        int c1=(int)(x1/TILE), r1=(int)(y1/TILE);
        int c2=(int)(x2/TILE), r2=(int)(y2/TILE);
        int dc=Math.abs(c2-c1), dr=Math.abs(r2-r1);
        int sc2=c1<c2?1:-1, sr2=r1<r2?1:-1;
        int err=dc-dr, c=c1, r=r1;
        while (true) {
            if (isSolid(c,r)) return true;
            if (c==c2&&r==r2) return false;
            int e2=2*err;
            if (e2>-dr){err-=dr;c+=sc2;}
            if (e2<dc) {err+=dc;r+=sr2;}
        }
    }

    // ══════════════════════════════════════════════════════════════════════════
    // Game start / round
    // ══════════════════════════════════════════════════════════════════════════

    void startGame() {
        state = S_PLAY;
        score = 0; coins = 0; mult = 1f; combo = 0; multTimer = 0;
        round = 1; wantedLvl = 1; roundComplete = false;
        tick = 0;

        // Player
        px = spawnWx; py = spawnWy;
        pvx = 0; pvy = 0;
        playerRad = CHAR_RAD[charIdx];
        speed = CHAR_SPD[charIdx] * TILE;      // px/sec
        maxLives = CHAR_LIVES[charIdx];
        lives = maxLives;
        stamina = CHAR_STAM[charIdx];
        dashCharges = CHAR_DASH[charIdx];
        dashCdTimer = 0; dashing = false; dashTicks = 0; ghostTicks = 0; hitCooldown = 0;

        // Clear lists
        cops.clear(); powerups.clear(); particles.clear(); floatTexts.clear(); coinItems.clear();
        shieldTicks=0; rushTicks=0; freezeTicks=0; smokeTicks=0; magnetTicks=0;
        pupSpawnTimer = 600;

        // Camera
        camX = px - RunHome.W/2f;
        camY = py - RunHome.H/2f;

        spawnCops(copCount());
        spawnCoins(8);
    }

    int copCount() { return 2 + (round-1) + diff; }

    void nextRound() {
        round++;
        wantedLvl = Math.min(5, round);
        cops.clear();
        spawnCops(copCount());
        spawnCoins(6);
        px = spawnWx; py = spawnWy;
        pvx = 0; pvy = 0;
        stamina = CHAR_STAM[charIdx];
        dashCharges = CHAR_DASH[charIdx];
        dashing = false; ghostTicks = 0;
        addFloatText(px, py, "ROUND " + round + "!", new Color(0xffbe0b));
    }

    void spawnCops(int n) {
        for (int i = 0; i < n; i++) {
            // Spawn cops on roads, away from player
            for (int attempt = 0; attempt < 50; attempt++) {
                int col = RNG.nextInt(GCOLS), row = RNG.nextInt(GROWS);
                if (grid[row][col] == T_ROAD) {
                    float wx = col*TILE + TILE/2f, wy = row*TILE + TILE/2f;
                    float dx = wx-px, dy = wy-py;
                    if (dx*dx+dy*dy > 250*250) { cops.add(new Cop(wx, wy)); break; }
                }
            }
        }
    }

    void spawnCoins(int n) {
        for (int i = 0; i < n; i++) {
            for (int attempt = 0; attempt < 30; attempt++) {
                int col = RNG.nextInt(GCOLS), row = RNG.nextInt(GROWS);
                if (grid[row][col] == T_ROAD || grid[row][col] == T_SIDE) {
                    float wx = col*TILE + TILE/2f, wy = row*TILE + TILE/2f;
                    coinItems.add(new float[]{wx, wy});
                    break;
                }
            }
        }
    }

    // ══════════════════════════════════════════════════════════════════════════
    // Game loop
    // ══════════════════════════════════════════════════════════════════════════

    @Override public void actionPerformed(ActionEvent e) {
        update();
        repaint();
        pressed.clear();
        clickConsumed = true;
    }

    void update() {
        tick++;
        switch (state) {
            case S_MENU  -> updateMenu();
            case S_PLAY  -> updatePlay();
            case S_PAUSE -> updatePause();
            case S_DEAD  -> updateDead();
            case S_WIN   -> updateWin();
            case S_OVER  -> updateOver();
        }
    }

    // ── Menu ──────────────────────────────────────────────────────────────────

    void updateMenu() {
        if (isPressed(KeyEvent.VK_ENTER) || isPressed(KeyEvent.VK_SPACE)) startGame();
        // Cycle characters
        if (isPressed(KeyEvent.VK_LEFT)  || isPressed(KeyEvent.VK_A)) charIdx = (charIdx+3)%4;
        if (isPressed(KeyEvent.VK_RIGHT) || isPressed(KeyEvent.VK_D)) charIdx = (charIdx+1)%4;
        // Difficulty
        if (isPressed(KeyEvent.VK_1)) diff=0;
        if (isPressed(KeyEvent.VK_2)) diff=1;
        if (isPressed(KeyEvent.VK_3)) diff=2;
    }

    // ── Pause ─────────────────────────────────────────────────────────────────

    void updatePause() {
        if (isPressed(KeyEvent.VK_ESCAPE) || isPressed(KeyEvent.VK_P)) state = S_PLAY;
    }

    // ── Dead/Win/Over ─────────────────────────────────────────────────────────

    void updateDead() {
        if (isPressed(KeyEvent.VK_R)) startGame();
        if (isPressed(KeyEvent.VK_ESCAPE)) state = S_MENU;
    }
    void updateWin() {
        roundTimer--;
        if (roundTimer <= 0) nextRound();
        if (isPressed(KeyEvent.VK_R)) nextRound();
    }
    void updateOver() {
        if (isPressed(KeyEvent.VK_R)) startGame();
        if (isPressed(KeyEvent.VK_ESCAPE)) state = S_MENU;
    }

    // ── Main gameplay ─────────────────────────────────────────────────────────

    void updatePlay() {
        if (isPressed(KeyEvent.VK_ESCAPE) || isPressed(KeyEvent.VK_P)) { state = S_PAUSE; return; }

        float dt = 1f; // 60 fps normalized

        // ── Input → movement ──────────────────────────────────────────────────
        float dx=0, dy=0;
        if (held.contains(KeyEvent.VK_W)||held.contains(KeyEvent.VK_UP))    dy-=1;
        if (held.contains(KeyEvent.VK_S)||held.contains(KeyEvent.VK_DOWN))  dy+=1;
        if (held.contains(KeyEvent.VK_A)||held.contains(KeyEvent.VK_LEFT))  dx-=1;
        if (held.contains(KeyEvent.VK_D)||held.contains(KeyEvent.VK_RIGHT)) dx+=1;
        float len = (float)Math.sqrt(dx*dx+dy*dy);
        if (len>1){dx/=len;dy/=len;}

        boolean sprinting = held.contains(KeyEvent.VK_SHIFT) && stamina > 0 && len > 0;
        float curSpeed = sprinting ? speed * 1.7f : speed;
        if (rushTicks > 0) curSpeed *= 1.4f;

        // Drain stamina
        if (sprinting) {
            stamina = Math.max(0, stamina - CHAR_DRAIN[charIdx] * dt);
        } else {
            stamina = Math.min(CHAR_STAM[charIdx], stamina + 0.5f * dt);
        }

        // Friction
        pvx *= 0.82f; pvy *= 0.82f;

        if (!dashing) {
            pvx += dx * curSpeed * 0.18f;
            pvy += dy * curSpeed * 0.18f;
            // Cap velocity
            float spd2 = (float)Math.sqrt(pvx*pvx+pvy*pvy);
            if (spd2 > curSpeed) { pvx=pvx/spd2*curSpeed; pvy=pvy/spd2*curSpeed; }
        }

        // Dash
        if (isPressed(KeyEvent.VK_SPACE) && dashCharges > 0 && !dashing &&
            System.currentTimeMillis() > dashCdTimer) {
            float ddx = dx, ddy = dy;
            if (ddx==0&&ddy==0){ddx=0;ddy=-1;} // dash forward if no direction
            float d2=(float)Math.sqrt(ddx*ddx+ddy*ddy);
            ddx/=d2; ddy/=d2;
            dashVx = ddx*11f; dashVy = ddy*11f;
            dashing = true; dashTicks = 14;
            if (charIdx==2) ghostTicks=70; // Phantom: invincible during dash
            dashCharges--;
            dashCdTimer = System.currentTimeMillis() + 700;
            spawnBurst(px, py, CHAR_CLR[charIdx], 12);
        }

        if (dashing) {
            pvx = dashVx; pvy = dashVy;
            dashTicks--;
            if (dashTicks <= 0) { dashing = false; if(dashCharges<CHAR_DASH[charIdx]) dashCharges++; }
        }

        // ── Move + wall resolve ───────────────────────────────────────────────
        px += pvx * dt;
        float[] rx = resolveWall(px, py, playerRad);
        px = rx[0];

        py += pvy * dt;
        float[] ry = resolveWall(px, py, playerRad);
        py = ry[0]; py = ry[1];

        px = clamp(px, playerRad, WW-playerRad);
        py = clamp(py, playerRad, WH-playerRad);

        // Trail particles
        if (tick % 3 == 0) {
            Color tc = charIdx==2 ? new Color(0x8338ec66,true) : new Color(CHAR_CLR[charIdx].getRGB() & 0x00ffffff | 0x55000000, true);
            particles.add(new Particle(px, py, (RNG.nextFloat()-0.5f)*0.5f, (RNG.nextFloat()-0.5f)*0.5f, 18, tc, playerRad*0.7f));
        }

        // ── Dash recharge ─────────────────────────────────────────────────────
        if (dashCharges < CHAR_DASH[charIdx] && System.currentTimeMillis() > dashCdTimer)
            dashCharges = CHAR_DASH[charIdx];

        // ── Timers ────────────────────────────────────────────────────────────
        if (ghostTicks   > 0) ghostTicks--;
        if (hitCooldown  > 0) hitCooldown--;
        if (shieldTicks  > 0) shieldTicks--;
        if (rushTicks    > 0) rushTicks--;
        if (freezeTicks  > 0) freezeTicks--;
        if (smokeTicks   > 0) smokeTicks--;
        if (magnetTicks  > 0) magnetTicks--;
        if (multTimer    > 0) { multTimer--; if(multTimer==0){mult=1f;combo=0;} }

        // ── Score ─────────────────────────────────────────────────────────────
        score += (int)(wantedLvl * mult * 0.5f);

        // ── Coins pickup ──────────────────────────────────────────────────────
        coinItems.removeIf(ci -> {
            float cdx=ci[0]-px, cdy=ci[1]-py;
            boolean near = magnetTicks>0 ? Math.sqrt(cdx*cdx+cdy*cdy)<120 : Math.sqrt(cdx*cdx+cdy*cdy)<22;
            if (near) {
                int earn = (int)(5 * mult);
                coins += earn; totalCash += earn;
                combo++; mult = Math.min(4f, 1f + combo * 0.2f); multTimer = 180;
                addFloatText(ci[0], ci[1], "+" + earn + "💰", C_COIN);
                spawnBurst(ci[0], ci[1], C_COIN, 6);
                return true;
            }
            if (magnetTicks>0) {
                float md=(float)Math.sqrt(cdx*cdx+cdy*cdy);
                if(md>5){ci[0]+=cdx/md*(-4);ci[1]+=cdy/md*(-4);}
            }
            return false;
        });

        // ── Power-up pickup ───────────────────────────────────────────────────
        powerups.removeIf(p -> {
            float pdx=p.x-px, pdy=p.y-py;
            if (pdx*pdx+pdy*pdy < (playerRad+12)*(playerRad+12)) {
                applyPowerUp(p.type, p.x, p.y);
                return true;
            }
            return false;
        });

        // Spawn power-ups periodically
        pupSpawnTimer--;
        if (pupSpawnTimer <= 0 && powerups.size() < 4) {
            spawnRandomPup();
            pupSpawnTimer = 400 + RNG.nextInt(200);
        }

        // ── Cops ──────────────────────────────────────────────────────────────
        boolean frozen = freezeTicks > 0;
        for (Cop cop : cops) {
            if (frozen) { cop.lightTick++; continue; }

            cop.lightTick++;

            // Confusion from Brick dash
            if (cop.confused) {
                cop.confusedTicks--;
                if (cop.confusedTicks <= 0) cop.confused = false;
                cop.vx *= 0.9f; cop.vy *= 0.9f;
                cop.x += cop.vx; cop.y += cop.vy;
                continue;
            }

            float cdx = px - cop.x, cdy = py - cop.y;
            float dist = (float)Math.sqrt(cdx*cdx+cdy*cdy);
            boolean los = !losBlocked(cop.x, cop.y, px, py);
            float visionRange = 200 + wantedLvl * 30;

            // State machine
            switch (cop.state) {
                case Cop.PATROL -> {
                    if (los && dist < visionRange) {
                        cop.state = Cop.CHASE;
                        // Alert nearby cops
                        for (Cop other : cops) {
                            float od = (float)Math.sqrt((other.x-cop.x)*(other.x-cop.x)+(other.y-cop.y)*(other.y-cop.y));
                            if (od < 200 && other.state == Cop.PATROL) {
                                other.state = Cop.ALERTED; other.alertTimer = 300;
                            }
                        }
                    }
                    // Patrol: drift in patrol angle
                    cop.patrolTimer--;
                    if (cop.patrolTimer <= 0) {
                        cop.patrolAngle += (RNG.nextFloat()-0.5f) * 1.5f;
                        cop.patrolTimer = 40 + RNG.nextInt(40);
                    }
                    float ps = 1.1f;
                    cop.vx += (float)Math.cos(cop.patrolAngle) * ps * 0.15f;
                    cop.vy += (float)Math.sin(cop.patrolAngle) * ps * 0.15f;
                }
                case Cop.ALERTED -> {
                    cop.alertTimer--;
                    if (cop.alertTimer <= 0) cop.state = Cop.PATROL;
                    if (los && dist < visionRange*1.5f) cop.state = Cop.CHASE;
                    // Move toward last known position (player pos)
                    steerCopToward(cop, px, py, 1.8f + wantedLvl*0.15f);
                }
                case Cop.CHASE -> {
                    if (dist > visionRange * 2 || (!los && dist > 140)) {
                        cop.state = Cop.ALERTED; cop.alertTimer = 240;
                    }
                    float copSpd = smokeTicks>0 ? 1.4f : (2.0f + wantedLvl*0.2f + round*0.05f);
                    steerCopToward(cop, px, py, copSpd);
                }
            }

            // Friction + cap
            cop.vx *= 0.85f; cop.vy *= 0.85f;
            float maxSpd = 2.8f + wantedLvl*0.25f;
            float cs = (float)Math.sqrt(cop.vx*cop.vx+cop.vy*cop.vy);
            if (cs > maxSpd) { cop.vx=cop.vx/cs*maxSpd; cop.vy=cop.vy/cs*maxSpd; }

            cop.x += cop.vx; cop.y += cop.vy;

            // Cop wall resolution
            float[] cr = resolveWall(cop.x, cop.y, 10);
            cop.x = cr[0]; cop.y = cr[1];

            cop.angle = (float)Math.atan2(cop.vy, cop.vx);

            // ── Cop collision with player ──────────────────────────────────────
            float hdx=cop.x-px, hdy=cop.y-py;
            if (hdx*hdx+hdy*hdy < (playerRad+11)*(playerRad+11)) {
                // Brick: shove
                if (charIdx==3 && dashing) {
                    cop.confused = true; cop.confusedTicks = 120;
                    cop.vx = (hdx/(float)Math.sqrt(hdx*hdx+hdy*hdy))*8;
                    cop.vy = (hdy/(float)Math.sqrt(hdx*hdx+hdy*hdy))*8;
                    addFloatText(cop.x, cop.y, "STUNNED!", Color.ORANGE);
                } else if (shieldTicks > 0) {
                    shieldTicks = 0;
                    addFloatText(px, py, "SHIELD!", new Color(0x33aaff));
                    spawnBurst(px, py, new Color(0x33aaff), 16);
                } else if (ghostTicks > 0 || hitCooldown > 0) {
                    // invincible
                } else {
                    hitCooldown = 90;
                    lives--;
                    shake(10);
                    spawnBurst(px, py, Color.RED, 20);
                    addFloatText(px, py, "HIT! -1 LIFE", Color.RED);
                    if (lives <= 0) { endGame(); return; }
                }
            }
        }

        // Periodically spawn extra cop on high wanted
        if (wantedLvl >= 3 && tick % (Math.max(200, 600 - wantedLvl*60)) == 0) {
            spawnCops(1);
        }

        // ── Check: reached home ───────────────────────────────────────────────
        float hdx=homeWx-px, hdy=homeWy-py;
        if (hdx*hdx+hdy*hdy < 60*60) {
            int bonus = (int)(1000 * mult * (3-diff) * 0.5f + 1);
            score += bonus; coins += 20; totalCash += 20;
            addFloatText(px, py-30, "+"+bonus+" BONUS!", new Color(0x44ff44));
            spawnBurst(px, py, new Color(0x44ff44), 30);
            state = S_WIN;
            roundTimer = 180;
            if (score > bestScore) { bestScore = score; save.bestScore = score; }
            save.cash = totalCash; save.save();
        }

        // ── Particles ─────────────────────────────────────────────────────────
        particles.removeIf(p -> {
            p.x += p.vx; p.y += p.vy; p.vx *= 0.95f; p.vy *= 0.95f; return --p.life <= 0;
        });

        // ── Float texts ───────────────────────────────────────────────────────
        floatTexts.removeIf(ft -> { ft.y -= 0.8f; return --ft.life <= 0; });

        // ── Camera ────────────────────────────────────────────────────────────
        float tcx = px - RunHome.W/2f, tcy = py - RunHome.H/2f;
        camX += (tcx-camX)*0.1f; camY += (tcy-camY)*0.1f;
        camX = clamp(camX, 0, WW-RunHome.W);
        camY = clamp(camY, 0, WH-RunHome.H);
        if (shakeAmt > 0.5f) shakeAmt *= 0.85f; else shakeAmt = 0;
    }

    void steerCopToward(Cop cop, float tx, float ty, float force) {
        float cdx=tx-cop.x, cdy=ty-cop.y;
        float d=(float)Math.sqrt(cdx*cdx+cdy*cdy);
        if (d>1){cdx/=d;cdy/=d;}
        cop.vx += cdx*force*0.15f;
        cop.vy += cdy*force*0.15f;
    }

    void applyPowerUp(int type, float wx, float wy) {
        switch(type) {
            case 0 -> { shieldTicks=360; addFloatText(wx,wy,"SHIELD!",   new Color(0x33aaff)); }
            case 1 -> { rushTicks  =300; addFloatText(wx,wy,"RUSH!",     new Color(0xffe040)); }
            case 2 -> { smokeTicks =240; addFloatText(wx,wy,"SMOKE!",    Color.LIGHT_GRAY); }
            case 3 -> { freezeTicks=180; addFloatText(wx,wy,"FREEZE!",   new Color(0x88ddff)); }
            case 4 -> { magnetTicks=300; addFloatText(wx,wy,"MAGNET!",   new Color(0xff8a00)); }
        }
        spawnBurst(wx, wy, PowerUp.COLS[type], 10);
    }

    void spawnRandomPup() {
        for (int attempt=0; attempt<30; attempt++) {
            int col=RNG.nextInt(GCOLS), row=RNG.nextInt(GROWS);
            if (grid[row][col]==T_ROAD||grid[row][col]==T_SIDE) {
                float wx=col*TILE+TILE/2f, wy=row*TILE+TILE/2f;
                float d2=(px-wx)*(px-wx)+(py-wy)*(py-wy);
                if (d2 > 100*100) {
                    powerups.add(new PowerUp(wx, wy, RNG.nextInt(5)));
                    return;
                }
            }
        }
    }

    void endGame() {
        state = S_OVER;
        save.cash = totalCash; save.save();
    }

    // ══════════════════════════════════════════════════════════════════════════
    // Rendering
    // ══════════════════════════════════════════════════════════════════════════

    @Override protected void paintComponent(Graphics g0) {
        super.paintComponent(g0);
        Graphics2D g = (Graphics2D) g0;
        g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        g.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);

        switch (state) {
            case S_MENU  -> drawMenu(g);
            case S_PLAY  -> { drawWorld(g); drawHUD(g); }
            case S_PAUSE -> { drawWorld(g); drawPause(g); }
            case S_DEAD  -> { drawWorld(g); drawDead(g); }
            case S_WIN   -> { drawWorld(g); drawWinBanner(g); }
            case S_OVER  -> { drawWorld(g); drawGameOver(g); }
        }
    }

    // ── World rendering ───────────────────────────────────────────────────────

    void drawWorld(Graphics2D g) {
        // Background
        g.setColor(C_BG);
        g.fillRect(0, 0, RunHome.W, RunHome.H);

        float sx = shakeAmt > 0 ? (RNG.nextFloat()*2-1)*shakeAmt : 0;
        float sy = shakeAmt > 0 ? (RNG.nextFloat()*2-1)*shakeAmt : 0;

        int c0 = Math.max(0, (int)(camX/TILE)-1);
        int r0 = Math.max(0, (int)(camY/TILE)-1);
        int c1 = Math.min(GCOLS-1, c0+RunHome.W/TILE+2);
        int r1 = Math.min(GROWS-1, r0+RunHome.H/TILE+2);

        for (int row=r0; row<=r1; row++) {
            for (int col=c0; col<=c1; col++) {
                int scx = (int)(col*TILE - camX + sx);
                int scy = (int)(row*TILE - camY + sy);
                int t = grid[row][col];
                switch(t) {
                    case T_ROAD  -> drawRoadTile(g, scx, scy, col, row);
                    case T_SIDE  -> { g.setColor(C_SIDE); g.fillRect(scx,scy,TILE,TILE); }
                    case T_ALLEY -> { g.setColor(C_ALLEY); g.fillRect(scx,scy,TILE,TILE); }
                    case T_HOME  -> drawHomeTile(g, scx, scy);
                    case T_BLDG  -> drawBldgTile(g, scx, scy, col, row);
                }
            }
        }

        // Coins
        for (float[] ci : coinItems) {
            int scx=(int)(ci[0]-camX+sx), scy=(int)(ci[1]-camY+sy);
            drawCoin(g, scx, scy);
        }

        // Power-ups
        for (PowerUp p : powerups) {
            int scx=(int)(p.x-camX+sx), scy=(int)(p.y-camY+sy);
            drawPowerUp(g, scx, scy, p);
        }

        // Particles
        for (Particle p : particles) {
            float alpha = (float)p.life/p.maxLife;
            Color c2 = new Color(p.color.getRed(),p.color.getGreen(),p.color.getBlue(),(int)(alpha*200));
            g.setColor(c2);
            int s=(int)p.size;
            g.fillOval((int)(p.x-camX+sx)-s/2,(int)(p.y-camY+sy)-s/2,s,s);
        }

        // Cops
        for (Cop cop : cops) {
            int scx=(int)(cop.x-camX+sx), scy=(int)(cop.y-camY+sy);
            drawCop(g, scx, scy, cop);
        }

        // Player
        drawPlayer(g, (int)(px-camX+sx), (int)(py-camY+sy));

        // Float texts
        for (FloatText ft : floatTexts) {
            float alpha = (float)ft.life/60;
            Color c2 = new Color(ft.color.getRed(),ft.color.getGreen(),ft.color.getBlue(),(int)(alpha*255));
            g.setColor(c2);
            g.setFont(FONT_MED);
            int tw=g.getFontMetrics().stringWidth(ft.text);
            g.drawString(ft.text, (int)(ft.x-camX)-tw/2, (int)(ft.y-camY));
        }

        // Shield ring
        if (shieldTicks>0) {
            float pulse = (float)(0.7+0.3*Math.sin(tick*0.15));
            g.setColor(new Color(51,170,255,(int)(pulse*140)));
            int sr=(int)(playerRad*1.8);
            g.setStroke(new BasicStroke(2.5f));
            g.drawOval((int)(px-camX+sx)-sr,(int)(py-camY+sy)-sr,sr*2,sr*2);
            g.setStroke(new BasicStroke(1f));
        }

        // Home beacon (arrow to home)
        drawHomeBeacon(g, sx, sy);
    }

    void drawRoadTile(Graphics2D g, int sx, int sy, int col, int row) {
        g.setColor(C_ROAD);
        g.fillRect(sx,sy,TILE,TILE);
        // Dashed road markings
        if (col%BLOCK==0) {
            g.setColor(C_ROAD_MK);
            if ((row/2)%2==0) g.fillRect(sx+TILE/2-1,sy,2,TILE);
        }
        if (row%BLOCK==0) {
            g.setColor(C_ROAD_MK);
            if ((col/2)%2==0) g.fillRect(sx,sy+TILE/2-1,TILE,2);
        }
    }

    void drawBldgTile(Graphics2D g, int sx, int sy, int col, int row) {
        Color base = bldgCol[row*GCOLS+col];
        g.setColor(base);
        g.fillRect(sx,sy,TILE,TILE);
        // Windows
        if (col%2==0&&row%2==0) {
            boolean lit = ((col*13+row*7+tick/90)%4) != 0;
            g.setColor(lit ? new Color(0xffff99) : new Color(0x223344));
            g.fillRect(sx+6,sy+6,9,7);
            g.fillRect(sx+22,sy+6,9,7);
            g.fillRect(sx+6,sy+22,9,7);
            g.fillRect(sx+22,sy+22,9,7);
        }
        // Dark top/left edges (building depth)
        g.setColor(new Color(0,0,0,70));
        g.fillRect(sx,sy,TILE,2);
        g.fillRect(sx,sy,2,TILE);
    }

    void drawHomeTile(Graphics2D g, int sx, int sy) {
        g.setColor(C_HOME);
        g.fillRect(sx,sy,TILE,TILE);
        float p=(float)(0.6+0.4*Math.sin(tick*0.08));
        g.setColor(new Color(68,255,68,(int)(p*180)));
        g.drawRect(sx+1,sy+1,TILE-2,TILE-2);
        g.drawRect(sx+3,sy+3,TILE-6,TILE-6);
    }

    void drawCoin(Graphics2D g, int sx, int sy) {
        float bob = (float)Math.sin(tick*0.12)*3;
        g.setColor(new Color(0xffcc00));
        g.fillOval(sx-7,(int)(sy-7+bob),14,14);
        g.setColor(new Color(0xffe566));
        g.fillOval(sx-5,(int)(sy-5+bob),8,8);
    }

    void drawPowerUp(Graphics2D g, int sx, int sy, PowerUp p) {
        float bob=(float)Math.sin(tick*0.1+p.bobTick)*4;
        p.bobTick++;
        int s=18;
        g.setColor(new Color(PowerUp.COLS[p.type].getRed(),PowerUp.COLS[p.type].getGreen(),PowerUp.COLS[p.type].getBlue(),60));
        g.fillOval(sx-s,(int)(sy-s+bob),s*2,s*2);
        g.setColor(PowerUp.COLS[p.type]);
        g.setStroke(new BasicStroke(2));
        g.drawOval(sx-s,(int)(sy-s+bob),s*2,s*2);
        g.setFont(new Font("Dialog",Font.PLAIN,16));
        g.drawString(PowerUp.ICONS[p.type], sx-7,(int)(sy+6+bob));
        g.setStroke(new BasicStroke(1));
    }

    void drawCop(Graphics2D g, int sx, int sy, Cop cop) {
        // Light bar flashing
        boolean redOn  = (cop.lightTick/8)%2==0;
        boolean blueOn = (cop.lightTick/8)%2==1;
        if (!cop.confused) {
            if (redOn)  { g.setColor(new Color(255,60,60,160));  g.fillOval(sx-18,sy-18,36,36); }
            if (blueOn) { g.setColor(new Color(60,120,255,160)); g.fillOval(sx-18,sy-18,36,36); }
        }

        // Body
        Color body = cop.confused ? new Color(0xffaa00) : C_COP;
        g.setColor(body);
        g.fillOval(sx-10,sy-10,20,20);

        // Badge
        g.setColor(Color.WHITE);
        g.fillOval(sx-4,sy-4,8,8);
        g.setColor(new Color(0x001166));
        g.fillOval(sx-3,sy-3,6,6);

        // Direction arrow
        g.setColor(C_COP_HL);
        g.setStroke(new BasicStroke(2));
        g.drawLine(sx,sy,(int)(sx+Math.cos(cop.angle)*13),(int)(sy+Math.sin(cop.angle)*13));
        g.setStroke(new BasicStroke(1));

        // Vision cone (in chase state)
        if (cop.state == Cop.CHASE) {
            float a1=(float)(cop.angle-Math.PI/5), a2=(float)(cop.angle+Math.PI/5);
            int vr=120;
            int[] xp={sx,(int)(sx+Math.cos(a1)*vr),(int)(sx+Math.cos(a2)*vr)};
            int[] yp={sy,(int)(sy+Math.sin(a1)*vr),(int)(sy+Math.sin(a2)*vr)};
            g.setColor(new Color(255,255,0,22));
            g.fillPolygon(xp,yp,3);
        }
    }

    void drawPlayer(Graphics2D g, int sx, int sy) {
        Color body = CHAR_CLR[charIdx];
        Color acc  = CHAR_ACC[charIdx];
        int r = playerRad;

        // Ghost transparency for Phantom
        if (charIdx==2 && ghostTicks>0) {
            g.setColor(new Color(body.getRed(),body.getGreen(),body.getBlue(),100));
        } else {
            g.setColor(hitCooldown>0 && (tick/4)%2==0 ? Color.RED : body);
        }
        g.fillOval(sx-r,sy-r,r*2,r*2);

        // Accent ring
        g.setColor(acc);
        g.setStroke(new BasicStroke(2));
        g.drawOval(sx-r,sy-r,r*2,r*2);
        g.setStroke(new BasicStroke(1));

        // Emoji label
        g.setFont(new Font("Dialog",Font.PLAIN,16));
        String[] emojis = {"🏃","⚡","👻","💪"};
        g.setColor(Color.WHITE);
        g.drawString(emojis[charIdx], sx-8, sy+6);

        // Dash glow
        if (dashing) {
            g.setColor(new Color(acc.getRed(),acc.getGreen(),acc.getBlue(),100));
            g.fillOval(sx-r-6,sy-r-6,(r+6)*2,(r+6)*2);
        }
    }

    void drawHomeBeacon(Graphics2D g, float sx, float sy) {
        // Arrow pointing to home
        float hdx = homeWx-px, hdy = homeWy-py;
        float dist=(float)Math.sqrt(hdx*hdx+hdy*hdy);
        if (dist < 150) return; // close enough, no need for beacon
        float angle=(float)Math.atan2(hdy,hdx);
        int bx=RunHome.W/2+(int)(Math.cos(angle)*180);
        int by=RunHome.H/2+(int)(Math.sin(angle)*180);
        float p=(float)(0.7+0.3*Math.sin(tick*0.1));
        g.setColor(new Color(68,255,68,(int)(p*200)));
        g.setStroke(new BasicStroke(2.5f));
        drawArrow(g, bx, by, angle);
        g.setFont(FONT_SM);
        g.drawString("HOME "+(int)dist+"m", bx-24, by-18);
        g.setStroke(new BasicStroke(1));
    }

    void drawArrow(Graphics2D g, int x, int y, float angle) {
        int len=14;
        int tx=(int)(x+Math.cos(angle)*len), ty=(int)(y+Math.sin(angle)*len);
        g.drawLine(x,y,tx,ty);
        g.drawLine(tx,ty,(int)(tx+Math.cos(angle+2.5f)*8),(int)(ty+Math.sin(angle+2.5f)*8));
        g.drawLine(tx,ty,(int)(tx+Math.cos(angle-2.5f)*8),(int)(ty+Math.sin(angle-2.5f)*8));
    }

    // ── HUD ───────────────────────────────────────────────────────────────────

    void drawHUD(Graphics2D g) {
        // Score bar
        g.setColor(new Color(0,0,0,160));
        g.fillRoundRect(8,8,280,62,10,10);
        g.setColor(Color.WHITE);
        g.setFont(FONT_HUD);
        g.drawString("SCORE: "+score, 18, 30);
        g.setFont(FONT_SM);
        g.drawString("BEST: "+bestScore+"  ROUND: "+round+"  WANTED: "+"★".repeat(wantedLvl), 18, 48);
        if (mult > 1f) {
            g.setColor(new Color(0xffe040));
            g.setFont(FONT_MED);
            g.drawString(String.format("×%.1f COMBO %d", mult, combo), 18, 68);
        }

        // Lives
        int lx = RunHome.W - 18;
        for (int i=0; i<maxLives; i++) {
            g.setColor(i < lives ? Color.RED : new Color(0x555555));
            g.fillOval(lx-14, 12, 12, 12);
            lx -= 16;
        }

        // Stamina bar
        g.setColor(new Color(0,0,0,150));
        g.fillRoundRect(8, RunHome.H-34, 160, 18, 8, 8);
        float stPct = stamina / CHAR_STAM[charIdx];
        Color stCol = stPct>0.5f ? new Color(0x44ff44) : stPct>0.2f ? new Color(0xffe040) : Color.RED;
        g.setColor(stCol);
        g.fillRoundRect(10, RunHome.H-32, (int)(156*stPct), 14, 6, 6);
        g.setColor(Color.WHITE);
        g.setFont(FONT_SM);
        g.drawString("STAMINA", 16, RunHome.H-20);

        // Dash charges
        for (int i=0; i<CHAR_DASH[charIdx]; i++) {
            g.setColor(i < dashCharges ? new Color(0xffe040) : new Color(0x444444));
            g.fillRoundRect(178+i*22, RunHome.H-34, 18, 18, 5, 5);
            g.setColor(Color.WHITE);
            g.setFont(FONT_SM);
            g.drawString("⚡", 178+i*22+2, RunHome.H-20);
        }

        // Active power-ups
        int puX = RunHome.W - 10;
        if (shieldTicks>0) puX = drawHudPup(g, puX, "⛉ SHIELD", new Color(0x33aaff), shieldTicks, 360);
        if (rushTicks>0)   puX = drawHudPup(g, puX, "⚡ RUSH",   new Color(0xffe040), rushTicks, 300);
        if (freezeTicks>0) puX = drawHudPup(g, puX, "❄ FREEZE", new Color(0x88ddff), freezeTicks, 180);
        if (smokeTicks>0)  puX = drawHudPup(g, puX, "💨 SMOKE",  Color.LIGHT_GRAY,    smokeTicks, 240);
        if (magnetTicks>0) puX = drawHudPup(g, puX, "⊕ MAGNET", new Color(0xff8a00), magnetTicks, 300);

        // Coins
        g.setColor(new Color(0,0,0,150));
        g.fillRoundRect(RunHome.W/2-50, 8, 100, 28, 8, 8);
        g.setColor(C_COIN);
        g.setFont(FONT_HUD);
        String coinStr = "💰 " + coins;
        int cw = g.getFontMetrics().stringWidth(coinStr);
        g.drawString(coinStr, RunHome.W/2 - cw/2, 28);

        // Wanted stars
        g.setColor(new Color(0,0,0,150));
        g.fillRoundRect(RunHome.W/2-70, 42, 140, 22, 8, 8);
        g.setFont(FONT_SM);
        StringBuilder wb=new StringBuilder();
        for(int i=0;i<5;i++) wb.append(i<wantedLvl?"★":"☆");
        g.setColor(new Color(0xffe040));
        int ww=g.getFontMetrics().stringWidth(wb.toString());
        g.drawString(wb.toString(), RunHome.W/2-ww/2, 58);
    }

    int drawHudPup(Graphics2D g, int rx, String label, Color c, int remaining, int max) {
        int w=110;
        g.setColor(new Color(0,0,0,160));
        g.fillRoundRect(rx-w, RunHome.H-60, w, 24, 6, 6);
        g.setColor(c);
        g.fillRoundRect(rx-w+2, RunHome.H-58, (int)((w-4)*(float)remaining/max), 20, 4, 4);
        g.setColor(Color.WHITE);
        g.setFont(FONT_SM);
        g.drawString(label, rx-w+6, RunHome.H-43);
        return rx - w - 6;
    }

    // ── Menu ──────────────────────────────────────────────────────────────────

    void drawMenu(Graphics2D g) {
        // Animated background
        g.setColor(C_BG);
        g.fillRect(0,0,RunHome.W,RunHome.H);
        drawMenuParticles(g);

        // Title
        g.setColor(new Color(0xffe040));
        g.setFont(new Font("Monospaced",Font.BOLD,72));
        shadowText(g,"RUN HOME",RunHome.W/2,130, new Color(0xffe040), new Color(0,0,0,180));

        g.setColor(new Color(0xcccccc));
        g.setFont(FONT_MED);
        centreText(g,"OUTRUN THE LAW",RunHome.W/2,175);

        // Character select
        g.setColor(new Color(0xffffff));
        g.setFont(FONT_MED);
        centreText(g,"◄ / ► SELECT CHARACTER",RunHome.W/2,220);

        int cw=220, cx0=RunHome.W/2-(cw*4+24)/2;
        for (int i=0; i<4; i++) {
            int bx=cx0+i*(cw+8), by=240;
            boolean sel=i==charIdx;
            g.setColor(sel ? new Color(0x1a2a4a) : new Color(0x12121f));
            g.fillRoundRect(bx,by,cw,130,12,12);
            g.setColor(sel ? CHAR_CLR[i] : new Color(0x444444));
            g.setStroke(new BasicStroke(sel?3:1));
            g.drawRoundRect(bx,by,cw,130,12,12);
            g.setStroke(new BasicStroke(1));

            g.setColor(CHAR_CLR[i]);
            g.setFont(new Font("Monospaced",Font.BOLD,18));
            centreText(g,CHAR_NAME[i],bx+cw/2,270);
            g.setColor(new Color(0xaaaaaa));
            g.setFont(FONT_SM);
            centreText(g,CHAR_ROLE[i],bx+cw/2,290);
            g.setColor(new Color(0x88aacc));
            g.setFont(new Font("Monospaced",Font.PLAIN,12));
            centreText(g,CHAR_SPEC[i],bx+cw/2,310);
            g.setColor(new Color(0x888888));
            centreText(g,"SPD:"+(int)(CHAR_SPD[i]*10)+" STA:"+(int)CHAR_STAM[i],bx+cw/2,330);
            g.setColor(new Color(0xffaa00));
            centreText(g,"LIVES: "+"♥".repeat(CHAR_LIVES[i]),bx+cw/2,352);
        }

        // Difficulty
        g.setColor(Color.WHITE);
        g.setFont(FONT_MED);
        centreText(g,"DIFFICULTY (1/2/3)",RunHome.W/2,408);
        String[] dLabels={"EASY","MEDIUM","HARD"};
        Color[]  dCols  ={new Color(0x44cc44),new Color(0xffaa00),new Color(0xff4444)};
        int dw=120;
        for (int i=0;i<3;i++) {
            int bx=RunHome.W/2-3*dw/2-8+i*(dw+8), by=420;
            g.setColor(i==diff ? dCols[i] : new Color(0x333344));
            g.fillRoundRect(bx,by,dw,32,8,8);
            g.setColor(i==diff ? Color.WHITE : new Color(0x888888));
            g.setFont(FONT_MED);
            centreText(g,dLabels[i],bx+dw/2,442);
        }

        // Play button
        float pbPulse=(float)(0.85+0.15*Math.sin(tick*0.08));
        g.setColor(new Color(0x22aa44));
        g.fillRoundRect(RunHome.W/2-110,475,220,50,14,14);
        g.setColor(new Color(0xffe040,(int)(pbPulse*255)));
        g.setFont(new Font("Monospaced",Font.BOLD,26));
        centreText(g,"▶  PLAY",RunHome.W/2,507);

        // Controls hint
        g.setColor(new Color(0x888888));
        g.setFont(FONT_SM);
        centreText(g,"WASD/ARROWS  ·  SHIFT sprint  ·  SPACE dash  ·  ESC pause",RunHome.W/2,560);
        g.setColor(new Color(0x666666));
        centreText(g,"Best: "+bestScore+"  Cash: "+totalCash+"💰",RunHome.W/2,580);

        // Handle play click
        if (!clickConsumed && mouseDown) {
            if (clickX>RunHome.W/2-110&&clickX<RunHome.W/2+110&&clickY>475&&clickY<525) startGame();
            for (int i=0;i<3;i++) { int bx=RunHome.W/2-3*dw/2-8+i*(dw+8); if(clickX>bx&&clickX<bx+dw&&clickY>420&&clickY<452) diff=i; }
            for (int i=0;i<4;i++) { int bx=cx0+i*(cw+8); if(clickX>bx&&clickX<bx+cw&&clickY>240&&clickY<370) charIdx=i; }
        }
    }

    long menuPartTick = 0;
    float[] menuPx = new float[40], menuPy = new float[40], menuPvx = new float[40], menuPvy = new float[40];
    boolean menuPartsInit = false;

    void drawMenuParticles(Graphics2D g) {
        if (!menuPartsInit) {
            for (int i=0;i<40;i++) {
                menuPx[i]=RNG.nextFloat()*RunHome.W;
                menuPy[i]=RNG.nextFloat()*RunHome.H;
                menuPvx[i]=(RNG.nextFloat()-0.5f)*0.6f;
                menuPvy[i]=(RNG.nextFloat()-0.5f)*0.6f;
            }
            menuPartsInit=true;
        }
        for (int i=0;i<40;i++) {
            menuPx[i]+=menuPvx[i]; menuPy[i]+=menuPvy[i];
            if(menuPx[i]<0)menuPx[i]=RunHome.W; if(menuPx[i]>RunHome.W)menuPx[i]=0;
            if(menuPy[i]<0)menuPy[i]=RunHome.H; if(menuPy[i]>RunHome.H)menuPy[i]=0;
            float a=(float)(0.2+0.15*Math.sin(tick*0.04+i));
            g.setColor(new Color(CHAR_CLR[i%4].getRed(),CHAR_CLR[i%4].getGreen(),CHAR_CLR[i%4].getBlue(),(int)(a*255)));
            g.fillOval((int)menuPx[i]-3,(int)menuPy[i]-3,6,6);
        }
    }

    // ── Pause ─────────────────────────────────────────────────────────────────

    void drawPause(Graphics2D g) {
        g.setColor(new Color(0,0,0,150));
        g.fillRect(0,0,RunHome.W,RunHome.H);
        g.setColor(Color.WHITE);
        g.setFont(FONT_BIG);
        centreText(g,"PAUSED",RunHome.W/2,RunHome.H/2-30);
        g.setFont(FONT_MED);
        g.setColor(new Color(0xaaaaaa));
        centreText(g,"ESC or P to resume",RunHome.W/2,RunHome.H/2+20);
    }

    // ── Win banner ────────────────────────────────────────────────────────────

    void drawWinBanner(Graphics2D g) {
        g.setColor(new Color(0,0,0,100));
        g.fillRect(0,RunHome.H/2-70,RunHome.W,120);
        g.setColor(new Color(0x44ff44));
        g.setFont(new Font("Monospaced",Font.BOLD,52));
        centreText(g,"HOME SAFE!",RunHome.W/2,RunHome.H/2-10);
        g.setColor(Color.WHITE);
        g.setFont(FONT_MED);
        centreText(g,"ROUND "+(round+1)+" INCOMING... (R to skip)",RunHome.W/2,RunHome.H/2+35);
    }

    // ── Game over ─────────────────────────────────────────────────────────────

    void drawGameOver(Graphics2D g) {
        g.setColor(new Color(0,0,0,180));
        g.fillRect(0,0,RunHome.W,RunHome.H);
        g.setColor(new Color(0xff4444));
        g.setFont(new Font("Monospaced",Font.BOLD,64));
        centreText(g,"BUSTED!",RunHome.W/2,RunHome.H/2-80);
        g.setColor(Color.WHITE);
        g.setFont(FONT_MED);
        centreText(g,"SCORE: "+score,RunHome.W/2,RunHome.H/2-20);
        centreText(g,"COINS: "+coins+"💰",RunHome.W/2,RunHome.H/2+15);
        if (score >= bestScore) { g.setColor(new Color(0xffe040)); centreText(g,"★ NEW BEST! ★",RunHome.W/2,RunHome.H/2+50); }
        g.setColor(new Color(0xaaaaaa));
        g.setFont(FONT_SM);
        centreText(g,"R to play again  ·  ESC for menu",RunHome.W/2,RunHome.H/2+90);
    }

    void drawDead(Graphics2D g) { drawGameOver(g); }

    // ══════════════════════════════════════════════════════════════════════════
    // Helpers
    // ══════════════════════════════════════════════════════════════════════════

    void spawnBurst(float wx, float wy, Color c, int n) {
        for (int i=0;i<n;i++) {
            float a=(float)(Math.random()*Math.PI*2);
            float spd=(float)(Math.random()*4+1);
            particles.add(new Particle(wx, wy, (float)Math.cos(a)*spd, (float)Math.sin(a)*spd,
                    20+RNG.nextInt(20), c, 4+RNG.nextFloat()*5));
        }
    }

    void addFloatText(float wx, float wy, String t, Color c) {
        floatTexts.add(new FloatText(wx, wy, t, c));
    }

    void shake(float amount) { shakeAmt = Math.max(shakeAmt, amount); }

    boolean isPressed(int k) { return pressed.contains(k); }

    void centreText(Graphics2D g, String s, int cx, int y) {
        int w=g.getFontMetrics().stringWidth(s);
        g.drawString(s, cx-w/2, y);
    }

    void shadowText(Graphics2D g, String s, int cx, int y, Color fg, Color shadow) {
        int w=g.getFontMetrics().stringWidth(s);
        g.setColor(shadow); g.drawString(s, cx-w/2+3, y+3);
        g.setColor(fg);     g.drawString(s, cx-w/2, y);
    }

    static float clamp(float v, float lo, float hi) { return Math.max(lo, Math.min(hi, v)); }
}
