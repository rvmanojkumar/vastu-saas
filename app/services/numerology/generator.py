import os
import shutil
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from app.services.numerology.calculator import build_chart


def _template_dir():
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(base, "..", "templates"))


def generate_numerology_pdf(payload: dict, file_path: str) -> str:
    """
    payload keys: full_name, date_of_birth (date), gender, mobile_number, lang
    """
    lang = (payload.get("lang") or "en").lower()
    # For now EN template is the styled base; MR/HI reuse until translated copies exist
    template_name = "numerology_en.html"
    mr_path = os.path.join(_template_dir(), "numerology_mr.html")
    hi_path = os.path.join(_template_dir(), "numerology_hi.html")
    if lang == "mr" and os.path.exists(mr_path):
        template_name = "numerology_mr.html"
    elif lang == "hi" and os.path.exists(hi_path):
        template_name = "numerology_hi.html"

    chart = build_chart(
        full_name=payload["full_name"],
        dob=payload["date_of_birth"],
        gender=payload.get("gender") or "M",
        mobile_number=payload.get("mobile_number"),
    )

    env = Environment(loader=FileSystemLoader(_template_dir()), autoescape=True)
    template = env.get_template(template_name)
    html = template.render(
        chart=chart,
        lang=lang,
        report_title=f"SPIRITUAL HUT - Numerology Report - {chart['full_name']}",
    )

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    HTML(string=html, base_url=_template_dir()).write_pdf(file_path)

    # Also keep HTML sibling for debugging (optional)
    html_path = file_path.replace(".pdf", ".html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    return file_path


def ensure_lang_templates():
    """Copy EN template to MR/HI placeholders if missing."""
    base = _template_dir()
    en = os.path.join(base, "numerology_en.html")
    for lang in ("mr", "hi"):
        dest = os.path.join(base, f"numerology_{lang}.html")
        if not os.path.exists(dest) and os.path.exists(en):
            shutil.copy(en, dest)
