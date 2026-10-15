# Mission Control — 100% free

One app — a real Windows app plus the same app on your phone — to run:
- **YouTube Shorts**: up to ~20 a day across your channels. Every short has new characters, a new
  world and a new art style. Nothing goes live without your OK, and you can publish or schedule them
  all with one tap.
- **AI Fitness App**: task board until we build it.

Everything runs in the cloud on free plans, so your computer can be off.

| Part | Free service | Free limit |
|---|---|---|
| Script writer | Google Gemini | plenty for 20/day |
| Pictures (8 per short) | Cloudflare Workers AI (FLUX) | ~170/day → **~20 shorts/day** |
| Motion | Our own engine: depth-aware 3D camera moves (runs in the worker) | unlimited |
| Voice + timed captions | Microsoft Edge voices | unlimited |
| Worker | GitHub Actions (public repo) | unlimited |
| Database, login, previews | Supabase | 500 MB DB / 1 GB files |
| App hosting | Vercel | free |

How a short is made: Gemini writes 4 scenes → Cloudflare draws 2 shots per scene → the motion
engine estimates depth in every picture and flies a camera through it (near things move more than
far things), with cross-fades → narration, word-by-word captions, title, music → a small preview
goes to the app → on **Publish** the full 1080×1920 version is made and uploaded.

---

## Setup (about 45 minutes, once). Use the same Google account everywhere.

### 1. GitHub
1. Create a new repository `shorts-pipeline` and make it **Public**. Public repos get unlimited
   free worker minutes. Your keys stay hidden in Secrets, and no videos are stored in the repo.
2. Upload everything in this folder, including the hidden `.github` folder.
3. Profile → Settings → Developer settings → **Fine-grained tokens** → Generate. Choose
   *Only select repositories* → `shorts-pipeline`, permission **Contents: Read and write**.
   Keep the token for step 2.

### 2. Supabase
1. supabase.com → **New project** (region: West EU).
2. **SQL Editor** → paste `supabase/setup.sql`, fill in the 3 values at the top → **Run**.
3. **Authentication → Users → Add user**: your email and a password, with *Auto confirm* on.
4. **Authentication → Sign In / Providers**: turn **off** "Allow new users to sign up".
5. **Project Settings → API**: copy the *Project URL*, the *anon* key and the *service_role* key.

### 3. Cloudflare (pictures)
dash.cloudflare.com → sign up. Copy your **Account ID** (right sidebar on the overview page).
Then **My Profile → API Tokens → Create Token** → template **Workers AI** → copy the token.

### 4. Gemini (writer)
aistudio.google.com → **Get API key** → create a key.

### 5. Put the app online
1. vercel.com → sign in with GitHub → **Add New → Project** → import `shorts-pipeline` →
   *Root Directory* `dashboard` → **Deploy**. Note your link, e.g. `https://mission-abc.vercel.app`.

### 6. YouTube permission (lets the app connect your channels)
console.cloud.google.com → your project:
1. **APIs & Services → Library**: enable **YouTube Data API v3**.
2. **OAuth consent screen**: External, app name "Mission Control", your email. Add yourself as a
   test user, then **Publish app** (otherwise connections expire after 7 days).
3. **Credentials → Create → OAuth client ID → Web application**. Under *Authorized redirect URIs*
   add your app link with a slash at the end (`https://mission-abc.vercel.app/`). Copy the
   *Client ID* and *Client secret*.

### 7. Fill in the app's settings
Edit `dashboard/config.js` on GitHub with the Supabase URL, the **anon** key, the Google Client ID
and your repo name, then Commit. Vercel updates the app by itself.

### 8. GitHub secrets
Repo → Settings → Secrets and variables → Actions → New repository secret:

`SUPABASE_URL` · `SUPABASE_SERVICE_KEY` (the service_role key) · `GEMINI_API_KEY` ·
`CLOUDFLARE_ACCOUNT_ID` · `CLOUDFLARE_API_TOKEN` · `YT_CLIENT_ID` · `YT_CLIENT_SECRET`

Optional: `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` for phone pings.

### 9. Go
1. Open your app link → sign in → **Install app** (computer) or Share → **Add to Home Screen** (iPhone).
2. **Channels**: edit the 2 starter channels (names and niches), then tap **Connect YouTube** on each.
   Pick the right channel when Google asks.
3. Tap **New shorts**. Previews arrive in *To approve* within minutes.

From then on, each channel's daily shorts are made every morning at ~07:00. You approve, publish
or "Schedule all" from the app.

### 10. Windows app
1. GitHub repo → Settings → Secrets and variables → Actions → **Variables** tab → New variable:
   `PANEL_URL` = your app link (e.g. `https://mission-abc.vercel.app/`).
2. **Actions** tab → **Build Windows app** → **Run workflow**. It takes about 5 minutes, and it also
   rebuilds by itself whenever the `desktop` folder changes.
3. Repo → **Releases** → *Mission Control for Windows* → download **Mission-Control-Setup.exe** → run it.
   Windows may say "Windows protected your PC". Click **More info → Run anyway**. The app isn't
   code-signed, because signing costs money.

What you get: a Mission Control icon on the desktop and Start menu, its own window, Windows
notifications when shorts are ready, and a tray icon with "N to approve", *Start with Windows* and
*Quit*. Closing the window keeps it running in the tray. Same login and data as your phone.
"Connect YouTube" finishes in your normal browser, because Google requires that.

---

## Important
- **Uploads start Private.** Google locks uploads from new API projects as Private until it reviews
  the project. Submit the form "YouTube API Services – Audit and Quota Extension" from Google Cloud
  right away. Until it's approved: YouTube Studio (web) → Content → select all → Edit → Visibility → Public.
- **Phone-verify each channel** (youtube.com/verify), or YouTube limits daily uploads.
- **Spread the volume.** YouTube demonetizes channels that look mass-produced. 2–3 channels with
  different niches beat 20 a day on one. Use **Change** on weak stories. Every short already gets
  a new cast and art style.
- **Made for kids** is on by default per channel. It's required by law for children's content, and
  it lowers earnings per view.
- **Music**: put royalty-free .mp3 files in the `music` folder (YouTube Studio → Audio Library is free).
- **Preview the app without setup**: open `dashboard/index.html?demo`.
