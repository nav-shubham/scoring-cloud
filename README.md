# ☁️ Telegram Habit Scoring - Cloud Webhook Version

This directory contains the premium, self-contained **Cloud Webhook Edition** of your Telegram Habit Scoring Application. 

By hosting this version in the cloud on **[PythonAnywhere](https://www.pythonanywhere.com/)** (completely free, no credit card required), your habit tracker will run **24/7 in the cloud** without requiring your PC to be turned on.

### 🌟 Key Enhancements in the Cloud Edition
1. **Real-time Webhook Scoring:** Instead of checking for scores periodically, a Flask Web Server listens to Telegram. When you tap a button on your phone, the score is recorded instantly, and the bot answers in real-time (no more loading spinners!).
2. **Instant Visual Trends:** As soon as you tap the final habit button of the day, your progress is calculated, and a gorgeous dark-mode matplotlib trend chart is generated and sent to you instantly.
3. **Daily Cloud Scheduler (100% Free):** Morning questions are triggered automatically every day at your chosen hour using a free external scheduling request to your server.
4. **Automatic Catch-ups:** Includes the smart catch-up look-back logic. If you pause the cloud server or miss a day, it will catch up cleanly.
5. **No PC Required:** Your computer remains completely out of the equation!

---

## 🏗️ Directory Structure
```
scoring_cloud/
├── .env                  # Pre-configured Telegram credentials
├── questions.txt         # Your active list of habits
├── db.py                 # SQLite database initialization and helper scripts
├── send_questions.py     # Script to send morning prompts
├── app.py                # Flask Web App to receive webhook callbacks and handle HTTP trigger
├── setup_webhook.py      # Utility script to register the webhook with Telegram
└── README.md             # This instruction manual
```

---

## 🚀 Step-by-Step PythonAnywhere Setup Guide

### Step 1: Create a Free Account
1. Go to **[PythonAnywhere](https://www.pythonanywhere.com/)**.
2. Click **Pricing & signup** -> **Create a Beginner account** (this is 100% free and requires no credit card).
3. Choose a username (your site URL will be `yourusername.pythonanywhere.com`).

---

### Step 2: Upload Your Files
1. Log in to PythonAnywhere and click the **Files** tab in the top-right corner.
2. In the "Directories" box, click **New directory**, type `scoring_cloud`, and click **New directory**.
3. Click into the new `scoring_cloud` folder.
4. Upload all **6 files** from this local directory using the **Upload a file** button:
   - `app.py`
   - `db.py`
   - `questions.txt`
   - `send_questions.py`
   - `setup_webhook.py`
   - `.env` *(Make sure to upload `.env`—you may need to enable "show hidden files" in your local file explorer to see it)*.

---

### Step 3: Install Required Python Packages
1. From the top-right menu on PythonAnywhere, go to the **Consoles** tab.
2. Click on **Bash** under "New console" to open a cloud terminal.
3. Run the following command to install the required libraries inside your free account storage:
   ```bash
   pip install --user requests python-dotenv matplotlib
   ```
4. Once completed, keep this console open for Step 5!

---

### Step 4: Configure the Web App
1. Open the PythonAnywhere dashboard in a new tab and go to the **Web** tab.
2. Click **Add a new web app**.
3. Choose **Manual Configuration** (do not select Flask directly; choosing manual configuration is cleaner and runs better).
4. Select **Python 3.10** as the version.
5. Click Next to finish creating the app.
6. Now, on your Web App dashboard page, scroll down to the **Code** section:
   - **Source code directory:** Set to `/home/yourusername/scoring_cloud` (replace `yourusername` with your actual username).
   - **Working directory:** Set to `/home/yourusername/scoring_cloud`.
7. Scroll down to the **WSGI configuration file** link (it will look like `/var/www/yourusername_pythonanywhere_com_wsgi.py`). Click it to edit it.
8. Delete all existing content in that file, paste the following snippet, and click **Save**:
   ```python
   import sys
   import os

   path = '/home/yourusername/scoring_cloud'
   if path not in sys.path:
       sys.path.insert(0, path)

   from app import app as application
   ```
   *(Ensure you change `yourusername` to your actual PythonAnywhere username!)*

---

### Step 5: Register the Webhook with Telegram
1. Return to your active **Bash Console** from Step 3.
2. Run the webhook registration script, passing your PythonAnywhere site URL as an argument:
   ```bash
   python /home/yourusername/scoring_cloud/setup_webhook.py https://yourusername.pythonanywhere.com
   ```
   *(Be sure to replace both instances of `yourusername`!)*
3. You should see a success message: 
   `🎉 Webhook registered successfully!`

---

### Step 6: Set Up Your Daily Morning Timer (100% FREE via cron-job.org)
Since PythonAnywhere free tier restricts internal scheduled tasks, we trigger your morning questions securely and for free using a web ping service:
1. Go to **[cron-job.org](https://cron-job.org/)** and sign up for a free account.
2. Click **Create Cronjob** in the dashboard.
3. Configure the cronjob:
   - **Title:** `Habit Tracker - Morning Questions`
   - **URL:** `https://yourusername.pythonanywhere.com/send?key=YOUR_TELEGRAM_BOT_TOKEN`
     *(Replace `yourusername` with your PythonAnywhere username and `YOUR_TELEGRAM_BOT_TOKEN` with the token in your `.env` file!)*
   - **Schedule:** Select **Daily** and choose your preferred morning hour (e.g. `07:30`).
   - **Timezone:** Select your local timezone (e.g. `Asia/Kolkata` or `IST`).
4. Click **Create**.

*Note: You can also manually trigger the morning questions at any time by just opening that URL directly in your web browser!*

---

### Step 7: Reload and Test!
1. Go to the **Web** tab on PythonAnywhere.
2. Click the green **Reload yourusername.pythonanywhere.com** button at the top.
3. Open your browser and navigate to `https://yourusername.pythonanywhere.com/`. 
   - You should see a gorgeous dark-themed landing page saying: **📊 Habit Tracker Webhook - Webhook Status: ACTIVE**.
4. Open Telegram on your phone, click on a habit button, and watch it score in real-time instantly!
