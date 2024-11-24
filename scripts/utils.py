import os
import pygame

BASE_IMG_PATH = 'data/images/'

def load_image(path):
    img = pygame.image.load(BASE_IMG_PATH + path).convert() #convert makes the image optimized in memory
    img.set_colorkey((0,0,0)) #all black in bkgds becomes transparent
    return img

def load_images(path):
    images = []
    for img_name in os.listdir(BASE_IMG_PATH + path):
        images.append(load_image(path + '/' + img_name))
    return images

class Animation:
    def __init__(self, images, img_dur=5, loop=True):
        self.images = images
        self.loop = loop
        self.img_duration = img_dur
        self.done = False
        self.frame = 0

    def copy(self): #will leverage the reference of the images list - every copy will share the same list
        return Animation(self.images, self.img_duration, self.loop)
    
    def update(self): #loops around at the end
        if self.loop:
            self.frame = (self.frame + 1) % (self.img_duration * len(self.images)) #module avoids off by one
        else:
            self.frame = min(self.frame + 1, self.img_duration * len(self.images) - 1) #-1 because off by one
            if self.frame >= self.img_duration * len(self.images) - 1:
                self.done = True
    
    def img(self): #get the current image of the animation
        return self.images[int(self.frame / self.img_duration)]

    
