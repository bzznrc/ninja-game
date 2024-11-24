import random
import math
import pygame

from scripts.particle import Particle
from scripts.spark import Spark

class PhysicsEntity:
    def __init__(self, game, e_type, pos, size):
        self.game = game
        self.type = e_type
        self.pos = list(pos) #convert every iterable into a list
        self.size = size
        self.velocity = [0, 0]
        self.collisions = {'up': False, 'down': False, 'right': False, 'left': False} #keep track of collisions

        self.action = ''
        self.anim_offset = (-3, -3) #account for space needed for the animation (e.g. for running)
        self.flip = False
        self.set_action('idle')

        self.last_movement = [0, 0]


    def rect(self):
        return pygame.Rect(self.pos[0], self.pos[1], self.size[0], self.size[1])
    
    def set_action(self, action):
        if action != self.action: #prevent running logic at every frame
            self.action = action
            self.animation = self.game.assets[self.type + '/' + self.action].copy()

    def update(self, tilemap, movement=(0,0)):
        #RESET COLLISIONS
        self.collisions = {'up': False, 'down': False, 'right': False, 'left': False}

        #CALCULATE MOVEMENT
        frame_movement = (movement[0] + self.velocity[0], movement[1] + self.velocity[1])

        #UPDATE and COLLISIONS X
        self.pos[0] += frame_movement[0]
        entity_rect = self.rect()
        for rect in tilemap.physics_rects_around(self.pos):
            if entity_rect.colliderect(rect):
                if frame_movement[0] > 0: #you were moving right
                    entity_rect.right = rect.left #set our right side to the left one of the oject collided
                    self.collisions['right'] = True
                if frame_movement[0] < 0:
                    entity_rect.left = rect.right
                    self.collisions['left'] = True
                self.pos[0] = entity_rect.x #the final X position is stored in self.pos

        #UPDATE and COLLISIONS Y
        self.pos[1] += frame_movement[1]
        entity_rect = self.rect()
        for rect in tilemap.physics_rects_around(self.pos):
            if entity_rect.colliderect(rect):
                if frame_movement[1] > 0:
                    entity_rect.bottom = rect.top
                    self.collisions['down'] = True
                if frame_movement[1] < 0:
                    entity_rect.top = rect.bottom
                    self.collisions['up'] = True
                self.pos[1] = entity_rect.y

        #APPLY FLIP if required
        if movement[0] > 0: #our assets already face right
            self.flip = False
        if movement[0] < 0:
            self.flip = True

        #SET LAST MOVEMENT
        self.last_movement = movement

        #APPLY GRAVITY
        self.velocity[1] = min(5, self.velocity[1] + 0.1) #velocity is capped to 5 (terminal velocity)

        #RESET VELOCITY if Collision Y
        if self.collisions['down'] or self.collisions['up']:
            self.velocity[1] = 0

        self.animation.update()

    def render(self, surf, offset=(0, 0)):
        surf.blit(pygame.transform.flip(self.animation.img(), self.flip, False), (self.pos[0] - offset[0] + self.anim_offset[0], self.pos[1] - offset[1] + self.anim_offset[1]))

#INHERITING PE into CLASSES to implement specific behaviours (e.g. airtime for Player)
class Player(PhysicsEntity):
    def __init__(self, game, pos, size):
        super().__init__(game, 'player', pos, size) #use the super init fixing the type to player
        self.air_time = 0
        self.jumps = 1
        self.wall_slide = False
        self.dashing = 0

    def update(self, tilemap, movement=(0,0)):
        super().update(tilemap, movement=movement)
               
        #SET AIRTIME and JUMP
        if self.collisions['down']:
            self.air_time = 0
            self.jumps = 1 #restore the jumps
        else:
            self.air_time += 1 #jumping

        #DIE on AIRTIME
        if self.air_time > 180:
            self.game.screenshake = max(16, self.game.screenshake)
            self.game.dead += 1

        #SET WALLJUMP - check if valid at every update
        if (self.collisions['right'] or self.collisions['left']) and self.air_time >= 5:
            self.wall_slide = True
            self.velocity[1] = min(self.velocity[1], 0.5) #walljump y velocity is capped at 0.5
            if(self.collisions['right']): #flip if facing left
                self.flip = False
            else:
                self.flip = True
            self.set_action('wall_slide') #set action for the animation
        else:
            self.wall_slide = False
        
        #SET OTHER ACTION based on Airtime and Movement
        if not self.wall_slide:
            if self.air_time >= 5:
                self.set_action('jump')
            elif movement[0] != 0:
                self.set_action('run')
            else:
                self.set_action('idle')

        #SET DASHING
        #dash for 10/60 frames, cooldown for 50/60 frames
        if abs(self.dashing) > 50: #during dash
            self.velocity[0] = abs(self.dashing) / self.dashing * 8 #either 8 or -8
        elif abs(self.dashing) == 50: #stop dashing after 10 frames
            self.velocity[0] *= 0.1

        #DASHING PARTICLES
        if abs(self.dashing) > 50 and abs(self.dashing) < 60: #during dash
            p_velocity = [abs(self.dashing) / self.dashing * random.random() * 3, 0] #no y particles
            self.game.particles.append(Particle(self.game, 'particle', self.rect().center, velocity=p_velocity, frame=random.randint(0, 7)))
        
        elif abs(self.dashing) in {50, 60}: #either start or end of dash - burst of 20 particles
            for i in range(20):
                p_angle = random.random() * math.pi * 2
                p_speed = random.random() * 0.5 + 0.5
                p_velocity = [math.cos(p_angle) * p_speed, math.sin(p_angle) * p_speed] #standard way to derive velocity from angles
                self.game.particles.append(Particle(self.game, 'particle', self.rect().center, velocity=p_velocity, frame=random.randint(0, 7)))
        
        #CONTROLLING DASHING
        if self.dashing > 0:
            self.dashing = max(0, self.dashing - 1)
        elif self.dashing < 0:
            self.dashing = min(0, self.dashing + 1)

        #CONTROLLING X VELOCITY
        if self.velocity[0] > 0:
            self.velocity[0] = max(self.velocity[0] - 0.1, 0)
        elif self.velocity[0] < 0:
            self.velocity[0] = min(self.velocity[0] + 0.1, 0)

    def jump(self):
        if self.wall_slide:
            if self.flip and self.last_movement[0] < 0:
                self.velocity[0] = 3.5
                self.velocity[1] = -2.5
                self.air_time = 5
                self.jumps = max(0, self.jumps - 1)
            elif not self.flip and self.last_movement[0] > 0:
                self.velocity[0] = -3.5
                self.velocity[1] = -2.5
                self.air_time = 5
                self.jumps = max(0, self.jumps - 1)
            return True
                
        elif self.jumps:
            self.velocity[1] = -3
            self.jumps -= 1
            self.air_time = 5
            return True

    def dash(self):
        if not self.dashing:
            if self.flip:
                self.dashing = -60
            else:
                self.dashing = 60
            return True

    def render(self, surf, offset=(0, 0)):
        if abs(self.dashing) <= 50: #TODO ???
            super().render(surf, offset=offset)

