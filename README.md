# mafia_rest_service
## Запуск
### Всё локально, кроме rabbitmq
#### RabbitMQ 
```docker run -it --rm -p 5672:5672 -p 15672:15672 rabbitmq:3.9-management```
#### Rest service
```go mod download && cd RestServer && go run main.go ```
#### PDF worker
```go mod download && cd PDFWorker && go run main.go ```

#### Rest service, небольшой комментарий
На данном этапе уже можно зайти на http://loacalhost:8080/index.html и использовать все функции REST сервера 
(создание, удаление пользователей, изменение параметров профиля пользователя, изменение аватара, получение статистики в виде пдф документа, 
просмотр профилей всех пользователей, либо профиля выбранного пользователя и т.д.).

Сервер реализует REST API (например один из возможных запросов - ```GET /users/:login/:property```), а также возвращает HTML страницы для удобного взаимодействия с REST API 
(например ```GET /index.html``` вернёт основную HTML страницу, с которой можно открывать другие HTML страницы по ссылкам (```/index.html, /users.html, /signup.html```, ...)).

Более подробную информацию о всех поддерживаемых запросах к серверу можно узнать из исходного кода сервера (RestServer/main.go)

Так как сервер может возвращать HTML страницы, то в качестве клиента можно использовать браузер (я тестировал с Google Chrome 100.0.4896.127, но другие браузеры скорее всего тоже подойдут).

Для простоты реализации все данные хранятся в оперативной памяти сервера, при рестарте они никуда не сохраняются.

Сервер работает по HTTP, все данные и пароли передаются по сети в незашифрованном виде. С точки зрения реального приложения, это очень плохой подход, но это было сделано также ради простоты.
(Т.к. не нужно получать TLS сертификат, и нет дополнительной сложности при отладке через curl, postman, при отправке запросов к серверу через resty и requests).

#### Mafia server
```cd basic_mafia && pip3 install -r requirements.txt && python3 ./mafia_server.py```

дальше вводим:

```
5000
http://localhost:8080
[::]
50051
```

#### Mafia client
```cd basic_mafia && pip3 install -r requirements.txt && python3 ./mafia_client.py```

вводим:

```
localhost:50051
IP адрес сервера, например 172.17.224.1. Адрес можно узнать, если посмотреть на строчку вида "Running on IP: 172.17.224.1", которая выводится в момент запуска mafia сервера.
5000
логин (например user1)
пароль (например 1234)
имя комнаты (например 1)
```
Пользователь перед запуском mafia клиента должен быть зарегистрирован в базе данных REST сервера, иначе войти в комнату не получится.
Если все данные корректны, то после того, как в комнату войдут 4 игрока игра начнётся. Когда игра заканчивается, mafia server отправляет запрос к REST серверу, чтобы он обновил статистику по игрокам.

### Запуск всех компонент в докере, кроме клиентов
#### build
Данный шаг можно пропустить, если использовать контейнеры asmorodinov/pdfworker, asmorodinov/restserver, asmorodinov/mafiaserver вместо pdfworker, restserver, mafiaserver

```docker build . -t pdfworker -f=DockerfilePDFWorker```

```docker build . -t restserver -f=DockerfileRestServer```

```cd basic_mafia && docker build . -t mafiaserver```
#### создаём новую сеть 
```docker network create test-net```
#### RabbitMQ
```docker run -it --rm --name rabbitmq --network test-net -p 5672:5672 -p 15672:15672 rabbitmq:3.9-management```
#### Rest service
```docker run -i --network test-net --name server -p 8080:8080 restserver -mqaddr=amqp://guest:guest@rabbitmq:5672/ -addr=[::]:8080```

или

```docker run -i --network test-net --name server -p 8080:8080 asmorodinov/restserver -mqaddr=amqp://guest:guest@rabbitmq:5672/ -addr=[::]:8080```
#### Worker (может быть несколько)
```docker run -i --network test-net --name worker pdfworker -mqaddr=amqp://guest:guest@rabbitmq:5672/ -addr=http://server:8080```

или

```docker run -i --network test-net --name worker asmorodinov/pdfworker -mqaddr=amqp://guest:guest@rabbitmq:5672/ -addr=http://server:8080```
#### Mafia server
```docker run -p 5000:5000 -p 50051:50051 -i --name mafia --network test-net mafiaserver```

или

```docker run -p 5000:5000 -p 50051:50051 -i --name mafia --network test-net asmorodinov/mafiaserver```

вводим: 
```
5000
http://server:8080
[::]
50051
```
#### Клиент (в докере запускать нельзя, так как не будет работать звуковая карта)
```cd basic_mafia && pip3 install -r requirements.txt && python3 ./mafia_client.py```

вводим:
```
localhost:50051
localhost
5000
логин (например user1)
пароль (например 1234)
имя комнаты (например 1)
```

## p.s.
Если запускать mafia сервер в докере, то voice chat не работает, а если без докера - то работает. Но в условии про наличие войс чата ничего сказано не было, поэтому это незначительная проблема.
