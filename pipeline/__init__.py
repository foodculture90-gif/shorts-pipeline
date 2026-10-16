"""Mission Control pipeline."""
import os

# Keys pasted into GitHub secrets often carry an invisible space or line break,
# which makes services answer "401 Unauthorized". Clean them once, here.
for _k in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY", "GEMINI_API_KEY", "CLOUDFLARE_ACCOUNT_ID",
           "CLOUDFLARE_API_TOKEN", "YT_CLIENT_ID", "YT_CLIENT_SECRET", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
    if os.environ.get(_k):
        os.environ[_k] = os.environ[_k].strip().strip('"').strip("'").strip()
