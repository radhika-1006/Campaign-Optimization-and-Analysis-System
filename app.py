from flask import Flask, render_template, request, redirect, url_for, session, flash
import pymysql
import re
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "change-this-secret-key"  # TODO: move to env variable before deployment

# --- Database connection settings (update to match your local MySQL setup) ---
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "1234",          # set your MySQL root password here
    "database": "campop",
    "cursorclass": pymysql.cursors.DictCursor,
}


def get_db_connection():
    return pymysql.connect(**DB_CONFIG)
def is_password_valid(password):
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."
    if not re.search(r"[A-Za-z]", password):
        return False, "Password must include at least one letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must include at least one number."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=~`\[\];'/\\]", password):
        return False, "Password must include at least one special character."
    return True, ""

# =====================================================
# CAMPAIGN ANALYSIS MODULE
# =====================================================
#
# STEP 1: Add this helper function to app.py, ABOVE your routes
# (right after the get_db_connection() function is a good spot).
# It takes one campaign record and returns it with calculated stats added.

def calculate_campaign_stats(c):
    """Takes a campaign dict (from DB) and adds CTR, CPC, CPA, Conversion Rate, ROI."""
    impressions = c["impressions"] or 0
    clicks = c["clicks"] or 0
    conversions = c["conversions"] or 0
    budget = float(c["budget"] or 0)
    revenue = float(c["revenue"] or 0)

    # CTR = (Clicks / Impressions) * 100
    c["ctr"] = round((clicks / impressions) * 100, 2) if impressions > 0 else 0

    # CPC = Budget / Clicks
    c["cpc"] = round(budget / clicks, 2) if clicks > 0 else 0

    # Conversion Rate = (Conversions / Clicks) * 100
    c["conversion_rate"] = round((conversions / clicks) * 100, 2) if clicks > 0 else 0

    # CPA = Budget / Conversions
    c["cpa"] = round(budget / conversions, 2) if conversions > 0 else 0

    # ROI = ((Revenue - Budget) / Budget) * 100
    c["roi"] = round(((revenue - budget) / budget) * 100, 2) if budget > 0 else 0

    return c


# =====================================================
# STEP 2: REPLACE your existing /campaigns route with this
# updated version, which calculates stats for every campaign
# before sending them to the template.
# =====================================================

@app.route("/campaigns")
def campaigns():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM campaigns WHERE user_id=%s ORDER BY created_at DESC",
                (session["user_id"],),
            )
            campaign_list = cursor.fetchall()
    finally:
        conn.close()

    # Add calculated stats (CTR, CPC, CPA, Conversion Rate, ROI) to each campaign
    campaign_list = [calculate_campaign_stats(c) for c in campaign_list]

    return render_template("campaigns.html", campaigns=campaign_list)
# ---------------- Home ----------------
@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


# ---------------- Register ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if not name or not email or not password:
            flash("All fields are required.")
            return redirect(url_for("register"))

        hashed_pw = generate_password_hash(password)

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM users WHERE email=%s", (email,))
                if cursor.fetchone():
                    flash("An account with that email already exists.")
                    return redirect(url_for("register"))

                cursor.execute(
                    "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
                    (name, email, hashed_pw),
                )
                conn.commit()
            flash("Registration successful. Please log in.")
            return redirect(url_for("login"))
        finally:
            conn.close()

    return render_template("register.html")


# ---------------- Login ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
                user = cursor.fetchone()
        finally:
            conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["is_admin"] = bool(user["is_admin"])
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password.")
            return redirect(url_for("login"))

    return render_template("login.html")


# ---------------- Logout ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------- Dashboard (placeholder for next step) ----------------
# =====================================================
# UPDATED DASHBOARD ROUTE
# Replace your existing @app.route("/dashboard") function with this.
# It pulls quick stats (total campaigns, total budget, total revenue,
# average ROI) to show on the dashboard.
# =====================================================

# =====================================================
# UPDATED DASHBOARD ROUTE (with chart data)
# Replace your existing @app.route("/dashboard") function with this.
# =====================================================

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM campaigns WHERE user_id=%s AND status='approved'",
                (session["user_id"],),
            )
            campaign_list = cursor.fetchall()
    finally:
        conn.close()

    total_campaigns = len(campaign_list)
    total_budget = sum(float(c["budget"] or 0) for c in campaign_list)
    total_revenue = sum(float(c["revenue"] or 0) for c in campaign_list)

    if total_budget > 0:
        avg_roi = round(((total_revenue - total_budget) / total_budget) * 100, 2)
    else:
        avg_roi = 0

    # Data for the Budget vs Revenue bar chart (per campaign)
    chart_labels = [c["name"] for c in campaign_list]
    chart_budgets = [float(c["budget"] or 0) for c in campaign_list]
    chart_revenues = [float(c["revenue"] or 0) for c in campaign_list]

    # Data for the Budget-by-Platform pie chart
    platform_totals = {}
    for c in campaign_list:
        platform = c["platform"] or "Other"
        platform_totals[platform] = platform_totals.get(platform, 0) + float(c["budget"] or 0)
    platform_labels = list(platform_totals.keys())
    platform_values = list(platform_totals.values())

    return render_template(
        "dashboard.html",
        user_name=session.get("user_name"),
        total_campaigns=total_campaigns,
        total_budget=round(total_budget, 2),
        total_revenue=round(total_revenue, 2),
        avg_roi=avg_roi,
        chart_labels=chart_labels,
        chart_budgets=chart_budgets,
        chart_revenues=chart_revenues,
        platform_labels=platform_labels,
        platform_values=platform_values,
    )

# =====================================================
# CAMPAIGN MANAGEMENT MODULE
# Add this code to your existing app.py, just above:
#   if __name__ == "__main__":
# =====================================================

from datetime import datetime


# ---------------- View all campaigns ----------------

# ---------------- Add a new campaign ----------------
@app.route("/campaigns/add", methods=["GET", "POST"])
# =====================================================
# UPDATED add_campaign() and edit_campaign() ROUTES
# Replace your existing versions of BOTH functions with these,
# which now handle the new "description" field.
# =====================================================

@app.route("/campaigns/add", methods=["GET", "POST"])
def add_campaign():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form["name"].strip()
        platform = request.form["platform"].strip()
        description = request.form.get("description", "").strip()
        budget = request.form["budget"]
        impressions = request.form.get("impressions", 0)
        clicks = request.form.get("clicks", 0)
        conversions = request.form.get("conversions", 0)
        revenue = request.form.get("revenue", 0)
        start_date = request.form.get("start_date") or None
        end_date = request.form.get("end_date") or None

        if not name or not platform or not budget:
            flash("Name, platform, and budget are required.")
            return redirect(url_for("add_campaign"))

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO campaigns
                    (user_id, name, platform, description, budget, impressions, clicks, conversions, revenue, start_date, end_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        session["user_id"], name, platform, description, budget,
                        impressions, clicks, conversions, revenue,
                        start_date, end_date,
                    ),
                )
                conn.commit()
            flash("Campaign added successfully.")
            return redirect(url_for("campaigns"))
        finally:
            conn.close()

    return render_template("campaign_form.html", campaign=None)

# ---------------- Edit a campaign ----------------
@app.route("/campaigns/edit/<int:campaign_id>", methods=["GET", "POST"])
def edit_campaign(campaign_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM campaigns WHERE id=%s AND user_id=%s",
                (campaign_id, session["user_id"]),
            )
            campaign = cursor.fetchone()

        if not campaign:
            flash("Campaign not found.")
            return redirect(url_for("campaigns"))

        if request.method == "POST":
            name = request.form["name"].strip()
            platform = request.form["platform"].strip()
            budget = request.form["budget"]
            impressions = request.form.get("impressions", 0)
            clicks = request.form.get("clicks", 0)
            conversions = request.form.get("conversions", 0)
            revenue = request.form.get("revenue", 0)
            start_date = request.form.get("start_date") or None
            end_date = request.form.get("end_date") or None

            with conn.cursor() as cursor:
                cursor.execute(
                    """UPDATE campaigns SET
                        name=%s, platform=%s, budget=%s, impressions=%s,
                        clicks=%s, conversions=%s, revenue=%s,
                        start_date=%s, end_date=%s
                    WHERE id=%s AND user_id=%s""",
                    (
                        name, platform, budget, impressions, clicks,
                        conversions, revenue, start_date, end_date,
                        campaign_id, session["user_id"],
                    ),
                )
                conn.commit()
            flash("Campaign updated successfully.")
            return redirect(url_for("campaigns"))
    finally:
        conn.close()

    return render_template("campaign_form.html", campaign=campaign)


# ---------------- Delete a campaign ----------------
@app.route("/campaigns/delete/<int:campaign_id>", methods=["POST"])
def delete_campaign(campaign_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM campaigns WHERE id=%s AND user_id=%s",
                (campaign_id, session["user_id"]),
            )
            conn.commit()
        flash("Campaign deleted.")
    finally:
        conn.close()

    return redirect(url_for("campaigns"))
@app.route("/compare")
def compare():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM campaigns WHERE user_id=%s AND status='approved'",
                (session["user_id"],),
            )
            campaign_list = cursor.fetchall()
    finally:
        conn.close()

    campaign_list = [calculate_campaign_stats(c) for c in campaign_list]

    if not campaign_list:
        return render_template("compare.html", campaigns=[], best=None, worst=None, suggestions=[])

    ranked = sorted(campaign_list, key=lambda c: c["roi"], reverse=True)
    best = ranked[0]
    worst = ranked[-1]

    suggestions = []
    if len(ranked) >= 2:
        suggestions.append(
            f"'{best['name']}' has the highest ROI ({best['roi']}%). Consider shifting more budget toward it."
        )
        if worst["roi"] < 0:
            suggestions.append(
                f"'{worst['name']}' has a negative ROI ({worst['roi']}%). Consider pausing or reducing its budget."
            )
        elif worst["roi"] < best["roi"] / 2:
            suggestions.append(
                f"'{worst['name']}' is underperforming compared to '{best['name']}'. Review its targeting or creative."
            )

    for c in campaign_list:
        if c["ctr"] < 1:
            suggestions.append(f"'{c['name']}' has a low CTR ({c['ctr']}%). Try improving ad creative or targeting.")
        if c["conversion_rate"] < 2 and c["clicks"] and c["clicks"] > 20:
            suggestions.append(f"'{c['name']}' has a low conversion rate ({c['conversion_rate']}%). Check your landing page.")

    if not suggestions:
        suggestions.append("All campaigns are performing reasonably well. Keep monitoring regularly.")

    return render_template(
        "compare.html",
        campaigns=ranked,
        best=best,
        worst=worst,
        suggestions=suggestions,
    )
# =====================================================
# REPORT MODULE
# Add this route to app.py, among your other routes
# (e.g. right after /compare).
# =====================================================

from datetime import datetime as dt


@app.route("/report")
def report():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM campaigns WHERE user_id=%s AND status='approved'",
                (session["user_id"],),
            )
            campaign_list = cursor.fetchall()
    finally:
        conn.close()

    campaign_list = [calculate_campaign_stats(c) for c in campaign_list]

    total_campaigns = len(campaign_list)
    total_budget = sum(float(c["budget"] or 0) for c in campaign_list)
    total_revenue = sum(float(c["revenue"] or 0) for c in campaign_list)
    avg_roi = round(((total_revenue - total_budget) / total_budget) * 100, 2) if total_budget > 0 else 0

    best = worst = None
    suggestions = []
    if campaign_list:
        ranked = sorted(campaign_list, key=lambda c: c["roi"], reverse=True)
        best = ranked[0]
        worst = ranked[-1]

        if len(ranked) >= 2:
            suggestions.append(f"'{best['name']}' has the highest ROI ({best['roi']}%). Consider shifting more budget toward it.")

        for c in campaign_list:
            if c["roi"] < 0:
                suggestions.append(f"'{c['name']}' has a negative ROI ({c['roi']}%). Consider pausing or reducing its budget.")
            if c["ctr"] < 1:
                suggestions.append(f"'{c['name']}' has a low CTR ({c['ctr']}%). Try improving ad creative or targeting.")

        if not suggestions:
            suggestions.append("All campaigns are performing reasonably well.")

    return render_template(
        "report.html",
        user_name=session.get("user_name"),
        generated_at=dt.now().strftime("%d %B %Y, %I:%M %p"),
        campaigns=campaign_list,
        total_campaigns=total_campaigns,
        total_budget=round(total_budget, 2),
        total_revenue=round(total_revenue, 2),
        avg_roi=avg_roi,
        best=best,
        worst=worst,
        suggestions=suggestions,
    )
@app.route("/admin/campaigns")
def admin_campaigns():
    if "user_id" not in session or not session.get("is_admin"):
        flash("You do not have access to this page.")
        return redirect(url_for("dashboard"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """SELECT campaigns.*, users.name AS owner_name, users.email AS owner_email
                   FROM campaigns
                   JOIN users ON campaigns.user_id = users.id
                   ORDER BY
                       CASE campaigns.status
                           WHEN 'pending' THEN 0
                           WHEN 'approved' THEN 1
                           ELSE 2
                       END,
                       campaigns.created_at DESC"""
            )
            all_campaigns = cursor.fetchall()
    finally:
        conn.close()

    return render_template("admin_campaigns.html", campaigns=all_campaigns)


@app.route("/admin/campaigns/approve/<int:campaign_id>", methods=["POST"])
def approve_campaign(campaign_id):
    if "user_id" not in session or not session.get("is_admin"):
        flash("You do not have access to this action.")
        return redirect(url_for("dashboard"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE campaigns SET status='approved' WHERE id=%s",
                (campaign_id,),
            )
            conn.commit()
        flash("Campaign approved.")
    finally:
        conn.close()

    return redirect(url_for("admin_campaigns"))


@app.route("/admin/campaigns/reject/<int:campaign_id>", methods=["POST"])
def reject_campaign(campaign_id):
    if "user_id" not in session or not session.get("is_admin"):
        flash("You do not have access to this action.")
        return redirect(url_for("dashboard"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE campaigns SET status='rejected' WHERE id=%s",
                (campaign_id,),
            )
            conn.commit()
        flash("Campaign rejected.")
    finally:
        conn.close()

    return redirect(url_for("admin_campaigns"))
if __name__ == "__main__":
    app.run(debug=True)
