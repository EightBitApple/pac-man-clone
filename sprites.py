import random
import math
import pygame as pg

# files
from settings import *
from pygame.math import Vector2


class MovementUtilities:
    '''Homogenised movement code that Pac-Man and the Ghosts inherit from.'''

    def hitbox_collide(self, sprite, other):
        '''Check if hit boxes of two sprites collided. Passed in as a parameter
        for 'pygame.sprite.spritecollide()'.'''

        return sprite.hitbox.colliderect(other.hitbox)

    def move(self,
             position,
             next_tile,
             direction,
             speed,
             time_delta,
             between_tiles=True):
        '''Smoothly move from one tile to the next across multiple frames.'''

        if position != next_tile:
            delta = next_tile - position
            # time delta used to re-base movement on time rather then
            # frame rate
            next_step = direction * speed * time_delta
            # comparison used to ensure that entity does not overshoot next
            # tile
            if delta.length() > next_step.length():
                # keep on moving until the next tile is reached
                position += next_step
            else:
                # entity has arrived at the tile
                position = next_tile
                between_tiles = False

        return position, direction, between_tiles

    def update_rect_and_hitbox(self, position, rect, hitbox, offset):
        '''update rect and hitbox to reflect any movement'''

        rect.topleft = position
        hitbox.center = position + offset

        return rect.topleft, hitbox.center

    def update_last_next_tile(self, direction, last_tile, next_tile, rect):
        '''Update the last and next tile for the entity.'''

        current_tile = rect.centerx // TILESIZE, rect.centery // TILESIZE
        last_tile = Vector2(current_tile) * TILESIZE
        next_tile = last_tile + direction * TILESIZE

        return last_tile, next_tile

    def screen_wrap_check(self, position, direction, next_tile, last_tile):
        '''Update position when on the edges of screen.'''

        # right wrap
        if position.x >= WIDTH:
            position.x = -TILESIZE
            last_tile.x = 0 - TILESIZE
            next_tile.x = position.x + (direction.x * TILESIZE)

        # left wrap
        elif position.x <= 0 - TILESIZE:
            position.x = WIDTH
            last_tile.x = WIDTH
            next_tile.x = position.x + (direction.x * TILESIZE)

        return position, next_tile, last_tile


class Spritesheet:
    '''Utility class for loading and parsing sprite sheets.'''

    def __init__(self, filename):
        self.spritesheet = pg.image.load(filename).convert()

    def get_image(self, x, y, width, height):
        # slice an image out of a spritesheet
        image = pg.Surface((width, height))
        image.blit(self.spritesheet, (0, 0), (x, y, width, height))
        image.set_colorkey(HOTPINK)
        return image


