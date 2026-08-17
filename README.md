# LCOJ: Luyện Code Online Judge [![AGPL License](https://img.shields.io/badge/license-AGPLv3.0-blue.svg)](http://www.gnu.org/licenses/agpl-3.0)

LCOJ (Luyện Code Online Judge) is a free, practice-focused online judge and learning platform. It offers a large bank of programming problems with instant online grading, organized by difficulty and topic, so learners can immediately verify whether their solutions are correct — from beginner exercises to competitive-programming and technical-interview prep.

This repository is the Django application that powers LCOJ. It is a fork of [VNOJ](https://github.com/VNOI-Admin/OJ) (VNOI's online judge), which is itself a fork of [DMOJ](https://github.com/DMOJ/online-judge). See [License & attribution](#license--attribution) below for how credit is preserved across this fork chain.

## Live deployments

This codebase is deployed to more than one site. Each production site is tracked on its own `prod/*` branch:

| Site | URL | Branch |
| --- | --- | --- |
| LCOJ | [luyencode.net](https://luyencode.net/) | `prod/luyencode` |
| Có Thì Lập Trình | [code.cothilaptrinh.vn](https://code.cothilaptrinh.vn/) | `prod/cothilaptrinh` |

Feature work happens on `feature/*`/`feat/*` branches off `main`/`master` and is merged into the relevant `prod/*` branch(es) to ship.

## Features

Check out the base feature set [here](https://github.com/DMOJ/online-judge#features). On top of that, LCOJ adds its own features on `feature/*` branches (e.g. the quiz system under `quiz/`).

## Installation

Refer to the LCOJ install documentation [here](https://docs.luyencode.net/#/site/installation).

This repo is typically deployed via a separate Docker Compose setup that wraps `manage.py` commands and mounts this repo at `/site/`.

### Additional installation steps

- You **have to** define `DMOJ_PROBLEM_DATA_ROOT` in `local_settings.py`, which should be the path to the directory that contains your problems' tests.

- Regarding disabling full-text search, please read [this issue](https://github.com/VNOI-Admin/OJ/issues/4) for more information.

- To sync the judge server and the site's cache, change the cache framework (`CACHES`) to `memcached` or `redis` instead of the default (local-memory caching).

- If you use `python3 manage.py loaddata demo`, the home button in the admin dashboard (/admin) links you to `localhost:8081`, there are 2 ways to change that:

  1. You can change that in [demo.json](/judge/fixtures/demo.json)
  2. You can go to the admin page, scroll down to find the `Sites` setting and change `localhost:8081` to your domain.

- To support `testlib.h`, you need to copy [testlib.h](https://github.com/MikeMirzayanov/testlib/blob/master/testlib.h) to `g++`'s include path in the judge server. To speed up compile time, you can also create a precompiled header for `testlib.h`.

## Contributing ![PR's Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat)

Take a look at [our contribution guideline](CONTRIBUTING.md).

If you find a bug, please open an issue on this repo.

Pull requests are welcome as well. Before you submit your PR, please check your code with [flake8](https://flake8.pycqa.org/en/latest/) and format it if needed. There's also `prettier` if you need to format JS code (in `websocket/`).

Translation contributions are also welcome.

## License & attribution

LCOJ is licensed under the [GNU Affero General Public License v3.0](LICENSE) (AGPL-3.0), the same license used by its upstream projects. This project builds on the work of:

- **[DMOJ: Modern Online Judge](https://github.com/DMOJ/online-judge)** — the original online judge platform this is forked from.
- **[VNOJ: VNOI Online Judge](https://github.com/VNOI-Admin/OJ)** — VNOI's fork of DMOJ, from which this repository was in turn forked, and whose additions this project continues to build on.

As required by the AGPL, the full source of this repository (including modifications) is available, and any network-accessible deployment of this code (such as the sites listed above) must likewise make its complete corresponding source available to its users.
