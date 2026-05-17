from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import os
import math


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

    # sanitize
    data = sanitize_payload(data)

    # template loader
    env = Environment(
        loader=FileSystemLoader("app/templates")
    )

    template = env.get_template("report.html")

    # render html
    html_content = template.render(
        company_name=data.get("company_name"),
        project_name=data.get("project_name"),
        phone=data.get("phone"),
        email=data.get("email"),
        notes=data.get("notes"),
        rooms=data.get("rooms", []),
        objects=data.get("objects", []),
    )

    # ensure folder exists
    os.makedirs(
        os.path.dirname(file_path),
        exist_ok=True
    )

    # generate pdf
    HTML(string=html_content).write_pdf(file_path)

    return file_path