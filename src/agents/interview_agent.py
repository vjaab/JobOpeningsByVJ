import os
import json
import logging
import requests
import html
from datetime import datetime, timezone
from serpapi import GoogleSearch

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.pdfgen import canvas

from src.utils.config import SERPAPI_KEY, GEMINI_API_KEY
from src.utils.db import get_state, set_state
from src.utils.telegram_bot import TelegramBot
from src.utils.whatsapp_bot import send_whatsapp_file, send_whatsapp_message

logger = logging.getLogger(__name__)

ROLES = [
    "SDE1",
    "SDE2",
    "SDE3",
    "Technical Architect",
    "Solution Architect",
    "Enterprise Architect"
]

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages):
        self.saveState()
        primary_color = colors.HexColor("#1E3A8A")
        gray_light = colors.HexColor("#E5E7EB")
        gray_dark = colors.HexColor("#4B5563")

        # Top Header (pages 2+)
        if self._pageNumber > 1:
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(primary_color)
            self.drawString(54, 750, "DAILY TECH JOBS DIGEST BY VJ")
            
            self.setFont("Helvetica", 8)
            self.setFillColor(gray_dark)
            self.drawRightString(558, 750, "INTERVIEW PREPARATION SERIES")
            
            self.setStrokeColor(gray_light)
            self.setLineWidth(0.75)
            self.line(54, 742, 558, 742)

        # Bottom Footer (all pages)
        self.setStrokeColor(gray_light)
        self.setLineWidth(0.75)
        self.line(54, 52, 558, 52)

        self.setFont("Helvetica", 8)
        self.setFillColor(gray_dark)
        self.drawString(54, 38, "Role-wise Interview Preparation Guide | Curated daily by VJ")
        
        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(558, 38, page_str)

        self.restoreState()