class Player(pg.sprite.Sprite, MovementUtilities):
    '''The movement, updating, and collision detection of Pac-Man'''

    def __init__(self, game, x, y, frames):
        self._layer = PLAYER_LAYER
        self.game = game
        self.groups = game.all_sprites
        pg.sprite.Sprite.__init__(self, self.groups)

        self.direction = Vector2(0, 0)
        self.new_direction = Vector2(0, 0)
        self.facing_direction = Vector2(0, 0)

        self.position = Vector2(x, y)
        self.ORIGINAL_POSITION = Vector2(x, y)

        self.next_tile = self.position
        self.last_tile = self.position

        self.frames = frames
        self.frame_angle = 0
        self.new_frame_angle = 0
        self.eat_animation_delay = 25
        self.death_animation_delay = 250
        self.last_frame_update = 0
        self.eat_frame = 0

        self.image = self.frames[-1][self.eat_frame]
        self.rect = self.image.get_rect(topleft=self.position)

        # smaller version of bounding box used for non-wall collision
        self.hitbox = self.rect.inflate(-12, -12)
        self.offset = Vector2(self.rect.width * .5, self.rect.height * .5)

        self.death_animation = False
        self.level_clear = False
        self.between_tiles = False
        self.first_frame = False

        self.speed = TILESIZE * 6
        self.score = 0
        self.lives = 2
        self.eaten_multiplier = 1

    def animate(self):
        '''Either play death of eating animation depending on game state.'''
        now = pg.time.get_ticks()
        # play eating animation
        if not self.death_animation:
            if now - self.last_frame_update > self.eat_animation_delay:
                self.last_frame_update = now

                self.eat_frame = (self.eat_frame + 1) % len(
                    self.frames[self.frame_angle])

                self.image = self.frames[self.frame_angle][self.eat_frame]

        # play death animation
        elif now - self.last_frame_update > self.death_animation_delay:
            self.last_frame_update = now

            if self.eat_frame <= len(self.frames[self.frame_angle]) - 1:
                self.image = self.frames[self.frame_angle][self.eat_frame]
                self.eat_frame += 1
            else:
                # disappear once death animation has finished playing
                self.image.fill(HOTPINK)

    def reset_status(self):
        '''Reset position, frame, flags, etc.'''

        self.direction = Vector2(0, 0)
        self.facing_direction = Vector2(0, 0)
        self.position = Vector2(self.ORIGINAL_POSITION.x,
                                self.ORIGINAL_POSITION.y)

        self.rect.topleft, self.hitbox.center = self.update_rect_and_hitbox(
            self.position, self.rect, self.hitbox, self.offset)

        self.first_frame = True
        self.first_move = True
        self.eat_frame = 0
        self.frame_angle = 0
        self.eaten_multiplier = 1
        self.between_tiles = False
        self.death_animation = False
        self.image = self.frames[-1][0]

    def check_collision(self):
        '''Check if colliding with walls, pellets or ghosts.'''

        if self.direction != Vector2(0, 0):
            # wall collision
            if pg.sprite.spritecollide(self, self.game.walls, False):
                self.position = self.last_tile
                self.next_tile = self.last_tile
                self.direction = Vector2(0, 0)
                self.between_tiles = False

            if self.position == self.next_tile:
                self.position, self.next_tile, self.last_tile = self.screen_wrap_check(
                    self.position, self.direction, self.next_tile,
                    self.last_tile)

                # move in memorised direction if possible
                if not self.check_for_walls(self.new_direction):
                    self.direction = self.new_direction
                    self.frame_angle = self.new_frame_angle
                    self.facing_direction = self.direction
                    self.between_tiles = True

                self.last_tile, self.next_tile = self.update_last_next_tile(
                    self.direction, self.last_tile, self.next_tile, self.rect)

            self.rect.topleft, self.hitbox.center = self.update_rect_and_hitbox(
                self.position, self.rect, self.hitbox, self.offset)

        eaten_pellet = pg.sprite.spritecollide(self, self.game.pellets, False,
                                               self.hitbox_collide)
        if eaten_pellet:
            self.score += getattr(eaten_pellet[0], 'eaten_score')
            # don't count the bonus fruit
            if not getattr(eaten_pellet[0], 'bonus'):
                self.game.dots_remain -= 1

                if self.game.dots_remain <= 0:
                    self.level_clear = True
                    self.game.pause_countdown = 5

                elif getattr(eaten_pellet[0], 'powered'):
                    for ghost in self.game.ghosts:
                        # store attributes in local variables for cleaner code
                        fright_mode = getattr(ghost, 'fright_mode')
                        eaten_mode = getattr(ghost, 'eaten_mode')

                        if fright_mode and not eaten_mode:
                            setattr(ghost, 'fright_timer', 0)

                        elif not eaten_mode:
                            ghost.toggle_fright_mode(True, ghost.fright_speed,
                                                     FRIGHT_BLUE)

            eaten_pellet[0].kill()

        else:
            collided_ghosts = pg.sprite.spritecollide(self, self.game.ghosts,
                                                      False,
                                                      self.hitbox_collide)
            if collided_ghosts:
                for ghost in collided_ghosts:
                    if ghost.fright_mode:
                        # eat the ghost
                        self.game.pause_countdown = .5
                        self.score += ghost.eaten_score * self.eaten_multiplier
                        self.eaten_multiplier += 1
                        ghost.toggle_eaten_mode(True, ghost.eaten_speed,
                                                ghost.eaten_colour)

                    elif not ghost.fright_mode and not ghost.eaten_mode:
                        # get caught
                        self.lives -= 1

                        self.game.pause_countdown = 5
                        self.death_animation = True
                        self.frame_angle = -1
                        self.eat_frame = 0

                        self.score //= 2
                        break

    def check_for_walls(self, new_direction):
        '''Checks if memorised direction will lead to a wall.'''

        self.position += new_direction * TILESIZE
        self.rect.topleft = self.position

        if pg.sprite.spritecollide(self, self.game.walls, False):
            is_wall = True
        else:
            is_wall = False

        self.position -= new_direction * TILESIZE
        self.rect.topleft = self.position

        return is_wall

    def get_movement_keys(self):
        '''Checks if movement keys have been pressed and updates vectors
        accordingly.'''

        new_direction = Vector2(0, 0)
        keys = pg.key.get_pressed()

        if keys[pg.K_LEFT] or keys[pg.K_a]:
            new_direction = Vector2(-1, 0)
            self.new_frame_angle = 3

        elif keys[pg.K_RIGHT] or keys[pg.K_d]:
            new_direction = Vector2(1, 0)
            self.new_frame_angle = 0

        elif keys[pg.K_UP] or keys[pg.K_w]:
            new_direction = Vector2(0, -1)
            self.new_frame_angle = 1

        elif keys[pg.K_DOWN] or keys[pg.K_s]:
            new_direction = Vector2(0, 1)
            self.new_frame_angle = 2

        elif keys[pg.K_SPACE]:
            self.direction = Vector2(0, 0)

        # if a key was pressed
        if new_direction != Vector2(0, 0):
            self.position, self.next_tile, self.last_tile = self.screen_wrap_check(
                self.position, self.direction, self.next_tile, self.last_tile)

            self.new_direction = new_direction  # memorise direction

            # check if this new direction is eligible
            if not self.check_for_walls(self.new_direction):
                self.direction = self.new_direction
                self.facing_direction = self.new_direction
                self.frame_angle = self.new_frame_angle

                self.last_tile, self.next_tile = self.update_last_next_tile(
                    self.direction, self.last_tile, self.next_tile, self.rect)

            self.between_tiles = True  # now on the move

    def update(self):
        '''Sequentially call methods every frame.'''

        self.get_movement_keys()

        if not self.first_frame:  # to prevent a bug with Pac-man's animation
            self.position, self.direction, self.between_tiles = self.move(
                self.position, self.next_tile, self.direction, self.speed,
                self.game.time_delta, self.between_tiles)

            self.rect.topleft, self.hitbox.center = self.update_rect_and_hitbox(
                self.position, self.rect, self.hitbox, self.offset)

        if self.direction != Vector2(0, 0):
            self.animate()

        self.check_collision()

        self.first_frame = False


