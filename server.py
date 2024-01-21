import json
import socket
import threading

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

    def start(self):
        # while True:
        client_socket, client_address = self.socket.accept()
        thread_server = threading.Thread(target=self.handle_video_compressor_connection, args=(client_socket, client_address), daemon=True)
        thread_server.start()
        thread_server.join()
        return
    def handle_video_compressor_connection(self, client_socket, client_address):
    # Handle the client connection
        try:
            # BUFFER_SIZEに応じてデータを分割してrecv()メソッドで全データ受信完了まで繰り返し受信する
            data = bytearray()
            # print(f'init_data:{data}')
            # print(f'init_data len:{len(data)}')
            while True:
                print('\nwaiting for a tcpclient connection')
                print('connection from', client_address)
                print("client_socket: ", client_socket)
                client_socket.settimeout(15)
                packet = client_socket.recv(Server.PACKET_SIZE)
                print(f'packet: {packet}')
                # if not packet:
                #     break
                data.extend(packet)
                # self.process_message(data, client_socket)
                # client_socket.close()
        except Exception as e:
                print(f"Error occurred: {e}")
        finally:
            # 要件では64バイトと記載されているが、メディアタイプが1~4バイトを取りうるため拡張している
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
            print(f'header_file:{header_file}')
            # header_file = json.loads(body[:header_filesize])
            print('header_file: received {} bytes data: {}'.format(len(body[:header_filesize]), header_file))
            media_type = body[header_filesize:header_filesize+media_typesize].decode(encoding='utf-8')
            print('media_type: received {} bytes data: {}'.format(len(body[header_filesize:header_filesize+media_typesize]), media_type))
            payload = body[header_filesize+media_typesize:]
            # print('payload: received {} bytes data: {}'.format(len(body[header_filesize+media_typesize:]), payload))

            print('closing socket')
            self.socket.close()

    def compress(self):
        return
    
    def update_resolution(self):
        return

    def update_aspect_ratio(self):
        return

    def distill_audio(self):
        return

    def cut_out(self):
        return

    def delete_file(self):
        return

    def restrict_number_of_processings(self):
        return

def main():

    # サーバーを立ち上げる
    server = Server()

    thread_server = threading.Thread(target=server.start, daemon=True)

    thread_server.start()

    thread_server.join()

if __name__ == '__main__':
    main()