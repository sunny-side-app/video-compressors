import os

from dataclasses import dataclass

@dataclass
class File:
    _filepath: str = 'default'
    _filesize: int = 1400
    _media_type: str = '.mp3'

    # def is_mp4file(self, pathname: str) -> bool:
    #     return pathlib.Path(pathname) == '.mp4'
    
    def get_filepath(self):
        return self._filepath
    
    def get_filesize(self):
        return self._filesize
    
    def get_media_type(self):
        return self._media_type

    def set_filepath(self):
        # while True:
        filepath = input("Type in the file name or the file path: ")
        # if self.is_mp4file(filepath):
        #     print(
        #         f'Your file: {filepath} must be .mp4 file')
        #     continue
        self._filepath = filepath
        # break
        return
    
    def set_filesize(self):
        self._filesize = os.path.getsize(self.get_filepath())
        return

    def set_fileextension(self):
        filepath_tuple = os.path.splitext(self.get_filepath())
        self._media_type = filepath_tuple[1]
        return