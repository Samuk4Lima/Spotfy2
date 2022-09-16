import socket
import json
import os
from datetime import datetime as dt
import copy
import time

def writeOnJson(location, info):
    with open(location, 'w') as f:
        json.dump(info, f)
        f.close()
# Checando se existe um arquivo que guarda as informações
# dos usuários, caso não tenha, é criado um novo
if not os.path.exists('data/users.json'):
    writeOnJson('data/users.json', {})
user_list = json.load(open('data/users.json'))

# O dicionário que vai armazenar todas os arquivos de
# Imagem, HTML e CSS do projeto de maneira ordenada
website_dict = {}

# Lista bruta com todos os arquivos que serão adicionados
# Ao servidor, daqui eles serão transformados para dict
allFiles = []

def getAllFiles(dir):
    for file in os.listdir(dir):
        # Checa se o arquivo é uma pasta para poder iterar
        # Caso seja uma pasta ele pode ser iterado, e se
        # For um arquivo será adicionado
        if not file.find('.') >= 0:
            getAllFiles(f'{dir}/{file}')
        else:
            allFiles.append(f'{dir}/{file}')
abs_path = os.getcwd()
getAllFiles(abs_path)

def adjustHTMLResponseSize(original_response, new_response):
    i = original_response.find(b'\r\nContent-Length') + 18
    f = original_response.find(b'\r\n\r\n')
    original_length = str.encode(str(len(original_response[original_response.find(b'\r\n\r\n')+4:])))
    new_length = str.encode(str(len(new_response[new_response.find(b'\r\n\r\n')+4:])))
    return new_response.replace(original_length, new_length)

# Músicas que podem ser tocadas
song_locations = []

for file in allFiles:
    file = str(file[len(abs_path)+1:])
    format = file[file.rfind('.')+1:]
    # Imagem
    if format in ['jpg','jpeg','png','ico','svg']:
        data = open(file, 'rb').read()
        if format != 'svg':
            format = f'image/{format}'
        else:
            format = 'image/svg+xml'
        resp = f'HTTP/1.1 200 OK\r\nContent-Type: {format}\r\nContent-Length: {len(data)}\r\n\r\n'
        website_dict[file] = str.encode(resp) + data
    # Áudio
    elif format in ['wav','mp3','ogg']:
        data = open(file, 'rb').read()
        format = f'audio/{format}'
        # Accept-Ranges permite voltar ou adiantar
        # O áudio que está tocando
        l = len(data)
        resp = f'HTTP/1.1 200 OK\r\nContent-Type: {format}\r\nAccept-Ranges: bytes\r\nContent-Length: {l}\r\nContent-Range: bytes 0-{l-1}/{l}\r\n\r\n'
        website_dict[file] = str.encode(resp) + data
        song_locations.append(file[11:])
    # CSS
    elif format in ['css']:
        data = open(file, 'r').read()
        resp = f'HTTP/1.1 200 OK\r\nContent-Type: text/css\r\nContent-Length: {len(data)}\r\n\r\n'
        website_dict[file] = str.encode(resp + data)
    # Javascript
    elif format in ['js']:
        data = open(file, 'r').read()
        
        if file.find('index_script.js'):
            # Adicionando as músicas no código do index
            # Música - Banda
            song_names = [s[s.rfind('/')+1:s.rfind('.')] + ' - ' + s[:s.find('/')] for s in song_locations]
            str_locations = f'var song_locations = {song_locations}'
            str_names = f'var song_names = {song_names}'
            data = data.replace('var song_locations = []', str_locations)
            data = data.replace('var song_names = []', str_names)
            # Adicionando as principais playlists (álbums) no código do index
            album_dict = {}
            for i, s in enumerate(song_locations):
                # Álbum - Banda
                title = s[s.find('/')+1:]
                title = title[:title.find('/')] + ' - ' + s[:s.find('/')]
                album_dict[title] = album_dict[title] + [song_names[i]] if title in album_dict.keys() else [song_names[i]]
            album_array = []
            for album in album_dict.keys():
                album_array += [f'[\'{album}\', ' + str(album_dict[album])[1:-1] + ']']
            album_array = 'var standard_playlists = ' + str(album_array).replace('"','')
            data = data.replace('var standard_playlists = []', album_array)
        resp = f'HTTP/1.1 200 OK\r\nContent-Type: text/javascript\r\nContent-Length: {len(data)}\r\n\r\n'
        website_dict[file] = (resp + data).encode('latin1')

for file in allFiles:
    file = str(file[len(abs_path)+1:])
    format = file[file.rfind('.')+1:]
    # HTML
    if format in ['html']:
        data = open(file, 'r').read()
        filename_list = [
            file[file.rfind('/')+1:-5], # Sem .html no final
            file[file.rfind('/')+1:],   # Com .html no final
            file,                       # Nome no endereço
        ]
        # Outras nomeclaturas para index
        if file.find('index.html') >= 0:
            filename_list += ['']

        resp = f'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {len(data)}\r\n\r\n'
        for name in filename_list:
            website_dict[name] = (resp + data).encode('latin1')

online_users = []

