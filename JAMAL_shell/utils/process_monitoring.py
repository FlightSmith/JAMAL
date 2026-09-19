import errno
import fcntl
import logging
import os
import pty
import re
import select
import signal
import sys
import termios
import subprocess
import time
from typing import Callable, List, Optional


def monitor_process_output(
    command: List[str],
    cwd: Optional[str] = None,
    env: Optional[dict] = None,
    logging_verbosity: int = 1,
    keywords: Optional[List[str]] = None,
    inactivity_timeout: int = 3600,
    process_name: str = "process",
    cleanup_callback: Optional[Callable[[], None]] = None,
    log_level: int = logging.DEBUG,
    log_format: Optional[str] = None,
) -> int:
    """Run *command* inside a PTY, monitor its output live, and return the exit code.

    The process's stdout and stderr are combined on the PTY and written **directly**
    to ``sys.stdout`` with immediate flushing.  Carriage-return leakage is fixed by
    clearing the entire line whenever a ``\\r`` is followed by regular text (i.e.,
    a new line that will be shorter than the previous one).

    Keyword scanning is performed only on **complete lines** (after a newline),
    and any text that was overwritten by a carriage return inside that line is
    discarded.

    Args:
        command:         Command and arguments as a list.
        cwd:             Working directory for the subprocess (or ``None``).
        env:             Environment dictionary (or ``None``).
        logging_verbosity: 0-3, controls monitoring chatter.
        keywords:        List of regex patterns to trigger kill.
        inactivity_timeout: Seconds of inactivity before killing.
        process_name:    Name for logging.
        cleanup_callback: Optional callable run after kill.
        log_level:       Log level for monitoring messages.
        log_format:      ``""`` for bare ``"%(message)s"``, ``None`` for default.

    Returns:
        Exit code (positive) or negative signal number if killed.
    """
    logger = logging.getLogger("process_monitor")
    handler: Optional[logging.Handler] = None
    previous_level = logger.level
    previous_propagate = logger.propagate

    try:
        if log_format != None and False:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(log_format))
            logger.addHandler(handler)
            logger.propagate = False
            if logger.level > log_level or logger.level == logging.NOTSET:
                logger.setLevel(log_level)

        # ---------- create PTY and fork ----------
        master_fd, slave_fd = pty.openpty()
        logger.debug(f"starting process {command}")

        process = subprocess.Popen(
            command,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            env=env,
            cwd=cwd,
            text=True,
            close_fds=True,
        )

        # ---------- parent ----------
        os.close(slave_fd)

        last_output_time = time.time()
        partial_line = b""
        final_exit_code: Optional[int] = None
        cr_pending = False  # True if last byte written was \r

        def write_clever(data: bytes) -> None:
            """Write *data* to terminal, inserting ANSI clear-line where needed."""
            nonlocal cr_pending
            buf = bytearray()
            for byte in data:
                if byte == 0x0D:  # \r
                    buf.append(byte)
                    cr_pending = True
                elif byte == 0x0A:  # \n
                    buf.append(byte)
                    cr_pending = False
                else:
                    if cr_pending:
                        # We are starting a new line after a \r → clear the whole line first.
                        buf.extend(b"\x1b[2K")
                        cr_pending = False
                    buf.append(byte)
            sys.stdout.buffer.write(bytes(buf))
            sys.stdout.buffer.flush()

        def handle_chunk(data: bytes) -> Optional[int]:
            """Write data, update scan buffer, and check keywords."""
            nonlocal last_output_time, partial_line

            write_clever(data)
            last_output_time = time.time()

            partial_line += data
            lines = partial_line.split(b"\n")
            partial_line = lines[-1]

            for raw_line in lines[:-1]:
                final_text = raw_line.split(b"\r")[-1]
                line_str = final_text.decode("utf-8", errors="replace")
                if keywords is not None:
                    for pattern in keywords:
                        if re.search(pattern, line_str, re.IGNORECASE):
                            logger.warning(
                                "Regex pattern '%s' detected, terminating %s",
                                pattern,
                                process_name,
                            )
                            if cleanup_callback:
                                cleanup_callback()
                            return -1
            return None

        # ---------- main loop ----------
        while process.poll() is None:

            try:       
                readable, _, _ = select.select([master_fd], [], [], 0.1)
                if readable:
                    try:
                        data = os.read(master_fd, 4096)
                        if not data:
                            break
                        logging.info(data.decode(errors="ignore"))
                    except OSError as e:
                        if e.errno == 5:  # Input/output error - process terminated
                            break
                        raise
                    logger.debug(f"calling handle_chunck with {data}")
                    if data:
                        keyword_rc = handle_chunk(data)
                        if keyword_rc is not None:
                            final_exit_code = keyword_rc
                            break
            except BlockingIOError:
                continue

            elapsed = time.time() - last_output_time

            if logging_verbosity >= 2 and logging_verbosity < 3 and elapsed > 60:
                logger.log(log_level, "Select returned, inactive for %.1f seconds", elapsed)
            if logging_verbosity >= 3:
                logger.log(log_level, "Select returned, inactive for %.1f seconds", elapsed)

            if elapsed > inactivity_timeout:
                logger.warning("No output for %d seconds, terminating due to inactivity", inactivity_timeout)
                rc = process.kill()
                if cleanup_callback:
                    cleanup_callback()
                final_exit_code = rc
                break

        # ---------- final partial line ----------
        if partial_line:
            if cr_pending:
                # Last thing was a \r – clear the line before writing the leftover.
                sys.stdout.buffer.write(b"\x1b[2K")
            sys.stdout.buffer.write(partial_line)
            if not partial_line.endswith(b"\n"):
                sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()

        return final_exit_code if final_exit_code is not None else process.poll()

    finally:
        if handler is not None:
            logger.removeHandler(handler)
            logger.setLevel(previous_level)
            logger.propagate = previous_propagate

