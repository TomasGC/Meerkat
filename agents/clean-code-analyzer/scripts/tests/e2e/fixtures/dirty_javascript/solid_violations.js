// KNOWN VIOLATIONS: SOLID-S=1, Naming=3, ErrorHandling=2, Comments=1

class UserManager {
  // SRP: manages users, sends emails, generates reports
  createUser(n) { }        // Naming: single-letter param
  sendEmail(e, b) { }      // Naming: single-letter params
  generateReport(d) { }
  deleteUser(id) { }

  processAll(data) {
    const x = data.length * 86400;  // Naming: magic number
    try {
      return this.save(data);
    } catch (err) { }  // ErrorHandling: swallowed
  }
}

// TODO: refactor this entire class  // Comments: tracked issue needed
function calc(a, b, c) {  // Naming: unclear function name, single-letter params
  try {
    return a + b + c;
  } catch(e) { }  // ErrorHandling: swallowed
}
