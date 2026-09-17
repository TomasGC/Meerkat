import functions_framework


@functions_framework.http
def ping(request):
    """Health probe deployed as a Cloud Function."""
    return "pong"
