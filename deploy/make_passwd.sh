#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")"

if [ "$#" -eq 0 ]; then
    echo "Usage: ./make_passwd.sh pump-01 pump-02 ingest alerts"
    exit 1
fi

first=1

for username in "$@"; do
    echo "Setting password for $username"

    if [ "$first" -eq 1 ]; then
        mosquitto_passwd -c passwd "$username"
        first=0
    else
        mosquitto_passwd passwd "$username"
    fi
done

echo "Password file created."