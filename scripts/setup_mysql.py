"""Create the NEXORA MySQL database and application user.

Run from the project root:

    python scripts/setup_mysql.py

The script asks for your MySQL administrator password (typed locally and
never stored), creates the database plus a dedicated NEXORA user, writes
the connection details into .env, applies the migrations and can seed the
demonstration records.
"""

from __future__ import annotations

import getpass
import os
import secrets
import subprocess
import sys
from pathlib import Path

try:
    import pymysql
except ImportError:  # pragma: no cover - dependency hint
    sys.exit("PyMySQL is missing. Run: pip install -r requirements.txt")

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"


def banner(text: str) -> None:
    print("\n" + "=" * 68)
    print(text)
    print("=" * 68)


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    answer = input(f"{prompt}{suffix}: ").strip()
    return answer or default


def read_env() -> dict:
    values = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def write_env_value(key: str, value: str) -> None:
    """Update a single key inside .env, keeping comments intact."""
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    found = False
    for index, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[index] = f"{key}={value}"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(command: list[str], env: dict) -> None:
    print(f"\n$ {' '.join(command)}")
    result = subprocess.run(command, cwd=ROOT, env=env)
    if result.returncode != 0:
        sys.exit(f"Command failed with exit code {result.returncode}.")


def main() -> None:
    banner("NEXORA · MySQL setup")

    if not ENV_FILE.exists():
        if not ENV_EXAMPLE.exists():
            sys.exit("Neither .env nor .env.example exists. Restore them first.")
        ENV_FILE.write_text(ENV_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        print("Created .env from .env.example.")

    current = read_env()
    host = ask("MySQL host", current.get("DB_HOST", "127.0.0.1"))
    port = ask("MySQL port", current.get("DB_PORT", "3306"))
    database = ask("Database name", current.get("DB_NAME", "nexora_db"))
    app_user = ask("Application database user", current.get("DB_USER", "nexora_user"))
    admin_user = ask("MySQL administrator username", "root")
    admin_password = getpass.getpass("MySQL administrator password (hidden, blank if none): ")

    print("\nConnecting to MySQL…")
    try:
        connection = pymysql.connect(
            host=host,
            port=int(port),
            user=admin_user,
            password=admin_password,
            charset="utf8mb4",
            autocommit=True,
        )
    except pymysql.err.OperationalError as error:
        code = error.args[0] if error.args else None
        if code == 1045:
            sys.exit(
                "MySQL rejected those administrator credentials (error 1045).\n"
                "Double-check the password, or reset it from MySQL Workbench."
            )
        if code == 2003:
            sys.exit(
                f"Could not reach MySQL at {host}:{port} (error 2003).\n"
                "Start the service first:  net start MySQL267   (or use services.msc)"
            )
        sys.exit(f"MySQL connection failed: {error}")

    app_password = current.get("DB_PASSWORD") or secrets.token_urlsafe(18)

    with connection.cursor() as cursor:
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{database}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        for account_host in ("localhost", "127.0.0.1"):
            cursor.execute(
                "CREATE USER IF NOT EXISTS %s@%s IDENTIFIED BY %s",
                (app_user, account_host, app_password),
            )
            cursor.execute(
                "ALTER USER %s@%s IDENTIFIED BY %s",
                (app_user, account_host, app_password),
            )
            cursor.execute(
                f"GRANT ALL PRIVILEGES ON `{database}`.* TO %s@%s",
                (app_user, account_host),
            )
        cursor.execute("FLUSH PRIVILEGES")

    connection.close()
    print(f"Database `{database}` and user `{app_user}` are ready.")

    write_env_value("DB_ENGINE", "mysql")
    write_env_value("DB_HOST", host)
    write_env_value("DB_PORT", port)
    write_env_value("DB_NAME", database)
    write_env_value("DB_USER", app_user)
    write_env_value("DB_PASSWORD", app_password)
    print("Connection details saved to .env (this file is git-ignored).")

    env = os.environ.copy()
    env.update(
        {
            "DB_ENGINE": "mysql",
            "DB_HOST": host,
            "DB_PORT": port,
            "DB_NAME": database,
            "DB_USER": app_user,
            "DB_PASSWORD": app_password,
        }
    )

    run([sys.executable, "manage.py", "migrate"], env)

    if "--no-seed" not in sys.argv:
        answer = ask("Seed the demonstration records now? (y/n)", "y").lower()
        if answer.startswith("y"):
            run([sys.executable, "manage.py", "seed_demo"], env)

    banner("Done — MySQL is connected")
    print("Start the application with:\n\n    python manage.py runserver\n")
    print("Then open http://127.0.0.1:8000/ and sign in:\n")
    print("    admin    / Nexora@123   (Administrator)")
    print("    manager  / Nexora@123   (Business Owner / Manager)")
    print("    staff    / Nexora@123   (Staff / Employee)\n")


if __name__ == "__main__":
    main()
