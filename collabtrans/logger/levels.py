# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
"""Custom log levels (e.g. TRACE below DEBUG)."""
import logging

# TRACE = 5, below DEBUG (10). Register so level name appears in logs.
TRACE = 5
logging.addLevelName(TRACE, "TRACE")
setattr(logging, "TRACE", TRACE)
