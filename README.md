# SecretBox

A small, self-hostable, password-protected, read-once secret sharing app.

## Deploy to Render

1. Create a GitHub repository and upload the contents of this folder.
2. In Render, choose **New > Blueprint**, then select the repository.
3. Render reads `render.yaml`. Keep the persistent disk enabled.
4. Set `PUBLIC_BASE_URL` to your deployed HTTPS origin, e.g. `https://secretbox-example.onrender.com`.
5. Deploy. Open the app URL, enter a message and a strong password, then create a link.
6. Share the link and password through separate channels.

Render's free web services may spin down and free-plan persistent disk availability/terms can change. For dependable persistence, use a paid persistent disk or another host with durable storage.

## Local run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export APP_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export FERNET_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
export DB_PATH="./secretbox.sqlite3"
python app.py
```

Open http://localhost:8000.

## Security behavior

- Message content is encrypted at rest using Fernet.
- The password is stored as a scrypt password hash, not plaintext.
- The public token is random; only its SHA-256 digest is stored.
- Successful password verification and deletion happen in one SQLite write transaction, preventing two concurrent successful reads.
- Incorrect passwords do not consume the note; after 10 failed attempts the note is deleted.
- Notes expire after 7 days by default (`MAX_AGE_HOURS`).
- Use HTTPS. Never share the password in the same message as the link.

## Important limitations

This is a deployable starter, not a hosted service. No live public link is created until you deploy it. Anyone who opens the link can attempt passwords; use a long, unique password and share it privately. A recipient can still copy, screenshot, or photograph a message after viewing it. Server administrators control the encryption key and hosting environment.
