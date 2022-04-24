package main

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"flag"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"os"
	"strconv"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/streadway/amqp"
	"golang.org/x/crypto/bcrypt"
)

type UserData struct {
	login       string
	avatar      []byte
	gender      string
	email       string
	gamesPlayed int
	gamesWon    int
	gamesLost   int
	timeInGame  time.Duration
}

type Server struct {
	// variables for rest server
	mutex         sync.Mutex
	loginToData   map[string]*UserData
	userPasswords map[string][]byte
	defaultAvatar []byte
	// variables for statistics generation
	defaultStatsPDF []byte
	PDFDocumentId   int
	pdfStatsMap     map[int][]byte
	// workers secret code to let them perform pdf put request
	workerCodeHash []byte
	// mafia server secret code to let it update stats
	mafiaServerHash []byte
}

func NewServer() *Server {
	defaultAvatar, err := ioutil.ReadFile("assets/defaultAvatar.png")
	if err != nil {
		panic(err)
	}

	defaultStatsPDF, err := ioutil.ReadFile("assets/defaultStats.pdf")
	if err != nil {
		panic(err)
	}

	workerCodeHash, err := bcrypt.GenerateFromPassword([]byte("aksmdkamdlsamd"), bcrypt.DefaultCost)
	if err != nil {
		panic(err)
	}

	mafiaServerHash, err := bcrypt.GenerateFromPassword([]byte("jfdsfndsfksdnfk"), bcrypt.DefaultCost)
	if err != nil {
		panic(err)
	}

	return &Server{sync.Mutex{}, make(map[string]*UserData), make(map[string][]byte), defaultAvatar, defaultStatsPDF, 0, make(map[int][]byte), workerCodeHash, mafiaServerHash}
}

func (s *Server) signupHandler(c *gin.Context) {
	// parse json body
	type SignupRequest struct {
		Login    string `json:"login"`
		Password string `json:"password"`
		Email    string `json:"email"`
	}
	var request SignupRequest
	if err := c.ShouldBindJSON(&request); err != nil {
		c.String(http.StatusBadRequest, err.Error())
		return
	}
	s.mutex.Lock()
	defer s.mutex.Unlock()

	// check if login does not exist already
	if _, ok := s.loginToData[request.Login]; ok {
		c.String(http.StatusBadRequest, "login %q is taken by someone else", request.Login)
		return
	}

	// bcrypt password
	hash, err := bcrypt.GenerateFromPassword([]byte(request.Password), bcrypt.DefaultCost)
	if err != nil {
		c.String(http.StatusInternalServerError, "Failed to bcrypt user password: %v", err)
		return
	}

	// save user data in the server memory
	s.loginToData[request.Login] = &UserData{request.Login, s.defaultAvatar, "not specified", request.Email, 0, 0, 0, time.Duration(0)}
	s.userPasswords[request.Login] = hash

	// success
	c.String(http.StatusOK, "successfully signed up login %q", request.Login)
}

func (s *Server) loginHandler(c *gin.Context) {
	// parse json body
	type Request struct {
		Login    string `json:"login"`
		Password string `json:"password"`
	}
	var request Request
	if err := c.ShouldBindJSON(&request); err != nil {
		c.String(http.StatusBadRequest, err.Error())
		return
	}

	s.mutex.Lock()
	defer s.mutex.Unlock()

	// check that user exists
	if _, ok := s.loginToData[request.Login]; !ok {
		c.String(http.StatusNotFound, "user with login %q not found in the database", request.Login)
		return
	}

	// check if user has rights to delete this account
	hash := s.userPasswords[request.Login]
	if cmperr := bcrypt.CompareHashAndPassword(hash, []byte(request.Password)); cmperr != nil {
		c.String(http.StatusUnauthorized, "Wrong password to log in to %q user account", request.Login)
		return
	}
	c.String(http.StatusOK, "")
}