class Enemy(PhysicsEntity):
    def __init__(self, game, pos, size):
        super().__init__(game, 'enemy', pos, size)

        self.walking = 0 #in frames

    def update(self, tilemap, movement=(0, 0)):
        if self.walking:
            #magic numbers on the solid check - checking 7px on x and 23px on y
            if tilemap.solid_check((self.rect().centerx + (-7 if self.flip else 7), self.pos[1] + 23)):
                if (self.collisions['right'] or self.collisions['left']):
                    self.flip = not self.flip
                else:
                    movement = (movement[0] - 0.5 if self.flip else 0.5, movement[1])
            else:
                self.flip = not self.flip
            self.walking = max(0, self.walking - 1)
            if not self.walking: #if enemy stopped walking, shoot #TODO - change shooting
                #SHOOTING
                dis = (self.game.player.pos[0] - self.pos[0], self.game.player.pos[1] - self.pos[1])
                if (abs(dis[1]) < 16):
                    if (self.flip and dis[0] < 0): #enemy facing left and player to its left
                        self.game.sfx['shoot'].play()
                        self.game.projectiles.append([[self.rect().centerx - 7, self.rect().centery], -1.5, 0])
                        #SPARKS - LEFT
                        for i in range(4):
                            self.game.sparks.append(Spark(self.game.projectiles[-1][0], random.random() - 0.5 + math.pi, 2 + random.random()))
                    elif (not self.flip and dis[0] > 0): #enemy facing right and player to its right
                        self.game.sfx['shoot'].play()
                        self.game.projectiles.append([[self.rect().centerx + 7, self.rect().centery], 1.5, 0])
                        #SPARKS - RIGHT
                        for i in range(4):
                            self.game.sparks.append(Spark(self.game.projectiles[-1][0], random.random() - 0.5, 2 + random.random()))
        elif random.random() < 0.01:
            self.walking = random.randint(30, 120)

        super().update(tilemap, movement=movement)

        if movement[0] != 0:
            self.set_action('run')
        else:
            self.set_action('idle')

        #ENEMY KILL - by dashing
        if abs(self.game.player.dashing) >= 50: #player dashing
            if self.rect().colliderect(self.game.player.rect()): #player collides with enemy
                self.game.screenshake = max(16, self.game.screenshake)
                self.game.sfx['hit'].play()
                #SPARKS
                for i in range(30):
                    s_angle = random.random() * math.pi * 2
                    s_speed = random.random() * 5
                    self.game.sparks.append(Spark(self.rect().center, s_angle, 2 + random.random()))
                    self.game.particles.append(Particle(self.game, 'particle', self.rect().center, velocity=[math.cos(s_angle + math.pi) * s_speed * 0.5, math.sin(s_angle + math.pi) * s_speed * 0.5], frame=random.randint(0, 7)))                
                #extra left and right sparks for enemies
                self.game.sparks.append(Spark(self.rect().center, 0, 5 + random.random()))
                self.game.sparks.append(Spark(self.rect().center, math.pi, 5 + random.random()))
                return True


    def render(self, surf, offset=(0, 0)):
        super().render(surf, offset=offset)

        if self.flip:
            surf.blit(pygame.transform.flip(self.game.assets['gun'], True, False), (self.rect().centerx - 4 - self.game.assets['gun'].get_width() - offset[0], self.rect().centery - offset[1]))
        else:
            surf.blit(self.game.assets['gun'], (self.rect().centerx + 4 - offset[0], self.rect().centery - offset[1]))