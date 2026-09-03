#!/usr/bin/env bash
# KNOWN VIOLATIONS: SOLID-S=1, Naming=2, ErrorHandling=2, Comments=1

# SRP violation: god function handles users, backup, AND email
do_everything() {
    local n=$1  # Naming: single-letter var
    local x=86400  # Naming: magic number

    # TODO: split this up  # Comments: tracked issue

    create_user "$n" || true  # ErrorHandling: error swallowed with || true
    send_email "$n" || :      # ErrorHandling: error swallowed with || :
    backup_database
    generate_report
}
