import os
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from openpyxl import Workbook
from pypdf import PdfWriter

from filewizard.services.CheckCorruptFilesService import (
    CheckCorruptFilesService,
)


class CheckCorruptFilesServiceTests(unittest.TestCase):

    def setUp(self):
        self.temporaryDirectory = tempfile.TemporaryDirectory()
        self.folderPath = self.temporaryDirectory.name

    def tearDown(self):
        self.temporaryDirectory.cleanup()

    def _writeValidPdf(self, filePath):
        os.makedirs(os.path.dirname(filePath), exist_ok=True)
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)

        with open(filePath, 'wb') as pdfFile:
            writer.write(pdfFile)

    def _writeCorruptPdf(self, filePath):
        os.makedirs(os.path.dirname(filePath), exist_ok=True)

        with open(filePath, 'wb') as pdfFile:
            pdfFile.write(b'%PDF-1.4\nthis is not a valid PDF')

    def _writeDocx(self, filePath, documentXml=None):
        os.makedirs(os.path.dirname(filePath), exist_ok=True)
        with zipfile.ZipFile(filePath, 'w') as archive:
            archive.writestr(
                '[Content_Types].xml',
                '<Types xmlns="http://schemas.openxmlformats.org/'
                'package/2006/content-types"></Types>',
            )
            archive.writestr(
                'word/document.xml',
                documentXml or (
                    '<w:document xmlns:w="http://schemas.openxmlformats.org/'
                    'wordprocessingml/2006/main"><w:body/></w:document>'
                ),
            )

    def _writeXlsx(self, filePath):
        os.makedirs(os.path.dirname(filePath), exist_ok=True)
        workbook = Workbook()
        workbook.active['A1'] = 'valid'
        workbook.save(filePath)

    def _writeOoxmlPackage(self, filePath, mainPart):
        os.makedirs(os.path.dirname(filePath), exist_ok=True)
        with zipfile.ZipFile(filePath, 'w') as archive:
            archive.writestr(
                '[Content_Types].xml',
                '<Types xmlns="http://schemas.openxmlformats.org/'
                'package/2006/content-types"></Types>',
            )
            archive.writestr(mainPart, '<root/>')

    def test_dry_run_reports_corrupt_pdf_without_moving_it(self):
        corruptPdf = os.path.join(self.folderPath, 'damaged.pdf')
        self._writeCorruptPdf(corruptPdf)
        with open(os.path.join(self.folderPath, 'notes.txt'), 'w') as textFile:
            textFile.write('Not a PDF')

        results = CheckCorruptFilesService(
            self.folderPath,
            dryRun=True,
            fileExtensions=['.pdf'],
        ).execute()

        self.assertEqual(len(results['corrupt']), 1)
        self.assertEqual(
            results['corrupt'][0]['filePath'],
            corruptPdf,
        )
        self.assertEqual(
            results['corrupt'][0]['destination'],
            os.path.join(self.folderPath, 'corrupt', 'damaged.pdf'),
        )
        self.assertTrue(os.path.exists(corruptPdf))
        self.assertFalse(
            os.path.exists(os.path.join(self.folderPath, 'corrupt'))
        )
        self.assertEqual(results['total'], 1)

    def test_recursive_scan_moves_only_corrupt_pdfs_and_preserves_paths(self):
        damagedPdf = os.path.join(
            self.folderPath,
            'nested',
            'document.pdf',
        )
        validPdf = os.path.join(
            self.folderPath,
            'nested',
            'valid.pdf',
        )
        existingDestination = os.path.join(
            self.folderPath,
            'corrupt',
            'nested',
            'document.pdf',
        )
        self._writeCorruptPdf(damagedPdf)
        self._writeValidPdf(validPdf)
        os.makedirs(os.path.dirname(existingDestination), exist_ok=True)
        with open(existingDestination, 'wb') as existingFile:
            existingFile.write(b'already here')

        results = CheckCorruptFilesService(
            self.folderPath,
            includeSubfolders=True,
            dryRun=False,
        ).execute()

        movedPdf = os.path.join(
            self.folderPath,
            'corrupt',
            'nested',
            'document_1.pdf',
        )
        self.assertFalse(os.path.exists(damagedPdf))
        self.assertTrue(os.path.exists(validPdf))
        self.assertTrue(os.path.exists(movedPdf))
        self.assertEqual(len(results['corrupt']), 1)
        self.assertEqual(results['corrupt'][0]['destination'], movedPdf)
        self.assertEqual(results['checked'], [validPdf])

    def test_non_recursive_scan_leaves_nested_pdf_untouched(self):
        rootPdf = os.path.join(self.folderPath, 'root.pdf')
        nestedPdf = os.path.join(
            self.folderPath,
            'nested',
            'nested.pdf',
        )
        self._writeCorruptPdf(rootPdf)
        self._writeCorruptPdf(nestedPdf)

        results = CheckCorruptFilesService(
            self.folderPath,
            includeSubfolders=False,
            dryRun=False,
        ).execute()

        self.assertEqual(len(results['corrupt']), 1)
        self.assertFalse(os.path.exists(rootPdf))
        self.assertTrue(os.path.exists(nestedPdf))

    def test_encrypted_pdf_is_skipped_without_moving(self):
        encryptedPdf = os.path.join(self.folderPath, 'encrypted.pdf')
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        writer.encrypt('password')
        with open(encryptedPdf, 'wb') as pdfFile:
            writer.write(pdfFile)

        results = CheckCorruptFilesService(
            self.folderPath,
            dryRun=False,
        ).execute()

        self.assertEqual(len(results['skipped']), 1)
        self.assertTrue(os.path.exists(encryptedPdf))
        self.assertEqual(results['corrupt'], [])

    def test_corrupt_docx_is_detected_and_moved(self):
        corruptDocx = os.path.join(self.folderPath, 'damaged.docx')
        self._writeDocx(corruptDocx, '<w:document>')

        results = CheckCorruptFilesService(
            self.folderPath,
            dryRun=False,
            fileExtensions=['.docx'],
        ).execute()

        destination = os.path.join(
            self.folderPath,
            'corrupt',
            'damaged.docx',
        )
        self.assertFalse(os.path.exists(corruptDocx))
        self.assertTrue(os.path.exists(destination))
        self.assertEqual(results['corrupt'][0]['extension'], '.docx')

    def test_valid_docx_is_checked_and_pdf_can_be_excluded(self):
        validDocx = os.path.join(self.folderPath, 'valid.docx')
        self._writeDocx(validDocx)
        self._writeCorruptPdf(
            os.path.join(self.folderPath, 'damaged.pdf')
        )

        results = CheckCorruptFilesService(
            self.folderPath,
            fileExtensions=['docx'],
        ).execute()

        self.assertEqual(results['total'], 1)
        self.assertEqual(results['checked'], [validDocx])
        self.assertEqual(results['corrupt'], [])
        self.assertEqual(results['fileExtensions'], ('.docx',))

    def test_recursive_scan_checks_and_moves_docx(self):
        corruptDocx = os.path.join(
            self.folderPath,
            'nested',
            'damaged.docx',
        )
        self._writeDocx(corruptDocx, '<w:document>')

        results = CheckCorruptFilesService(
            self.folderPath,
            includeSubfolders=True,
            dryRun=False,
            fileExtensions=['.pdf', '.docx'],
        ).execute()

        destination = os.path.join(
            self.folderPath,
            'corrupt',
            'nested',
            'damaged.docx',
        )
        self.assertFalse(os.path.exists(corruptDocx))
        self.assertTrue(os.path.exists(destination))
        self.assertEqual(results['total'], 1)
        self.assertEqual(len(results['corrupt']), 1)

    def test_invalid_docx_zip_is_corrupt(self):
        invalidDocx = os.path.join(self.folderPath, 'invalid.docx')
        with open(invalidDocx, 'wb') as document:
            document.write(b'not a zip archive')

        results = CheckCorruptFilesService(
            self.folderPath,
            fileExtensions=['.docx'],
        ).execute()

        self.assertEqual(len(results['corrupt']), 1)
        self.assertIn('zip', results['corrupt'][0]['reason'].lower())

    def test_no_selected_extensions_is_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            'Select at least one file type',
        ):
            CheckCorruptFilesService(
                self.folderPath,
                fileExtensions=[],
            )

    def test_validator_registry_covers_all_ui_extensions(self):
        self.assertEqual(
            set(CheckCorruptFilesService.SUPPORTED_EXTENSIONS),
            set(CheckCorruptFilesService.EXTENSION_VALIDATORS),
        )

    def test_valid_and_corrupt_xlsx_are_detected(self):
        validXlsx = os.path.join(self.folderPath, 'valid.xlsx')
        corruptXlsx = os.path.join(self.folderPath, 'broken.xlsx')
        self._writeXlsx(validXlsx)
        with open(corruptXlsx, 'wb') as brokenFile:
            brokenFile.write(b'not an Excel workbook')

        results = CheckCorruptFilesService(
            self.folderPath,
            fileExtensions=['.xlsx'],
        ).execute()

        self.assertEqual(results['checked'], [validXlsx])
        self.assertEqual(
            [item['filePath'] for item in results['corrupt']],
            [corruptXlsx],
        )

    def test_corrupt_powerpoint_package_is_detected(self):
        corruptPptx = os.path.join(self.folderPath, 'broken.pptx')
        self._writeOoxmlPackage(
            corruptPptx,
            'ppt/presentation.xml',
        )

        results = CheckCorruptFilesService(
            self.folderPath,
            fileExtensions=['pptx'],
        ).execute()

        self.assertEqual(len(results['corrupt']), 1)
        self.assertEqual(results['corrupt'][0]['extension'], '.pptx')

    def test_invalid_text_encoding_is_corrupt(self):
        invalidText = os.path.join(self.folderPath, 'broken.txt')
        with open(invalidText, 'wb') as textFile:
            textFile.write(b'\x81')

        results = CheckCorruptFilesService(
            self.folderPath,
            fileExtensions=['txt'],
        ).execute()

        self.assertEqual(len(results['corrupt']), 1)
        self.assertEqual(results['corrupt'][0]['extension'], '.txt')

    def test_utf16_text_file_is_checked_without_bom_decoder_error(self):
        utf16Text = os.path.join(self.folderPath, 'utf16.txt')
        with open(utf16Text, 'wb') as textFile:
            textFile.write('Valid UTF-16 text'.encode('utf-16-le'))

        results = CheckCorruptFilesService(
            self.folderPath,
            fileExtensions=['txt'],
        ).execute()

        self.assertEqual(results['checked'], [utf16Text])
        self.assertEqual(results['failed'], [])

    def test_unexpected_validation_error_identifies_file_and_continues(self):
        badFile = os.path.join(self.folderPath, 'bad.txt')
        goodFile = os.path.join(self.folderPath, 'good.txt')
        with open(badFile, 'w', encoding='utf-8') as textFile:
            textFile.write('bad')
        with open(goodFile, 'w', encoding='utf-8') as textFile:
            textFile.write('good')

        service = CheckCorruptFilesService(
            self.folderPath,
            fileExtensions=['txt'],
        )
        validateFile = service._validateFile

        def failOneFile(filePath):
            if filePath == badFile:
                raise UnicodeError('UTF-16 stream does not start with BOM')
            return validateFile(filePath)

        with patch.object(service, '_validateFile', side_effect=failOneFile):
            results = service.execute()

        self.assertEqual(results['checked'], [goodFile])
        self.assertEqual(len(results['failed']), 1)
        failure = results['failed'][0]
        self.assertEqual(failure['filePath'], badFile)
        self.assertEqual(failure['errorType'], 'UnicodeError')
        self.assertIn('UTF-16 stream does not start with BOM', failure['reason'])
        self.assertIn('UnicodeError', failure['traceback'])

    def test_corrupt_legacy_word_container_is_detected(self):
        corruptDoc = os.path.join(self.folderPath, 'broken.doc')
        with open(corruptDoc, 'wb') as document:
            document.write(bytes.fromhex('D0CF11E0A1B11AE1'))

        results = CheckCorruptFilesService(
            self.folderPath,
            fileExtensions=['doc'],
        ).execute()

        self.assertEqual(len(results['corrupt']), 1)
        self.assertEqual(results['corrupt'][0]['extension'], '.doc')

    def test_csv_and_tsv_are_checked_as_text_files(self):
        csvFile = os.path.join(self.folderPath, 'data.csv')
        tsvFile = os.path.join(self.folderPath, 'data.tsv')
        with open(csvFile, 'w', encoding='utf-8') as textFile:
            textFile.write('name,value\nsample,1\n')
        with open(tsvFile, 'w', encoding='utf-8') as textFile:
            textFile.write('name\tvalue\nsample\t1\n')

        results = CheckCorruptFilesService(
            self.folderPath,
            fileExtensions=['csv', 'tsv'],
        ).execute()

        self.assertEqual(results['checked'], [csvFile, tsvFile])
        self.assertEqual(results['corrupt'], [])


if __name__ == '__main__':
    unittest.main()
