from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import os
import math
import traceback
import sys


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

        TEMPLATE_DIR = os.path.abspath(
            os.path.join(BASE_DIR, "..", "templates")
        )

        print("TEMPLATE DIR:", TEMPLATE_DIR)

        # template loader
        env = Environment(
            loader=FileSystemLoader(TEMPLATE_DIR)
        )

        print("JINJA ENV CREATED")

        # load template
        template = env.get_template("report.html")

        print("TEMPLATE LOADED")

        # render html
        # html_content = template.render(
        #     company_name=data.get("company_name"),
        #     project_name=data.get("project_name"),
        #     phone=data.get("phone"),
        #     email=data.get("email"),
        #     notes=data.get("notes"),
        #     rooms=data.get("rooms", []),
        #     objects=data.get("objects", []),
        # )
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