class InterviewPrepAgent:
    def __init__(self):
        self.roles = ROLES
        self.serpapi_key = SERPAPI_KEY
        self.gemini_key = GEMINI_API_KEY

    def get_current_role(self):
        """
        Retrieves the next role to process from database state.
        """
        role_idx = get_state("interview_role_index", 0)
        try:
            role_idx = int(role_idx)
        except ValueError:
            role_idx = 0
        
        if role_idx >= len(self.roles) or role_idx < 0:
            role_idx = 0
            
        return self.roles[role_idx], role_idx

    def advance_role_index(self, current_idx):
        """
        Increments role rotation index in SQLite state.
        """
        next_idx = (current_idx + 1) % len(self.roles)
        set_state("interview_role_index", next_idx)
        logger.info(f"Advanced interview role index to {next_idx} ({self.roles[next_idx]})")

    def search_market_trends(self, role_name):
        """
        Searches the web using SerpApi to fetch latest interview topics and trends.
        """
        if not self.serpapi_key:
            logger.warning("No SERPAPI_KEY configured. Skipping SerpApi search grounding.")
            return "No search results available."

        query = f"{role_name} interview questions and answers current market trends 2026"
        logger.info(f"Searching web via SerpApi for: {query}")
        
        try:
            params = {
                "engine": "google",
                "q": query,
                "api_key": self.serpapi_key,
                "num": 8
            }
            search = GoogleSearch(params)
            results = search.get_dict()
            organic = results.get("organic_results", [])
            
            snippets = []
            for r in organic:
                title = r.get("title", "")
                snippet = r.get("snippet", "")
                link = r.get("link", "")
                snippets.append(f"Title: {title}\nSnippet: {snippet}\nSource: {link}\n---")
                
            return "\n".join(snippets)
        except Exception as e:
            logger.error(f"Error searching Google via SerpApi: {e}", exc_info=True)
            return "Search failed due to API error."

    def generate_questions_json(self, role_name, search_context):
        """
        Calls Gemini API with search context to generate structured interview questions.
        """
        if not self.gemini_key:
            raise ValueError("GEMINI_API_KEY is not defined in configuration.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={self.gemini_key}"
        headers = {'Content-Type': 'application/json'}
        
        prompt = f"""You are an expert technical interviewer and curriculum designer.
Generate a comprehensive, high-quality interview preparation guide (questions and answers) for the role: '{role_name}' as per current market trends in July 2026.

Use the following internet search results as current context of market expectations:
{search_context}

Please generate exactly 10 high-quality interview questions and their answers.
The output MUST be a single, valid JSON object in the following format:
{{
  "role": "{role_name}",
  "introduction": "A professional introduction to the interview expectations for the role, highlighting the current focus areas (e.g. system scalability, cloud native, system design, coding, or behavioral expectations).",
  "questions": [
    {{
      "id": 1,
      "category": "Coding & Algorithms | System Design | Computer Science | Behavioral | Architecture",
      "question": "The question text...",
      "content_blocks": [
        {{
          "type": "paragraph",
          "text": "Detailed, thorough answer paragraph. Make it clean and professional."
        }},
        {{
          "type": "subheading",
          "text": "Subheading or Section Title if needed"
        }},
        {{
          "type": "bullet_list",
          "items": [
            "Bullet point 1 detailing a key architectural component or technical fact",
            "Bullet point 2 with detailed technical content"
          ]
        }},
        {{
          "type": "code",
          "language": "python|java|sql|ascii",
          "text": "Code snippet or ASCII architectural diagram"
        }}
      ]
    }}
  ]
}}

Ensure that:
1. The answers are deeply detailed, accurate, and structured.
2. Code/ASCII diagrams are properly escaped and look correct.
3. Content blocks are returned in the order they should be displayed.
4. If a block is a subheading, type is 'subheading' and text is the subheading string.
5. If a block is a bullet list, type is 'bullet_list' and items is an array of strings.
6. If a block is code/diagram, type is 'code' and text is the code/diagram content.
7. Return ONLY the JSON object. Do not wrap in backticks or any markdown formatting.
"""

        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2
            }
        }
        
        logger.info(f"Calling Gemini API to generate questions for {role_name}...")
        response = requests.post(url, headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        
        res_json = response.json()
        try:
            raw_text = res_json['candidates'][0]['content']['parts'][0]['text'].strip()
            # Clean up backticks if any
            if raw_text.startswith("```json"):
                raw_text = raw_text.split("```json", 1)[1]
            if raw_text.startswith("```"):
                raw_text = raw_text.split("```", 1)[1]
            if raw_text.endswith("```"):
                raw_text = raw_text.rsplit("```", 1)[0]
            raw_text = raw_text.strip()
            
            return json.loads(raw_text)
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}. Raw response: {res_json}")
            raise ValueError("Invalid JSON response from Gemini API.")

    def format_code_block(self, text):
        """
        Escapes XML special characters in code and converts leading spaces to non-breaking spaces for ReportLab.
        """
        lines = text.split('\n')
        formatted_lines = []
        for line in lines:
            leading_spaces = len(line) - len(line.lstrip(' '))
            line_content = line.lstrip(' ')
            escaped = html.escape(line_content)
            formatted = '&nbsp;' * leading_spaces + escaped
            formatted_lines.append(formatted)
        return '<br/>'.join(formatted_lines)

    def format_paragraph(self, text):
        """
        Escapes basic XML special characters in paragraph text.
        """
        return html.escape(text)

    def build_pdf(self, data, pdf_path):
        """
        Generates a premium PDF document using ReportLab.
        """
        logger.info(f"Generating PDF for {data['role']} at {pdf_path}...")
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=letter,
            leftMargin=54,
            rightMargin=54,
            topMargin=72,
            bottomMargin=72
        )

        styles = getSampleStyleSheet()

        # Modify existing styles to be clean and modern
        normal_style = styles['Normal']
        normal_style.textColor = colors.HexColor('#1F2937') # Charcoal
        normal_style.fontSize = 10
        normal_style.leading = 14

        # Custom Custom styles
        title_style = ParagraphStyle(
            name='DocTitle',
            fontName='Helvetica-Bold',
            fontSize=24,
            leading=28,
            textColor=colors.HexColor('#1E3A8A'),
            spaceAfter=8
        )

        subtitle_style = ParagraphStyle(
            name='DocSubtitle',
            fontName='Helvetica',
            fontSize=12,
            leading=16,
            textColor=colors.HexColor('#4B5563'),
            spaceAfter=12
        )

        meta_style = ParagraphStyle(
            name='DocMeta',
            fontName='Helvetica-Oblique',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#6B7280'),
            spaceAfter=20
        )

        intro_style = ParagraphStyle(
            name='IntroText',
            parent=normal_style,
            fontSize=10.5,
            leading=15,
            textColor=colors.HexColor('#374151')
        )

        q_title_style = ParagraphStyle(
            name='QuestionTitle',
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=16,
            textColor=colors.HexColor('#1E3A8A'),
            spaceBefore=14,
            spaceAfter=6,
            keepWithNext=True
        )

        subheading_style = ParagraphStyle(
            name='BlockSubheading',
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#111827'),
            spaceBefore=8,
            spaceAfter=4,
            keepWithNext=True
        )

        code_style = ParagraphStyle(
            name='CodeBlock',
            fontName='Courier',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#0F172A'),
            backColor=colors.HexColor('#F8FAFC'),
            borderColor=colors.HexColor('#E2E8F0'),
            borderWidth=0.5,
            borderPadding=8,
            spaceBefore=6,
            spaceAfter=6
        )

        bullet_style = ParagraphStyle(
            name='BulletItem',
            parent=normal_style,
            leftIndent=15,
            firstLineIndent=-10,
            spaceBefore=3,
            spaceAfter=3
        )

        story = []

        # Header Title Area (Page 1)
        story.append(Paragraph("DAILY TECH JOBS DIGEST BY VJ", ParagraphStyle('TopKicker', fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor('#3B82F6'), spaceAfter=4)))
        story.append(Paragraph(f"Interview Preparation Guide: {data['role']}", title_style))
        story.append(Paragraph("Curated Current Market Questions & Explanatory Solutions", subtitle_style))
        
        date_str = datetime.now().strftime("%B %d, %Y")
        story.append(Paragraph(f"Published on {date_str} | Powered by Gemini Grounded AI Engine", meta_style))
        
        # Blue Divider bar
        divider_data = [['']]
        divider_table = Table(divider_data, colWidths=[504], rowHeights=[3])
        divider_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#1E3A8A')),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(divider_table)
        story.append(Spacer(1, 15))

        # Introduction Section
        story.append(Paragraph("Role Overview & Interview Trends", ParagraphStyle('SecH', fontName='Helvetica-Bold', fontSize=14, textColor=colors.HexColor('#1E3A8A'), spaceBefore=10, spaceAfter=8, keepWithNext=True)))
        story.append(Paragraph(self.format_paragraph(data['introduction']), intro_style))
        story.append(Spacer(1, 15))

        # Questions Q1 to Q10
        story.append(Paragraph("Curated Practice Questions", ParagraphStyle('SecH2', fontName='Helvetica-Bold', fontSize=14, textColor=colors.HexColor('#1E3A8A'), spaceBefore=10, spaceAfter=8, keepWithNext=True)))
        
        for q in data['questions']:
            q_elements = []
            
            # Question Title
            q_text = f"Q{q['id']}. {q['question']}"
            q_cat = f" [{q['category']}]" if 'category' in q else ""
            q_elements.append(Paragraph(self.format_paragraph(q_text) + f"<font color='#4B5563'><i>{self.format_paragraph(q_cat)}</i></font>", q_title_style))
            
            # Question Content Blocks
            for block in q.get('content_blocks', []):
                b_type = block.get('type')
                if b_type == 'paragraph':
                    q_elements.append(Paragraph(self.format_paragraph(block.get('text', '')), normal_style))
                    q_elements.append(Spacer(1, 6))
                elif b_type == 'subheading':
                    q_elements.append(Paragraph(self.format_paragraph(block.get('text', '')), subheading_style))
                elif b_type == 'bullet_list':
                    for item in block.get('items', []):
                        q_elements.append(Paragraph(f"&bull; {self.format_paragraph(item)}", bullet_style))
                    q_elements.append(Spacer(1, 6))
                elif b_type == 'code':
                    code_text = self.format_code_block(block.get('text', ''))
                    q_elements.append(Paragraph(code_text, code_style))
                    q_elements.append(Spacer(1, 6))
            
            q_elements.append(Spacer(1, 10))
            
            # We keep each question and its solution together if it fits on a single page, otherwise flows nicely.
            story.append(KeepTogether(q_elements))

        # Build PDF using NumberedCanvas
        doc.build(story, canvasmaker=NumberedCanvas)
        logger.info(f"Successfully generated PDF file: {pdf_path}")

    def execute_daily_run(self):
        """
        Executes the daily flow: role selection, trend scraping, PDF compilation, and sharing.
        """
        role_name, role_idx = self.get_current_role()
        logger.info(f"Daily Interview Prep Agent run starting for role: {role_name} (index: {role_idx})")
        
        bot = TelegramBot()
        
        try:
            # 1. Search internet for current topics/trends
            search_context = self.search_market_trends(role_name)
            
            # 2. Query Gemini for interview prep material
            data = self.generate_questions_json(role_name, search_context)
            
            # 3. Create PDF
            filename = f"{role_name.replace(' ', '_')}_Interview_Questions.pdf"
            pdf_path = os.path.abspath(filename)
            self.build_pdf(data, pdf_path)
            
            # 4. Upload/Send PDF via Telegram Channel
            telegram_caption = f"📚 *Daily Interview Preparation Guide*\n\nRole: *{role_name}*\n\nHere is a comprehensive PDF guide covering the latest interview questions, code snippets, architectural solutions, and behavioral patterns for the *{role_name}* role as per current 2026 market expectations.\n\nEnjoy preparing! 🚀\n#InterviewPrep #{role_name.replace(' ', '')}"
            bot.send_document(pdf_path, caption=telegram_caption)
            
            # 5. Upload/Send PDF via WhatsApp Channel
            # First send text notification
            wa_text = f"📚 *Daily Interview Preparation Guide*\n\nRole: *{role_name}*\n\nFind attached the compiled PDF guide with the latest interview questions and answers as per current market trends."
            send_whatsapp_message(wa_text)
            
            # Then send PDF document
            send_whatsapp_file(pdf_path)
            
            # 6. Advance index to next role on success
            self.advance_role_index(role_idx)
            
            # Clean up local PDF file
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
                logger.info(f"Cleaned up local PDF file at {pdf_path}")
                
            logger.info("Daily Interview Prep Agent completed successfully.")
            return True
            
        except Exception as e:
            logger.error(f"Error during daily interview prep agent run: {e}", exc_info=True)
            bot.send_admin_alert(f"Interview Prep Agent failed for {role_name}: {e}")
            return False
