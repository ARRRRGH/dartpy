import simulation.simulation as simul

def base_test():
    sim = simul.Simulation('D:/dartpy/config_templates/base560.toml')
    print(sim.default_config)
    sim.write()


if __name__ == '__main__':
    base_test()