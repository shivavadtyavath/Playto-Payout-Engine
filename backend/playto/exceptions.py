from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """Custom exception handler that returns consistent JSON error envelopes."""
    response = exception_handler(exc, context)

    if response is not None:
        # Normalize DRF validation errors into our envelope format
        if isinstance(response.data, dict) and 'detail' in response.data:
            response.data = {
                'error': str(response.data['detail']),
                'code': getattr(response.data['detail'], 'code', 'ERROR'),
            }
        elif isinstance(response.data, dict) and 'error' not in response.data:
            # Flatten field-level validation errors
            errors = []
            for field, messages in response.data.items():
                if isinstance(messages, list):
                    errors.extend([f"{field}: {m}" for m in messages])
                else:
                    errors.append(f"{field}: {messages}")
            response.data = {
                'error': '; '.join(errors),
                'code': 'VALIDATION_ERROR',
            }

    return response
