import os
from collections import defaultdict


class FilesCounterService:

    def __init__(self, folderPath, progressCallback=None):
        self.folderPath = os.path.abspath(folderPath)
        self.progressCallback = progressCallback

    def _formatSize(self, bytesSize):
        for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
            if bytesSize < 1024:
                return f'{bytesSize:.2f} {unit}'

            bytesSize /= 1024

        return f'{bytesSize:.2f} PB'

    def _getFileType(self, fileName):
        _, extension = os.path.splitext(fileName)

        return extension.lower() if extension else 'NO_EXTENSION'

    def _scanDirectory(self):
        counts = defaultdict(int)
        sizes = defaultdict(int)

        totalFiles = 0
        totalSize = 0
        emptyFiles = 0

        largestFile = None
        largestFileSize = 0

        for dirPath, _, fileNames in os.walk(self.folderPath):
            for fileName in fileNames:
                filePath = os.path.join(dirPath, fileName)

                try:
                    fileSize = os.path.getsize(filePath)
                except OSError:
                    continue

                fileType = self._getFileType(fileName)

                counts[fileType] += 1
                sizes[fileType] += fileSize

                totalFiles += 1
                totalSize += fileSize

                if fileSize == 0:
                    emptyFiles += 1

                if fileSize > largestFileSize:
                    largestFile = filePath
                    largestFileSize = fileSize

        return {
            'counts': dict(counts),
            'sizes': dict(sizes),
            'totalFiles': totalFiles,
            'totalSize': totalSize,
            'uniqueFileTypes': len(counts),
            'emptyFiles': emptyFiles,
            'largestFile': largestFile,
            'largestFileSize': largestFileSize,
        }

    def execute(self):
        if not os.path.isdir(self.folderPath):
            raise ValueError(
                f'Folder does not exist: {self.folderPath}'
            )

        results = self._scanDirectory()

        counts = results['counts']
        sizes = results['sizes']
        totalSize = results['totalSize']

        fileTypes = []

        for fileType in counts:
            typeSize = sizes[fileType]

            fileTypes.append({
                'type': fileType,
                'count': counts[fileType],
                'size': typeSize,
                'formattedSize': self._formatSize(typeSize),
                'percentage': (
                    (typeSize / totalSize) * 100
                    if totalSize
                    else 0
                ),
            })

        fileTypes.sort(
            key=lambda item: item['size'],
            reverse=True,
        )

        results['fileTypes'] = fileTypes
        results['formattedTotalSize'] = self._formatSize(totalSize)

        if results['largestFile']:
            results['formattedLargestFileSize'] = (
                self._formatSize(
                    results['largestFileSize']
                )
            )
        else:
            results['formattedLargestFileSize'] = '0 B'

        results['averageFileSize'] = (
            totalSize / results['totalFiles']
            if results['totalFiles']
            else 0
        )

        results['formattedAverageFileSize'] = (
            self._formatSize(
                results['averageFileSize']
            )
        )

        return {
            'folderPath': self.folderPath,
            **results,
        }
