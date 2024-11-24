import pygame
import json

#RULES for AUTOTILE
#tuple/sorted is for avoiding duplicate cases
#values are indexes for the variants needed in each case
AUTOTILE_MAP = {
    tuple(sorted([(1,0), (0, 1)])): 0,
    tuple(sorted([(1,0), (0, 1), (-1, 0)])): 1,
    tuple(sorted([(-1,0), (0,1)])): 2,
    tuple(sorted([(-1,0), (0,-1), (0,1)])): 3,
    tuple(sorted([(-1, 0), (0, -1)])): 4,
    tuple(sorted([(-1, 0), (0, -1), (1, 0)])): 5,
    tuple(sorted([(1,0), (0,-1)])): 6,
    tuple(sorted([(1, 0), (0, -1), (0, 1)])): 7,
    tuple(sorted([(1, 0), (-1, 0), (0, 1), (0, -1)])): 8,
}

NEIGHBOR_OFFSETS = [(-1,0),(-1,-1),(0,-1),(1,-1),(1,0),(0,0),(-1,1),(0,1),(1,1)]
PHYSICS_TILES = {'grass', 'stone'} #set of tile types that support physics
AUTOTILE_TYPES = {'grass', 'stone'}

class Tilemap:
    def __init__(self, game, tile_size=16):
        self.game = game
        self.tile_size = tile_size
        self.tilemap = {} #this handles physics
        self.offgrid_tiles = [] #this doesn't handle physics

    def extract(self, id_pairs, keep=False):
        '''takes id_pairs (types of tiles)
        returns their location on the map
        can remove them with keep
        '''
        matches = []
        
        #OFFGRID
        for tile in self.offgrid_tiles.copy():
            if(tile['type'], tile['variant']) in id_pairs:
                matches.append(tile.copy())
                if not keep:
                    self.offgrid_tiles.remove(tile)
        #ONGRID
        for loc in self.tilemap:
            tile = self.tilemap[loc]
            if(tile['type'], tile['variant']) in id_pairs:
                matches.append(tile.copy())
                #copying the pos value (no referece to tilemap) and setting it to pixels
                matches[-1]['pos'] = matches[-1]['pos'].copy()
                matches[-1]['pos'][0] *= self.tile_size
                matches[-1]['pos'][1] *= self.tile_size
                if not keep:
                    del self.tilemap[loc]
        
        return matches

    def tiles_around(self, pos):
        tiles = []
        tile_loc = (int(pos[0] // self.tile_size), int(pos[1] // self.tile_size)) #convert pixel pos into tile pos
        for offset in NEIGHBOR_OFFSETS:
            check_loc = str(tile_loc[0] + offset[0]) + ';' + str(tile_loc[1] + offset[1]) #add offset to tile pos
            if check_loc in self.tilemap: #check the new position is in the tilemap
                tiles.append(self.tilemap[check_loc])
        return tiles
    
    def physics_rects_around(self, pos):
        rects = [] #will generate rects for the physics tiles around (now drawing them though)
        for tile in self.tiles_around(pos):
            if tile['type'] in PHYSICS_TILES: #we can collide with that
                rects.append(pygame.Rect(tile['pos'][0] * self.tile_size, tile['pos'][1] * self.tile_size, self.tile_size, self.tile_size))
        return rects
    
    def solid_check(self, pos):
        '''checks if the pos is a solid tile
        '''
        tile_loc = str(int(pos[0] // self.tile_size)) + ';' + str(int(pos[1] // self.tile_size)) #pixels to tiles
        if tile_loc in self.tilemap:
            if self.tilemap[tile_loc]['type'] in PHYSICS_TILES:
                return self.tilemap[tile_loc]


    def render(self, surf, offset=(0, 0)):
        #RENDER for OFFGRID TILES (background) - not optimized
        for tile in self.offgrid_tiles:
            surf.blit(self.game.assets[tile['type']][tile['variant']], (tile['pos'][0] - offset[0], tile['pos'][1] - offset[1]))

        #RENDER for TILES (adjusting for tile_size) - only considering tiles on screen
        #get the leftmost and rightmost edges of the screen in tile_size
        #add padding on the range to avoid having bit items on the edges disappear
        for x in range(offset[0] // self.tile_size - 1, (offset[0] + surf.get_width()) // self.tile_size + 1):
            for y in range(offset[1] // self.tile_size - 1, (offset[1] + surf.get_height()) // self.tile_size + 1):
                loc = str(x) + ';' + str(y) #compute current location in string
                if loc in self.tilemap:
                    tile = self.tilemap[loc]
                    surf.blit(self.game.assets[tile['type']][tile['variant']], (tile['pos'][0] * self.tile_size - offset[0], tile['pos'][1] * self.tile_size - offset[1]))

    def autotile(self):
        for loc in self.tilemap:
            tile = self.tilemap[loc]
            neighbors = set()
            for shift in [(1, 0), (-1, 0), (0, -1), (0, 1)]:
                check_loc = str(tile['pos'][0] + shift[0]) + ';' + str(tile['pos'][1] + shift[1])
                if check_loc in self.tilemap:
                    if self.tilemap[check_loc]['type'] == tile['type']:
                        neighbors.add(shift)
            neighbors = tuple(sorted(neighbors))
            if (tile['type'] in AUTOTILE_TYPES) and (neighbors in AUTOTILE_MAP):
                tile['variant'] = AUTOTILE_MAP[neighbors]

    def save(self, path):
        f = open(path, 'w')
        json.dump({'tilemap': self.tilemap, 'tile_size': self.tile_size, 'offgrid': self.offgrid_tiles}, f)
        f.close()

    def load(self, path):
        f = open(path, 'r')
        map_data = json.load(f)
        f.close()

        self.tilemap = map_data['tilemap']
        self.tile_size = map_data['tile_size']
        self.offgrid_tiles = map_data['offgrid']