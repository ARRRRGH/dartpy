from . import components as cmp
import utils.general

import toml
import geopandas as gpd
from shapely.geometry import box
from fiona.crs import from_epsg
import logging
from shutil import copyfile
from pkg_resources import parse_version

import os
from time import gmtime, strftime

# TODO: add all needed xml components and mark with NONE
COMPONENTS = {'atmosphere': cmp.Atmosphere, 'phase': cmp.Phase, 'directions': cmp.Directions, 'plots': cmp.Plots,
              'coeff_diff': cmp.CoeffDiff, 'object3d': cmp.Object3d, 'maket': cmp.Maket}
CONFIG_FILE_NAME = 'config.toml'
USER_CONFIG_FILE_NAME = 'user_config.toml'
DEFAULT_CONFIG_FILE_PER_VERSION = {'5.6.0': '../default_params/default560.toml',
                                   '5.7.5': '../default_params/default575.toml'}


class Simulation(object):
    """
    Class managing reading, writing and running a DART simulation. This class is meant to be version independent.
    """

    def __init__(self, user_config, default_config=None, patch=True, land_cover=None, maket=None, no_gen=None,
                 *args, **kwargs):
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
        user_config = self._read_config(user_config, *args, **kwargs)
        self.components = {}
        self.component_params = {}

        self.non_generated_components = no_gen

        if patch or self.default_config is not None:
            self.config = self._patch_config(user_config, patch)
        else:
            self.config = user_config

        self._split_config()
        self._generate_components(self.non_generated_components)

    def is_complete(self):
        return None in self.components.values()

    def from_simulation(self, simulation_dir_path, config=None, default_patch=False,
                        copy_xml=None, use_db=None, force_xml_gen=False, *args, **kwargs):
        """
        Create a duplicate simulation.

        :param simulation_dir_path:
        :param args:
        :param kwargs:
        :return:
        """
        # TODO: add an option to reuse certain XML files
        # TODO: add an option to override simulation name and simulation location of loaded config file
        # TODO: add patching for mixed toml and xml when suppliying a config_file (this can be done by simple xml to dict
        # conversion and then patching

        simulation_config_path = os.path.normpath(os.path.join(simulation_dir_path, CONFIG_FILE_NAME))

        # if there is a config_file in the simulation directory and a user config, the configs are patched
        if config is not None and (os.path.exists(simulation_config_path) and os.path.exists(config)):
            sim_config = toml.load(simulation_config_path)
            user_config = toml.load(config)
            config = utils.general.merge_dicts(sim_config, user_config)

        # if there is no simulation config
        elif os.path.exists(simulation_config_path):
            config = simulation_config_path

        if os.path.exists(simulation_config_path):
            if force_xml_gen:
                copy_xml = COMPONENTS.keys()

            # generate all components that are not copied
            self.__init__(config, patch=default_patch, no_gen=copy_xml, *args, **kwargs)

            # copy component xml files
            for comp in copy_xml.keys():
                self.components[comp] = COMPONENTS[comp].from_file(simulation_dir_path, self.path, self.version)

        return self

    def _read_config(self, user_config, *args, **kwargs):
        """
        Read user config and create new simulation directory.
        :param user_config:
        :param args:
        :param kwargs:
        :return:
        """
        if not type(config) == dict:
            user_config = toml.load(user_config)

        # General
        self.dart_path = user_config['dart_path']
        self.version = user_config['dart_version']
        # TODO: check for version consistency

        # Path
        time = strftime("%Y-%m-%d-%H_%M_%S", gmtime())
        self.simulation_name = user_config['simulation_name'] + '_' + time
        self.simulation_location = user_config['simulation_location']
        self.path = os.path.normpath(os.path.join(self.simulation_location, self.simulation_name))
        if os.path.exists(self.path):
            logging.exception(
                'Simulation directory already exists! You cannot create a new simulation in the same directory. ' +
                'Use from_simulation to reload a simulation.')
        else:
            os.makedirs(self.path)
            self.user_config_path = os.path.normpath(os.path.join(self.path, USER_CONFIG_FILE_NAME))
            copyfile(user_config, self.user_config_path)

        return user_config

    def _patch_config(self, user_config, patch=True):
            if self.default_config is None:
                # get most recent version still before this version
                path_ver = [(path, parse_version(version))
                            for version, path in DEFAULT_CONFIG_FILE_PER_VERSION.items()
                            if parse_version(version) <= parse_version(self.version)]
                path_ver.sort(key=lambda i: i[1])
                self.default_config = path_ver[-1][0]

            default_config = toml.load(self.default_config)
            config = utils.general.merge_dicts(default_config, user_config)
            with open(os.path.normpath(os.path.join(self.path, CONFIG_FILE_NAME)), 'w+') as f:
                f.write(toml.dumps(config))

            return config

    def _split_config(self):
        self.component_params['phase'] = self.config.get('phase')
        self.component_params['directions'] = self.config.get('directions')
        self.component_params['maket'] = self.config.get('maket')
        self.component_params['atmosphere'] = self.config.get('atmosphere')
        self.component_params['object3d'] = self.config.get('object3d')
        self.component_params['plots'] = self.config.get('plots')
        self.component_params['coeff_diff'] = self.config.get('coeff_diff')

    def _generate_components(self, ignore=None):
        for comp, cls in COMPONENTS.items():
            if ignore is not None and comp in ignore:
                continue

            if cls is None:
                raise NotImplementedError('Not all Components are implemented. Use from_simulation to simply' +
                                          ' copy the missing xml files')

            self.components[comp] = cls(self.component_params[comp])

    def to_file(self):
        for component in self.components.values():
            component.to_file()

    def run(self):
        raise NotImplemented
