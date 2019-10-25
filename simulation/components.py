import utils.general

from lxml import etree as et
import os
import logging
from pkg_resources import parse_version
from shutil import copyfile, copytree

from functools import reduce
import operator

import utils.xml_utils

ROOT_TAG = 'DartFile'


class Component(object):
    """
    A component is any entity that is represented by a xml file in the DART simulation folder.
    """
    COMPONENT_FILE_NAME = None
    COMPONENT_NAME = None
    IMPLEMENTED_WRITE_VERSION = []

    def __init__(self, simulation_dir, params, version, xml_patch_path=None, *args, **kwargs):
        """
        Create a component from a params dict. The default config files in ../default_params implicitly define
        the form of the params dict for each version and each component. The dictionary may not be complete. In this
        case the component instantiation will succeed but running the simulation will fail probably. In this case,
        you are advised to  patch params to a valid component xml file using xml_patch_path.

        Check whether there is a component writer for your version by checking if it is in cls.IMPLEMENTED_WRITE_VERSION

        :param simulation_dir:
        :param params:
        :param version:
        :param xml_patch_path: path to a valid component xml file
        """
        self.simulation_dir = simulation_dir
        self.version = version
        self.xml_patch_path = xml_patch_path

        if type(params) is dict:
            self.params = params
            self.xml_root = et.Element(ROOT_TAG)
            self.xml_root.set('version', self.version)
            self._xml_only = False
        elif type(params) is tuple:
            self.params = None
            self.xml_root, self.original_path = params
            self._xml_only = True
        else:
            raise Exception('params must be a dictionary or a tuple. The tuple form should not be used by the user.')

        self._is_to_file = False
        self._is_patched_to_xml = False
        self._written_params = None

    @classmethod
    def is_implemented(cls):
        return len(cls.IMPLEMENTED_WRITE_VERSION) != 0

    @classmethod
    def is_version_implemented(cls, version):
        return version in cls.IMPLEMENTED_WRITE_VERSION

    @classmethod
    def from_simulation(cls, simulation_dir, base_path, version, force=False):
        """
        Create a component from valid component files in an existing simulation (denoted as base simulation). This
        instantiation checks for version consistency and copies all relevant files without changing.

        :param simulation_dir:
        :param base_path:
        :param version:
        :param force:
        :return:
        """
        xml_path = utils.general.create_path(base_path, 'input', cls.COMPONENT_FILE_NAME)
        xml_root = cls._read(xml_path)

        # Check if this is a dart file, if its version is correct (if supplied) and whether it is the correct component
        valid_version = parse_version(xml_root.get('version')) == parse_version(version)
        valid_file = cls.COMPONENT_NAME in [el.tag for el in list(xml_root)]

        if not ((valid_version and valid_file) or force):
            if not valid_version:
                raise Exception(
                    'Cannot load ' + xml_path + ' since file since there is a version mismatch. If you want to proceed'
                    + ' use force=True.')
            if not valid_file:
                raise Exception(
                    'Cannot load ' + xml_path + ' since file it is not a valid dart ' + cls.COMPONENT_NAME + ' file.')
        else:
            return cls(simulation_dir, (xml_root, xml_path), version)

    def patch_to_xml(self, xml_path):
        self.xml_root = utils.xml_utils.merge_xmls(self._read(xml_path), self.xml_root, remove_empty_paths=True)
        self._is_patched_to_xml = True

    def to_file(self):
        """
        Write out the component to file.
        :return:
        """
        inp_path = utils.general.create_path(self.simulation_dir, 'input')
        xml_path = utils.general.create_path(inp_path, self.COMPONENT_FILE_NAME)

        if not os.path.exists(inp_path):
            os.makedirs(inp_path)

        if not self._xml_only:
            self._write(**self.params)
            tree = et.ElementTree(self.xml_root)

            if not os.path.exists(inp_path):
                os.mkdir(inp_path)
            tree.write(xml_path, pretty_print=True)
        else:
            self._copy_from_simulation(self.original_path, xml_path)

        self._is_to_file = True

    @classmethod
    def _read(cls, path):
        tree = et.parse(path)
        return tree.getroot()

    def _write(self, params, *args, **kwargs):
        assert self._check_params(params)

        if parse_version(self.version) >= parse_version('5.7.5'):
            self._write575(params, *args, **kwargs)
        elif parse_version(self.version) >= parse_version('5.6.0'):
            self._write560(params, *args, **kwargs)

        if self.xml_patch_path is not None:
            self.patch_to_xml(self.xml_patch_path)

    @classmethod
    def _copy_from_simulation(cls, copy_xml_path, new_xml_path):
        copyfile(copy_xml_path, new_xml_path)

    def _set(self, el, key, params_path, check=None, as_is=False):
        if not as_is:
            val = self._get(params_path)
        else:
            val = params_path

        self._check_and_set(el, key, self._str_none(val), check=check)

    def _get(self, params_path, params=None):
        if params is None:
            params = self._written_params

        nodes = params_path.split('.')

        for i, n in enumerate(nodes):
            try:
                nodes[i] = int(n)
            except:
                pass

        try:
            return reduce(operator.getitem, nodes, params)
        except:
            return None

    @classmethod
    def _check_and_set(cls, element, key, val, check=None):
        if check is not None:
            assert check(key, val)

        try:
            element.set(key, val)
        except TypeError:
            logging.warning(cls.COMPONENT_NAME + ' component could not set DART parameter ' + key + ' defined as ' +
                            str(val))

    @classmethod
    def _str_none(cls, val):
        if val is not None:
            return str(val)
        return None

    def _check_params(self, params):
        raise NotImplementedError

    def _write575(self, params, *args, **kwargs):
        raise NotImplementedError

    def _write560(self, params, *args, **kwargs):
        raise NotImplementedError

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, state):
        self.__dict__ = state


class Inversion(Component):
    COMPONENT_NAME = 'DartInversion'
    COMPONENT_FILE_NAME = 'inversion.xml'

    def _check_params(self, params):
        return True

    @classmethod
    def _copy_from_simulation(cls, copy_xml_path, new_xml_path):
        Component._copy_from_simulation(copy_xml_path, new_xml_path)

        directory, fil = os.path.split(copy_xml_path)
        lut_properties_path = utils.general.create_path(directory, 'lut.properties')
        if not os.path.exists(lut_properties_path):
            raise Exception('lut.properties does not exist')

        directory, fil = os.path.split(new_xml_path)
        new_lut_properties_path = utils.general.create_path(directory, 'lut.properties')
        copyfile(lut_properties_path, new_lut_properties_path)


class Trees(Component):
    COMPONENT_NAME = 'Trees'
    COMPONENT_FILE_NAME = 'trees.xml'

    def _check_params(self, params):
        return True


class TriangleFile(Component):
    COMPONENT_FILE_NAME = 'triangleFile.xml'
    COMPONENT_NAME = 'TriangleFile'

    def _check_params(self, params):
        return True

    @classmethod
    def _copy_from_simulation(cls, copy_xml_path, new_xml_path):
        Component._copy_from_simulation(copy_xml_path, new_xml_path)

        directory, fil = os.path.split(copy_xml_path)
        bin_path = utils.general.create_path(directory, 'triangleFile.bin')
        if not os.path.exists(bin_path):
            raise Exception('triangleFile.bin does not exist')

        directory, fil = os.path.split(new_xml_path)
        new_bin_path = utils.general.create_path(directory, 'triangleFile.bin')
        copyfile(bin_path, new_bin_path)

        directory, fil = os.path.split(copy_xml_path)
        triangles_path = utils.general.create_path(directory, 'triangles')
        if not os.path.exists(triangles_path):
            raise Exception('triangles directory does not exist')

        directory, fil = os.path.split(new_xml_path)
        new_triangles_path = utils.general.create_path(directory, 'triangles')
        copytree(triangles_path, new_triangles_path)


class Urban(Component):
    COMPONENT_FILE_NAME = 'urban.xml'
    COMPONENT_NAME = 'Urban'

    def _check_params(self, params):
        return True


class Water(Component):
    COMPONENT_FILE_NAME = 'water.xml'
    COMPONENT_NAME = 'Water'

    def _check_params(self, params):
        return True


