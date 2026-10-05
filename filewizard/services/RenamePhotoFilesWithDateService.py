import os
import random
import string
from datetime import datetime

from PIL import Image


class RenamePhotoFilesWithDateService:

    PHOTO_EXTENSIONS = {
        '.jpg',
        '.jpeg',
        '.png',
        '.tif',
        '.tiff',
        '.webp',
        '.heic',
        '.heif',
    }

    EXIF_IFD_POINTER = 34665
    DATE_TAGS = (36867, 36868, 306)
    DATE_FORMAT = '%Y:%m:%d %H:%M:%S'

    def __init__(
        self,
        folderPath,
        includeSubfolders=False,
        dryRun=True,
        progressCallback=None,
    ):
        self.folderPath = os.path.abspath(folderPath)
        self.includeSubfolders = includeSubfolders
        self.dryRun = dryRun
        self.progressCallback = progressCallback

    def execute(self):
        self._validateFolder()
        photoFiles = self._getPhotoFiles()
        renamed = []
        skipped = []
        failed = []
        occupiedNames = {}
        reservedNames = {}
        total = len(photoFiles)

        for current, filePath in enumerate(photoFiles, start=1):
            folderPath = os.path.dirname(filePath)
            fileName = os.path.basename(filePath)
            folderKey = os.path.normcase(folderPath)

            if folderKey not in occupiedNames:
                occupiedNames[folderKey] = {
                    name.casefold()
                    for name in os.listdir(folderPath)
                }
                reservedNames[folderKey] = set()

            if self.progressCallback:
                self.progressCallback(current, total, filePath)

            try:
                dateTaken = self._getDateTaken(filePath)
            except Exception as exception:
                failed.append({
                    'filePath': filePath,
                    'reason': str(exception),
                })
                continue

            if dateTaken is None:
                skipped.append({
                    'filePath': filePath,
                    'fileName': fileName,
                    'reason': 'No valid Date Taken metadata.',
                })
                continue

            newName = self._buildAvailableName(
                dateTaken,
                os.path.splitext(fileName)[1].lower(),
                occupiedNames[folderKey],
                reservedNames[folderKey],
                fileName,
            )

            if newName is None:
                failed.append({
                    'filePath': filePath,
                    'reason': (
                        'No available single-letter filename '
                        'for this date.'
                    ),
                })
                continue

            newPath = os.path.join(folderPath, newName)
            reservedNames[folderKey].add(newName.casefold())

            if newName == fileName:
                renamed.append({
                    'filePath': filePath,
                    'oldName': fileName,
                    'newName': newName,
                    'dateTaken': dateTaken,
                    'unchanged': True,
                })
                continue

            if self.dryRun:
                renamed.append({
                    'filePath': filePath,
                    'oldName': fileName,
                    'newName': newName,
                    'dateTaken': dateTaken,
                })
                continue

            try:
                if os.path.exists(newPath):
                    raise FileExistsError(
                        f'Target file already exists: {newPath}'
                    )
                os.rename(filePath, newPath)
                occupiedNames[folderKey].discard(fileName.casefold())
                occupiedNames[folderKey].add(newName.casefold())
                renamed.append({
                    'filePath': filePath,
                    'oldName': fileName,
                    'newName': newName,
                    'dateTaken': dateTaken,
                })
            except OSError as exception:
                reservedNames[folderKey].discard(newName.casefold())
                failed.append({
                    'filePath': filePath,
                    'reason': str(exception),
                })

        return {
            'folderPath': self.folderPath,
            'total': total,
            'renamed': renamed,
            'skipped': skipped,
            'failed': failed,
            'dryRun': self.dryRun,
            'includeSubfolders': self.includeSubfolders,
        }

    def _validateFolder(self):
        if not os.path.isdir(self.folderPath):
            raise ValueError(
                f'Folder does not exist: {self.folderPath}'
            )

    def _getPhotoFiles(self):
        photoFiles = []

        if self.includeSubfolders:
            folders = []

            def raiseWalkError(exception):
                raise exception

            for root, _, _ in os.walk(
                self.folderPath,
                onerror=raiseWalkError,
            ):
                folders.append(root)
        else:
            folders = [self.folderPath]

        for folderPath in folders:
            try:
                fileNames = os.listdir(folderPath)
            except OSError as exception:
                raise OSError(
                    f'Unable to read folder {folderPath}: {exception}'
                ) from exception

            for fileName in fileNames:
                filePath = os.path.join(folderPath, fileName)

                if not os.path.isfile(filePath) or os.path.islink(filePath):
                    continue

                extension = os.path.splitext(fileName)[1].lower()

                if extension in self.PHOTO_EXTENSIONS:
                    photoFiles.append(filePath)

        return sorted(photoFiles, key=str.casefold)

    def _getDateTaken(self, filePath):
        with Image.open(filePath) as image:
            exif = image.getexif()

            if not exif:
                return None

            try:
                exifIfd = exif.get_ifd(self.EXIF_IFD_POINTER)
            except (AttributeError, KeyError, TypeError, ValueError):
                exifIfd = {}

            dateTaken = self._parseDateTags(exifIfd)

            if dateTaken is not None:
                return dateTaken

            return self._parseDateTags(exif)

    def _parseDateTags(self, exif):
        for tagId in self.DATE_TAGS:
            value = exif.get(tagId)

            if not value:
                continue

            try:
                return datetime.strptime(
                    str(value).strip(),
                    self.DATE_FORMAT,
                )
            except ValueError:
                continue

        return None

    def _buildAvailableName(
        self,
        dateTaken,
        extension,
        occupiedNames,
        reservedNames,
        currentName,
    ):
        dateString = dateTaken.strftime('%Y%m%d_%H%M%S')
        currentNameKey = currentName.casefold()
        letters = list(string.ascii_uppercase)
        random.shuffle(letters)

        for letter in letters:
            newName = f'IMG_{dateString}_{letter}{extension}'
            newNameKey = newName.casefold()

            if newNameKey == currentNameKey:
                return newName

            if (
                newNameKey not in occupiedNames
                and newNameKey not in reservedNames
            ):
                return newName

        return None
