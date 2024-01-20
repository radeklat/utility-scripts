notify () {
    # Find the logged-in user
    logged_in_user=$(who | grep '(:1)' | head -n 1 | awk '{print $1}')

    # Send notification
    if [ -n "$logged_in_user" ]; then
      sudo -u "$logged_in_user" DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/"$(id -u "$logged_in_user")"/bus notify-send -t 5000 "$@"
    fi
}

# `-i` icons from https://specifications.freedesktop.org/icon-naming-spec/latest/ar01s04.html
# or `find /usr/share/icons/ -iregex ".*<NAME>.*"`

notify_debug () {
    notify -i "dialog-information" -u "low" "$@"
}

notify_info () {
    notify -i "dialog-information" -u "normal" "$@"
}

notify_warning () {
    notify -i "dialog-warning" -u "normal" "$@"
}

notify_error () {
    notify -i "dialog-error" -u "normal" "$@"
}

notify_critical () {
    notify -i "dialog-error" -u "critical" "$@"
}

notify_network_error () {
    notify -i "network-error" -u "normal" "$@"
}