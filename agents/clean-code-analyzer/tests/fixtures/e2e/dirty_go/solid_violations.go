// KNOWN VIOLATIONS: SOLID-S=1, Naming=2, ErrorHandling=2

package main

// SRP violation: God struct handles multiple concerns
type GodService struct {
    db interface{}
}

func (s *GodService) CreateUser(n string) {}      // Does user AND email AND reporting
func (s *GodService) SendEmail(e string) {}
func (s *GodService) GenerateReport(d interface{}) {}
func (s *GodService) BackupDB() {}

func process(d interface{}) interface{} {  // Naming: unclear
    x := 86400  // Naming: magic number
    _ = x
    err := doRiskyThing()
    if err != nil {
        _ = err  // ErrorHandling: error ignored
    }
    err2 := doAnotherThing()
    _ = err2    // ErrorHandling: error ignored
    return nil
}

func doRiskyThing() error { return nil }
func doAnotherThing() error { return nil }
