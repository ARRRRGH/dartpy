from . import components as cmp
import utils.general

from pkg_resources import parse_version

import toml
import logging
from shutil import copyfile
from pkg_resources import parse_version

import os
from time import gmtime, strftime

# TODO: add all needed xml components and mark with NONE
COMPONENTS = {'atmosphere': cmp.Atmosphere, 'phase': cmp.Phase, 'directions': cmp.Directions, 'plots': cmp.Plots,
              'coeff_diff': cmp.CoeffDiff, 'object3d': cmp.Object3d, 'maket': cmp.Maket, 'inversion': cmp.Inversion,
              'trees': cmp.Trees, 'triangleFile': cmp.TriangleFile, 'urban': cmp.Urban, 'water': cmp.Water}

CONFIG_FILE_NAME = 'config.toml'
DEFAULT_CONFIG_FILE_PER_VERSION = {'5.6.0': '../default_params/default560.toml',
                                   '5.7.5': '../default_params/default575.toml'}


class Simulation(object):
    """
    Class managing reading, writing and running a DART simulation. This class is meant to be version independent.
    """

    def __init__(self, config, default_config=None, default_patch=True, xml_patch=None, land_cover=None, maket=None,
                 no_gen=None, version='5.7.5', simulation_name=None, simulation_location=None, dart_path=None, *args,
                 **kwargs):
        """
        Create new simulation from a user specified config file. This config file is patched to a default config file
        that can be supplied. If default_config is None the user config file is patched to a predefined config file. The
        simulation directory will contain both the user config file and the patched config file for easy introspection.

        :param user_config:
        :param default_config:
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
                self._split_config()

        else:
            if type(config) is str:
                config = toml.load(config)

            self.config = Simulation._patch_configs(config, init_user_config, [None])
            if default_patch:
                self.config = self._patch_to_default(self.config)
            self._split_config()

        self._create_simulation_dir(self.config, *args, **kwargs)
        self._generate_components(ignore=self.non_generated_components, xml_patch=self.xml_patch)

    def is_complete(self):
        return None in self.components.values()

    @classmethod
    def from_simulation(cls, path, config=None, default_patch=False, simulation_patch=True, xml_patch=None,
                        copy_xml=None, use_db=None, *args, **kwargs):
        """
        Create a duplicate simulation. Any supplied config is patched to the config in the simulation direct if there is
        one and if simulation_patch=True.

        :param simulation_patch: whether to patch config to the simulation dir config
        :param default_patch: whether to patch the possibly patched (config + simulation dir config) to a default
        :param use_db:
        :param copy_xml:
        :param path:
        :param args:
        :param kwargs:
        :return:
        """
        # TODO: add patching for mixed toml and xml when suppliying a config_file

        simulation_config_path = utils.general.create_path(path, CONFIG_FILE_NAME)

        user_config_valid = config is not None and os.path.exists(config)
        if not user_config_valid and config is not None:
            raise Exception('config file path does not exist')

        simulation_patch_valid = simulation_patch  and os.path.exists(simulation_config_path)

        # if there is a config_file in the simulation directory and a user config, the configs are patched
        if simulation_patch_valid and user_config_valid:
            config = Simulation._patch_configs(toml.load(simulation_config_path), toml.load(config))

        # if there is no user config but a config in the simulation directory
        elif simulation_patch_valid and not user_config_valid:
            config = simulation_config_path

        if os.path.exists(path):
            # generate valid xml_patch_path input
            xml_patch = cls._convert_component_to_path(xml_patch, path)

            # generate all components that are not copied
            sim = cls(config, default_patch=default_patch, no_gen=copy_xml, xml_patch=xml_patch, *args, **kwargs)

            # copy component xml files
            for comp in sim.non_generated_components:
                sim.components[comp] = COMPONENTS[comp].from_simulation(simulation_dir=sim.path, path=path,
                                                                        version=sim.version)

        else:
            raise Exception('Simulation directory ' + path + ' does not exist.')
        return sim

    @classmethod
    def _convert_component_to_path(cls, lis, simulation_dir_path):
        lis = cls._convert_component_kwarg(lis)

        for i, l in enumerate(lis):
            if type(l) is str and l in COMPONENTS.keys():
                lis[i] = (l, utils.general.create_path(simulation_dir_path, 'input', COMPONENTS[l].COMPONENT_FILE_NAME))
        return lis

    @staticmethod
    def _convert_component_kwarg(kwarg):
        if kwarg is None:
            return []

        if type(kwarg) is not str:
            return kwarg

        if kwarg == 'all':
            kwarg = list(COMPONENTS.keys())
        elif kwarg == 'not_implemented':
            kwarg = [comp for comp in COMPONENTS.keys() if not COMPONENTS[comp].is_implemented()]

        return kwarg

    def _create_simulation_dir(self, config, version=None, *args, **kwargs):
        """
        Read user config and create new simulation directory.
        :param user_config:
        :param args:
        :param kwargs:
        :return:
        """
        if type(config) == str:
            user_config_path = config
            user_config = toml.load(config)
        elif type(config) == dict:
            user_config_path = None
            user_config = config
        else:
            raise Exception('config must be a path to a valid toml file or a dictionary.')

        # General
        self.dart_path = user_config['dart_path']

        if version is not None and parse_version(version) != parse_version(user_config['version']):
            raise Exception('Version inconsistency')
        else:
            self.version = user_config['version']

        # Path
        time = strftime("%Y-%m-%d-%H_%M_%S", gmtime())
        self.simulation_name = user_config['simulation_name'] + '_' + time
        self.simulation_location = user_config['simulation_location']
        self.path = utils.general.create_path(self.simulation_location, self.simulation_name)
        if os.path.exists(self.path):
            logging.exception(
                'Simulation directory already exists! You cannot create a new simulation in the same directory. ' +
                'Use from_simulation to reload a simulation.')
        else:
            os.makedirs(self.path)
            self.user_config_path = utils.general.create_path(self.path, CONFIG_FILE_NAME)
            if user_config_path is not None:
                copyfile(user_config_path, self.user_config_path)
            else:
                with open(self.user_config_path, 'w+') as f:
                    f.write(toml.dumps(user_config))

    def _patch_to_default(self, user_config):
        if self.default_config is None:
            # get most recent version still before this version
            path_ver = [(path, parse_version(version))
                        for version, path in DEFAULT_CONFIG_FILE_PER_VERSION.items()
                        if parse_version(version) <= parse_version(user_config['version'])]
            path_ver.sort(key=lambda i: i[1])
            self.default_config = path_ver[-1][0]

        return Simulation._patch_configs(toml.load(self.default_config), user_config)

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
                                        params=self.component_params[comp], xml_patch=xml_patch.get(comp))

    def to_file(self):
        for component in self.components.values():
            component.to_file()

    def run(self):
        raise NotImplemented
