from app.services.report.service import get_report_context

context = get_report_context(
    project_id=20,
    user_id=2,
    request_data={}
)

print(context.keys())