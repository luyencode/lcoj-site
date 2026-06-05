# Brand Migration: "Cô Thi Lập Trình"

This design specification details the migration of the LCOJ platform's branding and navbar colors to the new brand: **Cô Thi Lập Trình**.

## 1. Brand Configuration Updates

The platform's branding values in the Django config file [local_settings.py](file:///home/lcoj-docker/dmoj/config/local_settings.py) will be updated as follows:

*   **`SITE_NAME`**: Update from `'LCOJ'` to `'Cô Thi Lập Trình'`.
*   **`SITE_LONG_NAME`**: Update from `'LCOJ: Luyện Code Online Judge'` to `'Cô Thi Lập Trình - Luyện Code Online'`.
*   **`SERVER_EMAIL`**: Update from `'LCOJ: Luyện Code Online Judge <luyencodeonline@gmail.com>'` to `'Cô Thi Lập Trình <luyencodeonline@gmail.com>'`.

## 2. Logo and Favicon Asset Updates

We will replace the existing branding icons under `/home/lcoj-docker/dmoj/repo/resources/icons/` using the new logo source ([logo.jpg](file:///home/lcoj-docker/dmoj/repo/logo.jpg)) and favicon source ([favicon.jpg](file:///home/lcoj-docker/dmoj/repo/favicon.jpg)). 

To maintain template compatibility and avoid breaking device/browser integrations, we will run a one-time Python/PIL conversion script inside the `lcoj_site` docker container (where the repository is mounted to `/site`) to generate:

1.  **Logo**:
    *   `/site/logo.png`
    *   `/site/resources/icons/logo.png`
2.  **Favicons and mobile icons** under `/site/resources/icons/`:
    *   `favicon.png` (original size)
    *   `favicon.ico` (standard ICO containing multiple sizes)
    *   `favicon-16x16.png`
    *   `favicon-32x32.png`
    *   `favicon-96x96.png`
    *   Android Chrome launcher icons: `36x36`, `48x48`, `72x72`, `96x96`, `144x144`, `192x192`, `256x256`, `384x384`, `512x512`
    *   Apple touch icons: `57x57`, `60x60`, `72x72`, `76x76`, `114x114`, `120x120`, `144x144`, `152x152`, `180x180`, and the default `apple-touch-icon.png` / `apple-touch-icon-precomposed.png`.
    *   Microsoft tiles: `70x70`, `144x144`, `150x150`, `310x310`.

## 3. Navbar Stylesheet Updates

The navbar background color will be changed to `#1A3254` to match the brand logo's background. We will update [resources/navbar.scss](file:///home/lcoj-docker/dmoj/repo/resources/navbar.scss):

*   Modify `#nav-background` background property to `#1A3254`.
*   Modify responsive mobile menu `#nav-list` background property to `#1A3254`.
*   Modify submenu dropdown container (`nav ul ul`) background property to `#1A3254`.

## 4. Asset Recompilation & Collection

After modifying the source SCSS files and replacing the resource icons, we will:

1.  Recompile the styles by executing:
    ```bash
    docker exec lcoj_site ./make_style.sh
    ```
2.  Collect all static assets to the `STATIC_ROOT` so the webserver can serve them:
    ```bash
    docker exec lcoj_site python3 manage.py collectstatic --no-input
    ```

## 5. Verification Plan

We will verify that:
1.  Brand titles and mail headers display "Cô Thi Lập Trình" correctly.
2.  The navbar background color is `#1A3254`.
3.  The new logo and favicons display properly across the pages.