class Phase(Component):
    COMPONENT_NAME = 'Phase'
    COMPONENT_FILE_NAME = 'phase.xml'
    IMPLEMENTED_WRITE_VERSION = ['5.7.5']

    def _check_params(self, params):
        return True

    def _write575(self, params, *args, **kwargs):
        self._written_params = params

        phase = et.SubElement(self.xml_root, self.COMPONENT_NAME)
        self._set(phase, 'calculatorMethod', 'calculatorMethod')

        # radiative transfer method
        atmosphere_radiative_transfer = et.SubElement(phase, 'AtmosphereRadiativeTransfer')
        self._set(atmosphere_radiative_transfer, 'TOAtoBOA', 'toaToBoa')

        # advanced mode
        expert_mode_zone = et.SubElement(phase, 'ExpertModeZone')
        self._set(expert_mode_zone, 'accelerationEngine', 'expert_flux_tracking.acceleration_engine')
        self._set(expert_mode_zone, 'albedoThreshold', 'expert_flux_tracking.albedoThreshold')
        self._set(expert_mode_zone, 'expertMode', 'expert_flux_tracking.expertMode')
        self._set(expert_mode_zone, 'illuminationRepartitionMode', 'expert_flux_tracking.illuminationRepartitionMode')
        self._set(expert_mode_zone, 'maxNbSceneCrossing', 'expert_flux_tracking.maxNbSceneCrossing')
        self._set(expert_mode_zone, 'lightPropagationThreshold', 'expert_flux_tracking.lightPropagationThreshold')
        self._set(expert_mode_zone, 'nbRandomPointsPerInteceptionAtmosphere',
                  'expert_flux_tracking.nbRandomPointsPerInteceptionAtmosphere')
        self._set(expert_mode_zone, 'nbSubSubcenterTurbidEmission', 'expert_flux_tracking.nbSubSubcenterTurbidEmission')
        self._set(expert_mode_zone, 'subFaceBarycenterEnabled', 'expert_flux_tracking.subFaceBarycenterEnabled')
        self._set(expert_mode_zone, 'subFaceBarycenterSubdivision', 'expert_flux_tracking.subFaceBarycenterSubdivision')
        self._set(expert_mode_zone, 'useExternalScripts', 'expert_flux_tracking.useExternalScripts')
        self._set(expert_mode_zone, 'surfaceBarycenterEnabled', 'expert_flux_tracking.surfaceBarycenterEnabled')
        self._set(expert_mode_zone, 'subFaceBarycenterEnabled', 'expert_flux_tracking.subFaceBarycenterEnabled')
        self._set(expert_mode_zone, 'isInterceptedPowerPerDirectionForSpecularCheck',
                  'expert_flux_tracking.isInterceptedPowerPerDirectionForSpecularCheck')
        self._set(expert_mode_zone, 'nbSubcenterIllumination', 'expert_flux_tracking.nbSubcenterIllumination')
        self._set(expert_mode_zone, 'nbTrianglesWithinVoxelAcceleration',
                  'expert_flux_tracking.nbTrianglesWithinVoxelAcceleration')
        self._set(expert_mode_zone, 'nbSubcenterVolume', 'expert_flux_tracking.nbSubcenterVolume')
        self._set(expert_mode_zone, 'nbThreads', 'expert_flux_tracking.nbThreads')
        self._set(expert_mode_zone, 'sparseVoxelAcceleration', 'expert_flux_tracking.sparseVoxelAcceleration')
        self._set(expert_mode_zone, 'thermalEmissionSurfaceSubdivision',
                  'expert_flux_tracking.thermalEmissionSurfaceSubdivision')
        self._set(expert_mode_zone, 'triangleStorageMode', 'expert_flux_tracking.triangleStorageMode')
        self._set(expert_mode_zone, 'distanceBetweenIlluminationSubCenters',
                  'expert_flux_tracking.distanceBetweenIlluminationSubCenters')

        # *** Dart Input Parameters ***
        dart_input_parameters = et.SubElement(phase, 'DartInputParameters')

        # flux tracking parameters
        nodefluxtracking = et.SubElement(dart_input_parameters, 'nodefluxtracking')
        self._set(nodefluxtracking, 'gaussSiedelAcceleratingTechnique',
                  'flux_tracking.gaussSiedelAcceleratingTechnique')
        self._set(nodefluxtracking, 'numberOfIteration', 'flux_tracking.numberOfIteration')

        # scene 3d temperature
        spectral_domain_tir = et.SubElement(dart_input_parameters, 'SpectralDomainTir')
        self._set(spectral_domain_tir, 'temperatureMode', 'spectral.temperatureMode')

        skyl_temperature = et.SubElement(spectral_domain_tir, 'skylTemperature')
        self._set(skyl_temperature, 'SKYLForTemperatureAssignation', 'temperature.SKYLForTemperatureAssignation')
        self._set(skyl_temperature, 'distanceBetweenIlluminationSubCenters',
                  'temperature.distanceBetweenIlluminationSubCenters')
        self._set(skyl_temperature, 'histogramThreshold', 'temperature.histogramThreshold')

        # spectral intervals
        spectral_intervals = et.SubElement(dart_input_parameters, 'SpectralIntervals')

        if self._get('spectral.meanLambda') is not None:
            for n in range(len(self._get('spectral.meanLambda'))):
                spectral_intervals_properties = et.SubElement(spectral_intervals, 'SpectralIntervalsProperties')
                self._set(spectral_intervals_properties, 'bandNumber', n, as_is=True)
                self._set(spectral_intervals_properties, 'deltaLambda', 'spectral.deltaLambda.' + str(n))
                self._set(spectral_intervals_properties, 'meanLambda', 'spectral.meanLambda.' + str(n))
                self._set(spectral_intervals_properties, 'spectralDartMode', 'spectral.spectralDartMode.' + str(n))

        # atmosphere brightness temperature
        temperature_atmosphere = et.SubElement(dart_input_parameters, 'temperatureAtmosphere')
        self._set(temperature_atmosphere, 'atmosphericApparentTemperature',
                  'temperature.atmosphericApparentTemperature')

        image_side_illumination = et.SubElement(dart_input_parameters, 'ImageSideIllumination')
        self._set(image_side_illumination, 'disableSolarIllumination', 'image_illumination.disableSolarIllumination')
        self._set(image_side_illumination, 'disableThermalEmission', 'image_illumination.disableThermalEmission')
        self._set(image_side_illumination, 'sideIlluminationEnabled', 'image_illumination.sideIlluminationEnabled')

        # earth scene irradiance
        node_illumination_mode = et.SubElement(dart_input_parameters, 'nodeIlluminationMode')
        # self._set(node_illumination_mode, 'illuminationMode', 'irradiance.illuminationMode')
        self._set(node_illumination_mode, 'irradianceMode', 'irradiance.irradianceMode')

        irradiance_database_node = et.SubElement(node_illumination_mode, 'irradianceDatabaseNode')
        self._set(irradiance_database_node, 'databaseName', 'irradiance.databaseName')
        self._set(irradiance_database_node, 'irradianceColumn', 'irradiance.irradianceColumn')
        self._set(irradiance_database_node, 'irradianceTable', 'irradiance.irradianceTable')
        self._set(irradiance_database_node, 'weightAtmosphereParameters', 'irradiance.weightAtmosphereParameters')
        self._set(irradiance_database_node, 'weightReflectanceParameters', 'irradiance.weightReflectanceParameters')

        weighting = et.SubElement(irradiance_database_node, 'WeightingParameters')
        self._set(weighting, 'sceneAverageTemperatureForPonderation',
                  'irradiance.sceneAverageTemperatureForPonderation')

        spectral_irradiance = et.SubElement(node_illumination_mode, 'SpectralIrradiance')

        common_parameters = et.SubElement(spectral_irradiance, 'CommonParameters')
        self._set(common_parameters, 'commonIrradianceCheckBox', 'irradiance.commonIrradianceCheckBox')
        self._set(common_parameters, 'commonSkylCheckBox', 'irradiance.commonSkylCheckBox')
        self._set(common_parameters, 'irraDef', 'irradiance.irraDef')

        spectral_irradiance_value = et.SubElement(spectral_irradiance, 'SpectralIrradianceValue')
        self._set(spectral_irradiance_value, 'Skyl', 'irradiance.Skyl')
        self._set(spectral_irradiance_value, 'bandNumber', 'irradiance.bandNumber')
        self._set(spectral_irradiance_value, 'irradiance', 'irradiance.irradiance')

        # *** Dart Products ***
        dart_product = et.SubElement(phase, 'DartProduct')

        dart_module_products = et.SubElement(dart_product, 'dartModuleProducts')
        common_products = et.SubElement(dart_module_products, 'CommonProducts')
        self._set(common_products, 'polarizationProducts', 'products.common.polarizationProducts')
        self._set(common_products, 'radiativeBudgetProducts', 'products.common.radiativeBudgetProducts')

        flux_tracking_products = et.SubElement(dart_module_products, 'FluxTrackingModeProducts')
        self._set(flux_tracking_products, 'allIterationsProducts', 'products.flux_tracking.allIterationsProducts')
        self._set(flux_tracking_products, 'brfProducts', 'products.flux_tracking.brfProducts')
        # self._set(dart_module_products, 'lidarImageProducts',        #                     'products.lidarImageProducts')
        # self._set(dart_module_products, 'lidarProducts',        #                     'products.lidarProducts')
        self._set(flux_tracking_products, 'order1Products', 'products.flux_tracking.order1Products')
        self._set(flux_tracking_products, 'temperaturePerTrianglePerCell',
                  'products.flux_tracking.temperaturePerTrianglePerCell')

        # TODO: find out what this is
        radiative_budget_properties = et.SubElement(common_products, 'radiativeBudgetProperties')
        self._set(radiative_budget_properties, 'binaryFormat', 'products.radiative_budget_properties.binaryFormat')
        self._set(radiative_budget_properties, 'budget3DParSurface',
                  'products.radiative_budget_properties.budget3DParSurface')
        self._set(radiative_budget_properties, 'budget3DParType',
                  'products.radiative_budget_properties.budget3DParType')
        self._set(radiative_budget_properties, 'budgetTotalParType',
                  'products.radiative_budget_properties.budgetTotalParType')
        self._set(radiative_budget_properties, 'budgetUnitModeR',
                  'products.radiative_budget_properties.budgetUnitModeR')
        self._set(radiative_budget_properties, 'extrapolation', 'products.radiative_budget_properties.extrapolation')
        self._set(radiative_budget_properties, 'fIRfARfSRfINTR1DProducts',
                  'products.radiative_budget_properties.fIRfARfSRfINTR1DProducts')
        self._set(radiative_budget_properties, 'fIRfARfSRfINTR3DProducts',
                  'products.radiative_budget_properties.fIRfARfSRfINTR3DProducts')
        self._set(radiative_budget_properties, 'fIRfARfSRfINTR2DProducts',
                  'products.radiative_budget_properties.fIRfARfSRfINTR2DProducts')
        self._set(radiative_budget_properties, 'budget2DParType',
                  'products.radiative_budget_properties.budget2DParType')

        components = et.SubElement(radiative_budget_properties, 'Components')
        cell_components = et.SubElement(components, 'CellComponents')
        element_components = et.SubElement(cell_components, 'ElementComponents')

        self._set(components, 'absorbed', 'products.radiative_budget_properties.cell_components.absorbed')
        self._set(components, 'backEntry', 'products.radiative_budget_properties.cell_components.backEntry')

        self._set(components, 'backExit', 'products.radiative_budget_properties.cell_components.backExit')
        self._set(components, 'bottomEntry', 'products.radiative_budget_properties.cell_components.bottomEntry')

        self._set(components, 'bottomExit', 'products.radiative_budget_properties.cell_components.bottomExit')
        self._set(components, 'emitted', 'products.radiative_budget_properties.cell_components.emitted')

        self._set(components, 'frontEntry', 'products.radiative_budget_properties.cell_components.frontEntry')
        self._set(components, 'frontExit', 'products.radiative_budget_properties.cell_components.frontExit')

        self._set(components, 'intercepted', 'products.radiative_budget_properties.cell_components.intercepted')
        self._set(components, 'leftEntry', 'products.radiative_budget_properties.cell_components.leftEntry')

        self._set(components, 'leftExit', 'products.radiative_budget_properties.cell_components.leftExit')
        self._set(components, 'rightEntry', 'products.radiative_budget_properties.cell_components.rightEntry')

        self._set(components, 'rightExit', 'products.radiative_budget_properties.cell_components.rightExit')
        self._set(components, 'scattered', 'products.radiative_budget_properties.cell_components.scattered')
        self._set(components, 'topEntry', 'products.radiative_budget_properties.cell_components.topEntry')

        self._set(components, 'topExit', 'products.radiative_budget_properties.cell_components.topExit')
        self._set(components, 'totalEntry', 'products.radiative_budget_properties.cell_components.totalEntry')
        self._set(components, 'totalExit', 'products.radiative_budget_properties.cell_components.totalExit')

        self._set(components, 'absorbed', 'products.radiative_budget_properties.element_components.absorbed')
        self._set(components, 'emitted', 'products.radiative_budget_properties.element_components.emitted')

        self._set(components, 'intercepted', 'products.radiative_budget_properties.element_components.intercepted')
        self._set(components, 'scattered', 'products.radiative_budget_properties.element_components.scattered')

        brf_products_properties = et.SubElement(flux_tracking_products, 'BrfProductsProperties')
        self._set(brf_products_properties, 'brfProduct', 'products.brf_properties.brfProduct')
        self._set(brf_products_properties, 'extrapolation', 'products.brf_properties.extrapolation')
        self._set(brf_products_properties, 'horizontalOversampling', 'products.brf_properties.horizontalOversampling')
        # self._set(BrfProductsProperties,'ifSensorImageSimulation', '0')
        self._set(brf_products_properties, 'image', 'products.brf_properties.image')
        self._set(brf_products_properties, 'luminanceProducts', 'products.brf_properties.luminanceProducts')
        self._set(brf_products_properties, 'maximalThetaImages', 'products.brf_properties.maximalThetaImages')
        self._set(brf_products_properties, 'nb_scene', 'products.brf_properties.nb_scene')
        # self._set(BrfProductsProperties,'outputHapkeFile', '0')
        self._set(brf_products_properties, 'projection', 'products.brf_properties.projection')
        self._set(brf_products_properties, 'sensorOversampling', 'products.brf_properties.sensorOversampling')
        self._set(brf_products_properties, 'sensorPlaneprojection', 'products.brf_properties.sensorPlaneprojection')
        self._set(brf_products_properties, 'transmittanceImages', 'products.brf_properties.transmittanceImages')
        self._set(brf_products_properties, 'pixelToSceneCorrespondences',
                  'products.brf_properties.pixelToSceneCorrespondences')
        self._set(brf_products_properties, 'centralizedBrfProduct', 'products.brf_properties.transmittanceImages')

        if self._get('products.brf_properties.image') == 1:
            expert_mode_zone_etalement = et.SubElement(brf_products_properties, 'ExpertModeZone_Etalement')
            self._set(expert_mode_zone_etalement, 'etalement', 'products.brf_properties.etalement')

            if self._get('products.brf_properties.sensorPlaneprojection') == 1:
                expert_mode_zone_projection = et.SubElement(expert_mode_zone_etalement, 'ExpertModeZone_Projection')
                self._set(expert_mode_zone_projection, 'keepNonProjectedImage',
                          'products.brf_properties.keepNonProjectedImage')

                expert_mode_zone_per_type = et.SubElement(expert_mode_zone_etalement, 'ExpertModeZone_PerTypeProduct')
                self._set(expert_mode_zone_per_type, 'generate_PerTypeProduct',
                          'products.brf_properties.generate_PerTypeProduct')

            if self._get('products.brf_properties.projection') == 1:
                expert_mode_zone_mask_projection = et.SubElement(brf_products_properties,
                                                                 'ExpertModeZone_maskProjection')
                self._set(expert_mode_zone_mask_projection, 'albedoImages', 'products.brf_properties.albedoImages')

        order1_options = et.SubElement(flux_tracking_products, 'Order1Options')
        self._set(order1_options, 'images_only', 'products.brf_properties.images_only')
        self._set(order1_options, 'order1only', 'products.brf_properties.order1only')

        sensor_image_simulation = et.SubElement(phase, 'SensorImageSimulation')
        self._set(sensor_image_simulation, 'importMultipleSensors', 'sensor.importMultipleSensors')

        if self._get('importMultipleSensors') is not None:
            sensors_importation = et.SubElement(sensor_image_simulation, 'SensorsImportation')
            self._set(sensors_importation, 'fileN', 'sensor.fileN')

        if self._get('sensor.pinhole') is not None:
            for n in range(len(self._get('sensor.pinhole'))):
                pinhole = et.SubElement(sensor_image_simulation, 'Pinhole')
                self._set(pinhole, 'defCameraOrientation', 'sensor.pinhole.' + str(n) + '.defCameraOrientation')
                self._set(pinhole, 'setImageSize', 'sensor.pinhole.' + str(n) + '.setImageSize')
                self._set(pinhole, 'ifFishEye', 'sensor.pinhole.' + str(n) + '.ifFishEye')

                sensor = et.SubElement(pinhole, 'Sensor')
                self._set(sensor, 'sensorPosX', 'sensor.pinhole.' + str(n) + '.sensorPosX')
                self._set(sensor, 'sensorPosY', 'sensor.pinhole.' + str(n) + '.sensorPosY')
                self._set(sensor, 'sensorPosZ', 'sensor.pinhole.' + str(n) + '.sensorPosZ')

                orientation_def = et.SubElement(pinhole, 'OrientationDef')
                self._set(pinhole, 'orientDefType', 'sensor.pinhole.' + str(n) + '.orientDefType')
                if self._get('sensor.pinhole.' + str(n) + '.orientDefType') == 0:
                    camera_orientation = et.SubElement(orientation_def, 'CameraOrientation')
                    self._set(camera_orientation, 'cameraRotation',
                              'sensor.pinhole.' + str(n) + '.intrinsic_ZYZ.cameraRotation')
                    self._set(camera_orientation, 'cameraPhi', 'sensor.pinhole.' + str(n) + '.intrinsic_ZYZ.cameraPhi')
                    self._set(camera_orientation, 'cameraTheta',
                              'sensor.pinhole.' + str(n) + '.intrinsic_ZYZ.cameraTheta')

                elif self._get('sensor.pinhole.' + str(n) + '.orientDefType') == 1:
                    camera_orient_ypr = et.SubElement(orientation_def, 'CameraOrientYPR')
                    self._set(camera_orient_ypr, 'pitch', 'sensor.pinhole.' + str(n) + '.tait_bryan.pitch')
                    self._set(camera_orient_ypr, 'roll', 'sensor.pinhole.' + str(n) + '.tait_bryan.roll')
                    self._set(camera_orient_ypr, 'rotDefBT', 'sensor.pinhole.' + str(n) + '.tait_bryan.rotDefBT')
                    self._set(camera_orient_ypr, 'yaw', 'sensor.pinhole.' + str(n) + '.tait_bryan.yaw')
                else:
                    raise Exception('Invalid Camera Orientation Definition')

                cam_image_FOV = et.SubElement(pinhole, 'CamImageFOV')
                self._set(cam_image_FOV, 'defNbPixels', 'sensor.pinhole.' + str(n) + '.defNbPixels')
                self._set(cam_image_FOV, 'definitionFOV', 'sensor.pinhole.' + str(n) + '.definitionFOV')

                if self._get('sensor.pinhole.' + str(n) + '.defNbPixels') == 1:
                    cam_nb_pixels = et.SubElement(cam_image_FOV, 'NbPixels')
                    self._set(cam_nb_pixels, 'nbPixelsX', 'sensor.pinhole.' + str(n) + '.nbPixelsX')
                    self._set(cam_nb_pixels, 'nbPixelsX', 'sensor.pinhole.' + str(n) + '.nbPixelsY')

                if self._get('sensor.pinhole.' + str(n) + '.definitionFOV') == 0:
                    cam_image_dim = et.SubElement(cam_image_FOV, 'CamImageDim')
                    self._set(cam_image_dim, 'sizeImageX', 'sensor.pinhole.' + str(n) + '.fov.sizeImageX')
                    self._set(cam_image_dim, 'nbPixelsX', 'sensor.pinhole.' + str(n) + '.fov.sizeImageY')

                elif self._get('sensor.pinhole.' + str(n) + '.definitionFOV') == 1:
                    cam_image_aov = et.SubElement(cam_image_FOV, 'CamImageAOV')
                    self._set(cam_image_aov, 'aovX', 'sensor.pinhole.' + str(n) + '.aov.x')
                    self._set(cam_image_aov, 'aovY', 'sensor.pinhole.' + str(n) + '.aov.y')

        if self._get('sensor.pushbroom') is not None:
            for n in range(len(self._get('sensor.pushbroom'))):
                pushbroom = et.SubElement(sensor_image_simulation, 'Pushbroom')
                self._set(pushbroom, 'importThetaPhi', 'sensor.pushbroom.' + str(n) + '.is_import')

                if self._get('sensor.pushbroom.' + str(n) + '.is_import') == 1:
                    importation = et.SubElement(pushbroom, 'Importation')
                    self._set(importation, 'sensorAltitude', 'sensor.pushbroom.import.' + str(n) + '.altitude')
                    self._set(importation, 'offsetX', 'sensor.pushbroom.' + str(n) + '.import.offsetX')
                    self._set(importation, 'offsetY', 'sensor.pushbroom.' + str(n) + '.import.offsetY')
                    self._set(importation, 'phiFile', 'sensor.pushbroom.' + str(n) + '.import.phiFile')
                    self._set(importation, 'resImage', 'sensor.pushbroom.' + str(n) + '.import.resImage')
                    self._set(importation, 'thetaFile', 'sensor.pushbroom.' + str(n) + '.import.thetaFile')

                elif self._get('sensor.pushbroom.' + str(n) + '.is_import') == 0:
                    platform = et.SubElement(pushbroom, 'Platform')
                    self._set(platform, 'pitchLookAngle', 'sensor.pushbroom.' + str(n) + '.no_import.pitchLookAngle')
                    self._set(platform, 'platformAzimuth', 'sensor.pushbroom.' + str(n) + '.no_import.platformAzimuth')
                    self._set(platform, 'platformDirection',
                              'sensor.pushbroom.' + str(n) + '.no_import.platformDirection')

                else:
                    raise Exception('Import is not properly defined. Should be 0 or 1.')

                sensor = et.SubElement(pushbroom, 'Sensor')
                self._set(sensor, 'sensorPosX', 'sensor.pushbroom.' + str(n) + '.sensorPosX')
                self._set(sensor, 'sensorPosY', 'sensor.pushbroom.' + str(n) + '.sensorPosY')
                self._set(sensor, 'sensorPosZ', 'sensor.pushbroom.' + str(n) + '.sensorPosZ')

        maket_module_products = et.SubElement(dart_product, 'maketModuleProducts')
        self._set(maket_module_products, 'MNEProducts', 'products.DEM.MNEProducts')
        self._set(maket_module_products, 'areaMaketProducts', 'products.DEM.areaMaketProducts')
        self._set(maket_module_products, 'coverRateProducts', 'products.DEM.coverRateProducts')
        self._set(maket_module_products, 'laiProducts', 'products.DEM.laiProducts')
        self._set(maket_module_products, 'objectGeneration', 'products.DEM.objectGeneration')

        area_maket_products_properties = et.SubElement(maket_module_products, 'areaMaketProducts')
        self._set(area_maket_products_properties, 'areaMaketPerType', 'products.DEM.areaMaketPerType')
        self._set(area_maket_products_properties, 'totalMaketArea', 'products.DEM.totalMaketArea')

        cover_rate_products_properties = et.SubElement(maket_module_products, 'coverRateProductsProperties')
        self._set(cover_rate_products_properties, 'coverRatePerType', 'products.DEM.coverRatePerType')
        self._set(cover_rate_products_properties, 'totalMaketCoverRate', 'products.DEM.totalMaketCoverRate')
        self._set(cover_rate_products_properties, 'coverRatePrecision', 'products.DEM.coverRatePrecision')

        lai_products_properties = et.SubElement(maket_module_products, 'LaiProductsProperties')
        self._set(lai_products_properties, 'lai1DProducts', 'products.DEM.lai1DProducts')
        self._set(lai_products_properties, 'lai3DProducts', 'products.DEM.lai3DProducts')
        self._set(lai_products_properties, 'nonEmptyCellsLayer', 'products.DEM.nonEmptyCellsLayer')


