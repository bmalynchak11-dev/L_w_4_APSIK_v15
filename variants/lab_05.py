import yaml


def _validate_port(port: int) -> None:
    if not (1 <= port <= 65535):
        raise ValueError(f"Некоректний порт: {port}")


def compose_web_db(
    project: str,
    web_image: str,
    web_port: int,
    web_health: list,
    db_image: str,
    db_name: str,
    db_user: str,
    host_port: int,
    build_context: str | None = None,
) -> str:
    # 1. Валідація образу бази (рядок postgres має входити в назву)
    if "postgres" not in db_image:
        raise ValueError(f"Образ бази даних має бути PostgreSQL: {db_image}")

    # 2. Валідація портів (спочатку web_port, потім host_port)
    _validate_port(web_port)
    _validate_port(host_port)

    # Конфігурація служби db
    db_service = {
        "image": db_image,
        "restart": "unless-stopped",
        "environment": {
            "POSTGRES_DB": db_name,
            "POSTGRES_USER": db_user,
            "POSTGRES_PASSWORD": "${POSTGRES_PASSWORD:?Задайте POSTGRES_PASSWORD у файлі .env}",
        },
        "healthcheck": {
            "test": ["CMD-SHELL", f"pg_isready -U {db_user} -d {db_name}"],
            "interval": "10s",
            "timeout": "5s",
            "retries": 5,
        },
    }

    # Конфігурація служби web
    web_service = {
        "image": web_image,
        "restart": "unless-stopped",
        "ports": [f"127.0.0.1:{host_port}:{web_port}"],
        "environment": {
            "DATABASE_URL": f"postgresql://{db_user}:${{POSTGRES_PASSWORD}}@db:5432/{db_name}"
        },
        "depends_on": {
            "db": {
                "condition": "service_healthy"
            }
        },
        "healthcheck": {
            "test": web_health,
            "interval": "10s",
            "timeout": "5s",
            "retries": 3,
            "start_period": "5s",
        },
    }

    if build_context is not None:
        web_service["build"] = {"context": build_context}

    compose_data = {
        "name": project,
        "services": {
            "db": db_service,
            "web": web_service,
        },
    }

    # Генерація чистого YAML без табуляцій та cr
    output = yaml.dump(compose_data, sort_keys=False, allow_unicode=True)
    if not output.endswith("\n"):
        output += "\n"
    return output