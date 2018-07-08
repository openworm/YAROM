__all__ = ['slice_dict']


def slice_dict(d, s):
    return {k: v for k, v in d.items() if k in s}


def FCN(cls):
    return str(cls.__module__) + '.' + str(cls.__name__)