func (s *Server) getUserPropertyHandler(c *gin.Context) {
	login := c.Params.ByName("login")
	property := c.Params.ByName("property")

	s.mutex.Lock()
	defer s.mutex.Unlock()

	// check that user exists
	if _, ok := s.loginToData[login]; !ok {
		c.String(http.StatusNotFound, "user with login %q not found in the database", login)
		return
	}

	user := s.loginToData[login]

	switch property {
	case "email":
		c.String(http.StatusOK, user.email)
	case "gender":
		c.String(http.StatusOK, user.gender)
	case "avatar.png":
		c.Data(http.StatusOK, "image/png", user.avatar)
	default:
		c.String(http.StatusBadRequest, "unknown property %q for user with login %q", property, login)
	}
}

type UserDataResponse struct {
	Login     string `json:"login"`
	AvatarURI string `json:"avatar_uri"`
	Gender    string `json:"gender"`
	Email     string `json:"email"`
}

func getHostUrl(req *http.Request) string {
	scheme := "http"
	if req.TLS != nil {
		scheme = "https"
	}
	return scheme + "://" + req.Host
}

func (s *Server) getUserDataResponse(login string, req *http.Request) UserDataResponse {
	user := s.loginToData[login]
	avatarURI := getHostUrl(req) + "/users/" + user.login + "/avatar.png"
	udr := UserDataResponse{user.login, avatarURI, user.gender, user.email}
	return udr
}

// return info about one user
func (s *Server) getUserDataHandler(c *gin.Context) {
	login := c.Params.ByName("login")

	s.mutex.Lock()
	defer s.mutex.Unlock()

	// check that user exists
	if _, ok := s.loginToData[login]; !ok {
		c.String(http.StatusNotFound, "user with login %q not found in the database", login)
		return
	}
	// return response
	c.JSON(http.StatusOK, s.getUserDataResponse(login, c.Request))
}

// return info about all users
func (s *Server) getUsersCollectionHandler(c *gin.Context) {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	users := make([]UserDataResponse, 0)
	for login := range s.loginToData {
		users = append(users, s.getUserDataResponse(login, c.Request))
	}
	// return response
	c.JSON(http.StatusOK, users)
}

func (s *Server) deleteUserData(c *gin.Context) {
	login := c.Params.ByName("login")
	// parse json body
	type DeleteRequest struct {
		Password string `json:"password"`
	}
	var request DeleteRequest
	if err := c.ShouldBindJSON(&request); err != nil {
		c.String(http.StatusBadRequest, err.Error())
		return
	}
	s.mutex.Lock()
	defer s.mutex.Unlock()

	// check if login exists
	if _, ok := s.loginToData[login]; !ok {
		c.String(http.StatusNoContent, "")
		return
	}

	// check if user has rights to delete this account
	hash := s.userPasswords[login]
	if cmperr := bcrypt.CompareHashAndPassword(hash, []byte(request.Password)); cmperr != nil {
		c.String(http.StatusUnauthorized, "wrong password to delete login %q", login)
		return
	}

	// delete account
	delete(s.loginToData, login)
	delete(s.userPasswords, login)
	c.String(http.StatusNoContent, "")
}

