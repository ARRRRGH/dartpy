import simulation.simulation as simul

def base_test():
    sim = simul.Simulation('D:/dartpy/config_templates/base560.toml')
    print(sim.default_config)
    sim.to_file()

def from_simulation_test():
    sim = simul.Simulation.from_simulation('D:/DART_575_v1140/DART_575/user_data/simulations/Simulation - Copy', copy_xml='all')


if __name__ == '__main__':
    base_test()