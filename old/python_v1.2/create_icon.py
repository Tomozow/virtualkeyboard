from PIL import Image, ImageDraw
import os

def create_keyboard_icon(size):
    """Create a simple keyboard icon with good visibility"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    padding = max(2, size // 16)
    
    bg_color = (55, 65, 81)
    key_color = (229, 231, 235)
    accent_color = (59, 130, 246)
    
    draw.rounded_rectangle(
        [padding, padding, size - padding, size - padding],
        radius=max(2, size // 12),
        fill=bg_color
    )
    
    inner_padding = max(3, size // 10)
    width = size - (inner_padding * 2)
    height = size - (inner_padding * 2)
    
    if size >= 32:
        rows = 3
        cols = 4
        key_size = min(width // (cols + 1), height // (rows + 1))
        key_padding = max(1, key_size // 4)
        
        start_x = inner_padding + (width - (cols * key_size + (cols - 1) * key_padding)) // 2
        start_y = inner_padding + (height - (rows * key_size + (rows - 1) * key_padding)) // 2
        
        for row in range(rows):
            for col in range(cols):
                x = start_x + col * (key_size + key_padding)
                y = start_y + row * (key_size + key_padding)
                
                if row == 2 and col >= 1 and col <= 2:
                    if col == 1:
                        spacebar_width = key_size * 2 + key_padding
                        draw.rounded_rectangle(
                            [x, y, x + spacebar_width, y + key_size],
                            radius=max(1, key_size // 6),
                            fill=accent_color
                        )
                        break
                else:
                    color = accent_color if (row == 0 and col == 0) else key_color
                    draw.rounded_rectangle(
                        [x, y, x + key_size, y + key_size],
                        radius=max(1, key_size // 6),
                        fill=color
                    )
    else:
        key_rows = 2
        key_cols = 3
        key_size = min(width // 4, height // 3)
        key_padding = 1
        
        start_x = inner_padding + (width - (key_cols * key_size + (key_cols - 1) * key_padding)) // 2
        start_y = inner_padding + (height - (key_rows * key_size + (key_rows - 1) * key_padding)) // 2
        
        for row in range(key_rows):
            for col in range(key_cols):
                x = start_x + col * (key_size + key_padding)
                y = start_y + row * (key_size + key_padding)
                
                color = accent_color if (row == 0 and col == 0) else key_color
                draw.rectangle(
                    [x, y, x + key_size, y + key_size],
                    fill=color
                )
    
    return img

def main():
    """Generate icon files in multiple sizes"""
    os.makedirs('current_app/assets', exist_ok=True)
    
    sizes = [16, 32, 64, 128, 256]
    images = []
    
    for size in sizes:
        img = create_keyboard_icon(size)
        img.save(f'current_app/assets/icon_{size}.png', 'PNG')
        images.append(img)
        print(f"Created icon_{size}.png")
    
    images[2].save('current_app/assets/icon.ico', format='ICO', sizes=[(16, 16), (32, 32), (64, 64), (128, 128), (256, 256)])
    print("Created icon.ico")
    
    images[2].save('current_app/assets/icon.png', 'PNG')
    print("Created icon.png (default 64x64)")

if __name__ == "__main__":
    main()