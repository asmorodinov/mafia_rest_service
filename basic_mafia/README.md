# basic_mafia_application

Пример запуска сервера в докере (работает немного странно)

```
docker run -p 8888:5000 -p 1111:50051 -i asmorodinov/basic_mafia_application  
```
```
Enter port number to run on --> 5000
Initialized voice chat server
Running on IP: 172.17.0.2
Running on port: 5000
INFO:root:Starting server
Select port to run server on (e.g. 50051): 50051
```

Если запускать просто на локальной машине, то два сервера (voice chat и мафия) получают разные ip адреса и всё прекрасно работает.

Например:

Сервер
```
python3 mafia_server.py
Enter port number to run on --> 5000
Initialized voice chat server
Running on IP: 172.21.240.1
Running on port: 5000
INFO:root:Starting server
Select port to run server on (e.g. 50051): 50051
```

Клиент
```
python3 mafia_client.py
Enter mafia server address (e.g. localhost:50051): localhost:50051
[VC] Enter IP address of server --> 172.21.240.1
[VC] Enter target port of server --> 5000
[VC] addr: ('172.21.240.1', 55240)
[VC] Connected to Server
```

## Upd (20.03 1:15)
Как оказалось, если запускать через докер, то voice chat ломается, хотя если запускать без докера (установка зависимостей не сложная, и описана в Dockerfile), то всё работет (вместе с voice chat-ом).

Если поставить ```self.ip=''```(или ```self.ip='0.0.0.0'```) в ```server_tcp.py```, то в логах видно, что все connection-ы к voice chat серверу accept-ятся, но voice chat не работает (я также пробовал другие варианты ```ip``` в ```server_tcp.py``` и ```mafia_server.py```, но они тоже не работают), при этом в логах никаких ошибок не видно.

Довольно странная проблема, возможно она как-то связана с тем, что докер контейнер может иметь только один внешний ip адрес, но я не уверен.

Можно наверное решить это с помощью docker compose, если явно объединить voice chat сервер и mafia сервер в одну сеть, но на это у меня уже не было времени(

Надеюсь, что того факта, что без докера всё работает, будет достаточно (docker build работает, но docker run нет) для 15 баллов. (с докером работает всё кроме voice чата).
