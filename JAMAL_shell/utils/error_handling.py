import functools
import logging

logger = logging.getLogger(__name__)

HNDL_EXCPT_MARKER_ATTRIBUTE = "__hndl_excpt_applied_marker__"
HNDL_EXCPT_PARAM_ATTRIBUTE = "__hndl_excpt_param_value__"


def handle_exceptions_on_line(error_prefix=None, collect_errors=True):
    """
    Decorator to handle exceptions in a consistent way.

    Args:
        error_prefix (str, optional): Prefix for error messages. If None, will use function name.
        collect_errors (bool): Whether to collect errors in self.errors list.

    Returns:
        Decorated function that handles exceptions.
    """

    def decorator(func):
        prefix = error_prefix or func.__name__

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Determine context for error messages

            # Extract line_num from args or kwargs if present
            line_num = None
            if len(args) >= 2 and isinstance(args[0], int) and isinstance(args[1], int):
                line_num = args[1]
            else:
                for arg in args:
                    if isinstance(arg, int):
                        line_num = arg
                        break

            if "line_num" in kwargs:
                line_num = kwargs["line_num"]

            # Build error message based on available context
            if line_num is not None:
                context = f"{prefix} line {line_num}"
            else:
                context = prefix

            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                # Log the error with full stack trace
                logger.error(
                    f"An unexpected error occurred in {context}: {e}", exc_info=True
                )

                # Collect error if requested
                if collect_errors and hasattr(self, "errors"):
                    self.errors.append(f"Unexpected error in {context}: {e}")

                # Return None or appropriate default value
                return None

        setattr(wrapper, HNDL_EXCPT_MARKER_ATTRIBUTE, True)
        setattr(wrapper, HNDL_EXCPT_PARAM_ATTRIBUTE, prefix)

        return wrapper

    return decorator
