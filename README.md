# Thoughtline — Blog Platform with Comments

Full-stack blogging platform built with Flask, SQLAlchemy, SQLite, Jinja, and vanilla CSS.

## Features
- Account registration/login/logout with password hashing
- Publish, edit, and delete your own blog posts
- Comment on posts when signed in
- Author ownership checks for edit/delete
- Post and comment JSON APIs: `GET /api/posts`, `GET /api/posts/<id>`, `GET /api/health`
- Responsive blog feed, article page, editor, and comment section

## Run
From this directory:
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r ../requirements.txt
python app.py
```
Open http://127.0.0.1:5000

SQLite database `blog.db` is created automatically. Set a strong `SECRET_KEY` and configure `DATABASE_URL` for deployment. Use HTTPS and add CSRF protection/rate limiting before production.
