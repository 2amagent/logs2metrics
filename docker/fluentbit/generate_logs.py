import random
import time

TEMPLATES = [
    "User {user} logged in from {ip}",
    "User {user} logged out",
    "Failed to connect to database at {ip}:5432",
    "Disk usage at {pct}% on volume /data",
    "Request to /api/orders/{oid} completed in {ms}ms",
    "Cache miss for key session:{user}",
    "Payment {oid} declined: insufficient funds",
    "Scheduled job backup-{oid} finished successfully",
]

# A few rare, distinct one-off lines so the demo shows new templates trickling in over time.
NOVEL = [
    "Certificate for {ip} expires in {pct} days",
    "Rate limit exceeded for client {user}",
    "Unhandled exception in worker pid={oid}",
]


def rand_ip() -> str:
    return f"10.0.{random.randint(0, 255)}.{random.randint(1, 254)}"


def render(template: str) -> str:
    return template.format(
        user=random.randint(100, 999),
        ip=rand_ip(),
        pct=random.randint(1, 100),
        oid=random.randint(10000, 99999),
        ms=random.randint(5, 500),
    )


def main() -> None:
    path = "/var/log/generated/sample.log"
    with open(path, "a", buffering=1) as f:
        i = 0
        while True:
            pool = NOVEL if i % 15 == 0 and i > 0 else TEMPLATES
            line = render(random.choice(pool))
            f.write(line + "\n")
            i += 1
            time.sleep(0.5)


if __name__ == "__main__":
    main()