class Directions(Component):
    COMPONENT_NAME = 'Directions'
    COMPONENT_FILE_NAME = 'directions.xml'
    IMPLEMENTED_WRITE_VERSION = ['5.7.5']

    def _check_params(self, params):
        return True

    def _write575(self, params, *args, **kwargs):
        self._written_params = params

        directions = et.SubElement(self.xml_root, self.COMPONENT_NAME)
        self._set(directions, 'exactDate', 'exactDate')
        self._set(directions, 'ifCosWeighted', 'ifCosWeighted')
        self._set(directions, 'numberOfPropagationDirections', 'numberOfPropagationDirections')

        sun_viewing_angles = et.SubElement(directions, 'SunViewingAngles')
        self._set(sun_viewing_angles, 'sunViewingAzimuthAngle', 'sun.sunViewingAzimuthAngle')
        self._set(sun_viewing_angles, 'sunViewingZenithAngle', 'sun.sunViewingZenithAngle')
        self._set(sun_viewing_angles, 'dayOfTheYear', 'sun.dayOfTheYear')

        hot_spot_properties = et.SubElement(directions, 'HotSpotProperties')
        self._set(hot_spot_properties, 'hotSpotParallelPlane', 'hotspot.hotSpotParallelPlane')
        self._set(hot_spot_properties, 'hotSpotPerpendicularPlane', 'hotspot.hotSpotPerpendicularPlane')
        self._set(hot_spot_properties, 'oversampleDownwardRegion', 'hotspot.oversampleDownwardRegion')
        self._set(hot_spot_properties, 'oversampleUpwardRegion', 'hotspot.oversampleUpwardRegion')

        hot_spot_downward_region = et.SubElement(hot_spot_properties, 'HotSpotDownwardRegion')
        self._set(hot_spot_downward_region, 'numberOfDirections', 'hotspot.numberOfDownwardDirections')
        self._set(hot_spot_downward_region, 'omega', 'hotspot.omegaDown')

        hot_spot_upward_region = et.SubElement(hot_spot_properties, 'HotSpotUpwardRegion')
        self._set(hot_spot_upward_region, 'numberOfDirections', 'hotspot.numberOfUpwardDirections')
        self._set(hot_spot_upward_region, 'omega', 'hotspot.omegaUp')

        penumbra_mode = et.SubElement(directions, 'Penumbra')
        self._set(penumbra_mode, 'mode', 'penumbraMode')

        expert_mode_zone = et.SubElement(directions, 'ExpertModeZone')
        self._set(expert_mode_zone, 'numberOfAngularSector', 'expert.numberOfAngularSector')
        self._set(expert_mode_zone, 'numberOfLayers', 'expert.numberOfLayers')


