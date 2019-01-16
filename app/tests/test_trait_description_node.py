# TODO
if self.trait_description != 'continuous' and \
        self.trait_description != 'binary' and \
        self.trait_description != 'ordinal':
    raise ValueError(
        "Description must be: continuous, binary or ordinal. You provided: {}".format(trait_description))