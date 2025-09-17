import pygame
import sys
import random

# --- Settings (formerly config/settings.py) ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
GRID_COLOR = (200, 200, 200)

BACKGROUND_COLOR = WHITE
TEXT_COLOR = BLACK

SNAKE_BLOCK_SIZE = 20
SNAKE_SPEED = 15
SNAKE_COLOR = GREEN
FOOD_COLOR = RED
FPS = 60

# --- Drawing helpers (formerly drawing/shapes.py) ---
def draw_text(surface, text, position, font_obj, color=BLACK):
    text_surface = font_obj.render(text, True, color)
    surface.blit(text_surface, position)

def draw_rectangle(surface, color, rect):
    pygame.draw.rect(surface, color, rect)

def draw_grid(surface):
    for x in range(0, SCREEN_WIDTH, SNAKE_BLOCK_SIZE):
        pygame.draw.line(surface, GRID_COLOR, (x, 0), (x, SCREEN_HEIGHT))
    for y in range(0, SCREEN_HEIGHT, SNAKE_BLOCK_SIZE):
        pygame.draw.line(surface, GRID_COLOR, (0, y), (SCREEN_WIDTH, y))

# --- Game over countdown ---
def game_over_countdown(screen, font, score):
    large_font = pygame.font.Font(None, 72)
    game_over_text = font.render(f"Game Over! Your Score: {score}", True, TEXT_COLOR)
    text_rect = game_over_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))

    for i in range(3, 0, -1):
        screen.fill(BACKGROUND_COLOR)
        draw_grid(screen)
        screen.blit(game_over_text, text_rect)
        countdown_text = large_font.render(str(i), True, TEXT_COLOR)
        countdown_rect = countdown_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20))
        screen.blit(countdown_text, countdown_rect)
        pygame.display.flip()
        pygame.time.wait(1000)

# --- Main game ---
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Snake Game")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 36)

    while True:
        snake_head = [SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2]
        snake_body = [
            [SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2],
            [SCREEN_WIDTH // 2 - SNAKE_BLOCK_SIZE, SCREEN_HEIGHT // 2],
            [SCREEN_WIDTH // 2 - 2 * SNAKE_BLOCK_SIZE, SCREEN_HEIGHT // 2],
        ]
        direction = 'RIGHT'
        change_to = direction

        food_pos = [
            random.randrange(0, SCREEN_WIDTH // SNAKE_BLOCK_SIZE) * SNAKE_BLOCK_SIZE,
            random.randrange(0, SCREEN_HEIGHT // SNAKE_BLOCK_SIZE) * SNAKE_BLOCK_SIZE,
        ]
        score = 0

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if (event.key in (pygame.K_UP, pygame.K_w)) and direction != 'DOWN':
                        change_to = 'UP'
                    elif (event.key in (pygame.K_DOWN, pygame.K_s)) and direction != 'UP':
                        change_to = 'DOWN'
                    elif (event.key in (pygame.K_LEFT, pygame.K_a)) and direction != 'RIGHT':
                        change_to = 'LEFT'
                    elif (event.key in (pygame.K_RIGHT, pygame.K_d)) and direction != 'LEFT':
                        change_to = 'RIGHT'

            direction = change_to

            # Movement (component-wise updates)
            if direction == 'UP':
                snake_head[1] -= SNAKE_BLOCK_SIZE
            elif direction == 'DOWN':
                snake_head[1] += SNAKE_BLOCK_SIZE
            elif direction == 'LEFT':
                snake_head[0] -= SNAKE_BLOCK_SIZE
            elif direction == 'RIGHT':
                snake_head[0] += SNAKE_BLOCK_SIZE

            # Body growth (insert by value)
            snake_body.insert(0, [snake_head[0], snake_head[1]])

            # Eat food
            if snake_head == food_pos:
                score += 1
                food_pos = [
                    random.randrange(0, SCREEN_WIDTH // SNAKE_BLOCK_SIZE) * SNAKE_BLOCK_SIZE,
                    random.randrange(0, SCREEN_HEIGHT // SNAKE_BLOCK_SIZE) * SNAKE_BLOCK_SIZE,
                ]
            else:
                snake_body.pop()

            # Draw
            screen.fill(BACKGROUND_COLOR)
            draw_grid(screen)

            for pos in snake_body:
                rect = pygame.Rect(pos[0], pos[1], SNAKE_BLOCK_SIZE, SNAKE_BLOCK_SIZE)
                draw_rectangle(screen, SNAKE_COLOR, rect)

            food_rect = pygame.Rect(food_pos[0], food_pos[1], SNAKE_BLOCK_SIZE, SNAKE_BLOCK_SIZE)
            draw_rectangle(screen, FOOD_COLOR, food_rect)

            # Collisions
            game_is_over = False
            if not (0 <= snake_head[0] < SCREEN_WIDTH and 0 <= snake_head[1] < SCREEN_HEIGHT):
                game_is_over = True

            for block in snake_body[1:]:
                if snake_head == block:
                    game_is_over = True
                    break

            if game_is_over:
                game_over_countdown(screen, font, score)
                break  # break inner loop; outer loop restarts a new game

            # HUD
            draw_text(screen, f"Score: {score}", (10, 10), font, TEXT_COLOR)

            pygame.display.update()
            clock.tick(SNAKE_SPEED)

if __name__ == "__main__":
    main()
