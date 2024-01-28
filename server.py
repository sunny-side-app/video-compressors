import ffmpeg
import json
import os
import socket
import threading

# from client import custom_bytes_header

class Server:
    # BUFFER_SIZE = 2 ** 30 # BUFFER_SIZEはバイトなので1GB=2^30を設定
    PACKET_SIZE = 1400
    TOTAL_SIZE = 64 + (2 ** 16) + (2 ** 47)

    def __init__(self) -> None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = '0.0.0.0'
        self.server_port = 12345
        self.socket.bind((self.server_address, self.server_port))
        self.socket.listen(10)
        self.client_ips = set()

    def start(self):

        while True:
            # clientの接続受付
            client_socket, client_address = self.socket.accept()
            # 処理中のIPアドレスリストに存在しなければ追加
            self.set_client_ip(client_address[0])
            print(f"self.client_ips(start):{self.client_ips}")

            # clientからのデータ受信受付はさらにサブスレッドで行う
            thread_server = threading.Thread(target=self.handle_video_compressor_connection, args=(client_socket, client_address), daemon=True)
            thread_server.start()
            thread_server.join()
            # 処理中のIPアドレスリストから削除
            self.delete_client_ip(client_address[0])
            print(f"self.client_ips(end):{self.client_ips}")
            print('\nwaiting for a tcpclient connection...')
        return
    def handle_video_compressor_connection(self, client_socket, client_address):
        # PACKET_SIZEに応じてデータを分割してrecv()メソッドで全データ受信完了まで繰り返し受信する
        data = bytearray()
        try:
            while True:
                print('\nwaiting for a tcpclient connection...')
                print('connection from', client_address)
                print("client_socket: ", client_socket)
                packet = client_socket.recv(Server.PACKET_SIZE)
                print(f'packet: {packet}')
                print(f'len(packet): {len(packet)}')
                # ref:https://stackoverflow.com/questions/17667903/python-socket-receive-large-amount-of-data
                if len(packet) < Server.PACKET_SIZE:
                    data.extend(packet)
                    break
                data.extend(packet)
            # except Exception as e:
            #         print(f"Error occurred: {e}")
            # else:
            header_file_json, media_type, payload = parse_mmp_packet(data=data)

            # バイナリデータをファイルで保存(ペイロードはファイルとして格納される)
            with open('payload_server' + media_type, 'wb') as f:
                f.write(payload)

            process_type = header_file_json['process_type']
            
            # 動画ファイル処理
            target_filepath = './'+'payload_server' + media_type

            if process_type == 1:
                processed_filepath = self.compress(input_filepath=target_filepath, 
                    process_type=process_type)
            elif process_type == 2:
                processed_filepath = self.update_resolution(input_filepath=target_filepath, 
                process_type=process_type, 
                process_param=header_file_json['resolution_code'])

            elif process_type == 3:
                processed_filepath = self.update_aspect_ratio(input_filepath=target_filepath, 
                process_type=process_type, 
                process_param=header_file_json['aspect_ratio_code'])

            elif process_type == 4:
                processed_filepath = self.distill_audio(input_filepath=target_filepath, 
                    process_type=process_type)
            elif process_type == 5:
                processed_filepath = self.cut_out(input_filepath=target_filepath, 
                process_type=process_type, 
                process_param=header_file_json['time_range'])
        except Exception as e:
            error_response = self.create_error_response(e)
            client_socket.sendall(error_response)

        # Client側へのレスポンス(header, bodyの作成、ファイル送信)
        # header(非エラー発生時)
        header = data[:67]
        body = data[67:]
        header_filesize =  int.from_bytes(header[:16], byteorder='big')
        header_file = body[:header_filesize]

        processed_filesize = os.path.getsize(processed_filepath)
        print(f'processed_filesize:{processed_filesize}')

        processed_filepath_tuple = os.path.splitext(processed_filepath)
        processed_media_type = processed_filepath_tuple[1]
        processed_media_type_bytes = processed_media_type.encode(encoding='utf-8')
        processed_media_typesize = len(processed_media_type_bytes)
        print(f'processed_media_typesize: {processed_media_typesize}')

        response_header = custom_bytes_header(jsonfile_size=header_filesize, mediatype_size=processed_media_typesize, payload_size=processed_filesize)
        print(f'response_header: {response_header}')

        # body
        with open(processed_filepath, 'rb') as target_f:
            payload_bytes = bytearray(target_f.read())

        # print(f'payload_bytes:{payload_bytes}')
        response_body = header_file + processed_media_type_bytes + payload_bytes
        client_socket.sendall(response_header + response_body)

        # 処理完了後にはサーバに保存されたファイルはストレージから削除
        self.delete_file(input_filepath=processed_filepath)


    def compress(self, input_filepath:str, process_type:int):
        """
        動画ファイルを圧縮する(total bitrateを下げる)
        :param input_filepath: the video you want to compress.
        :return: out_put filepath or error
        ToDO：下記を参考に動画品質と圧縮率のバランスを調整する
        https://gist.github.com/ESWZY/a420a308d3118f21274a0bc3a6feb1ff
        """

        print(f"called compress method")
        video_info = ffmpeg.probe(input_filepath)

        # video_bitrate = 7902541 # b/s
        # audio_bitrate = 177671 # b/s
        video_bitrate = float(video_info["streams"][0]["bit_rate"]) # b/s
        audio_bitrate = float(video_info["streams"][1]["bit_rate"]) # b/s
        
        output_filepath = './' + 'output_' + 'process_type=' + str(process_type) + '.mp4'

        target_video_br = 0.1 * video_bitrate
        target_audio_br = 0.1 * audio_bitrate

        i = ffmpeg.input(input_filepath)
        ffmpeg.output(i, output_filepath,
                          **{'c:v': 'libx264', 'b:v':target_video_br , 'c:a': 'aac', 'b:a': target_audio_br}
                          ).overwrite_output().run()

        return output_filepath
    
    def update_resolution(self, input_filepath: str, process_type:int, process_param:int):
        """
        選択された解像度に変換する
        process_param int: 解像度(1: 3840x2160, 2: 1920x1080, 3: 1280x720)
        """
        output_filepath = './' + 'output_' + 'process_type=' + str(process_type) + '.mp4'

        i = ffmpeg.input(input_filepath)
        if process_param == 1:
            ffmpeg.output(i, output_filepath,
                          **{'s': '3840x2160'}
                          ).overwrite_output().run()
        elif process_param == 2:
            ffmpeg.output(i, output_filepath,
                          **{'s': '1920x1080'}
                          ).overwrite_output().run()
        elif process_param == 3:
            ffmpeg.output(i, output_filepath,
                          **{'s': '1280x720'}
                          ).overwrite_output().run()
        else:
            pass

        return output_filepath


    def update_aspect_ratio(self, input_filepath: str, process_type:int, process_param:int):
        """
        選択されたアスペクト比に変換する
        process_param int: アスペクト比(1: 16:9, 2: 4:3)
        """
        output_filepath = './' + 'output_' + 'process_type=' + str(process_type) + '.mp4'

        i = ffmpeg.input(input_filepath)
        if process_param == 1:
            ffmpeg.output(i, output_filepath,
                          **{'c': 'copy', 'aspect': '16:9'}
                          ).overwrite_output().run()
        elif process_param == 2:
            ffmpeg.output(i, output_filepath,
                          **{'c': 'copy', 'aspect': '4:3'}
                          ).overwrite_output().run()
        else:
            pass

        return output_filepath

    def distill_audio(self, input_filepath:str, process_type:int):
        """
        動画から音声だけを抽出したMP3を返す
        ref:https://video.stackexchange.com/questions/17929/ffmpeg-invalid-audio-stream-exactly-one-mp3-audio-stream-is-required
        """

        output_filepath = './' + 'output_' + 'process_type=' + str(process_type) + '.mp3'

        i = ffmpeg.input(input_filepath)
        ffmpeg.output(i, output_filepath,
                        **{'c:a': 'libmp3lame'}
                        ).overwrite_output().run()

        return output_filepath

    def cut_out(self, input_filepath: str, process_type:int, process_param:tuple):
        """
        時間範囲を指定すると、その部分を切り取ってGIFまたはWEBMフォーマットに変換する
        process_param[0] int: 動画の開始時間(s)
        process_param[1] int: 動画の動画時間(s)
        """
        print(f"called cut out method")
        start_time = process_param[0]
        time_length = process_param[1]
        output_fileextension = process_param[2]

        if output_fileextension == 'GIF':
            output_filepath = './' + 'output_' + 'process_type=' + str(process_type) + '.gif'
        elif output_fileextension == 'WEBM': 
            output_filepath = './' + 'output_' + 'process_type=' + str(process_type) + '.webm'
        else:
            print('Incorrect value.')
            
        i = ffmpeg.input(input_filepath)
        ffmpeg.output(i, output_filepath,
                          **{'ss': start_time, 't': time_length}
                          ).overwrite_output().run()

        return output_filepath

    def delete_file(self, input_filepath:str):
        """
        ファイルを削除する
        """
        try:
            os.remove(input_filepath)
        except Exception as e:
            print(f"Error occurred: {e}")
            return e
        return

    def set_client_ip(self, client_ip:str):
        if client_ip not in self.client_ips:
            self.client_ips.add(client_ip)
        else:
            raise InvalidIpNumberError("処理中のIPアドレス数が不正です")
        return

    def delete_client_ip(self, client_ip:str):
        try:
            self.client_ips.remove(client_ip)
        except KeyError as e:
            raise e  
    
    def create_error_response(self, error) -> bytearray:
        """
        例外オブジェクトを受け取りエラーコード、説明、解決策を含むJSONファイルを準備
        エラーが1つでも発生したら専用のメソッドでheader,bodyを作る
        """
        print(f'error:{error}')
        header_error_filepath = './header_error_server.json'
        with open(header_error_filepath, 'w') as f:
            json.dump({'error_code':400,
                       'error_message':str(error),
                       'solution':"データ受信中または動画処理中にエラーが発生したためシステム管理者へ連絡してください\nPlease contact the system administrator because an error occurred during data reception or video processing."
                       }, f)
        header_error_filesize = os.path.getsize(header_error_filepath)
        header_error = custom_bytes_header(jsonfile_size=header_error_filesize, mediatype_size=0, payload_size=0)

        with open(header_error_filepath, 'rb') as header_f:
            header_error_bytes = bytearray(header_f.read())

        return header_error + header_error_bytes

