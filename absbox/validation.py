


def validation(deal):
    errors = []
    warnings = []
    if len(errors) > 0:
        return False,errors,warnings
    else:
        return True,[],warnings