class Ghost(pg.sprite.Sprite, MovementUtilities):
    '''Base class for ghosts. Will make a beeline straight to Pac-Man.'''

    def __init__(self, game, x, y, frames):
        self._layer = GHOST_LAYER
        self.game = game
        self.groups = game.all_sprites, game.ghosts
        pg.sprite.Sprite.__init__(self, self.groups)

        self.position = Vector2(x, y)
        self.ORIGINAL_POSITION = Vector2(x, y)

        self.last_tile = self.position
        self.next_tile = self.position

        self.direction = Vector2(0, 0)

        self.frames = frames
        self.frame_colour = 0
        self.ORIGINAL_FRAME_COLOUR = 0
        self.frame_direction = 2  # looking down on Pac-man with an intense stare
        self.image = self.frames[self.frame_colour][self.frame_direction]

        self.rect = self.image.get_rect(topleft=self.position)

        # smaller bounding box used for non-wall collision.
        self.hitbox = self.rect.inflate(-12, -12)
        self.offset = Vector2(10, 10)

        self.speed = TILESIZE * 5.9
        self.ORIGINAL_SPEED = self.speed

        self.target_tile = Vector2(0, 0)
        # corner 3 tiles from right side, one up from top
        self.maze_corner = Vector2(WIDTH - (TILESIZE * 3), TILESIZE * -1)

        # directions ordered by priority
        self.directions = [Vector2(0, -1), Vector2(-1, 0), Vector2(0, 1),
                           Vector2(1, 0)]
        self.between_tiles = False
        self.first_move = True
        self.first_frame = True

        self.chase_time = 20

        self.scatter_mode = True
        self.scatter_time = 7
        self.state_timer = 0
        self.scatter_counter = 0
        self.scatter_threshold = 3
        self.num_scatter_threshold = 5
        self.ignore_scatter = False  # for Blinky

        self.fright_mode = False
        self.fright_time = 10
        self.fright_timer = 0
        self.fright_speed = TILESIZE * 3.1

        # begin flashing when there's 3 seconds left
        self.flash_time = self.fright_time - 3
        self.flash_duration = .25  # how long a ghost stays as one colour
        self.flash_alternate = .25  # alternate between white in quarter-second intervals

        self.eaten_mode = False
        self.eaten_colour = GREEN
        self.eaten_target_tile = Vector2(
            14, 14) * TILESIZE  # just outside ghost house
        self.eaten_speed = TILESIZE * 10.1
        self.eaten_score = 200

    def set_target_tile(self):
        '''Sets target tile for ghosts to pursue. Each ghost overrides this to
        find their own unique tile. In this case simply set it to Pac-Man's
        current position'''

        self.target_tile = Vector2(self.game.player.position.x,
                                   self.game.player.position.y)

    def check_distance_from_pacman(self):
        '''Overridden by Clyde to check how close Pac-Man is to him'''

    def calculate_distance(self, x1, y1, x2, y2, sqroot):
        '''Distance calculation using Pythagoras' Theorem. Has a flag that - when set true - will square
        root the distance.'''

        dist = ((x1 - x2)**2 + (y1 - y2)**2)
        if sqroot:
            dist = math.sqrt(dist)
        return dist

    def choose_direction(self):
        '''Choose a direction that will get the ghost to the target tile the fastest.'''

        min_dist = 0
        min_dist_index = 0
        fright_list = []

        # iterate through cardinal directions and check possibility of moving
        # there
        for index, unit_vector in enumerate(self.directions):

            # discard up vector if ghost is in a 'no-up' tile
            if unit_vector == Vector2(0, -1):
                if self.position in self.game.noup_coords:
                    continue

            # move ghost to the new position
            self.position += unit_vector * TILESIZE
            self.rect.topleft = self.position

            dist = 0
            # invalidate direction if it causes the ghost to U-turn
            # if it's the ghost's first move it wont be checked.
            if self.position == self.last_tile and self.first_move == False:
                dist = -1
            # invalidate direction if it causes the ghost to move into a wall
            elif pg.sprite.spritecollide(self, self.game.walls, False):
                dist = -1

            elif not self.fright_mode:
                dist = self.calculate_distance(self.rect.centerx,
                                               self.rect.centery,
                                               self.target_tile.x,
                                               self.target_tile.y, False)

            # move back to original position
            self.position -= unit_vector * TILESIZE
            self.rect.topleft = self.position

            if dist == -1:
                continue

            if self.fright_mode:
                fright_list.append(index)
            else:
                # if both dist and min_dist are the same, the index remains
                # the same
                # doing this implements the direction priority system the
                # original game had
                if dist < min_dist or min_dist == 0:
                    min_dist = dist
                    min_dist_index = index

        # pick a direction after all vectors have been checked
        if self.fright_mode:
            self.direction = self.directions[random.choice(fright_list)]
        else:
            self.direction = self.directions[min_dist_index]
            self.frame_direction = min_dist_index
            self.image = self.frames[self.frame_colour][self.frame_direction]

        self.first_move = False

    def toggle_fright_mode(self, mode, speed=None, colour=None):
        '''Enter and exit frightened mode based on parameters passed'''

        if self.fright_mode:  # exit mode
            self.speed = self.ORIGINAL_SPEED

        else:  # enter mode
            self.direction = Vector2(-self.direction.x, -self.direction.y)

            # U-turn
            self.next_tile.x, self.last_tile.x = self.last_tile.x, self.next_tile.x
            self.next_tile.y, self.last_tile.y = self.last_tile.y, self.next_tile.y

            self.rect.topleft, self.hitbox.center = self.update_rect_and_hitbox(
                self.position, self.rect, self.hitbox, self.offset)

            self.image = self.frames[5][0]
            self.image.set_alpha(200)
            self.speed = speed

        self.flash_duration = .25
        self.fright_timer = 0
        self.fright_mode = mode

    def toggle_eaten_mode(self, mode, speed=None, colour=None):
        '''Enter and exit eaten mode based on parameters passed'''

        if not mode:  # exit mode
            self.speed = self.ORIGINAL_SPEED
            self.target_tile = self.maze_corner
            self.frame_colour = self.ORIGINAL_FRAME_COLOUR

        else:  # enter mode
            self.toggle_fright_mode(False)
            self.speed = speed
            self.target_tile = self.eaten_target_tile
            self.frame_colour = 4

        self.eaten_mode = mode

    def check_fright_flash(self):
        '''Check if it's time to flash.'''
        self.flash_duration += self.game.time_delta
        if self.flash_duration >= self.flash_alternate:
            # alternate colour
            self.flash_duration = 0
            self.image = self.frames[5][1] if self.image == self.frames[5][
                0] else self.frames[5][0]

    def check_current_state(self):
        '''Check and change the state of ghosts when appropriate.'''

        def start_chasing():
            self.state_timer = 0
            self.scatter_mode = False

        def start_scattering():
            self.state_timer = 0
            self.scatter_mode = True
            self.target_tile = self.maze_corner
            self.scatter_counter += 1

            if self.scatter_counter == self.scatter_threshold:
                self.scatter_time -= 2

        # ensures that ghosts will target maze corners on the first move
        if self.first_move and self.scatter_mode:
            self.target_tile = self.maze_corner
            self.scatter_counter += 1

        # Blinky only - ignore the changing between scatter and chase if less
        # than 30 pellets remain
        if self.ignore_scatter:
            self.scatter_mode = False
            return  # Blinky will now ignore checks below

        # pause timer while in frightened or eaten mode
        if not self.fright_mode and not self.eaten_mode:
            self.state_timer += self.game.time_delta

        elif self.fright_mode:
            self.fright_timer += self.game.time_delta

            if self.fright_timer >= self.fright_time:
                self.toggle_fright_mode(False)

            elif self.fright_timer >= self.flash_time:
                self.check_fright_flash()

        if self.eaten_mode and self.position == self.eaten_target_tile:
            self.toggle_eaten_mode(False)
            setattr(self.game.player, 'eaten_multiplier', 1)

        if self.scatter_counter < self.num_scatter_threshold:
            if self.state_timer >= self.scatter_time and self.scatter_mode:
                start_chasing()

            elif self.state_timer >= self.chase_time and not self.scatter_mode:
                start_scattering()

        else:
            self.scatter_mode = False

    def increment_temp_scatter_timer(self):
        '''Overridden by Clyde'''

    def reset_status(self):
        '''Reset position, frame, flags, etc.'''

        self.direction = Vector2(0, 0)
        self.position = Vector2(self.ORIGINAL_POSITION.x,
                                self.ORIGINAL_POSITION.y)

        self.rect.topleft, self.hitbox.center = self.update_rect_and_hitbox(
            self.position, self.rect, self.hitbox, self.offset)

        self.last_tile = self.position
        self.next_tile = self.position

        if self.fright_mode:
            self.toggle_fright_mode(False)
        elif self.eaten_mode:
            self.toggle_eaten_mode(False)

        self.state_timer = 0
        self.scatter_mode = True
        self.target_tile = self.maze_corner
        self.first_move = True
        self.first_frame = True
        self.between_tiles = False

        self.frame_colour = self.ORIGINAL_FRAME_COLOUR
        self.frame_direction = 2
        self.image = self.frames[self.frame_colour][self.frame_direction]

    def update(self):
        '''Sequentially call methods every frame.'''

        self.check_current_state()

        # only choose direction when not scattering, eaten or frightened
        # and aligned to a tile
        if not self.between_tiles:
            if not self.scatter_mode and not self.eaten_mode and not self.fright_mode:
                self.check_distance_from_pacman()
                self.set_target_tile()

            self.position, self.next_tile, self.last_tile = self.screen_wrap_check(
                self.position, self.direction, self.next_tile, self.last_tile)

            self.choose_direction()

            self.last_tile, self.next_tile = self.update_last_next_tile(
                self.direction, self.last_tile, self.next_tile, self.rect)
            self.between_tiles = True

        self.position, self.direction, self.between_tiles = self.move(
            self.position, self.next_tile, self.direction, self.speed,
            self.game.time_delta)

        self.rect.topleft, self.hitbox.center = self.update_rect_and_hitbox(
            self.position, self.rect, self.hitbox, self.offset)

        self.increment_temp_scatter_timer()  # for Clyde

        self.first_frame = False


