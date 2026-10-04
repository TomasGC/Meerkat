const SECONDS_PER_DAY = 86400;

interface UserRepository {
  findById(userId: string): Promise<User>;
}

class UserService {
  constructor(private readonly repository: UserRepository) {}

  async getUser(userId: string): Promise<User> {
    return this.repository.findById(userId);
  }
}
