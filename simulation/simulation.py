from . import components as cmp
import utils.general

import toml
import geopandas as gpd
from shapely.geometry import box
from fiona.crs import from_epsg
import logging
from shutil import copyfile

import os
from time import gmtime, strftime


CONFIG_FILE_NAME = 'config.toml'
USER_CONFIG_FILE_NAME = 'user_config.toml'
DEFAULT_CONFIG_FILE_PER_VERSION = {'5.6.0': '../default_params/default560.toml'}


class Simulation(object):
    """
    Class managing reading, writing and running a DART simulation. This class is meant to be version independent.
    """

    def __init__(self, config_file_path, default_config=None, patch=True, *args, **kwargs):
        """
        Create new simulation from a user specified config file. This config file is patched to a default config file
        that can be supplied. If default_config is None the user config file is patched to a predefined config file. The
        simulation directory will contain both the user config file and the patched config file for easy introspection.

        :param config_file_path:
        :param default_config:
        :param args:
        :param kwargs:
        """
        self.default_config = default_config
        user_config = self._read_config(config_file_path, *args, **kwargs)
        self.config = self._merge_config(user_config, patch)
        self._split_config()

    def from_simulation(self, simulation_dir_path, use_xml=None, use_db=None, *args, **kwargs):
        """
        Create a duplicate simulation.

        :param simulation_dir_path:
        :param args:
        :param kwargs:
        :return:
        """
        # TODO: add an option to reuse certain XML files
        # TODO: add an option to override simulation name and simulation location of loaded config file
        config_path = os.path.join(simulation_dir_path, CONFIG_FILE_NAME)
        if os.path.exists(config_path):
            self.__init__(config_path, *args, **kwargs)

    def _read_config(self, config_path, *args, **kwargs):
        """
        Read user config and create new simulation directory.
        :param config_path:
        :param args:
        :param kwargs:
        :return:
        """
        user_config = toml.load(config_path)

        # General
        self.dart_path = user_config['dart_path']
        self.version = user_config['dart_version']
        # TODO: check for version consistency

        # Path
        time = strftime("%Y-%m-%d-%H:%M:%S", gmtime())
        self.simulation_name = user_config['simulation_name'] + '_' + time
        self.simulation_location = user_config['simulation_location']
        self.path = os.path.join(self.simulation_location, self.simulation_name)
        if os.path.exists(self.path):
            logging.exception(
                'Simulation directory already exists! You cannot create a new simulation in the same directory. ' +
                'Use from_simulation to reload a simulation.')
        else:
            os.makedirs(self.path)
            self.user_config_path = os.path.join(self.path, USER_CONFIG_FILE_NAME)
            copyfile(config_path, self.user_config_path)

        return user_config

    def _merge_config(self, user_config, patch=True):
        if patch:
            if self.default_config is None:
                # TODO: implement proper version handling, i.e. geq
                self.default_config = DEFAULT_CONFIG_FILE_PER_VERSION[self.version]

            default_config = toml.load(self.default_config)
            config = utils.general.merge_dicts(default_config, user_config)
            with open(os.path.join(self.path, CONFIG_FILE_NAME), 'w+') as f:
                f.write(toml.dumps(config))

            return config
        else:
            return user_config

    def _split_config(self):
        self.run_params = self.config.run_parameters
        self.phase_params = self.config.phase
        self.product_params = self.config.products
        self.direction_params = self.config.directions
        self.sensor_params = self.config.sensor
        self.maket_params = self.config.maket
        self.atmosphere_params = self.config.atmosphere
        self.object3d_params = self.config.object3d
        self.post_processing_params = self.config.postprocessing

        # ROI
        try:
            self.ROI = gpd.GeoDataFrame({'geometry': box(self.config.geometry.ROI)},
                                        crs=from_epsg(self.config.geometry.epsg))
        except ValueError:
            self.ROI = None

    def write(self):
        # Write atmosphere XML
        cmp.Atmosphere(self.path, self.atmosphere_params, self.version).to_file()

    def run(self):
        raise NotImplemented
