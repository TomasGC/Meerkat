# KNOWN VIOLATIONS: SOLID-S=1, Naming=2, ErrorHandling=1, Comments=1

# God function - SRP violation: handles users, email, AND reporting
function Invoke-Everything {
    param($n, $e, $d)  # Naming: single-letter params

    $x = 86400  # Naming: magic number
    $server = "localhost"  # Naming: magic string

    # TODO: split this into separate functions  # Comments: tracked issue

    try {
        New-User -Name $n
        Send-Email -To $e -Body $d
        New-Report -Data $d
    } catch {
        # ErrorHandling: swallowed silently
    }
}
