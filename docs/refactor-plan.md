Refactor plan (src/main alignment)

Goal
- Standardize codebase to `src/main` / `src/main/test` layout for Lightspeed/OpenShift builds.

Target layout
- Backend: `src/main/backend/app/...`; move entrypoint to `src/main/backend/main.py`; keep `seed.py`, `__init__.py` alongside.
- Frontend: rename `frontend` to `ui` and place at `src/main/ui/...`.
- Resources: `src/main/data/.gitkeep` (and other assets when needed).
- Tests: move all tests into a single folder `src/main/test` (no subdirectories).
- Requirements: `src/main/requirements.txt` (from `backend/requirements.txt`).

Placeholders to create
- `src/main/helm`
- `src/main/scripts`


Command updates (post-move)
- Install: `pip install -r src/main/requirements.txt`
- Run app: `python src/main/backend/main.py` (or `python -m app.main` with PYTHONPATH including `src/main/backend`)
- Tests: `pytest src/main/test`

Notes
- Adjust any Dockerfile/pipeline COPY/WORKDIR paths to match the new layout.
