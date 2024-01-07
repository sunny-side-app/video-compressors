import json
import os
import pathlib
import socket

from dataclasses import dataclass
from typing import TypedDict

class Client:
    # BUFFER_SIZE = 2 ** 30 # BUFFER_SIZEはバイトなので1GB=2^30を設定
    PACKET_SIZE = 1400
    TOTAL_SIZE = 64 + (2 ** 16) + (2 ** 47)

    def __init__(self) -> None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = '0.0.0.0'
        self.server_port = 12345
        self.file_args: FileArgs = {
            'process_type': 1,
            # 'resolution_code': 1,
            # 'aspect_ratio_code': 1,
            # 'time_range': (2,2)
        }
        

        #サーバーに接続
        try:
            self.socket.connect((self.server_address, self.server_port))
            print(f"Connected to server at {self.server_address}:{self.server_port}")
        except Exception as e:
                print(f"Error occurred: {e}")
        return

    def start(self):
        print(
            f'server address:{self.server_address}, server port:{self.server_port}')

        client_address = socket.gethostbyname(socket.gethostname())
        print(f"client_address: {client_address}")

        #self.socket.bind((client_address,0))
        client_port = self.socket.getsockname()[1]
        print(f"client_port: {client_port}")

        target_file = File()
        target_file.set_filepath()
        target_file.set_fileextension()
        target_file.set_filesize()
        target_filepath = target_file.get_filepath()
        payload_size = target_file.get_filesize()

        # 動画への処理タイプの選択
        process_type = self.select_process_type()
        self.file_args['process_type'] = process_type

        # 処理タイプに応じて、必要な引数をsetする
        self.set_file_args(process_type=process_type)
        print(f"self.file_args: {self.file_args}")

        # Headerの作成
        header_filepath = input("Type in the file name or the header file(.json file) path: ")
        with open(header_filepath, 'w') as f:
            json.dump(self.file_args, f)
        # header_file = self.file_args
        header_filesize = os.path.getsize(header_filepath)
        print(f'header_filesize:{header_filesize}')

        media_type = target_file.get_media_type()
        media_type_bytes = media_type.encode(encoding='utf-8')
        media_typesize = len(media_type_bytes)
        print(f'media_type: {media_type}')

        header = self.custom_bytes_header(jsonfile_size=header_filesize, mediatype_size=media_typesize, payload_size=payload_size)
        print(f'Header: {header}')
        # hex_string = header.hex()
        # print(f'hex_string:{hex_string}')

        with open(header_filepath, 'rb') as header_f, open(target_filepath, 'rb') as target_f:
            header_file_bytes = bytearray(header_f.read())
            print(f'header_file_bytes:{header_file_bytes}')
            payload_bytes = bytearray(target_f.read())
            # print(f'payload_bytes:{payload_bytes}')
        
        # ファイル送信(リクエスト送信)
        body = header_file_bytes + media_type_bytes + payload_bytes
        self.upload_file(header+body)
        
        # データ受信
        print('waiting to receive data from server')
        recv_data = self.socket.recv(Client.PACKET_SIZE)
        print('\n received username {!r}'.format(recv_data))

        return

    def upload_file(self, data):
        print('uploading to server...')
        # self.socket.sendfile(file, offset=0, count=None)
        self.socket.sendall(data)
        return
    
    def select_process_type(self):
        while True:
            process_type = input('行いたい動画メディア処理を選択し番号を入力してください:\n'
                         '1: 動画ファイルの圧縮\n'
                         '2: 動画の解像度の変更\n'
                         '3: 動画のアスペクト比の変更\n'
                         '4: 動画のオーディオへの変換\n'
                         '5: 時間範囲でのGIFとWEBMの作成\n')
            if process_type == "1" :
                return 1
            elif process_type == "2" :
                return 2
            elif process_type == "3" :
                return 3
            elif process_type == "4" :
                return 4
            elif process_type == "5" :
                return 5
            else:
                print('入力を受け取ることができませんでした。')
        return

    def set_file_args(self, process_type: int):
        text_for_resolution = '所望の解像度を選択してください:\n \
        1: 解像度1\n \
        2: 解像度2\n \
        3: 解像度3\n'
        text_for_aspect_ratio = '所望のアスペクト比を選択してください:\n \
        1: アスペクト比1\n \
        2: アスペクト比2\n \
        3: アスペクト比3\n'
        #ToDo:time_rangeの入力形式
        text_for_time_range = '何秒時点から何秒間動画を切り取るか、所望の時間範囲(開始時間と動画時間)をカンマ区切りで指定してください'
        text_for_default = '追加の引数は不要です'
        while True:
            if process_type == 1 :
                print(text_for_default)
                break
            elif process_type == 2 :
                resolution_code = input(text_for_resolution)
                self.file_args['resolution_code'] = resolution_code
                break
            elif process_type == 3 :
                aspect_ratio_code = input(text_for_aspect_ratio)
                self.file_args['aspect_ratio_code'] = aspect_ratio_code
                break
            elif process_type == 4 :
                print(text_for_default)
                break
            elif process_type == 5 :
                time_range = tuple(map(int, input(text_for_time_range).split(",")))
                self.file_args['time_range'] = time_range
                break
            else:
                print('入力を受け取ることができませんでした。')
        return

    def custom_bytes_header(self, jsonfile_size: int, mediatype_size: int, payload_size: int) -> bytes:
        jsonfile_size_bytes = jsonfile_size.to_bytes(16, byteorder='big')
        print(f'json_size_bytes:{jsonfile_size_bytes}')
        mediatype_size_bytes = mediatype_size.to_bytes(4, byteorder='big')
        print(f'mediatype_size_bytes:{mediatype_size_bytes}')
        payload_size_bytes = payload_size.to_bytes(47, byteorder='big') 
        print(f'payload_size_bytes:{payload_size_bytes}')
        header_bytes = jsonfile_size_bytes + mediatype_size_bytes + payload_size_bytes
        return header_bytes

class FileArgs(TypedDict, total=False):
    """
    処理によって必要になる引数を格納する
    型アノテーションを付与し静的解析をするためTypedDictを使う
    """
    process_type: int
    resolution_code: int
    aspect_ratio_code: int
    time_range: tuple

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

def main():
    client = Client()
    client.start()

if __name__ == '__main__':
    main()