class Plots(Component):
    COMPONENT_NAME = 'Plots'
    COMPONENT_FILE_NAME = 'plots.xml'
    IMPLEMENTED_WRITE_VERSION = ['5.7.5']

    def _check_params(self, params):
        return True

    def _write575(self, params, land_cover, *args, **kwargs):
        self._written_params = params

        plots = et.SubElement(self.xml_root, self.COMPONENT_NAME)
        self._set(plots, 'isVegetation', 'general.isVegetation')
        self._set(plots, 'addExtraPlotsTextFile', 'general.addExtraPlotsTextFile')

        import_fichier_raster = et.SubElement(plots, 'ImportationFichierRaster')

        ground_types = self._get('general.ground_types')

        if land_cover is None:
            return

        for row in range(land_cover.shape[0]):
            for col in range(land_cover.shape[1]):
                if col == land_cover.shape[1] | land_cover[row, col] != land_cover[row, col + 1]:

                    plot_type = land_cover[row, col]

                    plot = et.SubElement(plots, 'Plot')
                    self._set(plot, 'form', '0')
                    self._set(plot, 'isDisplayed', '1')
                    # self._set(Plot,'hidden','0')

                    polygon_2d = et.SubElement(plot, 'Polygon2D')

                    voxel_size = self._get('voxelDim')
                    point_2d = et.SubElement(polygon_2d, 'Point2D')
                    self._set(point_2d, 'x', str(voxel_size[0] * row))
                    self._set(point_2d, 'y', str(voxel_size[1] * col))

                    point_2d = et.SubElement(polygon_2d, 'Point2D')
                    self._set(point_2d, 'x', str(voxel_size[0] * (row + 1)))
                    self._set(point_2d, 'y', str(voxel_size[1] * col))

                    point_2d = et.SubElement(polygon_2d, 'Point2D')
                    self._set(point_2d, 'x', str(voxel_size[0] * (row + 1)))
                    self._set(point_2d, 'y', str(voxel_size[1] * (col + 1)))

                    point_2d = et.SubElement(polygon_2d, 'Point2D')
                    self._set(point_2d, 'x', str(voxel_size[0] * row))
                    self._set(point_2d, 'y', str(voxel_size[1] * (col + 1)))

                    if plot_type in ground_types['vegetation'].ids:
                        vegetation_id = ground_types.ids.index(plot_type)
                        # TODO: shouldn't this be type 2 i.e. ground and vegetation
                        self._set(plot, 'type', '1')

                        plot_vegetation_properties = et.SubElement(plot, 'PlotVegetationProperties')
                        self._set(plot_vegetation_properties, 'densityDefinition', 'vegetation.densityDefinition')
                        self._set(plot_vegetation_properties, 'verticalFillMode', 'vegetation.verticalFillMode')

                        vegetation_geometry = et.SubElement(plot_vegetation_properties, 'VegetationGeometry')
                        self._set(vegetation_geometry, 'stDev', 'vegetation.stdDev.' + str(vegetation_id))
                        self._set(vegetation_geometry, 'baseheight', '0')
                        self._set(vegetation_geometry, 'height', 'vegetation.height.' + str(vegetation_id))

                        lai_vegetation = et.SubElement(plot_vegetation_properties, 'LAIVegetation')
                        self._set(lai_vegetation, 'LAI', 'vegetation.lai.' + str(vegetation_id))

                        vegetation_optical_property_link = et.SubElement(plot_vegetation_properties,
                                                                         'VegetationOpticalPropertyLink')
                        self._set(vegetation_optical_property_link, 'ident', 'vegetation.ident.' + str(vegetation_id))
                        self._set(vegetation_optical_property_link, 'indexFctPhase',
                                  'vegetation.indexFctPhase.' + str(vegetation_id))

                        ground_thermal_property_link = et.SubElement(plot_vegetation_properties,
                                                                     'GroundThermalPropertyLink')
                        self._set(ground_thermal_property_link, 'idTemperature', 'temperature.idTemperature')
                        self._set(ground_thermal_property_link, 'indexTemperature', 'temperature.indexTemperature')

                    elif plot_type in ground_types['ground'].ids:
                        litter_id = ground_types.ids.index(plot_type)
                        self._set(plot, 'type', '0')

                        ground_optical_property_link = et.SubElement(plot, 'GroundOpticalPropertyLink')
                        self._set(ground_optical_property_link, 'ident', 'ground.ident.' + str(litter_id))
                        self._set(ground_optical_property_link, 'indexFctPhase',
                                  'ground.indexFctPhase.' + str(litter_id))
                        self._set(ground_optical_property_link, 'type', 'ground.type.' + str(litter_id))

                        ground_thermal_property_link = et.SubElement(plot, 'GroundThermalPropertyLink')
                        self._set(ground_thermal_property_link, 'idTemperature', 'temperature.idTemperature')
                        self._set(ground_thermal_property_link, 'indexTemperature', 'temperature.indexTemperature')

                    # TODO: there should also be a treatment for type 2 and 3, i.e. ground and vegetation and fluids
                    else:
                        pass


