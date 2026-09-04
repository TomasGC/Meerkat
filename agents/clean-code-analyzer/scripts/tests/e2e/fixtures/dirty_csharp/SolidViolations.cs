// KNOWN VIOLATIONS: SOLID-S=1, SOLID-D=1, Naming=2, ErrorHandling=1

public class GodController
{
    // SRP violation: controller handles business logic, DB, and email
    private readonly SqlConnection _db = new SqlConnection("Server=localhost");  // DIP violation

    public void ProcessOrder(object o)  // Naming: 'o' param, 'object' type
    {
        try
        {
            // Business logic in controller
            var total = 0;
            for (int i = 0; i < 86400; i++)  // Naming: magic number
            {
                total += i;
            }
            _db.Open();
        }
        catch (Exception)
        {
            // ErrorHandling: swallowed
        }
    }
}