class Pinky(Ghost):
    '''Targets four tiles ahead of Pac-Man to flank.'''

    def __init__(self, game, x, y, sprites):
        super().__init__(game, x, y, sprites)

        # 3 tiles from left side, one up from top
        self.maze_corner = Vector2((TILESIZE * 3), TILESIZE * -1)
        self.frame_colour = 1
        self.ORIGINAL_FRAME_COLOUR = 1
        self.image = self.frames[self.frame_colour][self.frame_direction]

    def set_target_tile(self):
        '''Four tiles ahead of Pac-Man facing direction.'''
        self.target_tile = self.game.player.position + \
            self.game.player.facing_direction * (TILESIZE * 4)


class Inky(Ghost):
    '''Finds vector from immediate tile to Blinky and adds it to immediate tile
    position. Inky will join Blinky when Blinky is close to Pac-Man'''

    def __init__(self, game, x, y, sprites):
        super().__init__(game, x, y, sprites)

        # 1 tile from right, 2 from bottom
        self.maze_corner = Vector2(WIDTH - TILESIZE, HEIGHT - (TILESIZE * 2))
        self.frame_colour = 2
        self.ORIGINAL_FRAME_COLOUR = 2
        self.image = self.frames[self.frame_colour][self.frame_direction]

    def set_target_tile(self):
        '''Find vector to immediate position and add to immediate tile position.'''

        immediate_pos = self.game.player.position + \
            self.game.player.facing_direction * (TILESIZE * 2)

        immediate_vec = Vector2(immediate_pos - self.game.blinky.position)
        self.target_tile = Vector2(immediate_pos + immediate_vec)


