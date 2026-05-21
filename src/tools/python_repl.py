# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import os
from typing import Annotated, Optional

from langchain_core.tools import tool
# from langchain_experimental.utilities import PythonREPL  # removed: langchain-experimental 已移除

from .decorators import log_io

logger = logging.getLogger(__name__)


def _is_python_repl_enabled() -> bool:
    """Check if Python REPL tool is enabled from configuration."""
    # Python REPL is disabled because langchain-experimental has been removed.
    return False


@tool
@log_io
def python_repl_tool(
    code: Annotated[
        str, "The python code to execute to do further analysis or calculation."
    ],
):
    """Use this to execute python code and do data analysis or calculation. If you want to see the output of a value,
    you should print it out with `print(...)`. This is visible to the user."""
    error_msg = "Python REPL tool is disabled. langchain-experimental has been removed."
    logger.warning(error_msg)
    return f"Tool disabled: {error_msg}"
