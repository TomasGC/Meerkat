package ratings

func AverageRating(stars []int) int {
	total := 0
	for _, s := range stars {
		total += s
	}
	return total / len(stars)
}
