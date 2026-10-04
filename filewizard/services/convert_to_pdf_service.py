import os
import queue
import multiprocessing

import pythoncom
import win32com.client


# ============================================================
# FILE TYPES
# ============================================================

WORD_FILE_TYPES = {
    'doc': '.doc',
    'docx': '.docx',
    'dot': '.dot',
    'dotx': '.dotx',
    'rtf': '.rtf',
    'odt': '.odt',
}

POWERPOINT_FILE_TYPES = {
    'ppt': '.ppt',
    'pptx': '.pptx',
    'pps': '.pps',
    'ppsx': '.ppsx',
    'pot': '.pot',
    'potx': '.potx',
    'odp': '.odp',
}

FILE_TYPES = {
    **WORD_FILE_TYPES,
    **POWERPOINT_FILE_TYPES,
}

WORD_EXTENSIONS = set(WORD_FILE_TYPES.values())
POWERPOINT_EXTENSIONS = set(POWERPOINT_FILE_TYPES.values())

# Microsoft Office PDF format constants
WORD_PDF_FORMAT = 17
POWERPOINT_PDF_FORMAT = 32

# Maximum amount of time allowed for one file.
# If Office hangs for longer than this, the worker is terminated.
DEFAULT_CONVERSION_TIMEOUT = 60


# ============================================================
# PDF PATH HELPERS
# ============================================================

def unique_pdf_path(output_path):
    """
    If output_path already exists, return a unique filename.

    Example:
        report.pdf
        report_2.pdf
        report_3.pdf
        ...
    """

    if not os.path.exists(output_path):
        return output_path

    base, extension = os.path.splitext(output_path)
    index = 2

    while True:
        candidate = f'{base}_{index}{extension}'

        if not os.path.exists(candidate):
            return candidate

        index += 1


# ============================================================
# FILE COLLECTION
# ============================================================

def collect_files(folder_path, include_subfolders, extensions):
    """
    Find all supported files in the folder.

    If include_subfolders=True, subdirectories are also searched.
    """

    files = []

    if include_subfolders:

        for root, _directories, filenames in os.walk(folder_path):

            for filename in filenames:

                # Ignore temporary Microsoft Office files.
                if filename.startswith('~$'):
                    continue

                file_extension = os.path.splitext(
                    filename
                )[1].lower()

                if file_extension not in extensions:
                    continue

                files.append(
                    os.path.join(root, filename)
                )

    else:

        for filename in os.listdir(folder_path):

            input_path = os.path.join(
                folder_path,
                filename,
            )

            if not os.path.isfile(input_path):
                continue

            # Ignore temporary Microsoft Office files.
            if filename.startswith('~$'):
                continue

            file_extension = os.path.splitext(
                filename
            )[1].lower()

            if file_extension not in extensions:
                continue

            files.append(input_path)

    files.sort()

    return files


# ============================================================
# MAIN CONVERSION FUNCTION
# ============================================================

