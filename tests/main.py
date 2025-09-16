import pygame
import sys
import random
from config import settings
from drawing import shapes

def game_over(screen, font, score):
    """Displays the game over screen and exits."""
    game_over_text = font.render(f"Game Over! Your Score: {score}", True, settings.TEXT_COLOR)
    text_rect = game_over_text.get_rect(center=(settings.SCREEN_WIDTH / 2, settings.SCREEN_HEIGHT / 2))
    screen.blit(game_over_text, text_rect)
    pygame.display.flip()
    pygame.time.wait(3000)
    pygame.quit()
    sys.exit()

def main():
    pygame.init()

    screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
    pygame.display.set_caption("Snake Game")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 36)

    # Snake initial setup
    snake_head =
    snake_body = [,,]
    direction = 'RIGHT'
    change_to = direction

    # Food initial setup
    food_pos = [
        random.randrange(0, settings.SCREEN_WIDTH // settings.SNAKE_BLOCK_SIZE) * settings.SNAKE_BLOCK_SIZE,
        random.randrange(0, settings.SCREEN_HEIGHT // settings.SNAKE_BLOCK_SIZE) * settings.SNAKE_BLOCK_SIZE
    ]
    
    score = 0

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if (event.key == pygame.K_UP or event.key == pygame.K_w) and direction != 'DOWN':
                    change_to = 'UP'
                elif (event.key == pygame.K_DOWN or event.key == pygame.K_s) and direction != 'UP':
                    change_to = 'DOWN'
                elif (event.key == pygame.K_LEFT or event.key == pygame.K_a) and direction != 'RIGHT':
                    change_to = 'LEFT'
                elif (event.key == pygame.K_RIGHT or event.key == pygame.K_d) and direction != 'LEFT':
                    change_to = 'RIGHT'
        
        direction = change_to

        # Snake movement
        if direction == 'UP':
            snake_head -= settings.SNAKE_BLOCK_SIZE
        elif direction == 'DOWN':
            snake_head += settings.SNAKE_BLOCK_SIZE
        elif direction == 'LEFT':
            snake_head -= settings.SNAKE_BLOCK_SIZE
        elif direction == 'RIGHT':
            snake_head += settings.SNAKE_BLOCK_SIZE

        # Snake body growth
        snake_body.insert(0, list(snake_head))
        if snake_head == food_pos:
            score += 1
            food_pos = [
                random.randrange(0, settings.SCREEN_WIDTH // settings.SNAKE_BLOCK_SIZE) * settings.SNAKE_BLOCK_SIZE,
                random.randrange(0, settings.SCREEN_HEIGHT // settings.SNAKE_BLOCK_SIZE) * settings.SNAKE_BLOCK_SIZE
            ]
        else:
            snake_body.pop()

        # Drawing
        screen.fill(settings.BACKGROUND_COLOR)

        for pos in snake_body:
            snake_rect = pygame.Rect(pos, pos, settings.SNAKE_BLOCK_SIZE, settings.SNAKE_BLOCK_SIZE)
            shapes.draw_rectangle(screen, settings.SNAKE_COLOR, snake_rect)

        food_rect = pygame.Rect(food_pos, food_pos, settings.SNAKE_BLOCK_SIZE, settings.SNAKE_BLOCK_SIZE)
        shapes.draw_rectangle(screen, settings.FOOD_COLOR, food_rect)

        # Wall collision
        if not (0 <= snake_head < settings.SCREEN_WIDTH and 0 <= snake_head < settings.SCREEN_HEIGHT):
            game_over(screen, font, score)

        # Self collision
        for block in snake_body[1:]:
            if snake_head == block:
                game_over(screen, font, score)

        # Display score
        shapes.draw_text(screen, f"Score: {score}", (10, 10), font, settings.TEXT_COLOR)

        pygame.display.update()
        clock.tick(settings.SNAKE_SPEED)

if __name__ == '__main__':
    main()
