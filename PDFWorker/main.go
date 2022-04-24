package main

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"strconv"
	"time"

	"github.com/go-resty/resty/v2"
	"github.com/signintech/gopdf"
	"github.com/streadway/amqp"
)

// helper function
func failOnError(err error, msg string) {
	if err != nil {
		log.Panicf("%s: %s", msg, err)
	}
}

// rabbitmq message deserialization
type Message map[string]interface{}

func Deserialize(b []byte) (Message, error) {
	var msg Message
	buf := bytes.NewBuffer(b)
	decoder := json.NewDecoder(buf)
	err := decoder.Decode(&msg)
	return msg, err
}

// sender addr
var addr = flag.String("addr", "http://localhost:8080", "rest server address")
var rabbitMQAddr = flag.String("mqaddr", "amqp://guest:guest@localhost:5672/", "RabbitMQ address to connect to")

func generatePDF(login, avatarBase64, gender, email string, gamesPlayed, gamesWon, gamesLost int, timeInGame time.Duration) []byte {
	pdf := gopdf.GoPdf{}
	mm6ToPx := 22.68

	// Base trim-box
	pdf.Start(gopdf.Config{
		PageSize: *gopdf.PageSizeA4, //595.28, 841.89 = A4
		TrimBox:  gopdf.Box{Left: mm6ToPx, Top: mm6ToPx, Right: 595 - mm6ToPx, Bottom: 842 - mm6ToPx},
	})

	// Page trim-box
	opt := gopdf.PageOption{
		PageSize: gopdf.PageSizeA4, //595.28, 841.89 = A4
		TrimBox:  &gopdf.Box{Left: mm6ToPx, Top: mm6ToPx, Right: 595 - mm6ToPx, Bottom: 842 - mm6ToPx},
	}
	pdf.AddPageWithOption(opt)

	// load and set font
	err := pdf.AddTTFFont("loma", "ttf/Loma.ttf")
	failOnError(err, "failed to add font")

	err = pdf.SetFont("loma", "", 14)
	failOnError(err, "failed to set font")

	avatar, err := base64.StdEncoding.DecodeString(avatarBase64)
	failOnError(err, "failed to parse base64 avatar")

	// add image
	imgH1, err := gopdf.ImageHolderByBytes(avatar)
	failOnError(err, "failed to create image")
	pdf.ImageByHolder(imgH1, 64, 64, nil)

	// add text
	pdf.SetX(50)
	pdf.SetY(120)
	pdf.Cell(nil, "login: "+login)
	pdf.SetX(50)
	pdf.SetY(120 + 30)
	pdf.Cell(nil, "gender: "+gender)
	pdf.SetX(50)
	pdf.SetY(120 + 30*2)
	pdf.Cell(nil, "email: "+email)
	pdf.SetX(50)
	pdf.SetY(120 + 30*3)
	pdf.Cell(nil, "games played: "+strconv.Itoa(gamesPlayed))
	pdf.SetX(50)
	pdf.SetY(120 + 30*4)
	pdf.Cell(nil, "games won: "+strconv.Itoa(gamesWon))
	pdf.SetX(50)
	pdf.SetY(120 + 30*5)
	pdf.Cell(nil, "games lost: "+strconv.Itoa(gamesLost))
	pdf.SetX(50)
	pdf.SetY(120 + 30*6)
	pdf.Cell(nil, "time spent in the game: "+fmt.Sprintf("%s", timeInGame.Round(time.Second)))

	var buf bytes.Buffer
	pdf.Write(&buf)

	return buf.Bytes()
}

func main() {
	flag.Parse()

	// connect to rabbit mq
	var err error
	var conn *amqp.Connection
	for {
		conn, err = amqp.Dial(*rabbitMQAddr)
		if err != nil {
			fmt.Fprintln(os.Stderr, err, "Failed to connect to RabbitMQ")

			time.Sleep(2 * time.Second)

			continue
		}
		break
	}
	defer conn.Close()

	ch, err := conn.Channel()
	failOnError(err, "Failed to open a channel")
	defer ch.Close()

	q, err := ch.QueueDeclare(
		"hello", // name
		false,   // durable
		false,   // delete when unused
		false,   // exclusive
		false,   // no-wait
		nil,     // arguments
	)
	failOnError(err, "Failed to declare a queue")

	msgs, err := ch.Consume(
		q.Name, // queue
		"",     // consumer
		true,   // auto-ack
		false,  // exclusive
		false,  // no-local
		false,  // no-wait
		nil,    // args
	)
	failOnError(err, "Failed to register a consumer")

	client := resty.New()

	var forever chan struct{}

	go func() {
		// receive messages
		for d := range msgs {
			log.Printf("Received a message: %s", d.Body)
			msg, err := Deserialize(d.Body)
			if err != nil {
				fmt.Fprintln(os.Stderr, "deserialization error", msg, err)
				continue
			}
			// deserialized message
			login := msg["login"].(string)
			avatarBase64 := msg["avatar_base64"].(string)
			gender := msg["gender"].(string)
			email := msg["email"].(string)
			gamesPlayed := msg["games_played"].(float64)
			gamesWon := msg["games_won"].(float64)
			gamesLost := msg["games_lost"].(float64)
			timeInGame := msg["time_in_game"].(float64)

			id := int(msg["id"].(float64))
			idStr := strconv.Itoa(id)

			// generate pdf
			pdf := generatePDF(login, avatarBase64, gender, email, int(gamesPlayed), int(gamesWon), int(gamesLost), time.Duration(timeInGame))
			pdfEncoded := base64.StdEncoding.EncodeToString(pdf)

			// send put request
			resp, err := client.R().SetBody(map[string]interface{}{"password": "aksmdkamdlsamd", "value": pdfEncoded}).Put(*addr + "/pdf-stats/" + idStr)
			if err != nil {
				fmt.Println("resty err: ", err)
			}
			fmt.Println("resty status: ", resp.Status())
		}
	}()

	log.Printf(" [*] Waiting for messages. To exit press CTRL+C")
	<-forever
}
