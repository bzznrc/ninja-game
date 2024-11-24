import sys
import random
import math
import pygame

from scripts.entities import Player, Enemy
from scripts.tilemap import Tilemap
from scripts.clouds import Clouds
from scripts.particle import Particle
from scripts.spark import Spark
from scripts.utils import *

#TODO H5 https://www.youtube.com/watch?v=2gABYM5M0ww&list=PLX5fBCkxJmm07E9qQYYJMR2fPDkzdBZew&index=4 
#sparks positions on enemy shooting are set at tuples so we get an error on their update

class Game:
    def __init__(self) -> None:
        pygame.init()

        pygame.display.set_caption("Ninja Game")
        self.screen = pygame.display.set_mode((640, 480)) #window surface
        self.display = pygame.Surface((320, 240), pygame.SRCALPHA) #rendering surface (half size of screen) - render here and scale to screen
        self.display_2 = pygame.Surface((320, 240))

        self.clock = pygame.time.Clock()

        self.assets = {
            'decor': load_images('tiles/decor'),
            'large_decor': load_images('tiles/large_decor'),
            'grass': load_images('tiles/grass'),
            'stone': load_images('tiles/stone'),
            'player': load_image('entities/player.png'),
            'background': load_image('background.png'),
            'clouds': load_images('clouds'),
            'gun': load_image('gun.png'),
            'projectile': load_image('projectile.png'),
            'player/idle': Animation(load_images('entities/player/idle'), img_dur=6),
            'player/run': Animation(load_images('entities/player/run'), img_dur=4),
            'player/jump': Animation(load_images('entities/player/jump')),
            'player/slide': Animation(load_images('entities/player/slide')),
            'player/wall_slide': Animation(load_images('entities/player/wall_slide')),
            'particle/leaf': Animation(load_images('particles/leaf'), img_dur=20, loop=False),
            'particle/particle': Animation(load_images('particles/particle'), img_dur=6, loop=False),
            'enemy/idle': Animation(load_images('entities/enemy/idle'), img_dur=6),
            'enemy/run': Animation(load_images('entities/enemy/run'), img_dur=4),
        }

        self.sfx = {
            'jump': pygame.mixer.Sound('data/sfx/jump.wav'),
            'dash': pygame.mixer.Sound('data/sfx/dash.wav'),
            'hit': pygame.mixer.Sound('data/sfx/hit.wav'),
            'shoot': pygame.mixer.Sound('data/sfx/shoot.wav'),
            'ambience': pygame.mixer.Sound('data/sfx/ambience.wav'),
        }
        self.sfx['jump'].set_volume(0.8)
        self.sfx['dash'].set_volume(0.4)
        self.sfx['hit'].set_volume(0.8)
        self.sfx['shoot'].set_volume(0.4)
        self.sfx['ambience'].set_volume(0.2)

        self.movement = [False, False] #left/right movement

        self.clouds = Clouds(self.assets['clouds'], count=16)

        self.player = Player(self, (50,50), (8,15))

        self.tilemap = Tilemap(self, tile_size=16)

        self.level = 0
        self.load_level(self.level)

    def load_level(self, map_id):
        try:
            self.tilemap.load('data/maps/' + str(map_id) + '.json')
        except FileNotFoundError:
            print("ERROR - no map found")

        #LEVEL VARIABLES
        self.scroll = [0, 0] #keep track of the camera movement
        self.dead = 0
        self.screenshake = 0
        self.transition = -30 #transition for loading levels

        #COLLECTIONS
        self.particles = [] #active particles
        self.enemies = []
        self.projectiles = []
        self.sparks = []

        #SPAWNERS
        self.leaf_spawners = [] #Rects for spawning leaves
        for tree in self.tilemap.extract([('large_decor', 2)], keep=True):
            self.leaf_spawners.append(pygame.Rect(4 + tree['pos'][0], 4 + tree['pos'][1], 23, 23))
        
        for spawner in self.tilemap.extract([('spawners', 0), ('spawners', 1)]): #no keep
            if spawner['variant'] == 0:
                self.player.pos = spawner['pos']
            else:
                self.enemies.append(Enemy(self, spawner['pos'], (8, 15)))

    def run(self):
        #LOAD MUSIC
        pygame.mixer.music.load('data/music.wav') #no output - it's the only track
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(-1) #play forever

        self.sfx['ambience'].play(-1)

        while True:
            #EMPTY THE IMAGE
            self.display.fill((0, 0, 0, 0))
            self.display_2.blit(self.assets['background'], (0, 0)) #override all with a bkgrd (same size as screen)

            #TRANSITION to NEXT LEVEL
            #trans = 0 during play, <0 when starting and > 0 when enemies are defeated
            if not len(self.enemies): #if no enemies left, transition to next level
                self.transition += 1
                if self.transition > 30:
                    self.level = min(self.level + 1, len(os.listdir('data/maps')) - 1) #cap the max level to the maps
                    self.load_level(self.level)
            if self.transition < 0:
                self.transition += 1

            #CHECK DEAD and RESTART
            if self.dead:
                self.dead += 1 #keep running for 1s
                if self.dead >= 10:
                    self.transition = min(30, self.transition + 1) #add closing transition on death
                if self.dead >= 60:
                    self.player.air_time = 0
                    self.load_level(self.level)

            #SET SCREENSHAKE
            self.screenshake = max(0, self.screenshake - 1) #reduces the screenshake

            #SET a CAMERA MOVEMENT
            #centering on the player but adjusting for display width because the coordinates are relative to 0,0
            #divide by 30 in the end to move there progressively (also faster the further away)
            #self.scroll[0] += 0.5 #move linearly to the right
            self.scroll[0] += (self.player.rect().centerx - self.display.get_width() / 2 - self.scroll[0]) / 10#30
            self.scroll[1] += (self.player.rect().centery - self.display.get_width() / 2 - self.scroll[1]) / 10#30
            render_scroll = (int(self.scroll[0]), int(self.scroll[1])) #convert to int to avoid jittering

            #SPAWN PARTICLES
            for rect in self.leaf_spawners:
                if random.random() * 49999 < rect.width * rect.height:
                    #spawning locations are linearly distributed along the rect size (via random 0 to 1)
                    pos = (rect.x + random.random() * rect.width, rect.y + random.random() * rect.height)
                    self.particles.append(Particle(self, 'leaf', pos, velocity=[-0.1, 0.3], frame=random.randint(0, 20)))

            #UPDATE AND RENDER
            self.clouds.update()
            self.clouds.render(self.display_2, offset=render_scroll) #no outline

            self.tilemap.render(self.display, offset=render_scroll)

            for enemy in self.enemies.copy():
                kill = enemy.update(self.tilemap, (0,0))
                enemy.render(self.display, offset=render_scroll)
                if kill:
                    self.enemies.remove(enemy)

            if not self.dead:
                self.player.update(self.tilemap, (self.movement[1] - self.movement[0], 0))
                self.player.render(self.display, offset=render_scroll)

            #TODO make projectile a class
            #[[x,y], direction, timer]
            for projectile in self.projectiles.copy():
                projectile[0][0] += projectile[1] #modify the x component addind direction
                projectile[2] += 1 #increment timer
                img = self.assets['projectile']
                self.display.blit(img, (projectile[0][0] - img.get_width() / 2 - render_scroll[0], projectile[0][1] - img.get_height() / 2 - render_scroll[1]))
                #WALL HIT
                if self.tilemap.solid_check(projectile[0]):
                    self.projectiles.remove(projectile)
                    #SPARKS - will bounce back
                    for i in range(4):
                            self.sparks.append(Spark(projectile[0], random.random() - 0.5 + (math.pi if projectile[1] > 0 else 0), 2 + random.random()))
                #TIMEOUT
                elif projectile[2] > 360: #remove after 6s
                    self.projectiles.remove(projectile)
                #PLAYER HIT
                elif abs(self.player.dashing) < 50: #only if the player is not dashing
                    if self.player.rect().collidepoint(projectile[0]): #player is hit
                        self.projectiles.remove(projectile)
                        self.dead += 1
                        self.screenshake = max(32, self.screenshake)
                        self.sfx['hit'].play()
                        #SPARKS - TODO: make a class - used in enemy death as well
                        for i in range(30):
                            s_angle = random.random() * math.pi * 2
                            s_speed = random.random() * 5
                            self.sparks.append(Spark(self.player.rect().center, s_angle, 2 + random.random()))
                            self.particles.append(Particle(self, 'particle', self.player.rect().center, velocity=[math.cos(s_angle + math.pi) * s_speed * 0.5, math.sin(s_angle + math.pi) * s_speed * 0.5], frame=random.randint(0, 7)))

            #SPARK U&R
            for spark in self.sparks.copy():
                kill = spark.update()
                spark.render(self.display, offset=render_scroll)
                if kill:
                    self.sparks.remove(spark)

            #BUILD OUTLINES MASK
            #the silhouette has blobs of black wherever we drew something
            display_mask = pygame.mask.from_surface(self.display)
            display_silhouette = display_mask.to_surface(setcolor=(0, 0, 0, 180), unsetcolor=(0, 0, 0, 0)) #rgb + transparency
            
            #APPLY OUTLINES
            #self.display_2.blit(display_silhouette, (0,0))
            for offset in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                self.display_2.blit(display_silhouette, offset)

            #PARTICLE U&R
            for particle in self.particles.copy():
                kill = particle.update()
                if particle.p_type == 'leaf':
                    particle.pos[0] += math.sin(particle.animation.frame * 0.035) * 0.3
                if kill:
                    self.particles.remove(particle)
                particle.render(self.display, offset=render_scroll)

            #print(self.tilemap.physics_rects_around(self.player.pos))

            #GET INPUTS
            for event in pygame.event.get(): #all the inputs
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN: #a key has been pressed down
                    if event.key == pygame.K_a: #the specific key
                        self.movement[0] = True
                    if event.key == pygame.K_d:
                        self.movement[1] = True
                    #if event.key == pygame.K_w:
                    if event.key == pygame.K_SPACE:
                        if self.player.jump():
                            self.sfx['jump'].play()
                    if event.key == pygame.K_LSHIFT:
                        if self.player.dash():
                            self.sfx['dash'].play()
                if event.type == pygame.KEYUP: #a key has been lifted up
                    if event.key == pygame.K_a:
                        self.movement[0] = False
                    if event.key == pygame.K_d:
                        self.movement[1] = False

            if self.transition:
                transition_surf = pygame.Surface(self.display.get_size())
                #circle is drawn on transition_surf (not display) / 30 is transition value, 8 is a constant due to the 4 edges of the screen
                pygame.draw.circle(transition_surf, (255, 255, 255), (self.display.get_width()// 2, self.display.get_height()// 2), (30 - abs(self.transition)) * 8)
                transition_surf.set_colorkey((255, 255, 255)) #white becomes transparent
                self.display.blit(transition_surf, (0, 0))

            #DRAW DISPLAY 2 OVER DISPLAY 1 / add PROJECTION
            self.display_2.blit(self.display, (0, 0))

            #SCALE AND RENDER
            screenshake_offset = (random.random() * self.screenshake - self.screenshake / 2, random.random() * self.screenshake - self.screenshake / 2)
            self.screen.blit(pygame.transform.scale(self.display_2,self.screen.get_size()), screenshake_offset)

            #UPATE
            pygame.display.update() #draw the new things on the screen
            self.clock.tick(60) #dynamic pause to hit 60fps

Game().run()