import simulation.simulation as simul

def base_test():
    sim = simul.Simulation('/Users/jim/Studium/REMOTE_SENSING/DART/dartpy/config_templates/base560.toml')
    sim.write()


if __name__ == '__main__':
    base_test()