class CoeffDiff(Component):
    COMPONENT_NAME = 'Coeff_diff'
    COMPONENT_FILE_NAME = 'coeff_diff.xml'
    IMPLEMENTED_WRITE_VERSION = ['5.7.5']

    def _check_params(self, params):
        return True

    def _write575(self, params, *args, **kwargs):
        self._written_params = params

        coeff_diff = et.SubElement(self.xml_root, self.COMPONENT_NAME)
        self._set(coeff_diff, 'fluorescenceProducts', 'fluorescence.fluorescenceProducts')
        self._set(coeff_diff, 'fluorescenceFile',
                  'fluorescence.fluorescenceFile')  ## TODO: there should be a field to assign a file here!

        # *** 2d lambertian spectra ***
        lambertian_multi_functions = et.SubElement(coeff_diff, 'LambertianMultiFunctions')

        if self._get('lop2d.model') is not None:
            for m in range(len(self._get('lop2d.model'))):
                model = self._get('lop2d.model.' + str(m))
                lambertian_multi = et.SubElement(lambertian_multi_functions, 'LambertianMulti')

                self._set(lambertian_multi, 'ModelName', model.get('ModelName'), as_is=True)
                self._set(lambertian_multi, 'databaseName', model.get('databaseName'), as_is=True)
                self._set(lambertian_multi, 'ident', model.get('ident'), as_is=True)
                self._set(lambertian_multi, 'roStDev', model.get('roStDev'), as_is=True)
                # self._set(lambertian_multi, 'specularDatabaseName', model.get('databaseName'), as_is=True)
                # self._set(lambertian_multi, 'specularModelName', 'lop2d.ModelName'{m})
                # self._set(lambertian_multi, 'specularRoStDev', model.get('roStDev'), as_is=True)
                self._set(lambertian_multi, 'useMultiplicativeFactorForLUT', model.get('useMultiplicativeFactorForLUT'),
                          as_is=True)
                self._set(lambertian_multi, 'useSpecular', model.get('useSpecular'), as_is=True)

                prospect_external_module = et.SubElement(lambertian_multi, 'ProspectExternalModule')
                self._set(prospect_external_module, 'isFluorescent', model.get('is_fluorescent'), as_is=True)
                self._set(prospect_external_module, 'useProspectExternalModule', model.get('useProspectExternalModule'),
                          as_is=True)

                lambertian_node_multiplicative_factor_for_lut = et.SubElement(lambertian_multi,
                                                                              'lambertianNodeMultiplicativeFactorForLUT')
                self._set(lambertian_node_multiplicative_factor_for_lut, 'diffuseTransmittanceFactor',
                          model.get('diffuseTransmittanceFactor'), as_is=True)
                self._set(lambertian_node_multiplicative_factor_for_lut, 'diffuseTransmittanceAcceleration',
                          model.get('diffuseTransmittanceAcceleration'), as_is=True)
                self._set(lambertian_node_multiplicative_factor_for_lut, 'directTransmittanceFactor',
                          model.get('directTransmittanceFactor'), as_is=True)
                self._set(lambertian_node_multiplicative_factor_for_lut, 'reflectanceFactor',
                          model.get('reflectanceFactor'), as_is=True)
                self._set(lambertian_node_multiplicative_factor_for_lut, 'specularIntensityFactor',
                          model.get('specularIntensityFactor'), as_is=True)
                self._set(lambertian_node_multiplicative_factor_for_lut, 'useSameFactorForAllBands',
                          model.get('useSameFactorForAllBands'), as_is=True)
                self._set(lambertian_node_multiplicative_factor_for_lut, 'useSameOpticalFactorMatrixForAllBands',
                          model.get('useSameOpticalFactorMatrixForAllBands'), as_is=True)

                understory_multiplicative_factor_for_lut = et.SubElement(lambertian_node_multiplicative_factor_for_lut,
                                                                         'lambertianMultiplicativeFactorForLUT')
                self._set(understory_multiplicative_factor_for_lut, 'diffuseTransmittanceFactor',
                          model.get('diffuseTransmittanceFactor'), as_is=True)
                self._set(understory_multiplicative_factor_for_lut, 'directTransmittanceFactor',
                          model.get('directTransmittanceFactor'), as_is=True)
                self._set(understory_multiplicative_factor_for_lut, 'reflectanceFactor', model.get('reflectanceFactor'),
                          as_is=True)
                self._set(understory_multiplicative_factor_for_lut, 'specularIntensityFactor',
                          model.get('specularIntensityFactor'), as_is=True)
                self._set(understory_multiplicative_factor_for_lut, 'useOpticalFactorMatrix',
                          model.get('useSameOpticalFactorMatrixForAllBands'), as_is=True)

        # LambertianSpecularMultiFunctions = et.SubElement(coeff_diff, 'LambertianSpecularMultiFunctions')

        HapkeSpecularMultiFunctions = et.SubElement(coeff_diff, 'HapkeSpecularMultiFunctions')
        RPVMultiFunctions = et.SubElement(coeff_diff, 'RPVMultiFunctions')

        # *** 3d turbid spectra ***
        understory_multi_functions = et.SubElement(coeff_diff, 'UnderstoryMultiFunctions')
        self._set(understory_multi_functions, 'outputLADFile', 'understory_multi_functions.outputLADFile')
        self._set(understory_multi_functions, 'integrationStepOnPhi', 'understory_multi_functions.integrationStepOnPhi')
        self._set(understory_multi_functions, 'integrationStepOnTheta',
                  'understory_multi_functions.integrationStepOnTheta')
        # self._set(UnderstoryMultiFunctions, 'specularEffects',        #                     'understory_multi_functions.specularEffects')
        # self._set(UnderstoryMultiFunctions, 'useBunnick','0')

        if self._get('lop3d.model') is not None:
            for m in range(len(self._get('lop3d.model'))):
                model = self._get('lop3d.model.' + str(m))
                # (model_name, ident, lad) in enumerate(zip('lop3d.ModelName', 'lop3d.ident',
                #                                              'lop3d.lad')):
                understory_multi = et.SubElement(understory_multi_functions, 'UnderstoryMulti')
                self._set(understory_multi, 'dimFoliar', model.get('dimFoliar'), as_is=True)
                self._set(understory_multi, 'ident', model.get('ident'), as_is=True)
                self._set(understory_multi, 'lad', model.get('lad'), as_is=True)
                self._set(understory_multi, 'hasDifferentModelForBottom', model.get('hasDifferentModelForBottom'),
                          as_is=True)
                self._set(understory_multi, 'thermalHotSpotFactor', model.get('thermalHotSpotFactor'), as_is=True)
                self._set(understory_multi, 'useOpticalFactorMatrix', model.get('useOpticalFactorMatrix'), as_is=True)

                understory_multi_model = et.SubElement(understory_multi, 'UnderstoryMultiModel')
                self._set(understory_multi_model, 'ModelName', model.get('ModelName'), as_is=True)
                self._set(understory_multi_model, 'databaseName', model.get('databaseName'), as_is=True)
                self._set(understory_multi_model, 'useMultiplicativeFactorForLUT',
                          model.get('useMultiplicativeFactorForLUT'), as_is=True)
                self._set(understory_multi_model, 'useSpecular', model.get('useSpecular'), as_is=True)

                prospect_external_module = et.SubElement(understory_multi_model, 'ProspectExternalModule')
                self._set(prospect_external_module, 'useProspectExternalModule', model.get('useProspectExternalModule'),
                          as_is=True)
                self._set(prospect_external_module, 'isFluorescent', model.get('isFluorescent'), as_is=True)

                understory_node_multiplicative_factor_for_lut = et.SubElement(understory_multi_model,
                                                                              'understoryNodeMultiplicativeFactorForLUT')
                self._set(understory_node_multiplicative_factor_for_lut, 'LeafTransmittanceFactor',
                          model.get('LeafTransmittanceFactor'), as_is=True)
                self._set(understory_node_multiplicative_factor_for_lut, 'reflectanceFactor',
                          model.get('reflectanceFactor'), as_is=True)
                self._set(understory_node_multiplicative_factor_for_lut, 'diffuseTransmittanceAcceleration',
                          model.get('diffuseTransmittanceAcceleration'), as_is=True)
                self._set(understory_node_multiplicative_factor_for_lut, 'useSameFactorForAllBands',
                          model.get('useSameFactorForAllBands'), as_is=True)
                self._set(understory_node_multiplicative_factor_for_lut, 'useSameOpticalFactorMatrixForAllBands',
                          model.get('useSameOpticalFactorMatrixForAllBands'),
                          as_is=True)  # TODO: Implement further input datafile which is needed, when this parameter is set to true!

                understory_multiplicative_factor_for_lut = et.SubElement(understory_node_multiplicative_factor_for_lut,
                                                                         'understoryMultiplicativeFactorForLUT')
                self._set(understory_multiplicative_factor_for_lut, 'LeafTransmittanceFactor',
                          model.get('LeafTransmittanceFactor'), as_is=True)
                self._set(understory_multiplicative_factor_for_lut, 'reflectanceFactor', model.get('reflectanceFactor'),
                          as_is=True)
                self._set(understory_multiplicative_factor_for_lut, 'useOpticalFactorMatrix', model.get(
                    'useOpticalFactorMatrix'),
                          as_is=True)  # TODO:implement changes to xml file, when this is set to true!

                specular_data = et.SubElement(understory_multi_model, 'SpecularData')
                self._set(specular_data, 'specularDatabaseName', model.get('specularDatabaseName'), as_is=True)
                self._set(specular_data, 'specularModelName', model.get('specularModelName'), as_is=True)
                directional_clumping_index_properties = et.SubElement(understory_multi,
                                                                      'DirectionalClumpingIndexProperties')
                self._set(directional_clumping_index_properties, 'clumpinga', model.get('clumpinga'), as_is=True)
                self._set(directional_clumping_index_properties, 'clumpingb', model.get('clumpingb'), as_is=True)
                self._set(directional_clumping_index_properties, 'omegaMax', model.get('omegaMax'), as_is=True)
                self._set(directional_clumping_index_properties, 'omegaMin', model.get('omegaMin'), as_is=True)

        air_multi_functions = et.SubElement(coeff_diff, 'AirMultiFunctions')
        phase_extern_multi_functions = et.SubElement(coeff_diff, 'PhaseExternMultiFunctions')

        temperatures = et.SubElement(coeff_diff, 'Temperatures')
        thermal_function = et.SubElement(temperatures, 'ThermalFunction')
        self._set(thermal_function, 'deltaT', 'temperature.deltaT')
        self._set(thermal_function, 'idTemperature', 'temperature.idTemperature')
        self._set(thermal_function, 'meanT', 'temperature.meanT')
        self._set(thermal_function, 'override3DMatrix', 'temperature.override3DMatrix')
        self._set(thermal_function, 'singleTemperatureSurface', 'temperature.singleTemperatureSurface')
        self._set(thermal_function, 'useOpticalFactorMatrix', 'temperature.useOpticalFactorMatrix')
        self._set(thermal_function, 'usePrecomputedIPARs',
                  'temperature.usePrecomputedIPARs')  # self._set(ThermalFunction, 'useOpticalFactorMatrix', 'lop3d.useOpticalFactorMatrix')


