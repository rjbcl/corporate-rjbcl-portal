import traceback
from main_system.models import ReportAccessLog
 
 
def _format_query(sql_template: str, params: list) -> str:
    """
    Substitutes %s placeholders in the SQL template with their actual
    parameter values to produce a single human-readable query string.
 
    Strings and dates are wrapped in single quotes.
    None becomes NULL.
    Numbers are left unquoted.
    """
    formatted_params = []
    for param in params:
        if param is None:
            formatted_params.append('NULL')
        elif isinstance(param, (int, float)):
            formatted_params.append(str(param))
        else:
            # Strings, dates, and anything else — wrap in single quotes
            # and escape any internal single quotes
            escaped = str(param).replace("'", "''")
            formatted_params.append(f"'{escaped}'")
 
    # Replace each %s in order with its formatted value
    result = sql_template
    for value in formatted_params:
        result = result.replace('%s', value, 1)
 
    return result.strip()
 
 
def _format_error(exc: Exception) -> str:
    """
    Combines the exception message and full traceback into one string.
    """
    exc_message = str(exc)
    exc_traceback = traceback.format_exc()
    return f"Exception: {exc_message}\n\nTraceback:\n{exc_traceback}".strip()
 
 
def log_report_access(
    request,
    report_type: str,
    sql_template: str,
    params: list,
    status: str,
    exc: Exception = None,
    remarks: str = None,
):
    """
    Creates a ReportAccessLog entry.
 
    Args:
        request      : The DRF request object (used to extract username).
        report_type  : Human-readable report name e.g. 'Death Claim Report'.
        sql_template : Raw SQL string with %s placeholders.
        params       : List of parameters corresponding to the %s placeholders.
        status       : One of ReportAccessLog.Status values.
        exc          : The caught exception, if any. Used to populate error_message.
        remarks      : Optional free-form note to store alongside the log entry.
    """
    # Only store the generated SQL query for error outcomes.
    # For successful operations, store a placeholder and drop parameters.
    if status == ReportAccessLog.Status.SUCCESS:
        formatted_query = ''
    else:
        formatted_query = _format_query(sql_template, params)

    # Set has_error flag: 1 if error exists, 0 if no error
    has_error = status == ReportAccessLog.Status.ERROR or exc is not None

    ReportAccessLog.objects.create(
        generator=request.user.username,
        report_type=report_type.strip(),
        query=formatted_query,
        status=status,
        has_error=has_error,
        error_message=_format_error(exc) if exc is not None else None,
        remarks=remarks.strip() if remarks else None,
    )