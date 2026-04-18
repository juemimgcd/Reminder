_CACHE: dict[str, object] = {}


def get_cached_object(key: str) -> object | None:
    return _CACHE.get(key)


def set_cached_object(key: str, value: object) -> object:
    _CACHE[key] = value
    return value