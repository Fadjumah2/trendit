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
