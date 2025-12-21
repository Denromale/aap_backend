from django.core.files.storage import default_storage

from core.models import ProcedureFile, ClientDocument


def delete_file_if_unused(file_name: str, *, exclude_pf_id=None, exclude_doc_id=None) -> bool:
    """
    Удаляет физический файл из storage только если на него больше никто не ссылается.
    Возвращает True если файл удалён, иначе False.
    """
    if not file_name:
        return False

    pf_exists = (
        ProcedureFile.objects.filter(file=file_name)
        .exclude(pk=exclude_pf_id)
        .exists()
    )
    doc_exists = (
        ClientDocument.objects.filter(file=file_name)
        .exclude(pk=exclude_doc_id)
        .exists()
    )

    if pf_exists or doc_exists:
        return False

    if default_storage.exists(file_name):
        default_storage.delete(file_name)
        return True

    return False
