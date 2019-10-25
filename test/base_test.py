import simulation.simulation as simul
import simulation.components as cmp
import xmldiff.main
import xmldiff.formatting
import pickle
import utils.general


def base_test():
    sim = simul.Simulation('D:/dartpy/config_templates/base575.toml',
                           no_gen='not_implemented',
                           simulation_name='new',
                           simulation_location='D:/DART_575_v1140/DART_575/user_data/simulations/test')
    sim.to_file()
    return sim


def from_simulation_test():
    sim = simul.Simulation.from_simulation(
        config='D:/dartpy/config_templates/base575.toml',
        default_patch=True,
        version='5.7.5',
        base_path='D:/DART_575_v1140/DART_575/user_data/simulations/simulationTest',
        copy_xml='not_implemented + atmosphere',
        simulation_name='new',
        simulation_location='D:/DART_575_v1140/DART_575/user_data/simulations/test')
    sim.to_file()
    return sim


def from_simulation_xml_patch_test():
    sim = simul.Simulation.from_simulation(
        config='D:/dartpy/config_templates/base575.toml',
        default_patch=True,
        version='5.7.5',
        base_path='D:/DART_575_v1140/DART_575/user_data/simulations/simulationTest',
        copy_xml='not_implemented',
        simulation_name='xmlpatchTest',
        simulation_location='D:/DART_575_v1140/DART_575/user_data/simulations/test',
        xml_patch='all - atmosphere')
    sim.to_file()
    return sim


def none_test():
    sim = simul.Simulation.from_simulation(
        config=None,
        default_patch=False,
        version='5.7.5',
        base_path='D:/DART_575_v1140/DART_575/user_data/simulations/simulationTest',
        copy_xml='all',
        simulation_name='xmlpatchTest',
        simulation_location='D:/DART_575_v1140/DART_575/user_data/simulations/test')

    sim = simul.Simulation(None,
                           no_gen='not_implemented',
                           simulation_name='new',
                           simulation_location='D:/DART_575_v1140/DART_575/user_data/simulations/test')
    return sim


def load_test():
    sim = from_simulation_xml_patch_test()
    sim.load(sim.path)
    return sim


def diff_xmls(path1, path2, path3):
    diff = xmldiff.main.diff_files(path1, path2, formatter=xmldiff.formatting.XMLFormatter())
    with open(utils.general.create_path(path3, 'input', 'diff.xml'), 'w') as f:
        f.write(diff)


if __name__ == '__main__':
    #from_simulation_test()
    # base_test()
    #print(none_test().__dict__)
    print(load_test().component_params)