func (s *Server) putUserPropertyHandler(c *gin.Context) {
	login := c.Params.ByName("login")
	property := c.Params.ByName("property")

	// parse json body
	type PutRequest struct {
		Password string `json:"password"`
		Value    string `json:"value"`
	}
	var request PutRequest
	if err := c.ShouldBindJSON(&request); err != nil {
		c.String(http.StatusBadRequest, err.Error())
		return
	}

	s.mutex.Lock()
	defer s.mutex.Unlock()

	// check that user exists
	if _, ok := s.loginToData[login]; !ok {
		c.String(http.StatusNotFound, "user with login %q not found in the database", login)
		return
	}

	// check if user has rights to delete this account
	hash := s.userPasswords[login]
	if cmperr := bcrypt.CompareHashAndPassword(hash, []byte(request.Password)); cmperr != nil {
		c.String(http.StatusUnauthorized, "wrong password to change property %q for user with login %q", property, login)
		return
	}

	user := s.loginToData[login]

	switch property {
	case "login":
		// check if new login is available
		if _, ok := s.loginToData[request.Value]; ok {
			c.String(http.StatusBadRequest, "can't change login from %q to %q because there already exists user with login %q", login, request.Value, request.Value)
			return
		}
		userData := *user
		userData.login = request.Value
		delete(s.loginToData, login)
		delete(s.userPasswords, login)
		s.loginToData[request.Value] = &userData
		s.userPasswords[request.Value] = hash

		c.String(http.StatusOK, "successfully changed property %q for user with login %q to be %q", property, login, request.Value)
	case "email":
		user.email = request.Value
		c.String(http.StatusOK, "successfully changed property %q for user with login %q to be %q", property, login, request.Value)
	case "gender":
		user.gender = request.Value
		c.String(http.StatusOK, "successfully changed property %q for user with login %q to be %q", property, login, request.Value)
	case "avatar_base64":
		data, err := base64.StdEncoding.DecodeString(request.Value)
		if err != nil {
			c.String(http.StatusBadRequest, "base64 decode err: %v", err)
		}
		user.avatar = data
	default:
		c.String(http.StatusBadRequest, "can't change property %q for user with login %q to be %q", property, login, request.Value)
	}
}

// 'frontend' handlers (html pages)

type Link struct {
	Href string
	Text string
}

func (s *Server) indexHTMLHandler(c *gin.Context) {
	c.HTML(http.StatusOK, "index.tmpl", gin.H{
		"title": "Main page",
		"links": []Link{
			{Href: "/users.html", Text: "Get users list"},
			{Href: "/signup.html", Text: "Sign up new user"},
			{Href: "/delete.html", Text: "Delete user"},
			{Href: "/put.html", Text: "Change user property"},
			{Href: "/changeAvatar.html", Text: "Change user avatar image"},
			{Href: "/genstats.html", Text: "Generate pdf document with user stats"},
		},
	})
}

func (s *Server) getUsersHTMLHandler(c *gin.Context) {
	queryLogin, loginSpecified := c.GetQuery("login")

	s.mutex.Lock()
	defer s.mutex.Unlock()

	users := make([]UserDataResponse, 0)
	title := "Users list"

	if !loginSpecified {
		for login := range s.loginToData {
			users = append(users, s.getUserDataResponse(login, c.Request))
		}
	} else {
		if _, ok := s.loginToData[queryLogin]; !ok {
			c.String(http.StatusNotFound, "couldn't find user with login %q in the database", queryLogin)
			return
		}
		title = "User profile"
		users = append(users, s.getUserDataResponse(queryLogin, c.Request))
	}

	// return response
	c.HTML(http.StatusOK, "users.tmpl", gin.H{
		"title": title,
		"users": users,
	})
}

func (s *Server) signupHTMLHandler(c *gin.Context) {
	// return response
	c.HTML(http.StatusOK, "signup.tmpl", gin.H{
		"title": "This is a sign up form for a new user",
	})
}

func (s *Server) deleteHTMLHandler(c *gin.Context) {
	// return response
	c.HTML(http.StatusOK, "delete.tmpl", gin.H{
		"title": "This is a form to delete data of the selected user",
	})
}

func (s *Server) putHTMLHandler(c *gin.Context) {
	// return response
	c.HTML(http.StatusOK, "put.tmpl", gin.H{
		"title": "This is a form to change property of selected user",
	})
}

func (s *Server) changeAvatarHTMLHandler(c *gin.Context) {
	// return response
	c.HTML(http.StatusOK, "changeAvatar.tmpl", gin.H{
		"title": "This is a form to change avatar image of selected user",
	})
}

func (s *Server) generateStatsPDFHTMLHandler(c *gin.Context) {
	// return response
	c.HTML(http.StatusOK, "genstats.tmpl", gin.H{
		"title": "This is a form to generate pdf stats of selected user",
	})
}

