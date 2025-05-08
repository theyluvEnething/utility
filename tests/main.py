import pygame
import sys
from config import settings
from drawing import shapes

Initialize Pygame

pygame.init()

Screen setup

screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
pygame.display.set_caption("Interactive Circle")

Clock for controlling FPS

clock = pygame.time.Clock()

Font for instructions

try:
# Try to use a default system font if available
font = pygame.font.Font(None, 30)
except pygame.error:
# Fallback to a common system font
font = pygame.font.SysFont('arial', 30)

Circle state

circle_x = settings.SCREEN_WIDTH // 2
circle_y = settings.SCREEN_HEIGHT // 2
circle_radius = settings.INITIAL_CIRCLE_RADIUS
current_color_index = 0
circle_color = settings.AVAILABLE_COLORS[current_color_index]

Game loop

running = True
while running:
# Event handling
for event in pygame.event.get():
if event.type == pygame.QUIT:
running = False
if event.type == pygame.KEYDOWN:
if event.key == pygame.K_c:
current_color_index = (current_color_index + 1) % len(settings.AVAILABLE_COLORS)
circle_color = settings.AVAILABLE_COLORS[current_color_index]
if event.key == pygame.K_ESCAPE: # Allow quitting with ESC
running = False

# Key states for continuous movement
keys = pygame.key.get_pressed()
if keys[pygame.K_LEFT] or keys[pygame.K_a]:
    circle_x -= settings.CIRCLE_MOVE_SPEED
if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
    circle_x += settings.CIRCLE_MOVE_SPEED
if keys[pygame.K_UP] or keys[pygame.K_w]:
    circle_y -= settings.CIRCLE_MOVE_SPEED
if keys[pygame.K_DOWN] or keys[pygame.K_s]:
    circle_y += settings.CIRCLE_MOVE_SPEED

# Keep circle within screen bounds
# Adjust bounds check to prevent circle from being partially off-screen
circle_x = max(circle_radius, min(circle_x, settings.SCREEN_WIDTH - circle_radius))
circle_y = max(circle_radius, min(circle_y, settings.SCREEN_HEIGHT - circle_radius))

# Drawing
screen.fill(settings.BACKGROUND_COLOR) # Fill background

# Draw the circle
shapes.draw_circle(screen, circle_color, (circle_x, circle_y), circle_radius)

# Draw instructions
instructions = [
    "Arrows/WASD: Move circle",
    "C: Change color",
    "ESC: Quit"
]
for i, line in enumerate(instructions):
    shapes.draw_text(screen, line, (10, 10 + i * 25), font, settings.TEXT_COLOR)


# Update the display
pygame.display.flip()

# Cap the frame rate
clock.tick(settings.FPS)

Quit Pygame
pygame.quit()
sys.exit()
