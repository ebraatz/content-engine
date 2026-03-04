# digest.py
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from anthropic import Anthropic
from dotenv import load_dotenv

from feeds import fetch_feeds

load_dotenv()

SYSTEM_PROMPT = """You are a content strategist for Eric Braatz — pharma ops and quality
practitioner, 20 years GMP manufacturing, DEA compliance specialist,
AI skeptic-optimist. Building a LinkedIn thought leadership presence
at the intersection of pharma operations and AI.

Your job is NOT to write a post. Your job is to surface the best angle
from today's signals.

For each signal, identify:
1. Which of these patterns it connects to (pick the closest):
   - Foundation Fallacy: tools deployed on broken foundations
   - Knowledge Exodus: institutional knowledge walking out the door
   - Chesterton's Fence: removing rules without understanding why they exist
   - Validation Theater: compliance designed for auditors not operators
   - Regulator Moves First: FDA ahead of the industry it regulates
   - Seam Problem: compliance failures at system interfaces
   - Human Faculty Atrophy: skills degrading from disuse
   - Architecture Lie: RAG sold as something smarter
   - Same Pattern Different Decade: current AI wave rhymes with Six Sigma
   - Pipeline Gap: discovery accelerated, ops unchanged
   - SME Credibility Premium: insider knowledge vs outside commentary
   - Measurement Trap: optimizing metrics not outcomes

2. Which named story from Eric's library is the best match:
   - Floppy Disk Sampling Plan
   - Six Sigma Pilgrimage
   - Elsa Deployed Anyway
   - SMR Workflow
   - DEA Database That Never Shipped
   - Bob (recurring character)
   - Phone Number Problem
   - CAPA Board

3. One suggested hook line in Eric's voice — punchy, specific, no corporate language

If nothing today is genuinely interesting, respond with:
WEAK DAY. Best signal: [headline]. Pattern: [closest match]. Skip recommended.

RECENT PATTERNS USED: [leave blank for now — we will update weekly]"""


def build_prompt(articles):
    if not articles:
        return "No articles were found today."

    lines = ["Here are today's signals:\n"]
    for i, article in enumerate(articles, 1):
        lines.append(f"{i}. [{article['source']}] {article['title']}")
        if article.get("summary"):
            summary = article["summary"][:300].strip()
            lines.append(f"   {summary}")
        lines.append(f"   {article['url']}\n")

    return "\n".join(lines)


def run_digest():
    articles = fetch_feeds()
    prompt = build_prompt(articles)

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    response = message.content[0].text

    date_str = datetime.now().strftime("%Y-%m-%d")
    output_path = os.path.join("outputs", f"{date_str}-digest.md")
    os.makedirs("outputs", exist_ok=True)

    with open(output_path, "w") as f:
        f.write(f"# Digest — {date_str}\n\n")
        f.write(response)
        f.write("\n\n---\n")
        f.write(f"_Generated from {len(articles)} articles across {len(set(a['source'] for a in articles))} sources._\n")

    print(f"[digest] Saved to {output_path}")

    send_email(date_str, output_path)
    return output_path


def send_email(date_str, digest_path):
    gmail_user = os.environ["GMAIL_USER"]
    gmail_password = os.environ["GMAIL_APP_PASSWORD"]

    with open(digest_path, "r") as f:
        body = f.read()

    msg = MIMEText(body, "plain")
    msg["Subject"] = f"🧪 Pharma AI Digest — {date_str}"
    msg["From"] = gmail_user
    msg["To"] = "ebraatz@gmail.com"

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, "ebraatz@gmail.com", msg.as_string())

    print(f"[digest] Email sent to ebraatz@gmail.com")


if __name__ == "__main__":
    run_digest()
