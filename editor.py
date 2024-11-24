import sys
import pygame

from scripts.tilemap import Tilemap
from scripts.utils import *

RENDER_SCALE = 2.0

class Editor:
    def __init__(self) -> None:
        pygame.init()

        pygame.display.set_caption("Editor")
        self.screen = pygame.display.set_mode((640, 480)) #window surface
        self.display = pygame.Surface((320, 240)) #rendering surface (half size of screen) - render here and scale to screen
        #self.display = pygame.Surface((160, 120))

        self.clock = pygame.time.Clock()

        self.assets = {
            'decor': load_images('tiles/decor'),
            'large_decor': load_images('tiles/large_decor'),
            'grass': load_images('tiles/grass'),
            'stone': load_images('tiles/stone'),
            'spawners': load_images('tiles/spawners'),
        }
        #print(self.assets)

        self.movement = [False, False, False, False] #camera movement

        self.tilemap = Tilemap(self, tile_size=16)
        try:
            self.tilemap.load('map.json')
        except FileNotFoundError:
            pass

        self.scroll = [0, 0]

        self.tile_list = list(self.assets)
        self.tile_group = 0
        self.tile_variant = 0

        self.clicking = False
        self.right_clicking = False
        self.shift = False
        self.ongrid = True

    def run(self):
        while True:
            #EMPTY THE IMAGE
            self.display.fill((100, 100, 250))

            #SET a CAMERA MOVEMENT
            self.scroll[0] += (self.movement[1] - self.movement[0]) * 2
            self.scroll[1] += (self.movement[3] - self.movement[2]) * 2
            render_scroll = (int(self.scroll[0]), int(self.scroll[1]))

            #RENDER TILEMAP
            self.tilemap.render(self.display, offset=render_scroll)

            #RENDER CURRENT TILE
            current_tile_img = self.assets[self.tile_list[self.tile_group]][self.tile_variant].copy()
            current_tile_img.set_alpha(100) #0-transparent, 255-opaque
            self.display.blit(current_tile_img, (5,5))

            #STORE MOUSE POSITION
            mpos = pygame.mouse.get_pos()
            mpos = (mpos[0] / RENDER_SCALE, mpos[1] /RENDER_SCALE)
            tile_pos = (int((mpos[0] + self.scroll[0]) // self.tilemap.tile_size), int((mpos[1] + self.scroll[1]) // self.tilemap.tile_size))
            
            #DISPLAY PREVIEW - starting from the tile_pos to align with the grid
            if self.ongrid:
                self.display.blit(current_tile_img, (tile_pos[0] * self.tilemap.tile_size - self.scroll[0], tile_pos[1] * self.tilemap.tile_size - self.scroll[1]))
            else:
                self.display.blit(current_tile_img, mpos)
            
            #PLACE a NEW TILE
            if self.clicking and self.ongrid: #the off-grid is on the mouse button listener
                self.tilemap.tilemap[str(tile_pos[0]) + ';' + str(tile_pos[1])] = {'type': self.tile_list[self.tile_group], 'variant': self.tile_variant, 'pos': tile_pos}
                
            #DELETE TILES
            if self.right_clicking:
                tile_loc = str(tile_pos[0]) + ';' + str(tile_pos[1])
                if tile_loc in self.tilemap.tilemap:
                    del self.tilemap.tilemap[tile_loc]
                #DELETING OFFGRID - not optimised
                for tile in self.tilemap.offgrid_tiles:#.copy(): #TODO: use copy to avoid messing with the iteration
                    tile_img = self.assets[tile['type']][tile['variant']] #computing hitbox for offgrid tile
                    tile_r = pygame.Rect(tile['pos'][0] - self.scroll[0], tile['pos'][1] - self.scroll[1], tile_img.get_width(), tile_img.get_height())
                    if tile_r.collidepoint(mpos):
                        self.tilemap.offgrid_tiles.remove(tile)

            #GET INPUTS
            for event in pygame.event.get(): #all the inputs
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1: #left click
                        self.clicking = True
                        if not self.ongrid:
                            self.tilemap.offgrid_tiles.append({'type': self.tile_list[self.tile_group], 'variant': self.tile_variant, 'pos': (mpos[0] + self.scroll[0], mpos[1] + self.scroll[1])})
                    if event.button == 3: #right click
                        self.right_clicking = True
                    if self.shift: #GROUPS > VARIANTS
                        if event.button == 4: #scroll up
                            self.tile_variant = (self.tile_variant - 1) % len(self.assets[self.tile_list[self.tile_group]])
                        if event.button == 5: #scroll down
                            self.tile_variant = (self.tile_variant + 1) % len(self.assets[self.tile_list[self.tile_group]])
                    else: #GROUPS
                        if event.button == 4: #scroll up 
                            self.tile_group = (self.tile_group - 1) % len(self.tile_list)
                            self.tile_variant = 0
                        if event.button == 5: #scroll down
                            self.tile_group = (self.tile_group + 1) % len(self.tile_list)
                            self.tile_variant = 0

                if event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        self.clicking = False
                    if event.button == 3:
                        self.right_clicking = False

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_a:
                        self.movement[0] = True
                    if event.key == pygame.K_d:
                        self.movement[1] = True
                    if event.key == pygame.K_w:
                        self.movement[2] = True
                    if event.key == pygame.K_s:
                        self.movement[3] = True
                    if event.key == pygame.K_g:
                        self.ongrid = not self.ongrid #toggle OnGrid
                    if event.key == pygame.K_t:
                        self.tilemap.autotile()
                    if event.key == pygame.K_F5:
                        self.tilemap.save('map.json')
                    if event.key == pygame.K_LSHIFT:
                        self.shift = True
                if event.type == pygame.KEYUP: #a key has been lifted up
                    if event.key == pygame.K_a:
                        self.movement[0] = False
                    if event.key == pygame.K_d:
                        self.movement[1] = False
                    if event.key == pygame.K_w:
                        self.movement[2] = False
                    if event.key == pygame.K_s:
                        self.movement[3] = False
                    if event.key == pygame.K_LSHIFT:
                        self.shift = False
            
            #SCALE AND RENDER
            self.screen.blit(pygame.transform.scale(self.display,self.screen.get_size()), (0,0))
            
            #UPATE
            pygame.display.update() #draw the new things on the screen
            self.clock.tick(60) #dynamic pause to hit 60fps

Editor().run()