class Object3d(Component):
    COMPONENT_NAME = 'object_3d'
    COMPONENT_FILE_NAME = 'object_3d.xml'
    IMPLEMENTED_WRITE_VERSION = ['5.7.5']

    def _check_params(self, params):
        return True

    def _write575(self, params, *args, **kwargs):
        self._written_params = params

        object_3d = et.SubElement(self.xml_root, self.COMPONENT_NAME)

        types = et.SubElement(object_3d, 'Types')
        default_types = et.SubElement(types, 'DefaultTypes')

        default_type = et.SubElement(default_types, 'DefaultType')
        self._set(default_type, 'indexOT', '101', as_is=True)
        self._set(default_type, 'name', 'Default_Object', as_is=True)
        self._set(default_type, 'typeColor', '125 0 125', as_is=True)

        default_type2 = et.SubElement(default_types, 'DefaultType')
        self._set(default_type2, 'indexOT', '102', as_is=True)
        self._set(default_type2, 'name', 'Leaf', as_is=True)
        self._set(default_type2, 'typeColor', '0 175 0', as_is=True)

        custom_types = et.SubElement(types, 'CustomTypes')
        object_list = et.SubElement(object_3d, 'ObjectList')

        obj = et.SubElement(object_list, 'Object')
        self._set(obj, 'file_src', 'path2obj')
        self._set(obj, 'hasGroups', 'hasGroups')
        self._set(obj, 'hidden', 'hidden')
        self._set(obj, 'isDisplayed', 'isDisplayed')
        self._set(obj, 'name', 'name')
        self._set(obj, 'num', 'num')
        self._set(obj, 'objectColor', 'objectColor')
        self._set(obj, 'objectDEMMode', 'objectDEMMode')

        geom_prop = et.SubElement(obj, 'GeometricProperties')

        pos_prop = et.SubElement(geom_prop, 'PositionProperties')
        self._set(pos_prop, 'xpos', 'location.0')
        self._set(pos_prop, 'ypos', 'location.1')
        self._set(pos_prop, 'zpos', 'location.2')

        dimension = et.SubElement(geom_prop, 'Dimension3D')
        self._set(dimension, 'xdim', 'dim.0')
        self._set(dimension, 'ydim', 'dim.1')
        self._set(dimension, 'zdim', 'dim.2')

        scale_prop = et.SubElement(geom_prop, 'ScaleProperties')
        self._set(scale_prop, 'xScaleDeviation', 'scale.xScaleDeviation')
        self._set(scale_prop, 'xscale', 'scale.xscale')
        self._set(scale_prop, 'yScaleDeviation', 'scale.yScaleDeviation')
        self._set(scale_prop, 'yscale', 'scale.yscale')
        self._set(scale_prop, 'zScaleDeviation', 'scale.zScaleDeviation')
        self._set(scale_prop, 'zscale', 'scale.zscale')

        rot_prop = et.SubElement(geom_prop, 'RotationProperties')
        self._set(rot_prop, 'xRotDeviation', 'rotation.xRotDeviation')
        self._set(rot_prop, 'xrot', 'rotation.xrot')
        self._set(rot_prop, 'yRotDeviation', 'rotation.yRotDeviation')
        self._set(rot_prop, 'yrot', 'rotation.yrot')
        self._set(rot_prop, 'zRotDeviation', 'rotation.zRotDeviation')
        self._set(rot_prop, 'zrot', 'rotation.zrot')

        object_optical_prop = et.SubElement(obj, 'ObjectOpticalProperties')
        self._set(object_optical_prop, 'doubleFace', 'optical_property.doubleFace')
        self._set(object_optical_prop, 'isLAICalc', 'optical_property.isLAICalc')
        self._set(object_optical_prop, 'isSingleGlobalLai', 'optical_property.isSingleGlobalLai')
        self._set(object_optical_prop, 'sameOPObject', 'optical_property.sameOPObject')

        object_property_link = et.SubElement(object_optical_prop, 'OpticalPropertyLink')
        self._set(object_property_link, 'ident', 'optical_property.modelName')
        self._set(object_property_link, 'indexFctPhase', 'optical_property.indexFctPhase')
        self._set(object_property_link, 'type', 'optical_property.type')

        thermal_property_link = et.SubElement(object_optical_prop, 'ThermalPropertyLink')
        self._set(thermal_property_link, 'idTemperature', 'temperature.idTemperature')
        self._set(thermal_property_link, 'indexTemperature', 'temperature.indexTemp')

        object_type_prop = et.SubElement(obj, 'ObjectTypeProperties')
        self._set(object_type_prop, 'sameOTObject', 'typeprop.sameOTObject')

        object_type_link = et.SubElement(object_type_prop, 'ObjectTypeLink')
        self._set(object_type_link, 'identOType', 'typeprop.identOType')
        self._set(object_type_link, 'indexOT', 'typeprop.indexOT')

        object_fields = et.SubElement(object_3d, 'ObjectFields')


