Pixora

A full-stack photo-sharing platform built with Flask and PostgreSQL — inspired by Flickr, designed for the modern web.

pixora-rlag.onrender.com



What is Pixora?
Pixora is a photo-sharing web portal where users can upload, organise, and discover photography. It supports public and private albums, a close-friends sharing system, notifications, tag-based discovery, personalised recommendations, and full user profiles — all backed by a PostgreSQL database with raw SQL queries (no ORM).
Built as a university database systems project at NKUA and extended into a portfolio-ready full-stack application.

Features
Photos & Albums

Upload photos stored as binary data directly in PostgreSQL (BYTEA)
Three privacy levels per album: Public, Close Friends (Instagram-style access list), Private
Manage exactly who can see your close-friends albums
Delete albums with full cascade — all photos, comments, likes removed automatically

Discovery

Tag-based browsing — click any tag to see all photos with that tag
AND search — search nafplion sea to find photos tagged with both
Most popular tags sorted by usage
Did you mean? suggestions when a tag search returns no results
Homepage shows the most liked photos across the platform, not just recent

Social

Follow system — directional follow (A follows B without B needing to follow back)
Like photos — heart button fills red when liked, grey when not (no page flash)
Comments — registered users and guests can comment; users cannot comment on their own photos (enforced by database trigger)
Notifications — real-time badge on navbar when someone likes or comments on your photo, or follows you
User profiles — public profile pages with stats, most liked photo, and album grid

Recommendations

People you may know — friends-of-friends algorithm ranked by mutual connection count
Photos you may also like — based on your top 5 most-used tags, ranked by match count with specificity as tiebreaker

Security & Data Integrity

Passwords hashed with bcrypt (werkzeug) — never stored in plain text
SQL injection protection via parameterized queries throughout
Database-level constraints: unique email, gender check, lowercase tags, no self-friendship, no self-comment trigger
DOB validation on both client and server — cannot be in the future
Session-based authentication with signed cookies


Tech Stack
LayerTechnologyBackendPython 3.14, FlaskDatabasePostgreSQL 18 (Supabase)DB Driverpsycopg2 (raw SQL, no ORM)AuthSession-based, werkzeug bcryptFrontendJinja2 templates, vanilla CSSFontsPlayfair Display, Outfit (Google Fonts)HostingRender (web service) + Supabase (database)

Screenshots
<!-- Add screenshots here after recording -->
<!-- Drag and drop images into this section on GitHub -->
Homepage
<!-- ![Homepage](assets/homepage.png) -->
Photo Detail
<!-- ![Photo Detail](assets/photo.png) -->
User Profile
<!-- ![Profile](assets/profile.png) -->
Album Privacy Settings
<!-- ![Privacy](assets/privacy.png) -->

Database Design
8 tables with full referential integrity and ON DELETE CASCADE throughout:
users         — registered users (bcrypt passwords)
albums        — photo collections with visibility levels
photos        — binary image data (BYTEA) + caption + tags
tags          — global lowercase tag vocabulary
photo_tags    — M:N junction: photos ↔ tags
comments      — registered users + guest comments
friends       — directional follow relationships
likes         — M:N junction: users ↔ photos
album_access  — per-user access grants for close-friends albums
notifications — like / comment / follow events with read state
Key SQL highlights
AND tag search — photos matching ALL specified tags:
sqlSELECT p.photo_id FROM photos p
WHERE p.photo_id IN (
    SELECT pt.photo_id FROM photo_tags pt
    JOIN tags t ON pt.tag_id = t.tag_id
    WHERE t.tag_name = ANY(%s)
    GROUP BY pt.photo_id
    HAVING COUNT(DISTINCT t.tag_name) = %s
)
Contribution leaderboard — photos uploaded + comments on others' photos:
sqlSELECT u.user_id,
       COUNT(DISTINCT p.photo_id) + COUNT(DISTINCT c.comment_id) AS score
FROM users u
LEFT JOIN albums a ON a.owner_id = u.user_id
LEFT JOIN photos p ON p.album_id = a.album_id
LEFT JOIN comments c ON c.user_id = u.user_id
    AND c.photo_id NOT IN (
        SELECT ph.photo_id FROM photos ph
        JOIN albums al ON ph.album_id = al.album_id
        WHERE al.owner_id = u.user_id
    )
GROUP BY u.user_id ORDER BY score DESC LIMIT 10
You may also like — ranked by tag match count, tiebroken by specificity:
sqlSELECT p.photo_id,
       COUNT(DISTINCT CASE WHEN pt.tag_id = ANY(%s) THEN pt.tag_id END) AS match_count,
       COUNT(DISTINCT pt.tag_id) AS total_tags
FROM photos p
JOIN photo_tags pt ON p.photo_id = pt.photo_id
GROUP BY p.photo_id
ORDER BY match_count DESC, total_tags ASC

Running Locally
Prerequisites

Python 3.8+
PostgreSQL 14+

Setup
bashgit clone https://github.com/Adam-Shawky23/ergasia-3.git
cd ergasia-3/k29photo

pip install -r requirements.txt

# Open db.py and set your local PostgreSQL username
# Then run:
createdb k29photo
psql -d k29photo -f schema.sql
psql -d k29photo -f data.sql
psql -d k29photo -f migration_pixora.sql

python3 app.py
Open http://localhost:5001
Sample credentials
All sample users share the password password123
EmailNamenikos.p@gmail.comNikos Papadopoulosmaria.g@gmail.comMaria Georgioukostas.a@gmail.comKostas Alexiou

Project Structure
k29photo/
├── app.py                  # Flask app factory, blueprint registration, error handlers
├── db.py                   # PostgreSQL connection via psycopg2 (one connection per request)
├── utils.py                # Shared login_required decorator
├── main.py                 # Homepage, browse, activity leaderboard, user profiles, notifications
├── auth.py                 # Register, login, logout
├── albums.py               # Album CRUD + privacy controls + sharing management
├── photos.py               # Photo upload/delete/serve, tag search, like/unlike
├── tags.py                 # Tag browsing, popular tags
├── comments.py             # Post comments, comment search
├── friends.py              # Follow/unfollow, user search, friends list
├── recommendations.py      # Friends-of-friends + you-may-also-like
├── schema.sql              # All CREATE TABLE, constraints, triggers, indexes
├── data.sql                # Sample data (12 users, 30 photos, 20 tags)
├── migration_pixora.sql    # Adds notifications, album_access, visibility column
├── setup.sh                # One-command local setup script
├── requirements.txt
├── Procfile                # gunicorn start command for Render
├── static/
│   └── style.css           # Dark editorial theme, responsive (mobile + tablet)
└── templates/              # 19 Jinja2 HTML templates

Deployment
Live at pixora-rlag.onrender.com
ServiceRoleRenderHosts the Flask web service (free tier)SupabaseHosts PostgreSQL database (free tier, no expiry)
The app uses the DATABASE_URL environment variable in production and falls back to a local PostgreSQL config in development — no code changes needed between environments.

Note: Render's free tier sleeps after 15 minutes of inactivity. The first visit after sleeping takes ~30 seconds to wake up.


Course Context
Originally developed as Assignment 3 for K29: Database Design and Use (Spring 2026) at the National and Kapodistrian University of Athens, Department of Informatics & Telecommunications. Extended significantly beyond the assignment requirements into a production-deployed portfolio project.

Built by Adam Ahmed