func (s *Server) generatePDFHandler(c *gin.Context) {
	// parse json body
	type PostRequest struct {
		Login string `json:"login"`
	}
	var request PostRequest
	if err := c.ShouldBindJSON(&request); err != nil {
		c.String(http.StatusBadRequest, err.Error())
		return
	}

	s.mutex.Lock()
	defer s.mutex.Unlock()

	if _, ok := s.loginToData[request.Login]; !ok {
		c.String(http.StatusNotFound, "login %q not found", request.Login)
		return
	}
	user := s.loginToData[request.Login]
	avatarEncoded := base64.StdEncoding.EncodeToString(user.avatar)

	s.PDFDocumentId++
	s.pdfStatsMap[s.PDFDocumentId] = s.defaultStatsPDF

	// send message to rabbit mq
	msg := Message{"login": user.login, "avatar_base64": avatarEncoded, "gender": user.gender, "email": user.email,
		"games_played": user.gamesPlayed, "games_won": user.gamesWon, "games_lost": user.gamesLost, "time_in_game": user.timeInGame, "id": s.PDFDocumentId}

	bytes, err := serialize(msg)
	if err != nil {
		c.String(http.StatusInternalServerError, "serialization err: %v", err)
		return
	}

	err = ch.Publish(
		"",     // exchange
		q.Name, // routing key
		false,  // mandatory
		false,  // immediate
		amqp.Publishing{
			ContentType: "text/plain",
			Body:        bytes,
		})
	if err != nil {
		c.String(http.StatusInternalServerError, "failed to publish rabbit mq message, err: %v", err)
		return
	}

	c.String(http.StatusOK, "%v/pdf-stats/%v", getHostUrl(c.Request), s.PDFDocumentId)
}

func (s *Server) getPDFStatHandler(c *gin.Context) {
	id, err := strconv.Atoi(c.Params.ByName("id"))
	if err != nil {
		c.String(http.StatusBadRequest, "Failed to parse pdf id: %v", err)
		return
	}

	s.mutex.Lock()
	defer s.mutex.Unlock()

	if _, ok := s.pdfStatsMap[id]; !ok {
		c.String(http.StatusNotFound, "Couldn't find pdf with id %v", id)
		return
	}

	doc := s.pdfStatsMap[id]
	c.Data(http.StatusOK, "application/pdf", doc)
}

func (s *Server) putPDFStatHandler(c *gin.Context) {
	id, err := strconv.Atoi(c.Params.ByName("id"))
	if err != nil {
		c.String(http.StatusBadRequest, "Failed to parse pdf id: %v", err)
		return
	}

	// parse json body
	type PutRequest struct {
		Password string `json:"password"`
		Value    string `json:"value"`
	}
	var request PutRequest
	if err := c.ShouldBindJSON(&request); err != nil {
		c.String(http.StatusBadRequest, err.Error())
		return
	}

	// check if user has rights to delete this account
	if cmperr := bcrypt.CompareHashAndPassword(s.workerCodeHash, []byte(request.Password)); cmperr != nil {
		c.String(http.StatusUnauthorized, "You are not authorized to change pdf document, only workers can do that")
		return
	}

	s.mutex.Lock()
	defer s.mutex.Unlock()

	if _, ok := s.pdfStatsMap[id]; !ok {
		c.String(http.StatusNotFound, "Couldn't find pdf with id %v", id)
		return
	}

	data, err := base64.StdEncoding.DecodeString(request.Value)
	if err != nil {
		c.String(http.StatusBadRequest, "base64 decode err: %v", err)
	}
	s.pdfStatsMap[id] = data

	c.String(http.StatusOK, "Successfully changed pdf with id %q", id)
}

// rabbit mq stuff
type Message map[string]interface{}

func serialize(msg Message) ([]byte, error) {
	var b bytes.Buffer
	encoder := json.NewEncoder(&b)
	err := encoder.Encode(msg)
	return b.Bytes(), err
}

