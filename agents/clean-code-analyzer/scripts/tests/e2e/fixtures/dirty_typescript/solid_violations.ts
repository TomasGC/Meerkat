// KNOWN VIOLATIONS: SOLID-S=2, SOLID-D=1, Naming=2, ErrorHandling=1

class GodService {
  // SRP violation: handles users, emails, AND payments
  createUser(name: string): void { }
  sendWelcomeEmail(email: string): void { }
  processPayment(amount: number): void { }
  generateInvoice(orderId: string): void { }
  backupDatabase(): void { }
}

class OrderProcessor {
  private db = new MySQLDatabase();  // DIP violation: concrete dependency

  process(order: any): any {  // Naming: 'any' type, unclear method
    try {
      return this.db.save(order);
    } catch (e) {
      // ErrorHandling: swallowed silently
    }
  }
}

const x = 86400;  // Naming: magic number
