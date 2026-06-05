# Cô Thi Lập Trình Branding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update the platform branding and navbar colors on LCOJ to the new "Cô Thi Lập Trình" identity, converting assets and applying CSS overrides.

**Architecture:** Use config setting changes, a one-time Python PIL image conversion script inside the `lcoj_site` docker container to build multi-format favicon assets, SCSS variable updates, and run a static collection process.

**Tech Stack:** Python, Django, SCSS/Sass, PostCSS, PIL/Pillow.

---

### Task 1: Brand Configuration Updates

**Files:**
- Modify: `dmoj/config/local_settings.py:111,138,140`

- [ ] **Step 1: Modify brand variables in local_settings.py**

Modify the branding and mail settings in [local_settings.py](file:///home/lcoj-docker/dmoj/config/local_settings.py):

*   Change `SERVER_EMAIL` (around line 111):
    ```python
    SERVER_EMAIL = 'Cô Thi Lập Trình <luyencodeonline@gmail.com>'
    ```
*   Change `SITE_NAME` (around line 138):
    ```python
    SITE_NAME = 'Cô Thi Lập Trình'
    ```
*   Change `SITE_LONG_NAME` (around line 140):
    ```python
    SITE_LONG_NAME = 'Cô Thi Lập Trình - Luyện Code Online'
    ```

- [ ] **Step 2: Run a quick syntax check on local_settings.py**

Run:
```bash
docker exec lcoj_site python3 -m py_compile /site/dmoj/config/local_settings.py
```
Expected output: No syntax error/compilation errors.

- [ ] **Step 3: Commit**

Run:
```bash
git add dmoj/config/local_settings.py
git commit -m "feat: update site branding names to Cô Thi Lập Trình in local_settings.py"
```

---

### Task 2: Logo and Favicon Asset Updates

**Files:**
- Create: `scratch/convert_assets.py`
- Modify: `logo.png`
- Modify: files in `resources/icons/`

- [ ] **Step 1: Create scratch asset converter script**

Create the script [scratch/convert_assets.py](file:///home/lcoj-docker/dmoj/repo/scratch/convert_assets.py):

```python
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
```

- [ ] **Step 2: Run conversion script in lcoj_site container**

Run:
```bash
docker exec lcoj_site python3 /site/scratch/convert_assets.py
```
Expected output: "All image conversions completed successfully!"

- [ ] **Step 3: Verify files are created**

Verify that `resources/icons/logo.png`, `resources/icons/favicon-32x32.png` and `logo.png` exist on the host filesystem.

- [ ] **Step 4: Commit**

Run:
```bash
git add scratch/convert_assets.py logo.png resources/icons/
git commit -m "feat: convert logo and favicon assets to required PNG/ICO formats"
```

---

### Task 3: Navbar Background SCSS Style Updates

**Files:**
- Modify: `resources/navbar.scss:66,148,239`

- [ ] **Step 1: Update navbar background colors to #1A3254**

In [resources/navbar.scss](file:///home/lcoj-docker/dmoj/repo/resources/navbar.scss):

*   Change `#nav-background` background (around line 66):
    ```scss
    #nav-background {
        position: absolute;
        z-index: 3;
        top: 0;
        left: 0;
        width: 100%;
        height: 56px;
        background: #1A3254;
    }
    ```
*   Change dropdown menu `ul` background (around line 148):
    ```scss
    #nav-container {
        ...
        ul {
            ...
            background: #1A3254;
            ...
        }
    }
    ```
*   Change mobile dropdown `#nav-list` background (around line 239):
    ```scss
    #nav-list {
        ...
        background: #1A3254;
        ...
    }
    ```

- [ ] **Step 2: Commit**

Run:
```bash
git add resources/navbar.scss
git commit -m "style: update navbar background to brand color #1A3254"
```

---

### Task 4: Compilation and Static Collection

**Files:**
- Modify: `resources/style.css` (compiled output)
- Modify: `resources/dark/style.css` (compiled output)

- [ ] **Step 1: Recompile SCSS styles**

Run:
```bash
docker exec lcoj_site ./make_style.sh
```
Expected output: Processes style.css and output files without error.

- [ ] **Step 2: Collect static assets**

Run:
```bash
docker exec lcoj_site python3 manage.py collectstatic --no-input
```
Expected output: Copies all static assets to the static root target folder.

- [ ] **Step 3: Verify color change compiled to CSS**

Check if `resources/style.css` contains the brand color `#1A3254`. Run:
```bash
grep -n "1A3254" resources/style.css
```
Expected output: Matches for `#nav-background`, `#nav-list` etc.

- [ ] **Step 4: Commit compiled CSS outputs**

Run:
```bash
git add resources/style.css resources/dark/style.css resources/ace-dmoj.css resources/dark/ace-dmoj.css resources/featherlight.css resources/dark/featherlight.css resources/martor-description.css resources/dark/martor-description.css resources/select2-dmoj.css resources/dark/select2-dmoj.css
git commit -m "style: recompile navbar scss changes to css assets"
```
