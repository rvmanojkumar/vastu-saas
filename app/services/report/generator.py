from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import os
import math
import traceback
import sys
from docxtpl import DocxTemplate,InlineImage
from docx.shared import Mm
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
from docxtpl import InlineImage
from docx.shared import Inches  # Ensure Inches is imported



# =========================
# SAFE HELPERS
# =========================
def sanitize_payload(data):

    if isinstance(data, dict):
        return {k: sanitize_payload(v) for k, v in data.items()}

    elif isinstance(data, list):
        return [sanitize_payload(v) for v in data]

    elif isinstance(data, float) and math.isnan(data):
        return 0

    elif data is None:
        return ""

    return data


# =========================
# GENERATE PDF
# =========================
def generate_pdf(data, file_path):

    try:

        print("\n========== PDF DEBUG ==========")

        print("PYTHON:", sys.executable)
        print("CURRENT DIR:", os.getcwd())

        # sanitize
        data = sanitize_payload(data)

        print("SANITIZED DATA OK")

        # absolute template path
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        lang = data.get("lang", "en")
        TEMPLATE_DIR = os.path.abspath(
            os.path.join(BASE_DIR, "..", "templates")
        )

        print("TEMPLATE DIR:", TEMPLATE_DIR)
        print("LANG:", lang)
        # template loader
        env = Environment(
            loader=FileSystemLoader(TEMPLATE_DIR)
        )
        print("JINJA ENV CREATED")
        # load template
        template = env.get_template(f"report_{lang}.html")
        print("TEMPLATE LOADED")
        html_content = template.render(**data)

        print("HTML RENDERED")
        print("HTML LENGTH:", len(html_content))

        # SAVE DEBUG HTML
        debug_html_path = file_path.replace(".pdf", ".html")

        os.makedirs(
            os.path.dirname(debug_html_path),
            exist_ok=True
        )

        with open(debug_html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print("DEBUG HTML SAVED:", debug_html_path)

        # ensure folder exists
        os.makedirs(
            os.path.dirname(file_path),
            exist_ok=True
        )

        print("GENERATING PDF...")

        # IMPORTANT:
        # generate bytes first
        pdf_bytes = HTML(
            string=html_content,
            base_url=TEMPLATE_DIR
        ).write_pdf()

        print("PDF GENERATED IN MEMORY")
        print("PDF BYTE LENGTH:", len(pdf_bytes))

        # SAVE PDF MANUALLY
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        print("PDF SAVED:", file_path)

        # verify final file
        final_size = os.path.getsize(file_path)

        print("FINAL PDF SIZE:", final_size)

        print("========== PDF SUCCESS ==========\n")

        return file_path

    except Exception as e:

        print("\n========== PDF ERROR ==========")

        print(str(e))

        traceback.print_exc()

        raise e

def generate_docx(data, file_path, project_id):

    try:

        print("\n========== DOCX DEBUG ==========")
        print("PYTHON:", sys.executable)
        print("CURRENT DIR:", os.getcwd())

        # sanitize
        data = sanitize_payload(data)
        print("SANITIZED DATA OK")
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        # absolute template path
        lang = data.get("lang", "en")
        TEMPLATE_PATH = os.path.abspath(
        os.path.join(BASE_DIR, "..", "templates", f"report_{lang}.docx")
        )
        print("LANG:", lang)
        print("TEMPLATE PATH:", TEMPLATE_PATH)

        # load template
        if not os.path.exists(TEMPLATE_PATH):
            raise FileNotFoundError(f"Template not found for lang '{lang}': {TEMPLATE_PATH}")
        doc = DocxTemplate(TEMPLATE_PATH)
        print("TEMPLATE LOADED")

        # prepare rating pairs for detailed analysis grid
        ratings = data.get('ratings', [])
        data['rating_pairs'] = [ratings[i:i+2] for i in range(0, len(ratings), 2)]
        print("RATING PAIRS BUILT:", len(data['rating_pairs']))

        # inline images
        chart32_path = os.path.abspath(f"storage/projects/{project_id}/compass_32.png")
        chart16_path = os.path.abspath(f"storage/projects/{project_id}/compass_16.png")

        print("CHART32 PATH:", chart32_path)
        print("CHART16 PATH:", chart16_path)

        if not os.path.exists(chart32_path):
            raise FileNotFoundError(f"compass_32.png not found: {chart32_path}")
        if not os.path.exists(chart16_path):
            raise FileNotFoundError(f"compass_16.png not found: {chart16_path}")

        data['chart32'] = InlineImage(doc, chart32_path, width=Inches(7.4), height=Inches(5.6))
        data['chart16'] = InlineImage(doc, chart16_path, width=Inches(7.4), height=Inches(5.6))
        print("CHART IMAGES LOADED")

        data['bar_chart'] = make_bar_chart_image(data['ratings'], doc)
        print("BAR CHART GENERATED")

        # ensure output folder exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        print("RENDERING DOCX...")
        doc.render(data)
        print("DOCX RENDERED")

        doc.save(file_path)
        print("DOCX SAVED:", file_path)

        # verify final file
        final_size = os.path.getsize(file_path)
        print("FINAL DOCX SIZE:", final_size)

        print("========== DOCX SUCCESS ==========\n")

        return file_path

    except Exception as e:

        print("\n========== DOCX ERROR ==========")
        print(str(e))
        traceback.print_exc()
        raise e

def make_bar_chart_image(ratings, tpl):
    """Generate a bar chart from room ratings and return an InlineImage."""
    rooms = [r['name'] for r in ratings if r.get('type', '').lower() == 'room']
    values = [float(r['rating']) for r in ratings if r.get('type', '').lower() == 'room']

    fig, ax = plt.subplots(figsize=(7, 3))
    bars = ax.bar(rooms, values, color='#3182ce', width=0.5)

    # Value labels on top of each bar
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                str(val), ha='center', va='bottom', fontsize=9, fontweight='bold')

    ax.set_ylim(0, 10)
    ax.set_yticks(range(0, 11, 2))
    ax.set_ylabel('Rating', fontsize=9)
    ax.set_title('Room Ratings Analysis', fontsize=11, fontweight='bold')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.xticks(fontsize=8, rotation=15, ha='right')
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150)
    plt.close(fig)
    buf.seek(0)
    return InlineImage(tpl, buf, width=Mm(140))