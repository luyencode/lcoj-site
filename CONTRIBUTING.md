# Contributing to LCOJ

## Issues found

First check if the bug is already reported under [Issues](https://github.com/luyencode/lcoj-site/issues).

If you're unable to find an open issue addressing the problem, [open](https://github.com/luyencode/lcoj-site/issues/new) a new one. Be sure to include a title and clear description, as much relevant information as possible, and a code sample or an executable test case demonstrating the expected behavior that is not occurring.

## Submitting changes

Ensure the PR description clearly describes the problem and solution. Include the relevant issue number if applicable.

Branch naming in this repo:

- `feature/*` / `feat/*` / `bugfix/*` / `fix/*` — work in progress, branched off `main`/`master`.
- `prod/*` — tracks what is actually deployed to a live site (e.g. `prod/luyencode` → [luyencode.net](https://luyencode.net/), `prod/cothilaptrinh` → [code.cothilaptrinh.vn](https://code.cothilaptrinh.vn/)). Don't target these directly with a feature PR unless you're doing a deploy merge.

## Coding convention

We use flake8. There's also `prettier` for JS code (in `websocket/`).

## Testing

Tests run through Docker, not a local `manage.py`:

```bash
docker compose exec site python3 manage.py test <app> -v 2
```

## Translation

Vietnamese translation is stored in [this folder](locale/vi/LC_MESSAGES). Feel free to do a PR on this file.

## License

By contributing, you agree that your contributions will be licensed under this project's [AGPL-3.0 license](LICENSE), consistent with the upstream [DMOJ](https://github.com/DMOJ/online-judge) and [VNOJ](https://github.com/VNOI-Admin/OJ) projects this repo is forked from.