class Maket(Component):
    COMPONENT_NAME = 'Maket'
    COMPONENT_FILE_NAME = 'maket.xml'
    IMPLEMENTED_WRITE_VERSION = ['5.7.5']

    def _check_params(self, params):
        return True

    def _write575(self, params, **kwargs):
        self._written_params = params

        maket = et.SubElement(self.xml_root, self.COMPONENT_NAME)
        self._set(maket, 'dartZone', 'dartZone')
        self._set(maket, 'exactlyPeriodicScene', 'exactlyPeriodicScene')
        self._set(maket, 'useRandomGenerationSeed', 'useRandomGenerationSeed')

        # scene
        scene = et.SubElement(self.xml_root, 'Scene')

        cell_dimensions = et.SubElement(self.xml_root, 'CellDimensions')
        self._set(cell_dimensions, 'x', 'voxelDim.' + str(0))
        self._set(cell_dimensions, 'z', 'voxelDim.' + str(2))

        scene_dimensions = et.SubElement(self.xml_root, 'SceneDimensions')
        self._set(scene_dimensions, 'x', 'sceneDim.' + str(1))
        self._set(scene_dimensions, 'y', 'sceneDim.' + str(0))

        # ground
        soil = et.SubElement(maket, 'Soil')

        # optical property
        OpticalPropertyLink = et.SubElement(soil, 'OpticalPropertyLink')
        self._set(OpticalPropertyLink, 'ident', 'optical_property.ident')
        self._set(OpticalPropertyLink, 'indexFctPhase', 'optical_property.indexFctPhase')
        self._set(OpticalPropertyLink, 'type', 'optical_property.type')

        # thermal function
        thermal_property_link = et.SubElement(soil, 'ThermalPropertyLink')
        self._set(thermal_property_link, 'idTemperature', 'thermal_property.idTemperature')
        self._set(thermal_property_link, 'indexTemperature', 'thermal_property.indexTemperature')

        # topography
        if not 'topography.fileName':
            topography = et.SubElement(soil, 'Topography')
            self._set(topography, 'presenceOfTopography', '0')

            DEM_properties = et.SubElement(soil, 'DEM_properties')
            self._set(DEM_properties, 'createTopography', '0')

        else:
            topography = et.SubElement(soil, 'Topography')
            self._set(topography, 'presenceOfTopography', 'topography.presenceOfTopography')

            topography_properties = et.SubElement(topography, 'TopographyProperties')
            self._set(topography_properties, 'fileName', 'DEM.outputFileName')

            DEM_properties = et.SubElement(soil, 'DEM_properties')
            self._set(DEM_properties, 'createTopography', 'DEM.createTopography')

            DEM_generator = et.SubElement(DEM_properties, 'DEMGenerator')
            self._set(DEM_generator, 'caseDEM', 'DEM.caseDEM')
            self._set(DEM_generator, 'outputFileName', 'DEM.outputFileName')

            # TODO: check this, I dont't know what is done here
            DEM_5 = et.SubElement(DEM_generator, 'DEM_5')
            self._set(DEM_5, 'dataEncoding', 'DEM5.dataEncoding')
            self._set(DEM_5, 'dataFormat', 'DEM5.dataFormat')
            self._set(DEM_5, 'fileName', 'DEM5.fileName')

        # geo-location
        location = et.SubElement(maket, 'LatLon')
        self._set(location, 'altitude', 'location.2')
        self._set(location, 'latitude', 'location.0')
        self._set(location, 'longitude', 'location.1')