class ServerError(Exception):
    """
    独自の例外クラス
    """
    pass

class InvalidIpNumberError(ServerError):
    """
    不正な処理中のIPアドレスの数(例:2以上)が指定されたときの例外
    """
    def __init__(self, messege: str) -> None:
        self.messege = messege

def parse_mmp_packet(data: bytearray) -> tuple:
    """
    Client-Server間でMMPでやり取りするデータを解析する
    :return: header_file_json: str, media_type: str, payload: bytearray
    """
    header = data[:67]
    body = data[67:]

    # header解析
    header_filesize =  int.from_bytes(header[:16], byteorder='big')
    print('\nheader_filesize: received {} bytes data: {}'.format(
    len(header[:16]), header_filesize))
    media_typesize =  int.from_bytes(header[16:20], byteorder='big')
    print('\nmedia_typesize: received {} bytes data: {}'.format(
    len(header[16:20]), media_typesize))
    payload_size =  int.from_bytes(header[20:], byteorder='big')
    print('\npayload_size: received {} bytes data: {}'.format(
    len(header[20:]), payload_size))

    # body解析
    header_file = body[:header_filesize]
    header_file_json = json.loads(header_file.decode('utf-8'))
    print(f'header_file:{header_file}')
    # header_file = json.loads(body[:header_filesize])
    print('header_file: received {} bytes data: {}'.format(len(body[:header_filesize]), header_file))
    media_type = body[header_filesize:header_filesize+media_typesize].decode(encoding='utf-8')
    print('media_type: received {} bytes data: {}'.format(len(body[header_filesize:header_filesize+media_typesize]), media_type))
    payload = body[header_filesize+media_typesize:]
    
    return header_file_json, media_type, payload

def custom_bytes_header(jsonfile_size: int, mediatype_size: int, payload_size: int) -> bytes:
    """
    各サイズを受け取りbytesに変換してheaderを作成する
    Client側でもServer側でも利用するため関数として定義
    """
    jsonfile_size_bytes = jsonfile_size.to_bytes(16, byteorder='big')
    print(f'json_size_bytes:{jsonfile_size_bytes}')
    mediatype_size_bytes = mediatype_size.to_bytes(4, byteorder='big')
    print(f'mediatype_size_bytes:{mediatype_size_bytes}')
    payload_size_bytes = payload_size.to_bytes(47, byteorder='big') 
    print(f'payload_size_bytes:{payload_size_bytes}')
    header_bytes = jsonfile_size_bytes + mediatype_size_bytes + payload_size_bytes
    
    return header_bytes

def main():

    # サーバーを立ち上げる
    server = Server()

    thread_server = threading.Thread(target=server.start, daemon=True)
    thread_server.start()
    thread_server.join()

if __name__ == '__main__':
    main()