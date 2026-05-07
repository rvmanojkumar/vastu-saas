from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
import matplotlib.pyplot as plt
import os
import math

# =========================
# SAFE HELPERS (ADDED)
# =========================
def safe_number(value, default=0):
    try:
        if value is None:
            return default
        if isinstance(value, float) and math.isnan(value):
            return default
        return value
    except:
        return default


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


styles = getSampleStyleSheet()

# 🎨 BRAND COLORS
PRIMARY = colors.HexColor("#1F3A5F")
ACCENT = colors.HexColor("#E67E22")
LIGHT_BG = colors.HexColor("#F4F6F7")


# =========================
# HEADER / FOOTER
# =========================
def add_header_footer(canvas, doc):
    canvas.saveState()

    canvas.setFont("Helvetica-Bold", 10)
    canvas.setFillColor(PRIMARY)
    canvas.drawString(40, 800, "Vastu SaaS Report")

    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.grey)
    canvas.drawString(40, 30, f"Page {doc.page}")

    canvas.setFont("Helvetica-Bold", 40)
    canvas.setFillColorRGB(0.9, 0.9, 0.9)
    canvas.drawCentredString(300, 400, "VASTU")

    canvas.restoreState()


# =========================
# MAIN PDF
# =========================
def generate_pdf(data, file_path):

    # 🔥 SANITIZE INPUT (ADDED)
    data = sanitize_payload(data)

    doc = SimpleDocTemplate(file_path, pagesize=A4)

    elements = []

    # -------------------------
    # COVER PAGE
    # -------------------------
    elements.append(Spacer(1, 100))

    # LOGO (safe)
    if data.get("logo") and os.path.exists(str(data.get("logo"))):
        elements.append(Image(data["logo"], width=120, height=80))
        elements.append(Spacer(1, 20))

    elements.append(Paragraph(
        f"<font size=26 color='{PRIMARY}'><b>{data.get('company_name','Unknown Company')}</b></font>",
        styles["Title"]
    ))

    elements.append(Spacer(1, 20))

    elements.append(Paragraph(
        "<font size=18><b>Vastu Analysis Report</b></font>",
        styles["Heading1"]
    ))

    elements.append(Spacer(1, 30))

    elements.append(Paragraph(f"<b>Project:</b> {data.get('project_name','Unknown Project')}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Phone:</b> {data.get('phone','')}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Email:</b> {data.get('email','')}", styles["Normal"]))

    elements.append(PageBreak())

    # -------------------------
    # SUMMARY
    # -------------------------
    elements.append(Paragraph(
        "<font size=16 color='#1F3A5F'><b>Project Summary</b></font>",
        styles["Heading2"]
    ))

    elements.append(Spacer(1, 10))

    elements.append(Paragraph(data.get("notes", "No notes"), styles["Normal"]))
    elements.append(Spacer(1, 20))

    # -------------------------
    # ROOM TABLE
    # -------------------------
    elements.append(Paragraph(
        "<font size=16 color='#1F3A5F'><b>Room Analysis</b></font>",
        styles["Heading2"]
    ))

    elements.append(Spacer(1, 10))

    table_data = [["Room", "Direction", "Result", "Color", "Therapy"]]

    good = 0
    bad = 0

    for r in data.get("rooms", []):
        result = r.get("result", "")

        if result == "good":
            good += 1
        else:
            bad += 1

        table_data.append([
            r.get("name", ""),
            str(safe_number(r.get("direction_16"))),  # ✅ FIXED
            result,
            r.get("color", ""),
            r.get("therapy", "")
        ])

    table = Table(table_data, colWidths=[80, 80, 60, 80, 120])

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 1), (-1, -1), LIGHT_BG),
    ]))

    elements.append(table)
    elements.append(PageBreak())

    # -------------------------
    # CHART
    # -------------------------
    chart_path = "storage/reports/chart.png"
    os.makedirs("storage/reports", exist_ok=True)

    # 🔥 FIX: avoid pie crash
    if good == 0 and bad == 0:
        good = 1

    plt.figure()
    plt.pie(
        [good, bad],
        labels=["Good", "Bad"],
        autopct="%1.0f%%"
    )
    plt.savefig(chart_path)
    plt.close()

    elements.append(Paragraph(
        "<font size=16 color='#1F3A5F'><b>Analysis Chart</b></font>",
        styles["Heading2"]
    ))

    elements.append(Spacer(1, 10))
    elements.append(Image(chart_path, width=300, height=300))

    elements.append(PageBreak())

    # -------------------------
    # RECOMMENDATIONS
    # -------------------------
    elements.append(Paragraph(
        "<font size=16 color='#1F3A5F'><b>Recommendations</b></font>",
        styles["Heading2"]
    ))

    elements.append(Spacer(1, 10))

    for r in data.get("rooms", []):
        elements.append(Paragraph(
            f"<b>{r.get('name','')}</b>: Use <font color='green'>{r.get('color','N/A')}</font> color. "
            f"Remedy: {r.get('therapy','N/A')}",
            styles["Normal"]
        ))
        elements.append(Spacer(1, 8))

    # -------------------------
    # BUILD
    # -------------------------
    doc.build(elements, onFirstPage=add_header_footer, onLaterPages=add_header_footer)