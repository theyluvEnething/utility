import pygame
from config import settings

def draw_text(surface, text, position, font_obj, color=(0, 0, 0)):
    """
    Draws text on the given surface.
    :param surface: Pygame surface to draw on.
    :param text: String to render.
    :param position: Tuple (x,y) for top-left corner of the text.
    :param font_obj: Pygame font object.
    :param color: Tuple (R,G,B) for text color.
    """
    text_surface = font_obj.render(text, True, color)
    surface.blit(text_surface, position)

def draw_rectangle(surface, color, rect):
    """
    Draws a rectangle on the given surface.
    :param surface: Pygame surface to draw on.
    :param color: Tuple (R, G, B) for rectangle color.
    :param rect: Pygame Rect object or tuple (x, y, width, height).
    """
    pygame.draw.rect(surface, color, rect)

def draw_grid(surface):
    """Draws a grid on the surface."""
    for x in range(0, settings.SCREEN_WIDTH, settings.SNAKE_BLOCK_SIZE):
        pygame.draw.line(surface, settings.GRID_COLOR, (x, 0), (x, settings.SCREEN_HEIGHT))
    for y in range(0, settings.SCREEN_HEIGHT, settings.SNAKE_BLOCK_SIZE):
        pygame.draw.line(surface, settings.GRID_COLOR, (0, y), (settings.SCREEN_WIDTH, y))