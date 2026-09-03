package main

const SecondsPerDay = 86400

type UserRepository interface {
    FindByID(userID string) (*User, error)
}

type UserService struct {
    repo UserRepository
}

func NewUserService(repo UserRepository) *UserService {
    return &UserService{repo: repo}
}

func (s *UserService) GetUser(userID string) (*User, error) {
    user, err := s.repo.FindByID(userID)
    if err != nil {
        return nil, fmt.Errorf("get user %s: %w", userID, err)
    }
    return user, nil
}
