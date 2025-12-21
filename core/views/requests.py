from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from core.utils import require_active_client
from core.models import AuditSubStep, ProcedureFile


@login_required
def requests_view(request):
    client, redirect_resp = require_active_client(request)
    if redirect_resp:
        return redirect_resp

    # Берём все файлы клиента, которые относятся к "запросам/шагам" (procedure_code хранит id подшага)
    # Логику не меняем: отображаем то, что уже есть в ProcedureFile.
    files = (
        ProcedureFile.objects
        .filter(client=client)
        .order_by("-created_at")
    )

    # Подтянем подшаги, чтобы можно было красиво показывать подпись (если в шаблоне нужно)
    substeps_by_id = {str(s.id): s for s in AuditSubStep.objects.select_related("step").all()}

    return render(
        request,
        "core/requests.html",
        {
            "selected_client": client,
            "files": files,
            "substeps_by_id": substeps_by_id,
        },
    )
