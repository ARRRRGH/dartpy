
import utils.xml_utils
from . import components as cmp
from . import run
import utils.general

import toml
import logging
from pkg_resources import parse_version
import dill
import os
from time import gmtime, strftime
import re


COMPONENTS = {'atmosphere': cmp.Atmosphere, 'phase': cmp.Phase, 'directions': cmp.Directions, 'plots': cmp.Plots,
              'coeff_diff': cmp.CoeffDiff, 'object3d': cmp.Object3d, 'maket': cmp.Maket, 'inversion': cmp.Inversion,
              'trees': cmp.Trees, 'triangleFile': cmp.TriangleFile, 'urban': cmp.Urban, 'water': cmp.Water}

CONFIG_FILE_NAME = 'config.toml'
DEFAULT_CONFIG_FILE_PER_VERSION = {'5.7.5': '../default_params/default575.toml'}
DILL_FIL = 'simulation.dill'


class Simulation(object):
    def __init__(self, config, default_config=None, default_patch=True, xml_patch=None, land_cover=None, maket=None,
                 no_gen=None, version='5.7.5', simulation_name='new', simulation_location='./test_simulations',
                 dart_path=None, *args, **kwargs):
        """
        Create a new simulation. Configs are patched in the following order: xml_patch, default_patch, config, args

        :param config (str, dict or list of str and dict): paths to config files or config dicts, higher indices override
        :param default_config (path or bool): if True get default to closest lower version
        :param xml_patch (list of tuples): tuples of the form (component_name, path)
        :param args:
        :param kwargs:
        """
        self.default_config = default_config
        self.non_generated_components = self._convert_component_kwarg(no_gen)

        self.xml_patch = xml_patch

        self.land_cover = land_cover
        self.maket = maket

        self.components = {}
        self.component_params = {}

        init_user_config = {'version': version, 'simulation_name': simulation_name,
                            'simulation_location': simulation_location, 'dart_path': dart_path}

        self.config = None
        if config is None:
            # if no user_config and no default is supplied
            # create minimal user_config for simulation directory instantiation
            if not default_patch:
                self.config = init_user_config
                self.non_generated_components = list(COMPONENTS.keys())
                logging.warning('No config nor default was supplied. No components are being generated. '
                                + 'You might be copying them though. In this case ignore this warning.')
            else:
                self.config = self._patch_to_default(init_user_config)
        else:
            if not hasattr(config, '__iter__') or type(config) is str:
                config = [config]

            patched_config = {}
            for conf in config:
                if type(conf) is str:
                    conf = toml.load(conf, _dict=dict)
                patched_config = utils.general.merge_dicts(src_dict=patched_config, patch_dict=conf)

            self.config = self._patch_configs(patched_config, init_user_config, [None])
            if default_patch:
                self.config = self._patch_to_default(self.config)

        self._split_config()
        self._create_simulation_dir(self.config, *args, **kwargs)
        self._generate_components(ignore=self.non_generated_components, xml_patch=self.xml_patch)

        self._is_to_file = False

    def is_complete(self):
        return None in self.components.values()

    @property
    def user_config_path(self):
        return utils.general.create_path(self.path, CONFIG_FILE_NAME)

    @classmethod
    def load(cls, path):
        with open(utils.general.create_path(path, DILL_FIL), 'rb') as f:
            return dill.load(f)

    @classmethod
    def from_simulation(cls, base_path, config=None, default_patch=False, simulation_patch=True, xml_patch=None,
                        copy_xml=None, no_gen=None, use_db=None, force=False, *args, **kwargs):
        """
        Create a new simulation based on an existing simulation directory. Configs are patched in the following order:
        xml_patch, default_patch, base_simulation_config, config, args

        :param default_config (path or bool): if True get default to closest lower version
        :param base_path: path to the base simulation
        :param simulation_patch (bool): whether to patch config to the base simulation config
        :param xml_patch (str or list of str or list of tuples): component names or tuples of the form (name, path),
                                                  if only name is supplied the component xml of the base simulation
                                                  is used, 'all', 'implemented' and 'not_implemented' and the component
                                                  names can be used in one string with - and + operators as well
        :param use_db:
        :param copy_xml (str or list of str): see xml_patch
        :param force: disregard version inconsistencies
        :param args:
        :param kwargs:
        :return:
        """

        simulation_config_path = utils.general.create_path(base_path, CONFIG_FILE_NAME)

        user_config_valid = config is not None and os.path.exists(config)
        if not user_config_valid and config is not None:
            raise Exception('config file path does not exist')

        simulation_patch_valid = simulation_patch and os.path.exists(simulation_config_path)

        # if there is a config_file in the simulation directory and a user config, the configs are patched
        if simulation_patch_valid and user_config_valid:
            config = Simulation._patch_configs(toml.load(simulation_config_path, _dict=dict), toml.load(config, _dict=dict))

        # if there is no user config but a config in the simulation directory and simulation_patch=True
        elif simulation_patch_valid and not user_config_valid:
            config = simulation_config_path

        if os.path.exists(base_path):
            # generate valid xml_patch_path input
            xml_patch = cls._convert_component_to_path(xml_patch, base_path)

            # generate all components that are not copied and are not excluded by no_gem
            no_gen_tot = copy_xml = cls._convert_component_kwarg(copy_xml)
            if no_gen is not None:
                no_gen_tot = no_gen_tot.union(cls._convert_component_kwarg(no_gen))

            sim = cls(config, default_patch=default_patch, no_gen=no_gen_tot, xml_patch=xml_patch, *args, **kwargs)

            # copy component xml files of copy_xml components
            for comp in copy_xml:
                sim.components[comp] = COMPONENTS[comp].from_simulation(simulation_dir=sim.path, base_path=base_path,
                                                                        version=sim.version, force=force)
        else:
            raise Exception('Simulation directory ' + base_path + ' does not exist.')
        return sim

    @classmethod
    def _convert_component_to_path(cls, lis, simulation_dir_path):
        """
        convert shortcut path to valid list of tuples

        :param lis:
        :param simulation_dir_path:
        :return:
        """
        lis = cls._convert_component_kwarg(lis)

        ret = []
        for i, l in enumerate(lis):
            if type(l) is str and l in COMPONENTS.keys():
                ret.append((l, utils.general.create_path(simulation_dir_path, 'input',
                                                         COMPONENTS[l].COMPONENT_FILE_NAME)))
            elif type(l) is tuple:
                ret[i].append(l)
            else:
                raise Exception('Must be a list with elements of type either tuple or string.')

        return ret

    @staticmethod
    def _convert_component_kwarg(kwarg):
        """
        convert shortcut path to list of components

        :param kwarg:
        :return:
        """
        if kwarg is None:
            return set()

        if type(kwarg) is not str:
            return set(kwarg)

        lis = re.findall(r'(\+|\-)?\s?([a-zA-Z_]+)', kwarg)
        kwarg = set()
        for op, kw in lis:
            if kw == 'all':
                kw = set(COMPONENTS.keys())
            elif kw == 'not_implemented':
                kw = set([comp for comp in COMPONENTS.keys() if not COMPONENTS[comp].is_implemented()])
            elif kw == 'implemented':
                kw = set([comp for comp in COMPONENTS.keys() if COMPONENTS[comp].is_implemented()])
            elif kw in COMPONENTS.keys():
                kw = {kw}
            else:
                raise Exception('kwarg ' + str(kw) + ' is not a component.')
            if op == '' or op == '+':
                kwarg = kwarg.union(kw)

            elif op == '-':
                kwarg = kwarg.difference(kw)

        return kwarg

    def _create_simulation_dir(self, user_config, *args, **kwargs):
        """
        Create new simulation directory. Check for version consistency
        :param user_config:
        :param args:
        :param kwargs:
        :return:
        """

        # General
        self.dart_path = user_config['dart_path']
        self.version = user_config['version']

        # Path
        time = strftime("%Y-%m-%d-%H_%M_%S", gmtime())
        simulation_name = user_config['simulation_name'] + '_' + time
        simulation_location = user_config['simulation_location']
        self.path = utils.general.create_path(simulation_location, simulation_name)
        if os.path.exists(self.path):
            logging.exception(
                'Simulation directory already exists! You cannot create a new simulation in the same directory. ' +
                'Use from_simulation to reload a simulation.')
        else:
            os.makedirs(self.path)
            self.save(user_config)

    def save(self, config=None):
        if config is not None:
            with open(self.user_config_path, 'w+') as f:
                f.write(toml.dumps(config))

        with open(utils.general.create_path(self.path, DILL_FIL), 'wb') as f:
            dill.dump(self, f, protocol=dill.HIGHEST_PROTOCOL)

    def __getstate__(self):
        save = self.__dict__.copy()

        # TODO: need this because of some toml dict type messing up the pickling, find way to cast these
        # dicts to builtin dict
        save.pop('config')
        save.pop('component_params')
        return save

    def __setstate__(self, state):
        self.__dict__ = state

        # TODO: need this because of some toml dict type messing up the pickling, find way to cast these
        # dicts to builtin dict
        self.config = toml.load(self.user_config_path)
        self.component_params = {}
        self._split_config()

    def _patch_to_default(self, user_config):
        if self.default_config is None:
            # get most recent version still before this version
            path_ver = [(path, parse_version(version))
                        for version, path in DEFAULT_CONFIG_FILE_PER_VERSION.items()
                        if parse_version(version) <= parse_version(user_config['version'])]
            path_ver.sort(key=lambda i: i[1])
            self.default_config = path_ver[-1][0]

        return Simulation._patch_configs(toml.load(self.default_config, _dict=dict), user_config, ignore=[None])

    @staticmethod
    def _patch_configs(src_config, patch_config, ignore=None):
        valid = src_config.get('version') is None or patch_config.get('version') is None \
                or src_config['version'] == patch_config['version']
        if valid:
            return utils.general.merge_dicts(src_config, patch_config, ignore=ignore)
        else:
            raise Exception('Version inconsistency')

    def _split_config(self):
        self.component_params['phase'] = {'params': self.config.get('phase')}
        self.component_params['directions'] = {'params': self.config.get('directions')}
        self.component_params['maket'] = {'params': self.config.get('maket')}
        self.component_params['atmosphere'] = {'params': self.config.get('atmosphere')}
        self.component_params['object3d'] = {'params': self.config.get('object3d')}
        self.component_params['plots'] = {'params': self.config.get('plots'), 'land_cover': self.land_cover}
        self.component_params['coeff_diff'] = {'params': self.config.get('coeff_diff')}

    def _generate_components(self, ignore=None, xml_patch=None):
        if xml_patch is None:
            xml_patch = {}
        else:
            xml_patch = dict(xml_patch)

        for comp, cls in COMPONENTS.items():
            if ignore is not None and comp in ignore:
                continue

            if cls is None:
                raise NotImplementedError('Not all Components are implemented. Use from_simulation to simply' +
                                          ' copy the missing xml files')
            self.components[comp] = cls(simulation_dir=self.path, version=self.version,
                                        xml_patch_path=xml_patch.get(comp), **self.component_params[comp])

    def to_file(self):
        """
        Write simulation to a simulation directory
        :return:
        """
        for component in self.components.values():
            component.to_file()
        self._is_to_file = True

    def run(self, *args, **kwargs):
        """
        Run simulation

        :return:
        """
        run.SimulationRunner(self).run(*args, **kwargs)
