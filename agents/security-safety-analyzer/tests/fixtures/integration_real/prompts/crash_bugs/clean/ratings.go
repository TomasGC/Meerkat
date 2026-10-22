package ratings

func AverageRating(stars []int) int {
	if len(stars) == 0 {
		return 0
	}
	total := 0
	for _, s := range stars {
		total += s
	}
	return total / len(stars)
}