def convert_files_to_pdf(
    folder_path,
    include_subfolders=False,
    dry_run=True,
    delete_original=False,
    overwrite_existing=False,
    file_types=None,
    progress_callback=None,
    conversion_timeout=DEFAULT_CONVERSION_TIMEOUT,
):
    """
    Convert Word and PowerPoint files to PDF.

    Parameters
    ----------
    folder_path : str
        Folder containing the files.

    include_subfolders : bool
        If True, recursively process subfolders.

    dry_run : bool
        If True, no files are actually converted.

    delete_original : bool
        If True, delete the original file after successful conversion.

    overwrite_existing : bool
        If True, overwrite an existing PDF.
        If False, create a unique PDF filename.

    file_types : list[str] | None
        Example:
            ['docx', 'doc', 'pptx']

        If None, all supported file types are processed.

    progress_callback : callable | None
        Called like:

            progress_callback(
                current,
                total,
                input_path
            )

    conversion_timeout : int | float
        Maximum number of seconds allowed for one file.

        If Word or PowerPoint gets stuck, for example on a
        password-protected document, the worker process is
        terminated after this timeout and processing continues.
    """

    folder_path = os.path.abspath(folder_path)

    # --------------------------------------------------------
    # VALIDATE FOLDER
    # --------------------------------------------------------

    if not os.path.isdir(folder_path):
        raise ValueError(
            f'Folder does not exist: {folder_path}'
        )

    # --------------------------------------------------------
    # DETERMINE FILE TYPES
    # --------------------------------------------------------

    if file_types:

        normalized_file_types = {
            str(file_type).lower().lstrip('.')
            for file_type in file_types
        }

        invalid_types = (
            normalized_file_types
            - set(FILE_TYPES.keys())
        )

        if invalid_types:
            raise ValueError(
                'Unsupported file types: '
                f'{sorted(invalid_types)}'
            )

        extensions = {
            FILE_TYPES[file_type]
            for file_type in normalized_file_types
        }

    else:

        extensions = set(FILE_TYPES.values())

    # --------------------------------------------------------
    # COLLECT FILES
    # --------------------------------------------------------

    files = collect_files(
        folder_path,
        include_subfolders,
        extensions,
    )

    # --------------------------------------------------------
    # RESULTS OBJECT
    # --------------------------------------------------------

    results = {
        'folderPath': folder_path,
        'total': len(files),
        'converted': [],
        'skipped': [],
        'failed': [],
        'deleted': [],
        'dryRun': dry_run,
    }

    # ========================================================
    # DRY RUN
    # ========================================================

    if dry_run:

        for index, input_path in enumerate(
            files,
            start=1,
        ):

            output_path = (
                os.path.splitext(input_path)[0]
                + '.pdf'
            )

            if (
                os.path.exists(output_path)
                and not overwrite_existing
            ):
                output_path = unique_pdf_path(
                    output_path
                )

            if progress_callback:

                progress_callback(
                    index,
                    len(files),
                    input_path,
                )

            results['converted'].append({
                'sourcePath': input_path,
                'outputPath': output_path,
            })

        return results

    # ========================================================
    # REAL CONVERSION
    # ========================================================

    for index, input_path in enumerate(
        files,
        start=1,
    ):

        # Notify caller of progress.
        if progress_callback:

            progress_callback(
                index,
                len(files),
                input_path,
            )

        result = _convert_one_file_with_timeout(
            input_path=input_path,
            overwrite_existing=overwrite_existing,
            conversion_timeout=conversion_timeout,
        )

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        if result['status'] == 'converted':

            output_path = result['outputPath']

            results['converted'].append({
                'sourcePath': input_path,
                'outputPath': output_path,
            })

            # Delete original only after successful
            # conversion.
            if delete_original:

                try:

                    os.remove(input_path)

                    results['deleted'].append(
                        input_path
                    )

                except Exception as exception:

                    results['failed'].append({
                        'filePath': input_path,
                        'stage': 'delete',
                        'reason': str(exception),
                    })

        # ----------------------------------------------------
        # TIMEOUT
        # ----------------------------------------------------

        elif result['status'] == 'timeout':

            results['failed'].append({
                'filePath': input_path,
                'stage': 'conversion',
                'reason': (
                    'Conversion timed out after '
                    f'{conversion_timeout} seconds. '
                    'The Office process was terminated. '
                    'The file may be password protected '
                    'or otherwise causing Office to hang.'
                ),
            })

        # ----------------------------------------------------
        # FAILURE
        # ----------------------------------------------------

        elif result['status'] == 'failed':

            results['failed'].append({
                'filePath': input_path,
                'stage': result.get(
                    'stage',
                    'conversion',
                ),
                'reason': result.get(
                    'reason',
                    'Unknown conversion error',
                ),
            })

        # ----------------------------------------------------
        # SKIPPED
        # ----------------------------------------------------

        elif result['status'] == 'skipped':

            results['skipped'].append({
                'filePath': input_path,
                'reason': result.get(
                    'reason',
                    'Skipped',
                ),
            })

    return results


# ============================================================
# CONVERT ONE FILE WITH TIMEOUT
# ============================================================

def _convert_one_file_with_timeout(
    input_path,
    overwrite_existing,
    conversion_timeout,
):
    """
    Convert a single file in a separate process.

    This is the important part of the solution.

    Word can block indefinitely when it displays a password
    dialog. A normal try/except cannot handle this because
    Documents.Open() never returns.

    By putting the Office automation in a separate process,
    the parent process can terminate it if it takes too long.
    """

    output_path = (
        os.path.splitext(input_path)[0]
        + '.pdf'
    )

    extension = os.path.splitext(
        input_path
    )[1].lower()

    # --------------------------------------------------------
    # CHECK FILE TYPE
    # --------------------------------------------------------

    if extension not in (
        WORD_EXTENSIONS
        | POWERPOINT_EXTENSIONS
    ):

        return {
            'status': 'skipped',
            'reason': (
                f'Unsupported file type: {extension}'
            ),
        }

    # --------------------------------------------------------
    # HANDLE EXISTING PDF
    # --------------------------------------------------------

    if os.path.exists(output_path):

        if overwrite_existing:

            try:

                os.remove(output_path)

            except Exception as exception:

                return {
                    'status': 'failed',
                    'stage': 'remove_existing_pdf',
                    'reason': str(exception),
                }

        else:

            output_path = unique_pdf_path(
                output_path
            )

    # --------------------------------------------------------
    # CREATE WORKER PROCESS
    # --------------------------------------------------------

    result_queue = multiprocessing.Queue()

    process = multiprocessing.Process(
        target=_conversion_worker,
        args=(
            input_path,
            output_path,
            result_queue,
        ),
    )

    process.start()

    # --------------------------------------------------------
    # WAIT FOR CONVERSION
    # --------------------------------------------------------

    process.join(conversion_timeout)

    # ========================================================
    # WORKER FINISHED
    # ========================================================

    if not process.is_alive():

        try:

            result = result_queue.get_nowait()

        except queue.Empty:

            result = {
                'status': 'failed',
                'stage': 'worker',
                'reason': (
                    'Conversion worker exited '
                    'without returning a result.'
                ),
            }

        result_queue.close()
        result_queue.join_thread()

        return result

    # ========================================================
    # WORKER TIMED OUT
    # ========================================================

    # The worker is still running.
    #
    # This means Word/PowerPoint is most likely stuck,
    # commonly because of a password dialog.
    #
    # Kill the worker so that the batch can continue.

    process.terminate()

    process.join(10)

    # If the process still refuses to exit, kill it.
    if process.is_alive():

        process.kill()
        process.join()

    result_queue.close()
    result_queue.join_thread()

    return {
        'status': 'timeout',
        'stage': 'conversion',
        'reason': (
            f'Conversion exceeded '
            f'{conversion_timeout} seconds.'
        ),
    }


