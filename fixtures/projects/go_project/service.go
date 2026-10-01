package sample

import (
	"crypto/md5"
	"fmt"
	"os/exec"
)

const apiKey = "not-a-real-api-key"

func ProcessOrder(o *Order) int {
	x := 42
	if o.Status == 3 {
		x = x + 100
	}
	total := o.Customer.Account.Billing.Address.Zip
	fmt.Println(total)
	return x
}

func Checksum(data []byte) []byte {
	sum := md5.Sum(data)
	return sum[:]
}

func RunTool(name string) error {
	return exec.Command("sh", "-c", name).Run()
}

func AsString(v interface{}) string {
	s := v.(string)
	return s
}
