# Setup and Deployment Guide: VibeSync AI SaaS

A complete manual to configure, run, and deploy the VibeSync AI Studio Karaoke application.

---

## Part 1 – Supabase Setup

Supabase provides the relational database (PostgreSQL) and session storage for this application.

### 1. Create a Supabase Account
1. Visit [Supabase.com](https://supabase.com) and click **Sign Up** (authenticate with GitHub or email).
2. Click **New Project** in your dashboard.
3. Set the project parameters:
   - **Name**: `vibesync-ai-studio`
   - **Password**: Create a secure password (write this down).
   - **Region**: Choose a region closest to your target audience/Render web service (e.g. `East US` or `West Europe`).
   - **Pricing**: Choose the Free tier.
4. Click **Create New Project** and wait ~2 minutes for provision.

### 2. Run Database Migrations
Once the project is ready:
1. Navigate to the **SQL Editor** tab in the left sidebar.
2. Click **New Query**.
3. Copy and run the following SQL script to create the `users` and `songs` schemas:

```sql
-- Create Users Table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    profile_picture VARCHAR(256),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);

-- Create Songs Table
CREATE TABLE songs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(256) NOT NULL,
    artist VARCHAR(256),
    composer VARCHAR(256),
    pitch VARCHAR(10),
    source VARCHAR(100),
    cover_image VARCHAR(512),
    lyrics TEXT,
    audio_file_url VARCHAR(512),
    karaoke_file_url VARCHAR(512),
    play_count INTEGER DEFAULT 0,
    favourite BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_songs_user_id ON songs(user_id);
```

### 3. Obtain Connection URLs
1. Navigate to the **Project Settings** (gear icon) in the bottom-left sidebar.
2. Select **Database**.
3. Under **Connection string**, select the **URI** tab.
4. Copy the connection string. Replace `[YOUR-PASSWORD]` with the database password you chose in Step 1.
5. In your local `.env` file, save this as `DATABASE_URL`.
   *Example:* `DATABASE_URL=postgresql://postgres:[password]@db.supabase.co:5432/postgres`

---

## Part 2 – Local Development

### 1. Configure Local Environment Variables
Create a file named `.env` in the project root directory and add:
```env
DATABASE_URL=sqlite:///karaoke_studio.db # Or paste your Supabase PostgreSQL connection URI here
JWT_SECRET_KEY=generate-a-secure-random-phrase-here
GENIUS_TOKEN=LZQYig_IDcBO4i8yBiSykKKmUKPQmbKlMef-2GHRUL1cvjRXvIE3Vg_zVrWhko1b
```

### 2. Execution Commands
1. Activate virtual environment:
   ```bash
   # Windows PowerShell
   .\venv\Scripts\Activate.ps1
   ```
2. Start the web application server:
   ```bash
   python app.py
   ```
3. Open [http://localhost:5000](http://localhost:5000) in your browser.

---

## Part 3 – Deployment

### 1. Deploy Backend (Render)
1. Log in to [Render.com](https://render.com).
2. Create a new **Web Service** and link your Git repository.
3. Render will auto-detect the configuration using `render.yaml`. Confirm these fields:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python app.py`
4. Under the **Environment** settings tab, add:
   - `DATABASE_URL` (Your Supabase PostgreSQL URI connection string)
   - `JWT_SECRET_KEY` (Your custom signature string)
   - `GENIUS_TOKEN` (Genius API key)

### 2. Deploy Frontend (Vercel)
1. Sign in to your [Vercel Dashboard](https://vercel.com).
2. Click **Add New** -> **Project** and import your repository.
3. Edit the root `vercel.json` file to match your live Render endpoint:
   - Replace `https://vibesync-ai-studio.onrender.com` in the routes proxy mapping to match your newly created Render service address.
4. Click **Deploy**. Vercel will host the frontend statically and automatically route `/api/*` requests to your Render app!

---

## Part 4 – Testing Checklist

To verify that the multi-user SaaS features are fully operational:

- [ ] **Registration**: Create a new account. Check that your user entry appears inside Supabase's `users` table.
- [ ] **Login & Session**: Reload the page. Verify you are automatically redirected to the dashboard (the login persists).
- [ ] **Private Studio Generation**: Input a song (e.g. `Blinding Lights`) and click generate. Confirm that the cassette loads, separating completes, and a new song record is created under your `user_id` inside Supabase's `songs` table.
- [ ] **Data Isolation**: Log out, create a *second* account with a different email, and verify that the library shelf is completely empty. The first user's songs are private and inaccessible.
- [ ] **Deletion**: Delete the song from User 2's dashboard and check that files in the `storage/` directory and Supabase DB rows are deleted.
