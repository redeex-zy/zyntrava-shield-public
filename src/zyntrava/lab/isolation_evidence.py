"""Interpret owned-container cleanup evidence conservatively."""


def confirmed_container_absence(returncode: int, stderr: str) -> bool:
    # Daemon/context/authorization errors are not proof that a container is absent.
    return returncode == 1 and any(
        marker in stderr.casefold() for marker in ("no such object:", "no such container:")
    )
