"""
Email templates for post approval workflow.
"""
import html

def draft_preview_email(post_id: str, post_type: str, draft_content: dict, backend_url: str) -> tuple[str, str]:
    title = draft_content.get("title", "")
    body = draft_content.get("body", "")
    cta = draft_content.get("cta", "")

    safe_title = html.escape(title)
    safe_body = html.escape(body).replace("\n", "<br>")
    safe_cta = html.escape(cta)
    
    subject = f"New {post_type.capitalize()} Post Draft for Approval"
    
    approve_url = f"{backend_url}/approve/{post_id}"
    reject_url = f"{backend_url}/reject/{post_id}"
    
    html_body = f"""
    <html>
    <body>
        <h2>New {post_type.capitalize()} Post Draft</h2>
        <p><b>Title:</b> {safe_title}</p>
        <p><b>Body:</b><br>{safe_body}</p>
        <p><i>CTA: {safe_cta}</i></p>
        <br>
        <p>
            <a href="{approve_url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Approve and Publish</a>
            &nbsp;&nbsp;
            <a href="{reject_url}" style="background-color: #f44336; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reject / Skip</a>
        </p>
    </body>
    </html>
    """
    return subject, html_body

def connection_confirmed_email(business_name: str, location_id: str) -> tuple[str, str]:
    subject = "Google Business Profile Connected"
    html_body = f"""
    <html>
    <body>
        <h2>Account Connected!</h2>
        <p>Your Google Business Profile for <b>{html.escape(business_name)}</b> is now connected to Trendit.</p>
        <p>We'll start generating your first post draft soon. Stay tuned!</p>
        <br>
        <p><i>Location ID: {html.escape(location_id)}</i></p>
    </body>
    </html>
    """
    return subject, html_body

def no_gbp_found_email(business_name: str) -> tuple[str, str]:
    subject = "Action Required: Google Business Profile Not Found"
    html_body = f"""
    <html>
    <body>
        <h2>We couldn't find your Business Profile</h2>
        <p>Hi there,</p>
        <p>We successfully connected to your Google account, but we couldn't find a Google Business Profile for <b>{html.escape(business_name)}</b>.</p>
        <p>To use Trendit, you need an active Google Business Profile. You can create one for free here:</p>
        <p><a href="https://www.google.com/business/go/" style="background-color: #4285F4; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Create Google Business Profile</a></p>
        <br>
        <p>Once created, please return to Trendit and try connecting again.</p>
    </body>
    </html>
    """
    return subject, html_body

def review_reply_preview_email(reply_id: str, reviewer_name: str, review_text: str, star_rating: int, draft_reply: str, backend_url: str) -> tuple[str, str]:
    safe_reviewer = html.escape(reviewer_name or "A customer")
    safe_review = html.escape(review_text).replace("\n", "<br>")
    safe_reply = html.escape(draft_reply).replace("\n", "<br>")
    
    subject = f"New AI Reply Draft for Review by {safe_reviewer}"
    
    approve_url = f"{backend_url}/approve-review/{reply_id}"
    reject_url = f"{backend_url}/reject-review/{reply_id}"
    
    html_body = f"""
    <html>
    <body>
        <h2>New AI Reply Draft</h2>
        <div style="background-color: #f9f9f9; padding: 15px; border-left: 4px solid #4285F4;">
            <p><b>Reviewer:</b> {safe_reviewer} ({star_rating} stars)</p>
            <p><b>Review:</b><br><i>"{safe_review}"</i></p>
        </div>
        <br>
        <p><b>AI Suggested Reply:</b><br>{safe_reply}</p>
        <br>
        <p>
            <a href="{approve_url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Approve and Post</a>
            &nbsp;&nbsp;
            <a href="{reject_url}" style="background-color: #f44336; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reject / Ignore</a>
        </p>
    </body>
    </html>
    """
    return subject, html_body

def decision_result_page(message: str) -> str:
    safe_message = html.escape(message)
    return f"""
    <html>
    <head><title>Trendit Approval</title></head>
    <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
        <h2>{safe_message}</h2>
        <p><a href="https://forms.trendexhub.com">Return to Dashboard</a></p>
    </body>
    </html>
    """
