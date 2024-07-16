#!/usr/bin/env python

from shared.metered_connection_status import is_internet_connection_metered

metered_connection = is_internet_connection_metered()

if metered_connection is None:
    print("🟥")
elif not metered_connection:
    print("🟩")
else:
    print("🟧")