class Clyde(Ghost):
    '''Makes a beeline straight to Pac-Man until they are less than eight tiles
    away of each other, in which case Clyde will scatter to his corner for two
    seconds.'''

    def __init__(self, game, x, y, sprites):
        super().__init__(game, x, y, sprites)

        self.temp_scatter_duration = 2
        self.temp_scatter_timer = 0
        self.temp_scatter_mode = False
        # squared to match un-rooted distance calculation
        self.scatter_radius = (TILESIZE * 8)**2

        self.maze_corner = Vector2(TILESIZE, HEIGHT - (TILESIZE * 2))

        self.frame_colour = 3
        self.ORIGINAL_FRAME_COLOUR = 3
        self.image = self.frames[self.frame_colour][self.frame_direction]

    def check_distance_from_pacman(self):
        '''Simply checks distance from Pac-Man using pythag. No square rooting
        for performance reasons.'''

        dist = self.calculate_distance(self.position.x, self.position.y,
                                       self.game.player.position.x,
                                       self.game.player.position.y, False)

        # scatter when Pac-Man is within radius
        if dist <= self.scatter_radius:
            self.temp_scatter_mode = True
            self.target_tile = self.maze_corner

    def increment_temp_scatter_timer(self):
        '''Increments timer when in temporary scatter mode.'''

        if self.temp_scatter_mode:
            self.temp_scatter_timer += self.game.time_delta

    def set_target_tile(self):
        '''Check if it's time to exit temporary scatter mode.'''

        if self.temp_scatter_mode:
            if self.temp_scatter_timer >= self.temp_scatter_duration:
                self.target_tile = self.game.player.position
                self.temp_scatter_timer = 0
                self.temp_scatter_mode = False
        else:
            self.target_tile = Vector2(self.game.player.position.x,
                                       self.game.player.position.y)


