# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Helper functions for retrying functions/code with tenacity."""

import logging
from typing import Callable

from tenacity import Future, RetryCallState, stop_after_attempt


def tenacity_retry_log(
    logger: logging.Logger,
    log_level: int = logging.WARNING,
) -> Callable[[RetryCallState], None]:
    """
    Log retry attempts after an exception has occurred.

    This should be specified as the after= argument to a tenacity.retry decorator,
    or a tenacity.Retrying context manager.
    """

    def log_attempt(retry_state: RetryCallState) -> None:
        """
        Inner function to log retry message.
        """
        if retry_state.outcome is None:
            logger.log(
                log_level, f"Retry {retry_state.attempt_number}: outcome is None."
            )
            return

        # NOTE: ignoring some typehints because https://github.com/jd/tenacity/pull/347
        #   did not seem to actually fix this problem, as was mentioned in
        #   https://github.com/jd/tenacity/issues/230

        outcome: Future = retry_state.outcome
        exc = outcome.exception()  # type: ignore[union-attr]
        tb = exc.__traceback__  # type: ignore[union-attr]

        # NOTE: if retry_state.fn is defined, then it means that a decorator
        #   (@tenacity.retry) was used, and we should look not in the immediate
        #   __traceback__ object (which will be tenacity code), but in the
        #   next __traceback__ which will be the originally wrapped/decorated
        #   function that caught the exception

        if retry_state.fn is not None:
            tb = exc.__traceback__.tb_next  # type: ignore[union-attr]

        frame = tb.tb_frame  # type: ignore[union-attr]
        lineno = tb.tb_lineno  # type: ignore[union-attr]

        stop_strategy = retry_state.retry_object.stop
        max_attempt_str = ""
        if isinstance(stop_strategy, stop_after_attempt):
            max_attempt_str = f" of {stop_strategy.max_attempt_number}"

        message = (
            f"Retry {retry_state.attempt_number}{max_attempt_str}: "
            f"while executing {frame}, an exception occurred "
            f"at line {lineno}: {retry_state.outcome}: "
            f"{retry_state.outcome.exception()}"
        )
        logger.log(log_level, message)

    return log_attempt