try:
    welcome_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    welcome_socket.bind(('', 8080))
    welcome_socket.listen(5)
    print('Server online')

    while True:
        web_socket, _ = welcome_socket.accept()
        data = web_socket.recv(2000).split(b' ')
        if data[0] == b'GET':
            t1 = time.time()
            client_IP = web_socket.getpeername()[0]
            request = data[1].decode('utf-8')[1:]
            request = request.replace('%7B', '{').replace('%7D', '}').replace('%20', ' ')
            successful = False

            # Requests padrões já armazenadas no website_dict
            #################################################
            # Alternativas caso os arquivos de mesmo caminho não sejam encontrados
            path_matches = list(filter(lambda filename : filename.endswith(request) and request.find('.') > 0, website_dict.keys()))
            path_matches += list(filter(lambda filename : request.endswith(filename) and request.find('.') > 0, website_dict.keys()))
            #################################################

            # Logar
            if request.find('login_u{') == 0 and request.find('}p{') > 0:
                username = request[request.index('u{')+2:request.index('}p')]
                password = request[request.index('p{')+2:request.rfind('}')]
                
                # A conta já está logada
                if username in online_users:
                    response = b'already_logged'

                # O usuário pode iniciar a conexão
                elif username in user_list.keys() and user_list[username]['password'] == password:
                    online_users.append(username)
                    user_list[username]['last IP'] = client_IP
                    user_list[username]['last access'] = dt.now().isoformat()
                    writeOnJson('data/users.json', user_list)
                    response = b'welcome'

                # Senha incorreta
                elif username in user_list.keys():
                    response = b'wrong_pass'

                # Esta conta não existe
                else:
                    response = b'non_existent'

                # Resposta
                resp = f'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: {len(response)}\r\n\r\n'
                web_socket.sendall(str.encode(resp) + response)
                successful = True
            
            # Criar conta
            elif request.find('signup_u{') == 0 and request.find('}p{') > 0:
                username = request[request.index('u{')+2:request.index('}p')]
                password = request[request.index('p{')+2:request.rfind('}')]
                
                # Esta conta já existe
                if username in online_users or username in user_list.keys():
                    response = b'already_exists'
                
                # Cria uma nova conta, atualiza o .json e mantém online
                else:
                    user_list[username] = {
                        'password': password,
                        'last IP': client_IP,
                        'last access': dt.now().isoformat(),
                        'liked songs': [],
                        'playlists': {}
                    }
                    writeOnJson('data/users.json', user_list)
                    online_users.append(username)
                    response = b'welcome'
                
                # Resposta
                resp = f'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: {len(response)}\r\n\r\n'
                web_socket.sendall(str.encode(resp) + response)
                successful = True
            
            elif request == 'isCommunicating':
                web_socket.sendall(b'HTTP/1.1 200 OK\r\n\r\n')
            
            # Checks if there is an active user on this address
            elif request == 'amILogged':
                response = b'NO'
                for user in online_users:
                    if user_list[user]['last IP'] == client_IP:
                        response = str.encode(user)
                        break
                resp = f'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: {len(response)}\r\n\r\n'
                web_socket.sendall(str.encode(resp) + response)

            # Sair da conta logada
            elif request.find('logout_u{') == 0 and request.find('}') > 0:
                username = request[request.index('{')+1:request.index('}')]
                if username in online_users:
                    online_users.remove(username)
                    user_list[username]['last access'] = dt.now().isoformat()
                    writeOnJson('data/users.json', user_list)
                web_socket.sendall(b'HTTP/1.1 200 OK\r\n\r\n')
                successful = True

            # Curtir música
            elif request.find('like_u{') == 0 and request.find('}s{') > 0:
                username = request[request.index('u{')+2:request.index('}s')]
                song = request[request.index('s{')+2:request.rfind('}')]
                if username in online_users:
                    user_list[username]['liked songs'] = list(dict.fromkeys(user_list[username]['liked songs'] + [song]))
                    writeOnJson('data/users.json', user_list)
                web_socket.sendall(b'HTTP/1.1 200 OK\r\n\r\n')
            
            # Descurtir música
            elif request.find('dislike_u{') == 0 and request.find('}s{') > 0:
                username = request[request.index('u{')+2:request.index('}s')]
                song = request[request.index('s{')+2:request.rfind('}')]
                if username in online_users:
                    if song in user_list[username]['liked songs']:
                        user_list[username]['liked songs'].remove(song)
                        writeOnJson('data/users.json', user_list)
                web_socket.sendall(b'HTTP/1.1 200 OK\r\n\r\n')
            
            # Recuperar músicas curtidas
            elif request.find('liked_u{') == 0:
                username = request[request.index('u{')+2:request.index('}')]
                data = str.encode(str(user_list[username]['liked songs'])[1:-1].replace('\'','').replace(', ', ','))
                resp = f'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: {len(data)}\r\n\r\n'
                web_socket.sendall(str.encode(resp) + data)
            
            # Adicionar playlist

            # Remover playlist

            # Recuperar playlists

            # Tenta achar o arquivo de mesmo nome e endereço
            elif request in website_dict.keys():
                web_socket.sendall(website_dict[request])
                successful = True
            
            # Se não encontrar ele busca em outras correspondências com o mesmo caminho
            elif len(path_matches) > 0:
                matched_request = path_matches[0]
                web_socket.sendall(website_dict[matched_request])
                successful = True
            
            # Arquivo não foi encontrado
            else:
                web_socket.sendall(b'HTTP/1.1 404 File not found\r\n\r\n')

            if successful:
                print(f'{client_IP} connected to /{request} successfully ({(time.time() - t1):.4f}s)')

except KeyboardInterrupt:
    print(" terminado pelo usuario")
    web_socket.close()
    welcome_socket.close()
