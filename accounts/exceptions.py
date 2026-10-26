from rest_framework.views import exception_handler


def first_message(detail):
    if isinstance(detail, dict):
        return first_message(next(iter(detail.values()), "Request failed."))
    if isinstance(detail, list):
        return first_message(detail[0]) if detail else "Request failed."
    return str(detail)


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    errors = response.data if isinstance(response.data, (dict, list)) else {"detail": response.data}
    response.data = {
        "status": "error",
        "message": first_message(response.data),
        "data": None,
        "errors": errors,
    }
    return response