class WallCollision(pg.sprite.Sprite):
    '''Collision that span the walls of the maze and iterated through during
    collision checking.'''

    def __init__(self, game, x, y, width, height):
        self.groups = game.walls
        pg.sprite.Sprite.__init__(self, self.groups)
        self.game = game
        self.rect = pg.Rect(x, y, width, height)


class Pellet(pg.sprite.Sprite):
    '''The pellets scattered throughout the maze.'''

    def __init__(self, game, x, y, frames):
        self._layer = PELLET_LAYER
        self.game = game
        self.groups = game.all_sprites, game.pellets
        pg.sprite.Sprite.__init__(self, self.groups)

        self.position = Vector2(x, y)
        self.frames = frames
        self.image = self.frames[0]
        self.rect = self.image.get_rect(topleft=self.position)

        # smaller version of bounding box used for non-wall collision
        self.hitbox = self.rect.inflate(-15, -15)
        offset = Vector2(10, 10)
        self.hitbox.center = self.position + offset

        self.powered = False
        self.bonus = False

        self.eaten_score = 1


class PowerPellet(Pellet):
    '''Placed at specific spots for Pac-Man to eat and frighten ghosts.'''

    def __init__(self, game, x, y, frames):
        super().__init__(game, x, y, frames)
        self.powered = True

        self.image = self.frames[1]
        self.last_flash = 0
        self.flash_delay = 200
        self.eaten_score = 10
        self.bonus = False

    def update(self):
        '''Animate flashing'''

        now = pg.time.get_ticks()
        if now - self.last_flash > self.flash_delay:
            self.last_flash = now
            self.image = self.frames[2] if self.image == self.frames[
                1] else self.frames[1]


class BonusFruit(Pellet):
    '''Appears just below the ghost house after a set time in the level.'''

    def __init__(self, game, x, y, frames):
        super().__init__(game, x, y, frames)
        self.image = random.choice(frames)
        self.eaten_score = 2500
        self.bonus = True
