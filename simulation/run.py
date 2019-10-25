class SimulationRunner(object):
    """
    Class dispatching and handling the running of possibly multiple DART simulations
    """

    def __init__(self, simulation):
        self.simulation = simulation

    def run(self, *args, **kwargs):
        raise NotImplemented

    def _dart_run(self, *args, **kwargs):
        raise NotImplemented
