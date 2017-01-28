
__all__ = [
    'warn_mismapping',
    'log_raise_mismapping_exception',
    'raise_mismapping_exception',
    'warn_mismapping']


def mismapMessage(mapping, key, should_be, is_actually):
    return "Mismapping of {} in {}. Is {}. Should be {}".format(
        key,
        mapping,
        is_actually,
        should_be)


def warn_mismapping(logger, mapping, key, should_be, is_actually=None):
    logger.warning(create_mismap_message(mapping, key, should_be, is_actually))


def raise_mismapping_exception(mapping, key, should_be, is_actually=None):
    raise Exception(create_mismap_message(mapping, key, should_be, is_actually))


def log_raise_mismapping_exception(
        logger,
        mapping,
        key,
        should_be,
        is_actually=None):
    warning_message = create_mismap_message(mapping, key, should_be, is_actually)
    logger.warning(warning_message)
    raise Exception(warning_message)


def create_mismap_message(mapping, key, should_be, is_actually):
    is_actually = get_actual(mapping, key, is_actually)
    return mismapMessage(mapping, key, should_be, is_actually)


def get_actual(mapping, key, is_actually):
    if is_actually is None:
        is_actually = mapping[key]