func failOnError(err error, msg string) {
	if err != nil {
		log.Panicf("%s: %s", msg, err)
	}
}

var q amqp.Queue
var ch *amqp.Channel
var conn *amqp.Connection

var addr = flag.String("addr", "localhost:8080", "rest server address")
var rabbitMQAddr = flag.String("mqaddr", "amqp://guest:guest@localhost:5672/", "RabbitMQ address to connect to")

func initRabbitMQ() {
	// connect to rabbit mq
	var err error
	for {
		conn, err = amqp.Dial(*rabbitMQAddr)
		if err != nil {
			fmt.Fprintln(os.Stderr, err, "Failed to connect to RabbitMQ")

			time.Sleep(2 * time.Second)

			continue
		}
		break
	}

	ch, err = conn.Channel()
	failOnError(err, "Failed to open a channel")

	q, err = ch.QueueDeclare(
		"hello", // name
		false,   // durable
		false,   // delete when unused
		false,   // exclusive
		false,   // no-wait
		nil,     // arguments
	)
	failOnError(err, "Failed to declare a queue")
}

func (s *Server) updateStats(c *gin.Context) {
	// parse json body
	type Request struct {
		Password         string        `json:"password"`
		Login            string        `json:"login"`
		GamesPlayedDelta int           `json:"games_played_delta"`
		GamesWonDelta    int           `json:"games_won_delta"`
		GamesLostDelta   int           `json:"games_lost_delta"`
		TimePlayedDelta  time.Duration `json:"time_played_delta"`
	}

	var request Request
	if err := c.ShouldBindJSON(&request); err != nil {
		c.String(http.StatusBadRequest, err.Error())
		return
	}

	if cmperr := bcrypt.CompareHashAndPassword(s.mafiaServerHash, []byte(request.Password)); cmperr != nil {
		c.String(http.StatusUnauthorized, "You are not authorized to change stats, only mafia server can do that")
		return
	}

	s.mutex.Lock()
	defer s.mutex.Unlock()

	user := s.loginToData[request.Login]
	user.gamesPlayed += request.GamesPlayedDelta
	user.gamesWon += request.GamesWonDelta
	user.gamesLost += request.GamesLostDelta
	user.timeInGame += request.TimePlayedDelta

	c.String(http.StatusOK, "Successfully changed stats of player with login %q", request.Login)
}

func main() {
	flag.Parse()

	// init rabbbit mq
	initRabbitMQ()
	defer conn.Close()
	defer ch.Close()

	// init gin
	router := gin.Default()
	router.LoadHTMLGlob("templates/*.tmpl")

	server := NewServer()

	// rest api handlers
	router.POST("/signup", server.signupHandler)
	// only exists to be able to check login and password, no sessions or tokens get created here
	router.GET("/signin", server.loginHandler)

	router.GET("/users", server.getUsersCollectionHandler)
	router.GET("/users/:login", server.getUserDataHandler)
	router.GET("/users/:login/:property", server.getUserPropertyHandler)

	router.DELETE("/users/:login", server.deleteUserData)

	router.PUT("/users/:login/:property", server.putUserPropertyHandler)

	// stats pdf generation handlers
	router.POST("/pdf-stats", server.generatePDFHandler)
	router.GET("/pdf-stats/:id", server.getPDFStatHandler)
	router.PUT("/pdf-stats/:id", server.putPDFStatHandler)

	router.POST("/stats", server.updateStats)

	// html handlers (for rest client)
	router.GET("/index.html", server.indexHTMLHandler)
	router.GET("/users.html", server.getUsersHTMLHandler)
	router.GET("/signup.html", server.signupHTMLHandler)
	router.GET("/delete.html", server.deleteHTMLHandler)
	router.GET("/put.html", server.putHTMLHandler)
	router.GET("/changeAvatar.html", server.changeAvatarHTMLHandler)
	router.GET("/genstats.html", server.generateStatsPDFHTMLHandler)

	router.Run(*addr)
}
