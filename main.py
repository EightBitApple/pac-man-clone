import pygame as pg
import pytmx

import os
import sys

from cryptography.fernet import Fernet
from pygame.math import Vector2
from os import path
import math

# files
from settings import *
from sprites import *


class Game:
    ''' Houses game initialisation, loading, loop, drawing and screens. '''

    def __init__(self):
        '''Initialise pygame, clock, font and windows.'''
        pg.init()
        # pg.mixer.init()  # sound engine
        self.screen = pg.display.set_mode((WIDTH, HEIGHT))
        pg.display.set_caption("PAC-MAN")

        self.clock = pg.time.Clock()
        self.font_name = pg.font.match_font(FONT_NAME)
        self.running = True
        self.playing = False
        self.key_debug_text = ""

        self.maze_flash_duration = .25
        self.maze_flash_alternate = .25

        self.dots_threshold = 30

        # load the high score and key and decrypt the score
        encryptor = SymmetricKeyEncrypt()
        loaded_key = encryptor.key_load('highscore_key')
        self.high_score = encryptor.file_decrypt(
            loaded_key, 'highscore.txt',  "Key and or high score has been tampered with!")

        # initalise file paths
        self.root = path.dirname(__file__)
        self.img_dir = path.join(self.root, 'img')
        self.maze_dir = path.join(self.root, 'maze')
        self.title_img = pg.image.load(path.join(self.img_dir,
                                                 'title_back.png'))

        self.new_game()

    def tint_image(self, image, colour):
        '''Tints an image a specifed colour using pygame blend modes. Used for
        making blue maze image.'''

        coloured_image = pg.Surface(image.get_size())
        coloured_image.fill(colour)

        final_image = image.copy()
        final_image.blit(coloured_image, (0, 0), special_flags=pg.BLEND_MULT)
        return final_image

    def new_game(self):
        ''' Initialise relevant attributes and load graphics and maze '''

        def slice_frame_sequence(coords, num_frames):
            '''Slice a sequence of contiguous frames.'''
            frames = []
            for i in range(num_frames):
                frames.append(self.spritesheet.get_image(
                    coords.x, coords.y, TILESIZE, TILESIZE))
                coords.x += TILESIZE
            return frames

        self.pause_countdown = 1.5
        self.pre_game_countdown = True
        self.manual_pause = False

        self.bonus_time = 60  # spawn bonus fruit 60 seconds into game
        self.bonus_timer = 0  # count the time elapsed since game begun

        self.bonus_spawned = False
        self.noup_coords = []

        self.maze = TiledMap(path.join(self.maze_dir, 'maze.tmx'))
        self.maze_white = self.maze.make_map().convert()
        self.maze_white.set_colorkey(BLACK)

        # create blue maze from white maze
        self.maze_blue = self.tint_image(self.maze_white, BLUE)
        self.maze_img = self.maze_blue
        self.maze_rect = self.maze_img.get_rect()
        self.maze_flash = True

        self.spritesheet = Spritesheet(os.path.join(self.img_dir, SPRITESHEET))

        # LOAD GRAPHICS -------------------------------------------------------
        pacman_frames = [[], [], [], []]
        ghost_frames = [[], [], [], [], [], [], []]

        # slice Pac-Man's eating frames, he will be facing right
        slice_coords = Vector2(60, 0)
        for i in range(4):
            pacman_frames[0].append(self.spritesheet.get_image(
                slice_coords.x, slice_coords.y, TILESIZE, TILESIZE))
            slice_coords.x += TILESIZE

        # using the sliced eating frames, create eating frames for each
        # orientation, this is faster than rotating frames at run time
        angle = 90
        for orientation in range(1, 4):
            for i in range(4):
                if orientation != 3:
                    # append up and down orientations
                    pacman_frames[orientation].append(
                        pg.transform.rotate(pacman_frames[0][i], angle))
                else:
                    # flip the sprite horizontally
                    pacman_frames[orientation].append(
                        pg.transform.flip(pacman_frames[0][i], True, False))
            angle -= 180

        # slice death frames
        pacman_frames.append(slice_frame_sequence(Vector2(60, 20), 4))

        # slice ghost frames
        slice_coords = Vector2(0, 0)
        for frame_trio in range(7):
            for i in range(3):
                ghost_frames[frame_trio].append(self.spritesheet.get_image(
                    slice_coords.x, slice_coords.y, TILESIZE, TILESIZE))
                slice_coords.x += TILESIZE

            # append a flipped frame after each ghost colour
            ghost_frames[frame_trio].append(pg.transform.flip(
                ghost_frames[frame_trio][1], True, False))
            slice_coords.y += TILESIZE
            slice_coords.x = 0

        pellet_frames = slice_frame_sequence(Vector2(60, 40), 3)
        self.fruit_frames = slice_frame_sequence(Vector2(60, 60), 4)

        self.all_sprites = pg.sprite.LayeredUpdates()  # for sprite layering
        self.walls = pg.sprite.Group()
        self.pellets = pg.sprite.Group()
        self.power_pellets = pg.sprite.Group()
        self.ghosts = pg.sprite.Group()
        self.fruits = pg.sprite.Group()

        # iterate through each object in Tiled object layers
        # object proprieties are given in a dictionary for quick lookup
        # pass in the appropriate frames for each object.
        for tile_object in self.maze.tmxdata.objects:

            if tile_object.name == 'pellet_spawn':
                Pellet(self, tile_object.x, tile_object.y, pellet_frames)
            elif tile_object.name == 'power_pellet_spawn':
                PowerPellet(self, tile_object.x, tile_object.y, pellet_frames)
            elif tile_object.name == 'bonus_spawn':
                self.bonus_coords = Vector2(tile_object.x, tile_object.y)

            elif tile_object.name == 'wall':
                WallCollision(self, tile_object.x, tile_object.y,
                              tile_object.width, tile_object.height)

            elif tile_object.name == 'player_spawn':
                self.player = Player(self, tile_object.x,
                                     tile_object.y, pacman_frames)

            elif tile_object.name == 'blinky_spawn':
                self.blinky = Ghost(self, tile_object.x, tile_object.y,
                                    ghost_frames)
            elif tile_object.name == 'pinky_spawn':
                self.pinky = Pinky(self, tile_object.x, tile_object.y,
                                   ghost_frames)
            elif tile_object.name == 'inky_spawn':
                self.inky = Inky(self, tile_object.x, tile_object.y,
                                 ghost_frames)
            elif tile_object.name == 'clyde_spawn':
                self.clyde = Clyde(self, tile_object.x, tile_object.y,
                                   ghost_frames)

            elif tile_object.name == 'no_up':
                self.noup_coords.append(Vector2(tile_object.x, tile_object.y))

        self.dots_remain = len(self.pellets.sprites())

        self.game_loop()

    def game_loop(self):
        '''Main game loop - set playing to false to end game'''

        while self.playing:
            # get time delta in milliseconds
            self.time_delta = self.clock.tick(FPS) / 1000
            self.get_events()

            # when the game is not paused
            if self.pause_countdown <= 0 and not self.manual_pause:
                self.pre_game_countdown = False
                if not self.bonus_spawned:
                    self.bonus_timer += self.time_delta

                # force Blinky into chase mode if there is less than 30
                # pellets on screen
                if self.dots_remain < self.dots_threshold:
                    setattr(self.blinky, 'ignore_scatter', True)

                # break into game over screen if all lives are depleted
                if getattr(self.player, 'lives') < 0:
                    self.post_message = "Game Over!"
                    self.playing = False
                    break

                # clear the level once all pellets have been eaten
                if getattr(self.player, 'level_clear'):
                    self.post_message = "Level Clear!"
                    self.playing = False
                    break

                # reset position once death animation has finished playing
                if getattr(self.player, 'death_animation'):
                    self.reset_entities()

                    # set ready for the next pre-game pause
                    self.pause_countdown = 1.5
                    self.pre_game_countdown = True
                    continue

                # check if it's time to spawn the bonus fruit
                elif not self.bonus_spawned and self.bonus_timer >= self.bonus_time:
                    BonusFruit(
                        self,
                        self.bonus_coords.x,
                        self.bonus_coords.y,
                        self.fruit_frames)
                    self.bonus_spawned = True

                self.update()  # game only updates when not paused

            else:
                self.pause_countdown -= self.time_delta

                if getattr(self.player, 'death_animation'):
                    if self.pause_countdown <= 3:
                        # play out death animation
                        self.player.animate()
                        for ghost in self.ghosts:
                            # make ghosts disappear by setting sprite to
                            # just hot pink
                            ghost.image = ghost.frames[5][2]

                elif getattr(self.player, 'level_clear'):
                    self.maze_flash_duration += self.time_delta

                    if self.pause_countdown <= 4:
                        # enter vibe mode
                        self.player.image = self.player.frames[-1][0]
                        # make ghosts disappear
                        for ghost in self.ghosts:
                            ghost.image = ghost.frames[5][2]

                        # flash the walls on a delay
                        if self.maze_flash_duration >= self.maze_flash_alternate:
                            self.maze_flash_duration = 0
                            if self.maze_flash:
                                self.maze_img = self.maze_white
                            else:
                                self.maze_img = self.maze_blue
                            self.maze_img = self.maze_white if self.maze_flash else self.maze_blue
                            self.maze_flash = not self.maze_flash

            self.draw()  # always draw no matter if game is paused or not.

    def update(self):
        '''Call each sprites update method.'''

        self.all_sprites.update()

    def draw_background_grid(self):
        ''' Draw a faint grid for the background for testing purposes.'''

        for x in range(0, WIDTH, TILESIZE):
            pg.draw.line(self.screen, LIGHTGREY, (x, TILESIZE * 3),
                         (x, HEIGHT - (TILESIZE * 3 - 10)))

        for y in range(TILESIZE * 3, HEIGHT - (TILESIZE * 3), TILESIZE):
            pg.draw.line(self.screen, LIGHTGREY, (0, y), (WIDTH, y))

    def draw(self):
        '''Draw sprites, maze and HUD elements.'''

        self.screen.fill(BACKGROUND_COLOUR)
        self.screen.blit(self.maze_img, (0, 0))
        self.all_sprites.draw(self.screen)

        # debug - draw text of currently pressed and registered key
        self.draw_text(self.key_debug_text, 22, WHITE,
                       WIDTH * .75, HEIGHT - 40)

        self.draw_text(str(getattr(self.player, 'score')),
                       22, WHITE, WIDTH * .5, 25)
        self.draw_text((str(self.high_score)), 18, WHITE, WIDTH * .5, 45)

        self.draw_text(
            f"Lives: {(str(getattr(self.player, 'lives')))}",
            22,
            WHITE,
            40,
            HEIGHT -
            40)

        # draw a countdown before the game starts
        if self.pause_countdown > 0 and self.pre_game_countdown:
            if self.manual_pause:
                countdown_text = "PAUSED"
            elif self.pause_countdown > .5:
                countdown_text = "READY?"
            else:
                countdown_text = "GO!"
            self.draw_text(countdown_text, 30, WHITE,
                           WIDTH * .5, HEIGHT * .5 - 10)

        elif self.manual_pause:
            self.draw_text("PAUSED", 30, WHITE,
                           WIDTH * .5, HEIGHT * .5 - 10)

        pg.display.flip()

    def draw_text(self, text, size, colour, x, y):
        '''Called to draw text of varying sizes, colours and positions.'''

        font = pg.font.Font(self.font_name, size)
        # flag means anti-aliasing
        text_surface = font.render(text, True, colour)
        text_rect = text_surface.get_rect()
        text_rect.center = (x, y)

        self.screen.blit(text_surface, text_rect)

    def draw_alpha_rect(self, x, y, width, height, alpha=200):
        '''Draw a rectangle with alpha transparency.'''

        surf = pg.Surface((width, height))
        surf.set_alpha(alpha)
        surf.fill(BLACK)
        self.screen.blit(surf, (x, y))

    def get_events(self):
        '''Catches non-gameplay key stokes and when the player presses close.'''

        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.playing = False
                self.running = False
            elif event.type == pg.KEYUP:
                if event.key == pg.K_ESCAPE:
                    if self.pause_countdown <= 0:
                        self.manual_pause = not self.manual_pause

    def reset_entities(self):
        '''Reset the states and position of ghosts and player.'''

        self.player.reset_status()
        for ghost in self.ghosts:
            ghost.reset_status()

    def wait_for_key(self):
        '''Loop to wait for key stroke during title and post-game screens.'''

        waiting = True
        while waiting:
            self.clock.tick(FPS)
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    self.running = False
                    waiting = False
                if event.type == pg.KEYUP:
                    if event.key == pg.K_RETURN:
                        self.running = True
                        self.playing = True
                        waiting = False

    def show_title_screen(self):
        '''Draws a static title screen.'''

        # since pygame font rendering does not support newline chars, A list
        # that's iterated through is the next best thing
        instuctions = [
            "Eat all the pellets and evade the ghosts!",
            "Eat the flashing pellets to frighten them!",
            "Eat frightened ghosts in quick succession to boost your score!",
            "Tap the WASD or arrow keys to move in a direction.",

            "Tap another direction to automatically move in when possible.",
            "Tap Space to stop moving."]
        spacing = 30

        self.screen.blit(self.title_img, (0, 0))

        self.draw_alpha_rect(0, HEIGHT * .2, WIDTH, HEIGHT * .15)
        self.draw_text("PAC-MAN", 48, PAC_YELLOW, WIDTH * .5, HEIGHT * .25)

        self.draw_text(f"High Score: {self.high_score}",
                       22, WHITE, WIDTH * .5, HEIGHT * .25 + 50)

        self.draw_alpha_rect(0, HEIGHT * .37, WIDTH, HEIGHT * .28)

        # iterate through list and multiply index by line number to apply spacing
        for line_num, line in enumerate(instuctions):
            self.draw_text(line, 22, WHITE, WIDTH * .5,
                           (HEIGHT * .4) + line_num * spacing)

        self.draw_alpha_rect(0, HEIGHT * .725, WIDTH, HEIGHT * .05)
        self.draw_text("Press Enter to play!", 22,
                       PAC_YELLOW, WIDTH * .5, HEIGHT * .75)

        pg.display.flip()
        self.wait_for_key()

    def show_post_game_screen(self):
        '''Screen that displays one of two messages depending on whether the
        player won or lost.'''

        # if the player clicked the close window button, then 'running' is set
        # to false, thus skip drawing this screen
        if not self.running:
            return

        player_score = getattr(self.player, 'score')
        high_score_message = ""

        self.screen.blit(self.title_img, (0, 0))

        self.draw_alpha_rect(0, HEIGHT * .2, WIDTH, HEIGHT * .1)
        self.draw_text(self.post_message, 48, PAC_YELLOW,
                       WIDTH * .5, HEIGHT * .25)

        self.draw_alpha_rect(0, HEIGHT * .47, WIDTH, HEIGHT * .18)
        self.draw_text(
            f"score: {player_score}", 22, WHITE, WIDTH * .5, HEIGHT * .5)

        self.draw_text(
            "Press enter to play again!",
            22,
            PAC_YELLOW,
            WIDTH * .5,
            HEIGHT * .5 + 80)

        try:
            if player_score > self.high_score:
                high_score_message = "NEW HIGH SCORE!"
                self.high_score = player_score

                # create a new key to encrypt the new high score
                encryptor = SymmetricKeyEncrypt()
                new_key = encryptor.key_create()
                encryptor.key_write(new_key, 'highscore_key')
                encryptor.file_encrypt(
                    new_key, self.high_score, 'highscore.txt')
            else:
                high_score_message = f"High Score: {self.high_score}"
        except:
            # if the key or high score has been tampered with, show the temper
            # message instead
            high_score_message = self.high_score

        self.draw_text(high_score_message, 22, WHITE,
                       WIDTH * .5, HEIGHT * .5 + 40)

        self.draw_text("Press the enter key to play again!",
                       22, WHITE, WIDTH * .5, HEIGHT * 3 / .25)

        pg.display.flip()

        self.wait_for_key()