class Atmosphere(Component):
    COMPONENT_NAME = 'Atmosphere'
    COMPONENT_FILE_NAME = 'atmosphere.xml'
    IMPLEMENTED_WRITE_VERSION = ['5.7.5', '5.6.0']

    def _check_params(self, params):
        # TODO: implement proper checks on type and consistency in params, should depend on self.version
        return True

    def _write560(self, params, *args, **kwargs):
        self._written_params = params

        atmos = et.SubElement(self.xml_root, self.COMPONENT_NAME)
        self._set(atmos, 'isRadiativeTransfertInBottomAtmosphereDefined',
                  'general.isRadiativeTransfertInBottomAtmosphereDefined')

        is_atmosphere = et.SubElement(atmos, 'IsAtmosphere')
        self._set(is_atmosphere, 'typeOfAtmosphere', str('general.typeOfAtmosphere'))

        atmosphere_iterations = et.SubElement(is_atmosphere, 'AtmosphereIterations')

        atmosphere_transfer_functions = et.SubElement(atmosphere_iterations, 'AtmosphereTransfertFunctions')
        self._set(atmosphere_transfer_functions, 'inputOutputTransfertFunctions',
                  'general.inputOutputTransfertFunctions')

        computed_transfer_functions = et.SubElement(atmosphere_transfer_functions, 'ComputedTransferFunctions')
        self._set(computed_transfer_functions, 'writeTransferFunctions', 'general.writeTransferFunctions')

        atmosphere_products = et.SubElement(atmosphere_iterations, 'AtmosphereProducts')
        self._set(atmosphere_products, 'atmosphereBRF_TOA', 'products.atmosphereBRF_TOA')
        self._set(atmosphere_products, 'atmosphereRadiance_BOA_apresCouplage',
                  'products.atmosphereRadiance_BOA_after_coupling')
        self._set(atmosphere_products, 'atmosphereRadiance_BOA_avantCouplage',
                  'products.atmosphereRadiance_BOA_before_coupling')
        self._set(atmosphere_products, 'ordreUnAtmos', 'products.order_1')

        atmosphere_components = et.SubElement(atmosphere_iterations, 'AtmosphereComponents')
        self._set(atmosphere_components, 'downwardingFluxes', 'cell_components.downwardingFluxes')
        self._set(atmosphere_components, 'upwardingFluxes', 'cell_components.upwardingFluxes')

        atmosphere_expert_mode_zone = et.SubElement(atmosphere_iterations, 'AtmosphereExpertModeZone')
        self._set(atmosphere_expert_mode_zone, 'extrapol_atmos', 'expert.extrapol_atmos')
        self._set(atmosphere_expert_mode_zone, 'seuilEclairementAtmos', 'expert.seuilEclairementAtmos')
        self._set(atmosphere_expert_mode_zone, 'seuilFTAtmos', 'expert.seuilFTAtmos')

        atmosphere_geometry = et.SubElement(is_atmosphere, 'AtmosphereGeometry')
        self._set(atmosphere_geometry, 'discretisationAtmos', 'geometry.discretisationAtmos')
        self._set(atmosphere_geometry, 'heightOfSensor', 'geometry.heightOfSensor')
        self._set(atmosphere_geometry, 'minimumNumberOfDivisions', 'geometry.minimumNumberOfDivisions')

        mid_atmosphere = et.SubElement(atmosphere_geometry, 'MidAtmosphere')

        cell_dimensions = et.SubElement(mid_atmosphere, 'cell_dimensions')
        self._set(cell_dimensions, 'xAI', 'dimensions.xAI')
        self._set(cell_dimensions, 'yAI', 'dimensions.yAI')
        self._set(cell_dimensions, 'zAI', 'dimensions.zAI')

        height = et.SubElement(mid_atmosphere, 'Height')
        self._set(height, 'hCFAI', 'dimensions.hCFAI')

        upper_atmosphere = et.SubElement(atmosphere_geometry, 'UpperAtmosphere')
        self._set(upper_atmosphere, 'hCFHA', 'dimensions.hCFHA')

        layer = et.SubElement(upper_atmosphere, 'Layer')
        self._set(layer, 'zHA', 'dimensions.zHA')

        if self._get('general.typeOfAtmosphere') == 1:
            atmospheric_optical_property_model = et.SubElement(is_atmosphere, 'AtmosphericOpticalPropertyModel')
            self._set(atmospheric_optical_property_model, 'correctionBandModel',
                      'optical_property_db.correctionBandModel')
            self._set(atmospheric_optical_property_model, 'databaseName', 'optical_property_db.dataBaseName')
            self._set(atmospheric_optical_property_model, 'temperatureModelName',
                      'optical_property_db.temperatureModelName')

            self._set(atmospheric_optical_property_model, 'hgParametersModelName',
                      'optical_property_db.aerosol.hgParametersModelName')
            self._set(atmospheric_optical_property_model, 'aerosolCumulativeModelName',
                      'optical_property_db.aerosol.cumulativeModelName')
            self._set(atmospheric_optical_property_model, 'aerosolOptDepthFactor',
                      'optical_property_db.aerosol.optDepthFactor')
            self._set(atmospheric_optical_property_model, 'aerosolsGroup', 'optical_property_db.aerosol.group')
            self._set(atmospheric_optical_property_model, 'aerosolsModelName', 'optical_property_db.aerosol.modelName')

            self._set(atmospheric_optical_property_model, 'gasCumulativeModelName',
                      'optical_property_db.gas.cumulativeModelName')
            self._set(atmospheric_optical_property_model, 'gasGroup', 'optical_property_db.gas.group')
            self._set(atmospheric_optical_property_model, 'gasModelName', 'optical_property_db.gas.modelName')
            self._set(atmospheric_optical_property_model, 'gasParametersModelName',
                      'optical_property_db.gas.gasParametersModelName')

            self._set(atmospheric_optical_property_model, 'precipitableWaterAmountCkeckbox',
                      'optical_property_db.water.include')
            water_amount = et.SubElement(atmospheric_optical_property_model, 'WaterAmount')
            self._set(water_amount, 'precipitableWaterAmount', 'optical_property_db.water.precipitableWaterAmount')

        elif self._get('general.typeOfAtmosphere') == 0:
            atmospheric_optical_property = et.SubElement(is_atmosphere, 'AtmosphericOpticalProperty')
            self._set(atmospheric_optical_property, 'courbureTerre', 'optical_property.correct_earth_curvature')
            self._set(atmospheric_optical_property, 'pointMilieu', 'optical_property.correct_mid_point')
            self._set(atmospheric_optical_property, 'a_HG', 'optical_property.heyney_greenstein_a')
            self._set(atmospheric_optical_property, 'g1', 'optical_property.heyney_greenstein_g1')
            self._set(atmospheric_optical_property, 'g2', 'optical_property.heyney_greenstein_g2')

            self._set(atmospheric_optical_property, 'aerosolOpticalDepth', 'optical_property.aerosol.optical_depth')
            self._set(atmospheric_optical_property, 'aerosolScaleFactor', 'optical_property.aerosol.scale_factor')
            self._set(atmospheric_optical_property, 'aerosolAlbedo', 'optical_property.aerosol.albedo')

            self._set(atmospheric_optical_property, 'gasOpticalDepth', 'optical_property.gas.optical_depth')
            self._set(atmospheric_optical_property, 'gasScaleFactor', 'optical_property.gas.scale_factor')
            self._set(atmospheric_optical_property, 'transmittanceOfGases', 'optical_property.gas.transmittance')

            temperature_model = et.SubElement(is_atmosphere, 'TemperatureFile')
            self._set(temperature_model, 'atmosphereTemperatureFileName', 'optical_property.temperature_file_name')
        else:
            raise TypeError('Variable typeOfAtmosphere must be 0 or 1')

        is_radiative_transfert_in_bottom_atmosphere = et.SubElement(is_atmosphere,
                                                                    'isRadiativeTransfertInBottomAtmosphere')
        self._set(is_radiative_transfert_in_bottom_atmosphere, 'BA_altitude', 'dimensions.BA_altitude')

    def _write575(self, params, *args, **kwargs):
        self._written_params = params

        atmos = et.SubElement(self.xml_root, self.COMPONENT_NAME)
        self._set(atmos, 'isRadiativeTransfertInBottomAtmosphereDefined',
                  'general.isRadiativeTransfertInBottomAtmosphereDefined')

        is_atmosphere = et.SubElement(atmos, 'IsAtmosphere')
        self._set(is_atmosphere, 'typeOfAtmosphere', str('general.typeOfAtmosphere'))

        atmosphere_iterations = et.SubElement(is_atmosphere, 'AtmosphereIterations')

        atmosphere_transfer_functions = et.SubElement(atmosphere_iterations, 'AtmosphereTransfertFunctions')
        self._set(atmosphere_transfer_functions, 'inputOutputTransfertFunctions',
                  'general.inputOutputTransfertFunctions')

        computed_transfer_functions = et.SubElement(atmosphere_transfer_functions, 'ComputedTransferFunctions')
        self._set(computed_transfer_functions, 'writeTransferFunctions', 'general.writeTransferFunctions')

        atmosphere_products = et.SubElement(atmosphere_iterations, 'AtmosphereProducts')
        self._set(atmosphere_products, 'atmosphereBRF_TOA', 'products.atmosphereBRF_TOA')
        self._set(atmosphere_products, 'atmosphereRadiance_BOA_apresCouplage',
                  'products.atmosphereRadiance_BOA_after_coupling')
        self._set(atmosphere_products, 'atmosphereRadiance_BOA_avantCouplage',
                  'products.atmosphereRadiance_BOA_before_coupling')
        self._set(atmosphere_products, 'ordreUnAtmos', 'products.order_1')
        self._set(atmosphere_products, 'atmosphereReport', 'products.atmosphereReport')

        atmosphere_components = et.SubElement(atmosphere_iterations, 'AtmosphereComponents')
        self._set(atmosphere_components, 'downwardingFluxes', 'components.downwardingFluxes')
        self._set(atmosphere_components, 'upwardingFluxes', 'components.upwardingFluxes')

        atmosphere_expert_mode_zone = et.SubElement(atmosphere_iterations, 'AtmosphereExpertModeZone')
        self._set(atmosphere_expert_mode_zone, 'extrapol_atmos', 'expert.extrapol_atmos')
        self._set(atmosphere_expert_mode_zone, 'number_iterationMax', 'expert.number_iterationMax')
        self._set(atmosphere_expert_mode_zone, 'threshold_Atmos_scattering', 'expert.threshold_Atmos_scattering')

        atmosphere_geometry = et.SubElement(is_atmosphere, 'AtmosphereGeometry')
        self._set(atmosphere_geometry, 'discretisationAtmos', 'geometry.discretisationAtmos')
        self._set(atmosphere_geometry, 'heightOfSensor', 'geometry.heightOfSensor')
        self._set(atmosphere_geometry, 'minimumNumberOfDivisions', 'geometry.minimumNumberOfDivisions')

        mid_atmosphere = et.SubElement(atmosphere_geometry, 'MidAtmosphere')

        cell_dimensions = et.SubElement(mid_atmosphere, 'cell_dimensions')
        self._set(cell_dimensions, 'xAI', 'dimensions.xAI')
        self._set(cell_dimensions, 'yAI', 'dimensions.yAI')
        self._set(cell_dimensions, 'zAI', 'dimensions.zAI')

        height = et.SubElement(mid_atmosphere, 'Height')
        self._set(height, 'hCFAI', 'dimensions.hCFAI')

        upper_atmosphere = et.SubElement(atmosphere_geometry, 'UpperAtmosphere')
        self._set(upper_atmosphere, 'hCFHA', 'dimensions.hCFHA')

        layer = et.SubElement(upper_atmosphere, 'Layer')
        self._set(layer, 'zHA', 'dimensions.zHA')

        aerosol = et.SubElement(atmos, 'Aerosol')
        aerosol_properties = et.SubElement(aerosol, 'AerosolProperties')
        self._set(aerosol_properties, 'hgParametersModelName', 'optical_property_db.aerosol.hgParametersModelName')
        self._set(aerosol_properties, 'aerosolCumulativeModelName', 'optical_property_db.aerosol.cumulativeModelName')
        self._set(aerosol_properties, 'aerosolOptDepthFactor', 'optical_property_db.aerosol.optDepthFactor')
        self._set(aerosol_properties, 'aerosolsGroup', 'optical_property_db.aerosol.group')
        self._set(aerosol_properties, 'aerosolsModelName', 'optical_property_db.aerosol.modelName')
        self._set(aerosol_properties, 'databaseName', 'optical_property_db.aerosol.dataBaseName')

        if self._get('general.typeOfAtmosphere') is not None:
            if self._get('general.typeOfAtmosphere') == 1:
                atmospheric_optical_property_model = et.SubElement(is_atmosphere, 'AtmosphericOpticalPropertyModel')
                self._set(atmospheric_optical_property_model, 'correctionBandModel',
                          'optical_property_db.correctionBandModel')
                self._set(atmospheric_optical_property_model, 'temperatureModelName',
                          'optical_property_db.temperatureModelName')

                self._set(atmospheric_optical_property_model, 'gasCumulativeModelName',
                          'optical_property_db.gas.cumulativeModelName')
                self._set(atmospheric_optical_property_model, 'gasGroup', 'optical_property_db.gas.group')
                self._set(atmospheric_optical_property_model, 'gasModelName', 'optical_property_db.gas.modelName')
                self._set(atmospheric_optical_property_model, 'gasParametersModelName',
                          'optical_property_db.gas.gasParametersModelName')

                self._set(atmospheric_optical_property_model, 'precipitableWaterAmountCkeckbox', 'water.include')
                water_amount = et.SubElement(atmospheric_optical_property_model, 'WaterAmount')
                self._set(water_amount, 'defWaterAmount', 'water.defWaterAmount')

                if self._get('water.defWaterAmount') == '0':
                    water_spec = et.SubElement(water_amount, 'M_factor')
                    water_spec.set('mulFactorH2O', 'water.mulFactorH2O')

            elif self._get('general.typeOfAtmosphere') == 0:
                atmospheric_optical_property = et.SubElement(is_atmosphere, 'AtmosphericOpticalProperty')
                self._set(atmospheric_optical_property, 'courbureTerre', 'optical_property.correct_earth_curvature')
                self._set(atmospheric_optical_property, 'pointMilieu', 'optical_property.correct_mid_point')
                self._set(atmospheric_optical_property, 'a_HG', 'optical_property.heyney_greenstein_a')
                self._set(atmospheric_optical_property, 'g1', 'optical_property.heyney_greenstein_g1')
                self._set(atmospheric_optical_property, 'g2', 'optical_property.heyney_greenstein_g2')

                self._set(atmospheric_optical_property, 'aerosolOpticalDepth', 'optical_property.aerosol.optical_depth')
                self._set(atmospheric_optical_property, 'aerosolScaleFactor', 'optical_property.aerosol.scale_factor')
                self._set(atmospheric_optical_property, 'aerosolAlbedo', 'optical_property.aerosol.albedo')

                self._set(atmospheric_optical_property, 'gasOpticalDepth', 'optical_property.gas.optical_depth')
                self._set(atmospheric_optical_property, 'gasScaleFactor', 'optical_property.gas.scale_factor')
                self._set(atmospheric_optical_property, 'transmittanceOfGases', 'optical_property.gas.transmittance')

                temperature_model = et.SubElement(is_atmosphere, 'TemperatureFile')
                self._set(temperature_model, 'atmosphereTemperatureFileName', 'optical_property.temperature_file_name')
            else:
                raise TypeError('Variable typeOfAtmosphere must be 0 or 1. You set '
                                + str(self._get('general.typeOfAtmosphere')) + ' of type '
                                + str(type(self._get('general.typeOfAtmosphere'))))

        is_radiative_transfert_in_bottom_atmosphere = et.SubElement(is_atmosphere,
                                                                    'isRadiativeTransfertInBottomAtmosphere')
        self._set(is_radiative_transfert_in_bottom_atmosphere, 'BA_altitude', 'dimensions.BA_altitude')
