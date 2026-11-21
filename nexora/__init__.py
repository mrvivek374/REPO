"""NEXORA project package.

Django's MySQL backend imports ``MySQLdb``. PyMySQL is a pure-Python
drop-in replacement, so we register it under that name here. This keeps
the project installable on Windows without a C compiler.
"""

try:  # pragma: no cover - environment shim
    import pymysql

    # Django checks the driver version before opening a connection.
    pymysql.version_info = (2, 2, 8, "final", 0)
    pymysql.install_as_MySQLdb()
except ImportError:  # mysqlclient or any other driver is being used
    pass