class TiledMap:
    '''Reads a *.tmx file and constructs an image from it.'''

    def __init__(self, filename):
        '''Load in the *.tmx file.'''

        tm = pytmx.load_pygame(filename, pixelalpha=True)
        self.width = tm.width * tm.tilewidth
        self.height = tm.height * tm.tileheight
        self.tmxdata = tm

    def render(self, surface):
        '''Transcode all tiles from file into a single image.'''

        ti = self.tmxdata.get_tile_image_by_gid
        for layer in self.tmxdata.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                for x, y, gid in layer:
                    tile = ti(gid)
                    if tile:
                        surface.blit(tile, (x * self.tmxdata.tilewidth,
                                            y * self.tmxdata.tileheight))

    def make_map(self):
        '''Calls the method to create the image and returns it.'''

        temp_surface = pg.Surface((self.width, self.height))
        self.render(temp_surface)
        return temp_surface


class SymmetricKeyEncrypt:
    '''Used to encrypt and decrypt a text file using symmetric key encryption.'''

    def key_create(self):
        key = Fernet.generate_key()
        return key

    def key_write(self, key, key_name):
        with open(key_name, 'wb') as mykey:
            mykey.write(key)

    def key_load(self, key_name):
        with open(key_name, 'rb') as mykey:
            key = mykey.read()
        return key

    def file_encrypt(self, key, value, encrypted_file):
        f = Fernet(key)

        # encode value to bytes before encrypting
        value = str(value)
        value = value.encode()

        encrypted = f.encrypt(value)

        with open(encrypted_file, 'wb') as file:
            file.write(encrypted)

    def file_decrypt(self, key, encrypted_file, tamper_msg):
        f = Fernet(key)

        with open(encrypted_file, 'rb') as file:
            encrypted = file.read()

        try:
            decrypt = f.decrypt(encrypted)
            decrypt = int(decrypt)
        except BaseException:
            decrypt = tamper_msg

        return decrypt


def main():
    '''Instantiates game object and calls screen methods.'''

    g = Game()
    g.show_title_screen()
    while getattr(g, "running"):
        g.new_game()
        g.show_post_game_screen()

    # safely quit out of pygame and python
    pg.quit()
    sys.exit()


if __name__ == '__main__':
    main()
