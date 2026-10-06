import os
import tempfile
import unittest
from unittest.mock import patch

from filewizard.services import ConvertOfficeFilesToPdfService as conversionModule
from filewizard.services.ConvertOfficeFilesToPdfService import (
    ConvertToPdfService,
    _conversionWorker,
)


class ConvertOfficeFilesToPdfServiceTests(unittest.TestCase):

    def setUp(self):
        self.temporaryDirectory = tempfile.TemporaryDirectory()
        self.folderPath = self.temporaryDirectory.name

    def tearDown(self):
        self.temporaryDirectory.cleanup()

    def test_dry_run_includes_selected_spreadsheet_files(self):
        spreadsheetPath = os.path.join(
            self.folderPath,
            'budget.xlsx',
        )
        with open(spreadsheetPath, 'wb') as spreadsheetFile:
            spreadsheetFile.write(b'workbook')

        results = ConvertToPdfService(
            self.folderPath,
            dryRun=True,
            fileTypes=['XLSX'],
        ).execute()

        self.assertEqual(results['total'], 1)
        self.assertEqual(
            results['converted'],
            [{
                'sourcePath': spreadsheetPath,
                'outputPath': os.path.join(
                    self.folderPath,
                    'budget.pdf',
                ),
            }],
        )
        self.assertEqual(
            ConvertToPdfService.EXCEL_EXTENSIONS,
            {
                '.xls',
                '.xlsx',
                '.xlsm',
                '.xlsb',
                '.xlt',
                '.xltx',
                '.xltm',
                '.ods',
                '.csv',
            },
        )

    def test_worker_exports_excel_workbook_as_pdf(self):
        inputPath = os.path.join(
            self.folderPath,
            'budget.xlsx',
        )
        outputPath = os.path.join(
            self.folderPath,
            'budget.pdf',
        )
        with open(inputPath, 'wb') as spreadsheetFile:
            spreadsheetFile.write(b'workbook')

        calls = {}

        class FakeWorkbook:
            def ExportAsFixedFormat(self, fileType, destination):
                calls['export'] = (fileType, destination)
                with open(destination, 'wb') as pdfFile:
                    pdfFile.write(b'%PDF-1.4')

            def Close(self, saveChanges):
                calls['workbookClosed'] = saveChanges

        class FakeWorkbooks:
            def Open(self, path, **options):
                calls['open'] = (path, options)
                return FakeWorkbook()

        class FakeExcelApplication:
            def __init__(self):
                self.Workbooks = FakeWorkbooks()

            def Quit(self):
                calls['excelQuit'] = True

        class FakeResultQueue:
            def put(self, result):
                calls['result'] = result

        application = FakeExcelApplication()
        with patch.object(
            conversionModule.pythoncom,
            'CoInitialize',
        ), patch.object(
            conversionModule.pythoncom,
            'CoUninitialize',
        ), patch.object(
            conversionModule.win32com.client,
            'DispatchEx',
            return_value=application,
        ) as dispatch:
            _conversionWorker(
                inputPath,
                outputPath,
                FakeResultQueue(),
            )

        dispatch.assert_called_once_with('Excel.Application')
        self.assertEqual(
            calls['open'],
            (
                inputPath,
                {
                    'UpdateLinks': 0,
                    'ReadOnly': True,
                    'IgnoreReadOnlyRecommended': True,
                    'AddToMru': False,
                },
            ),
        )
        self.assertEqual(
            calls['export'],
            (ConvertToPdfService.EXCEL_PDF_FORMAT, outputPath),
        )
        self.assertEqual(calls['workbookClosed'], False)
        self.assertTrue(calls['excelQuit'])
        self.assertEqual(calls['result']['status'], 'converted')
        self.assertTrue(os.path.isfile(outputPath))


if __name__ == '__main__':
    unittest.main()
