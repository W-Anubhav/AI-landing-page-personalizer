import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import base64
import json
import urllib.parse
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.set_page_config(page_title="AI Landing Page Personalizer", layout="wide")

st.title("🚀 AI Landing Page Personalizer")

# ---------------- SCRAPER ----------------
def scrape_page(url):
    try:
        response = requests.get(
            url,
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=8,
            verify=False
        )

        soup = BeautifulSoup(response.text, 'html.parser')

        # Fix relative URLs
        for tag in soup.find_all(['link', 'script', 'img']):
            if tag.get('src'):
                tag['src'] = urllib.parse.urljoin(url, tag['src'])
            if tag.get('href'):
                tag['href'] = urllib.parse.urljoin(url, tag['href'])

        h1 = soup.find('h1')
        p = soup.find('p')
        button = soup.find('button') or soup.find('a')

        return soup, {
            "headline": h1.get_text(strip=True) if h1 else "",
            "paragraph": p.get_text(strip=True) if p else "",
            "cta": button.get_text(strip=True) if button else ""
        }

    except Exception as e:
        return None, str(e)


# ---------------- AI ----------------
def generate_cro_copy(image_bytes, page_data):
    base64_image = base64.b64encode(image_bytes).decode('utf-8')

    prompt = f"""
You are a CRO expert.

Ad image is provided.

Current Page:
Headline: {page_data['headline']}
Paragraph: {page_data['paragraph']}
CTA: {page_data['cta']}

Rewrite ONLY:
- headline
- paragraph
- CTA

Make it aligned with the ad.

Return JSON:
{{
  "headline": "...",
  "paragraph": "...",
  "cta": "...",
  "theme_color": "#hex"
}}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                }
            ]
        }],
        response_format={"type": "json_object"}
    )

    return json.loads(response.choices[0].message.content)


# ---------------- UI ----------------
uploaded_file = st.file_uploader("📸 Upload Ad Image", type=["png", "jpg", "jpeg"])
url = st.text_input("🌐 Enter Landing Page URL")

if st.button("✨ Generate Personalized Page"):

    if not uploaded_file:
        st.error("Please upload an image")
        st.stop()

    if not url.startswith("http"):
        st.error("Enter valid URL")
        st.stop()

    with st.spinner("🔍 Scraping page..."):
        soup, page_data = scrape_page(url)

    if not soup:
        st.error(f"Scraping failed: {page_data}")
        st.stop()

    image_bytes = uploaded_file.read()

    with st.spinner("🤖 AI is personalizing..."):
        try:
            ai_data = generate_cro_copy(image_bytes, page_data)
        except Exception as e:
            st.error(f"AI Error: {str(e)}")
            st.stop()

    # -------- UPDATE PAGE --------
    h1 = soup.find('h1')
    p = soup.find('p')
    button = soup.find('button') or soup.find('a')

    if h1 and ai_data.get("headline"):
        h1.string = ai_data["headline"]

    if p and ai_data.get("paragraph"):
        p.string = ai_data["paragraph"]

    if button and ai_data.get("cta"):
        button.string = ai_data["cta"]

    # -------- STYLE --------
    theme_color = ai_data.get("theme_color", "#f5f5f5")

    style_tag = soup.new_tag("style")
    style_tag.string = f"""
    .ai-highlight {{
        border: 2px solid {theme_color};
        padding: 8px;
        border-radius: 6px;
    }}
    """

    if soup.head:
        soup.head.append(style_tag)

    if h1:
        h1['class'] = (h1.get('class', []) + ['ai-highlight'])

    # -------- SAVE --------
    html_output = str(soup)

    st.success("✅ Done!")

    st.download_button(
        label="⬇️ Download Personalized Page",
        data=html_output,
        file_name="personalized.html",
        mime="text/html"
    )

    st.subheader("🔍 Preview (Partial)")
    st.code(ai_data)