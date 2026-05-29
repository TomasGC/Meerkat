package main

import (
	"github.com/gin-gonic/gin"
)

func main() {
	router := gin.Default()

	router.GET("/api/users", getUsers)
	router.GET("/api/users/:id", getUser)
	router.POST("/api/users", createUser)

	router.Run(":8080")
}

func getUsers(c *gin.Context) {
	c.JSON(200, gin.H{"users": []string{"user1", "user2"}})
}

func getUser(c *gin.Context) {
	id := c.Param("id")
	c.JSON(200, gin.H{"id": id, "name": "User"})
}

func createUser(c *gin.Context) {
	c.JSON(201, gin.H{"status": "created"})
}
