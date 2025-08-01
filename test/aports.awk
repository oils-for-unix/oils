# Script to calculate size stats from APKINDEX
#
# Generated by Claude, then lightly edited

BEGIN {
    # Initialize variables
    package_name = ""
    package_size = 0
    total_packages = 0
    total_size = 0
}

# Match package name lines (P:package-name)
/^P:/ {
    package_name = substr($0, 3)  # Remove "P:" prefix
}

# Match size lines (S:123456)
/^S:/ {
    package_size = substr($0, 3)  # Remove "S:" prefix

    # Only print if we have both package name and size
    if (package_name != "" && package_size > 0) {
        printf "%-40s %12s %15s\n", package_name, package_size, human_readable(package_size)
        total_packages++
        total_size += package_size
    }

    # Reset for next package
    package_name = ""
    package_size = 0
}

# Function to convert bytes to human readable format
function human_readable(bytes) {
    if (bytes >= 1e9) {
        return sprintf("%.1f GB", bytes / 1e9)
    } else if (bytes >= 1e6) {
        return sprintf("%.1f MB", bytes / 1e6)
    } else if (bytes >= 1e3) {
        return sprintf("%.1f KB", bytes / 1e3)
    } else {
        return sprintf("%d B", bytes)
    }
}

END {
    printf "\n"
    printf "Total packages: %d\n", total_packages
    printf "Total size: %s (%s)\n", total_size, human_readable(total_size)
    printf "Average size: %s\n", human_readable(total_size / total_packages)
}
