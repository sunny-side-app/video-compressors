import json
import os
import pathlib
import socket

from file import File
# from server import custom_bytes_header
from server import custom_bytes_header, parse_mmp_packet

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
            # 'time_range': (2,2, GIF)
        }
        return

    def start(self):
        try:
            self.socket.connect((self.server_address, self.server_port))
            print(f"Connected to server at {self.server_address}:{self.server_port}")
        except Exception as e:
            print(f"Error occurred: {e}")
            raise
        print(
            f'server address:{self.server_address}, server port:{self.server_port}')
        # ローカルIPアドレス(プライベートIPアドレス)を取得
        client_address = socket.gethostbyname(socket.gethostname())
        print(f"client_address: {client_address}")

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

        # headerの作成
        header_filepath = input("Type in the the header .json file path(empty file is OK): ")
        with open(header_filepath, 'w') as f:
            json.dump(self.file_args, f)

        header_filesize = os.path.getsize(header_filepath)
        print(f'header_filesize:{header_filesize}')

        media_type = target_file.get_media_type()
        media_type_bytes = media_type.encode(encoding='utf-8')
        media_typesize = len(media_type_bytes)
        print(f'media_type: {media_type}')

        header = custom_bytes_header(jsonfile_size=header_filesize, mediatype_size=media_typesize, payload_size=payload_size)
        print(f'header: {header}')
        
        # bodyの作成
        with open(header_filepath, 'rb') as header_f, open(target_filepath, 'rb') as target_f:
            header_file_bytes = bytearray(header_f.read())
            print(f'header_file_bytes:{header_file_bytes}')
            payload_bytes = bytearray(target_f.read())
            # print(f'payload_bytes:{payload_bytes}')
        
        # ファイル送信(リクエスト送信)
        body = header_file_bytes + media_type_bytes + payload_bytes
        self.upload_file(header+body)

        # データ受信
        try:
            recv_data = bytearray()
            while True:
                print('waiting to receive data from server...')
                packet = self.socket.recv(Client.PACKET_SIZE)
                print(f'packet: {packet}')
                print(f'len(packet): {len(packet)}')
                # ref:https://stackoverflow.com/questions/17667903/python-socket-receive-large-amount-of-data
                if len(packet) < Client.PACKET_SIZE:
                    recv_data.extend(packet)
                    break
                recv_data.extend(packet)
        except Exception as e:
            print(f"Error occurred: {e}")
            return e
        else:
            print('\n received data: {!r}'.format(recv_data))

            # 受信したデータの解析
            recv_header_file, recv_media_type, recv_payload = parse_mmp_packet(recv_data)
            try:
                recv_process_type = recv_header_file['process_type']
                # 受信したファイルをClient側で保存
                processed_filepath = 'processed_file_' + 'process_type=' + str(recv_process_type)+recv_media_type
                with open(processed_filepath, 'wb') as f:
                    f.write(recv_payload)
            # When error occurred
            except KeyError:
                print(f"error_code:{recv_header_file['error_code']}")
                print(f"error_message:{recv_header_file['error_message']}")
                print(f"solution:{recv_header_file['solution']}")

        return 

    def upload_file(self, data):
        print('uploading to server...')
        self.socket.sendall(data)
        return
    
    def select_process_type(self):
        while True:
            process_type = input('Select the video processing you wish to perform and enter the number:\n'
                '1: compression of video files\n'
                '2: updates resolution of video files\n'
                '3: updates aspect ratio of video files\n'
                '4: converting video files to audio files\n'
                '5: creation of GIFs and WEBMs in a time range\n')
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
                print('Input could not be properly processed, please enter one of 1~5.')
        return

    def set_file_args(self, process_type: int):
        text_for_resolution = 'Please select the desired resolution:\n \
        1: 3840x2160 \n \
        2: 1920x1080 \n \
        3: 1280x720 \n'
        text_for_aspect_ratio = 'Please select the desired aspect ratio:\n \
        1: 16:9 \n \
        2: 4:3 \n'
        #ToDo:time_rangeの入力形式
        text_for_time_range = 'Specify the desired time range (start time and movie time) and output format (GIF, WEBM), separated by commas, from what point in time and for how many seconds to clip the movie.(Ex:2,2, GIF)\n'
        text_for_default = 'No additional arguments are neeeded'

        while True:
            try:
                if process_type == 1 :
                    print(text_for_default)
                    break
                elif process_type == 2 :
                    resolution_code = input(text_for_resolution)
                    self.file_args['resolution_code'] = int(resolution_code)
                    break
                elif process_type == 3 :
                    aspect_ratio_code = input(text_for_aspect_ratio)
                    self.file_args['aspect_ratio_code'] = int(aspect_ratio_code)
                    break
                elif process_type == 4 :
                    print(text_for_default)
                    break
                elif process_type == 5 :
                    time_range = tuple(input(text_for_time_range).split(","))
                    self.file_args['time_range'] = (int(time_range[0]), int(time_range[1]), time_range[2])
                    break
                else:
                    print('Input could not be properly processed.')
            except ValueError as e:
                print(f'Input could not be properly processed：{e}')
                # raise
        return

class FileArgs(TypedDict, total=False):
    """
    処理によって必要になる引数を格納する
    型アノテーションを付与し静的解析をするためTypedDictを使う
    """
    process_type: int
    resolution_code: int
    aspect_ratio_code: int
    time_range: tuple

def main():
    # while True:
    client = Client()
    client.start()

if __name__ == '__main__':
    main()