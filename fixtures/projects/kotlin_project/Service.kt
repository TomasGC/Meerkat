import java.security.MessageDigest

open class Base
open class Level1 : Base()
open class Level2 : Level1()
open class Level3 : Level2()
class Level4 : Level3()

class OrderService {
    private val password = "hunter2secret"

    fun process(order: Order) {
        // TODO: handle refunds
        // val old = legacyProcess(order)
        // logOld(old)
        doWork(order)
    }

    fun fingerprint(data: ByteArray): ByteArray =
        MessageDigest.getInstance("MD5").digest(data)

    fun quantity(input: String): Int {
        try { audit(input) } catch (e: Exception) {}
        return input.toInt()
    }
}
