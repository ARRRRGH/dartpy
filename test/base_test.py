import simulation.simulation as simul
import simulation.components as cmp


def base_test():
    sim = simul.Simulation('/Users/jim/Studium/REMOTE_SENSING/DART/dartpy/config_templates/base575.toml', no_gen='not_implemented')
    print(sim.default_config)
    sim.to_file()


def from_simulation_test():
    sim = simul.Simulation.from_simulation(
        config='D:/dartpy/config_templates/base575.toml',
        default_patch=True,
        version='5.7.5',
        path='D:/DART_575_v1140/DART_575/user_data/simulations/simulationTest',
        copy_xml='not_implemented',
        simulation_name='new',
        simulation_location='D:/DART_575_v1140/DART_575/user_data/simulations/test')
    sim.to_file()
    print(sim.components)


if __name__ == '__main__':
    #from_simulation_test()
    base_test()