# ============================================================
# OFFICE CONVERSION WORKER
# ============================================================

def _conversion_worker(
    input_path,
    output_path,
    result_queue,
):
    """
    This function runs inside a separate process.

    It creates its own Word or PowerPoint instance using
    DispatchEx().

    If Office hangs, the parent process can terminate this
    worker without blocking the entire batch.
    """

    pythoncom.CoInitialize()

    word_application = None
    powerpoint_application = None

    document = None
    presentation = None

    try:

        extension = os.path.splitext(
            input_path
        )[1].lower()

        # ====================================================
        # WORD
        # ====================================================

        if extension in WORD_EXTENSIONS:

            word_application = (
                win32com.client.DispatchEx(
                    'Word.Application'
                )
            )

            word_application.Visible = False

            word_application.DisplayAlerts = False

            # Disable macros where supported.
            try:

                word_application.AutomationSecurity = 3

            except Exception:
                pass

            # ------------------------------------------------
            # OPEN DOCUMENT
            # ------------------------------------------------
            #
            # If this document is password protected, Word may
            # display a password dialog here.
            #
            # Because this function runs in a separate process,
            # the parent process can terminate us if we hang.

            document = word_application.Documents.Open(
                FileName=input_path,
                ReadOnly=True,
                AddToRecentFiles=False,
                UpdateLinks=False,
                ConfirmConversions=False,
                PasswordDocument='',
            )

            # ------------------------------------------------
            # EXPORT PDF
            # ------------------------------------------------

            document.ExportAsFixedFormat(
                OutputFileName=output_path,
                ExportFormat=WORD_PDF_FORMAT,
            )

            # ------------------------------------------------
            # CLOSE DOCUMENT
            # ------------------------------------------------

            document.Close(False)
            document = None

        # ====================================================
        # POWERPOINT
        # ====================================================

        elif extension in POWERPOINT_EXTENSIONS:

            powerpoint_application = (
                win32com.client.DispatchEx(
                    'PowerPoint.Application'
                )
            )

            powerpoint_application.DisplayAlerts = False

            # ------------------------------------------------
            # OPEN PRESENTATION
            # ------------------------------------------------

            presentation = (
                powerpoint_application
                .Presentations.Open(
                    FileName=input_path,
                    ReadOnly=True,
                    WithWindow=False,
                )
            )

            # ------------------------------------------------
            # EXPORT PDF
            # ------------------------------------------------

            presentation.SaveAs(
                output_path,
                POWERPOINT_PDF_FORMAT,
            )

            # ------------------------------------------------
            # CLOSE PRESENTATION
            # ------------------------------------------------

            presentation.Close()
            presentation = None

        else:

            result_queue.put({
                'status': 'skipped',
                'reason': (
                    f'Unsupported file type: {extension}'
                ),
            })

            return

        # ====================================================
        # VERIFY PDF
        # ====================================================

        if not os.path.isfile(output_path):

            raise RuntimeError(
                'Office reported success, but the PDF '
                'was not created.'
            )

        # ====================================================
        # SUCCESS
        # ====================================================

        result_queue.put({
            'status': 'converted',
            'outputPath': output_path,
        })

    except Exception as exception:

        # ====================================================
        # ERROR
        # ====================================================

        result_queue.put({
            'status': 'failed',
            'stage': 'conversion',
            'reason': (
                f'{type(exception).__name__}: '
                f'{exception}'
            ),
        })

    finally:

        # ====================================================
        # CLEAN UP WORD DOCUMENT
        # ====================================================

        if document is not None:

            try:
                document.Close(False)
            except Exception:
                pass

        # ====================================================
        # CLEAN UP POWERPOINT PRESENTATION
        # ====================================================

        if presentation is not None:

            try:
                presentation.Close()
            except Exception:
                pass

        # ====================================================
        # QUIT WORD
        # ====================================================

        if word_application is not None:

            try:
                word_application.Quit()
            except Exception:
                pass

        # ====================================================
        # QUIT POWERPOINT
        # ====================================================

        if powerpoint_application is not None:

            try:
                powerpoint_application.Quit()
            except Exception:
                pass

        # ====================================================
        # UNINITIALIZE COM
        # ====================================================

        pythoncom.CoUninitialize()


# ============================================================
# WINDOWS MULTIPROCESSING ENTRY POINT
# ============================================================

if __name__ == '__main__':

    multiprocessing.freeze_support()