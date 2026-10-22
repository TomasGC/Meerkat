package hits

import "sync"

var (
	hits int
	mu   sync.Mutex
)

func Serve(requests int) {
	var wg sync.WaitGroup
	for i := 0; i < requests; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			mu.Lock()
			hits++
			mu.Unlock()
		}()
	}
	wg.Wait()
}
