# 🚀 AniHub Stream Marketing Engine

A fully automated, open-source social media marketing pipeline engineered to drive viral traffic from **Instagram** and **Twitter / X** directly to **[anihubstream.com](https://anihubstream.com/)**.

---

## 🌟 Key Features

- **Automated Trend & Schedule Discovery:** Queries **AniList GraphQL** and **Jikan (MyAnimeList)** daily for the hottest anime and upcoming airings.
- **Branded Asset Generation:** Uses Pillow to dynamically generate 1080x1350 (4:5 vertical) promotional graphics with AniHub branding, custom badges, ratings, and contrast gradients.
- **SEO & Conversion Copywriting:** Formats platform-native captions, viral hashtags, and deep links (`https://anihubstream.com/watch/<slug>?utm_source=social`).
- **Official Publishers:** 
  - Instagram via Meta Graph API v19.0 (2-step container publishing).
  - Twitter / X via API v2 & Tweepy.
- **Deduplication Engine:** SQLite database cache to ensure no anime is reposted within the same cycle.
- **100% Free Hosting:** Runs autonomously via **GitHub Actions** cron jobs with cached SQLite state tracking.
- **Discord/Telegram Webhooks:** Instant alerts on post successes and failures.

---

## 📁 Repository Structure

```
anihub-marketing-engine/
├── .github/
│   └── workflows/
│       └── daily_marketing.yml    # GitHub Actions automated cron runner
├── src/
│   ├── config.py                  # Typed configuration & env validation
│   ├── database/
│   │   └── tracker.py             # SQLite deduplication state store
│   ├── fetchers/
│   │   ├── anilist.py             # AniList GraphQL trend fetcher
│   │   └── jikan.py               # Jikan MAL daily schedule fetcher
│   ├── generators/
│   │   ├── graphic_builder.py     # 1080x1350 branded poster engine
│   │   └── copywriter.py          # Platform-specific copy & UTM generator
│   ├── publishers/
│   │   ├── instagram.py           # Meta Graph API publisher
│   │   └── twitter.py             # Twitter / X API v2 publisher
│   └── utils/
│       ├── uploader.py            # Temporary public image stager (Imgur/tmpfiles)
│       └── notifier.py            # Discord alert webhooks
├── tests/
│   └── test_pipeline.py           # Verification test suite
├── .env.example                   # Environment credentials template
├── requirements.txt               # Python package dependencies
├── main.py                        # Central pipeline CLI
└── README.md
```

---

## 🎬 Viral 9:16 Clip & Video Short Generator

Extract or generate 1080x1920 vertical video clips with ambient background motion blur, viral hook overlays, site CTA branding, and full SEO packages:

```bash
# Generate a viral short for any anime
python main.py --mode clip --anime "Jujutsu Kaisen" --duration 15

# Cut a specific highlight timestamp from an anime stream URL
python main.py --mode clip --anime "Solo Leveling" --stream "https://your-stream.m3u8" --start "00:04:30" --duration 30
```

This will automatically create:
1. `output/viral_short_<anime>.mp4`: 1080x1920 vertical video reel ready for TikTok, Instagram Reels, and YouTube Shorts.
2. `output/seo_<anime>.txt`: Viral Title, Caption, dynamic deep link (`anihubstream.com/watch/<slug>`), and 15+ high-ranking SEO tags.

---

## 🛠️ Local Quickstart

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/your-username/anihub-marketing-engine.git
cd anihub-marketing-engine
pip install -r requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 3. Run in Dry-Run Mode (Safe Test)
Test the entire pipeline without publishing live posts. This will fetch current anime, generate the branded poster in `./output/`, and print the generated captions:
```bash
python main.py --dry-run --mode trending --limit 1
```

---

## 🔑 Production Setup: API Keys

### 1. Instagram Graph API (Meta)
1. Convert your Instagram account to a **Creator** or **Business** account.
2. Link your Instagram account to a Facebook Page.
3. In [Meta for Developers](https://developers.facebook.com/), create an app with the **Instagram Graph API**.
4. Generate a **Never-Expiring System User Token** with permissions:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_show_list`
5. Note your **Instagram Business Account ID** and **Access Token**.

### 2. Twitter / X API v2
1. Go to the [X Developer Portal](https://developer.x.com/) and create a Project.
2. Set User Authentication settings to **Read and Write**.
3. Generate:
   - `API Key` & `API Key Secret`
   - `Access Token` & `Access Token Secret`

### 3. Image Hosting (Imgur or Cloudinary)
- Meta requires images to be accessible over public HTTPS. Register a free application on [Imgur API](https://api.imgur.com/oauth2/addclient) to get a free `Client-ID`.

---

## ⚡ Deployment via GitHub Actions (Zero Maintenance)

1. Push this project to your GitHub repository.
2. Navigate to **Settings > Secrets and variables > Actions**.
3. Add the following repository secrets:
   - `INSTAGRAM_ACCOUNT_ID`
   - `INSTAGRAM_ACCESS_TOKEN`
   - `TWITTER_API_KEY`
   - `TWITTER_API_SECRET`
   - `TWITTER_ACCESS_TOKEN`
   - `TWITTER_ACCESS_SECRET`
   - `IMGUR_CLIENT_ID`
   - `DISCORD_WEBHOOK_URL` (optional)
4. Go to the **Actions** tab in GitHub, select **Daily Anime Marketing Engine**, and click **Run workflow** to test!
