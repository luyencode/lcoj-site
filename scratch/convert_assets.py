from PIL import Image
import os

logo_path = '/site/logo.jpg'
favicon_path = '/site/favicon.jpg'
icons_dir = '/site/resources/icons/'

# Ensure icons dir exists
os.makedirs(icons_dir, exist_ok=True)

# 1. Logo
print("Converting logo.jpg to logo.png...")
im = Image.open(logo_path)
im.save('/site/logo.png', 'PNG')
im.save(os.path.join(icons_dir, 'logo.png'), 'PNG')

# 2. Favicons
print("Converting favicon.jpg to favicons...")
fav = Image.open(favicon_path)
# Save standard favicon.ico
fav.save(os.path.join(icons_dir, 'favicon.ico'), format='ICO', sizes=[(16, 16), (32, 32), (48, 48)])
# Save favicon.png
fav.save(os.path.join(icons_dir, 'favicon.png'), 'PNG')
# Save standard sizes
for size in [16, 32, 96]:
    fav.resize((size, size), Image.Resampling.LANCZOS).save(os.path.join(icons_dir, f'favicon-{size}x{size}.png'), 'PNG')

# 3. Android launcher icons
for size in [36, 48, 72, 96, 144, 192, 256, 384, 512]:
    fav.resize((size, size), Image.Resampling.LANCZOS).save(os.path.join(icons_dir, f'android-chrome-{size}x{size}.png'), 'PNG')

# 4. Apple Touch Icons
for size in [57, 60, 72, 76, 114, 120, 144, 152, 180]:
    fav.resize((size, size), Image.Resampling.LANCZOS).save(os.path.join(icons_dir, f'apple-touch-icon-{size}x{size}.png'), 'PNG')
fav.resize((180, 180), Image.Resampling.LANCZOS).save(os.path.join(icons_dir, 'apple-touch-icon.png'), 'PNG')
fav.resize((180, 180), Image.Resampling.LANCZOS).save(os.path.join(icons_dir, 'apple-touch-icon-precomposed.png'), 'PNG')

# 5. MS Tiles
for size in [70, 144, 150, 310]:
    fav.resize((size, size), Image.Resampling.LANCZOS).save(os.path.join(icons_dir, f'mstile-{size}x{size}.png'), 'PNG')

print("All image conversions completed successfully!")
