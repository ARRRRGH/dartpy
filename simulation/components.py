import utils.general

from lxml import etree as et
import os
import logging
from pkg_resources import parse_version
import utils.general as general
from shutil import copyfile, copytree

ROOT_TAG = 'DartFile'


class Component(object):
    """
    A component is any entity that is represented by a xml file in the DART simulation folder.
    """
    COMPONENT_FILE_NAME = None
    COMPONENT_NAME = None
    IMPLEMENTED_WRITE_VERSION = []

    def __init__(self, simulation_dir, params, version, *args, **kwargs):
        """
        Create a component from a complete params dict. The default config files in ../default_params implicitly define
        the form of the params dict for each version and each component. Normally, params is patched to a default file
        in the class Simulation.

        :param simulation_dir:
        :param params:
        :param version:
        """
        self.simulation_dir = simulation_dir
        self.version = version

        if type(params) is dict:
            self.params = params
            self.xml_root = et.Element(ROOT_TAG)
            self.xml_root.set('version', self.version)
            self._write(self.params, *args, **kwargs)
            self._xml_only = False
        elif type(params) is tuple:
            self.params = None
            self.xml_root, self.original_path = params
            self._xml_only = True
        else:
            raise Exception('params must be a dictionary or a tuple. The tuple form should not be used by the user.')

        self._is_to_file = False

    @classmethod
    def is_implemented(cls):
        return len(cls.IMPLEMENTED_WRITE_VERSION) != 0

    @classmethod
    def is_version_implemented(cls, version):
        return version in cls.IMPLEMENTED_WRITE_VERSION

    @classmethod
    def from_file(cls, simulation_dir, path, version, force=False):
        """
        Create a component from its xml file
        :param simulation_dir:
        :param path:
        :param version:
        :param force:
        :return:
        """
        xml_path = utils.general.create_path(path, 'input', cls.COMPONENT_FILE_NAME)
        xml_root = cls._read(xml_path)

        # Check if this is a dart file, if its version is correct (if supplied) and whether it is the correct component
        valid = parse_version(xml_root.get('version')) == parse_version(version) and \
                cls.COMPONENT_NAME in [el.tag for el in list(xml_root)]
        if not (valid or force):
            raise Exception(
                'Cannot load ' + xml_path + ' since file does not seem to be valid. If you are convinced it is, ' +
                'use force=True. Found ROOT_TAG ' + str(xml_root.get('version')) + ', tags: ' + str(
                    [el.tag for el in list(xml_root)]))
        else:
            return cls(simulation_dir, (xml_root, xml_path), version)

    def to_file(self):
        inp_path = utils.general.create_path(self.simulation_dir, 'input')
        xml_path = utils.general.create_path(inp_path, self.COMPONENT_FILE_NAME)

        if not os.path.exists(inp_path):
            os.makedirs(inp_path)

        if not self._xml_only:
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
        # this is to ensure undefined elements are projected to None and do not raise an Error a priori
        if parse_version(self.version) >= parse_version('5.7.5'):
            self._write575(params, *args, **kwargs)
        elif parse_version(self.version) >= parse_version('5.6.0'):
            self._write560(params, *args, **kwargs)

    def _check_and_set(self, element, key, val, check=None):
        if check is not None:
            assert check(key, val)

        if val is not None:
            element.set(key, val)
        else:
            logging.warning('Could not set ' + key + ' with value ' + str(val))

    @classmethod
    def _copy_from_simulation(cls, copy_xml_path, new_xml_path):
        copyfile(copy_xml_path, new_xml_path)

    def _str_none(self, val):
        if val is not None:
            return str(val)
        return None

    def _set(self, el, key, val, check=None):
        self._check_and_set(el, key, self._str_none(val))

    def _check_params(self, params):
        raise NotImplementedError

    def _write575(self, params, *args, **kwargs):
        raise NotImplementedError

    def _write560(self, params, *args, **kwargs):
        raise NotImplementedError


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
    def _copy_from_simulation(self, copy_xml_path, new_xml_path):
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
        phase = et.SubElement(self.xml_root, self.COMPONENT_NAME)
        self._set(phase, 'calculatorMethod', params.get('calculatorMethod'))

        # radiative transfer method
        atmosphere_radiative_transfer = et.SubElement(phase, 'AtmosphereRadiativeTransfer')
        self._set(atmosphere_radiative_transfer, 'TOAtoBOA', params.get('toaToBoa'))

        # advanced mode
        expert_mode_zone = et.SubElement(phase, 'ExpertModeZone')
        self._set(expert_mode_zone, 'accelerationEngine', params['expert_flux_tracking'].get('acceleration_engine'))
        self._set(expert_mode_zone, 'albedoThreshold', params['expert_flux_tracking'].get('albedoThreshold'))
        self._set(expert_mode_zone, 'expertMode', params['expert_flux_tracking'].get('expertMode'))
        self._set(expert_mode_zone, 'illuminationRepartitionMode',
                  params['expert_flux_tracking'].get('illuminationRepartitionMode'))
        self._set(expert_mode_zone, 'maxNbSceneCrossing', params['expert_flux_tracking'].get('maxNbSceneCrossing'))
        self._set(expert_mode_zone, 'lightPropagationThreshold',
                  params['expert_flux_tracking'].get('lightPropagationThreshold'))
        self._check_and_set(expert_mode_zone, 'nbRandomPointsPerInteceptionAtmosphere', self._str_none(
            params['expert_flux_tracking'].get('nbRandomPointsPerInteceptionAtmosphere')))
        self._set(expert_mode_zone, 'nbSubSubcenterTurbidEmission',
                  params['expert_flux_tracking'].get('nbSubSubcenterTurbidEmission'))
        self._set(expert_mode_zone, 'subFaceBarycenterEnabled',
                  params['expert_flux_tracking'].get('subFaceBarycenterEnabled'))
        self._set(expert_mode_zone, 'subFaceBarycenterSubdivision',
                  params['expert_flux_tracking'].get('subFaceBarycenterSubdivision'))
        self._set(expert_mode_zone, 'useExternalScripts', params['expert_flux_tracking'].get('useExternalScripts'))
        self._check_and_set(expert_mode_zone, 'distanceBetweenIlluminationSubCenters', self._str_none(
            params['expert_flux_tracking'].get('distanceBetweenIlluminationSubCenters')))
        self._set(expert_mode_zone, 'distanceBetweenIlluminationSubCenters',
                  params['expert_flux_tracking'].get('subFaceBarycenterEnabled'))
        self._check_and_set(expert_mode_zone, 'isInterceptedPowerPerDirectionForSpecularCheck',
                            self._str_none(
                                params['expert_flux_tracking'].get('isInterceptedPowerPerDirectionForSpecularCheck')))
        self._set(expert_mode_zone, 'nbSubcenterIllumination',
                  params['expert_flux_tracking'].get('nbSubcenterIllumination'))
        self._set(expert_mode_zone, 'nbTrianglesWithinVoxelAcceleration',
                  params['expert_flux_tracking'].get('nbTrianglesWithinVoxelAcceleration'))
        self._set(expert_mode_zone, 'nbSubcenterVolume', params['expert_flux_tracking'].get('nbSubcenterVolume'))
        self._set(expert_mode_zone, 'nbThreads', params['expert_flux_tracking'].get('nbThreads'))
        self._set(expert_mode_zone, 'sparseVoxelAcceleration',
                  params['expert_flux_tracking'].get('sparseVoxelAcceleration'))
        self._set(expert_mode_zone, 'thermalEmissionSurfaceSubdivision',
                  params['expert_flux_tracking'].get('thermalEmissionSurfaceSubdivision'))
        self._set(expert_mode_zone, 'triangleStorageMode', params['expert_flux_tracking'].get('triangleStorageMode'))

        # *** Dart Input Parameters ***
        dart_input_parameters = et.SubElement(phase, 'dart_input_parameters')

        # flux tracking parameters
        nodefluxtracking = et.SubElement(dart_input_parameters, 'nodefluxtracking')
        self._set(nodefluxtracking, 'gaussSiedelAcceleratingTechnique',
                  params['flux_tracking'].get('gaussSiedelAcceleratingTechnique'))
        self._set(nodefluxtracking, 'numberOfIteration', params['flux_tracking'].get('numberOfIteration'))

        # scene 3d temperature
        spectral_domain_tir = et.SubElement(dart_input_parameters, 'SpectralDomainTir')
        self._set(spectral_domain_tir, 'temperatureMode', params['spectral'].get('temperatureMode'))

        skylTemperature = et.SubElement(spectral_domain_tir, 'skylTemperature')
        self._set(skylTemperature, 'SKYLForTemperatureAssignation',
                  params['atmosphere'].get('SKYLForTemperatureAssignation'))

        # spectral intervals
        spectral_intervals = et.SubElement(dart_input_parameters, 'SpectralIntervals')

        for n in range(len(params['spectral'].get('meanLambda'))):
            spectral_intervals_properties = et.SubElement(spectral_intervals, 'SpectralIntervalsProperties')
            self._set(spectral_intervals_properties, 'bandNumber', self._str_none(n))
            self._set(spectral_intervals_properties, 'deltaLambda',
                      self._str_none(params['spectral'].get('deltaLambda')[n]))
            self._set(spectral_intervals_properties, 'meanLambda',
                      self._str_none(params['spectral'].get('meanLambda')[n]))
            self._set(spectral_intervals_properties, 'spectralDartMode',
                      self._str_none(params['spectral'].get('spectralDartMode')[n]))

        # atmosphere brightness temperature
        temperature_atmosphere = et.SubElement(dart_input_parameters, 'temperatureAtmosphere')
        self._set(temperature_atmosphere, 'atmosphericApparentTemperature',
                  params['atmosphere'].get('atmosphericApparentTemperature'))

        image_side_illumination = et.SubElement(dart_input_parameters, 'ImageSideIllumination')
        self._set(image_side_illumination, 'disableSolarIllumination',
                  params['image_illumination'].get('disableSolarIllumination'))
        self._set(image_side_illumination, 'disableThermalEmission',
                  params['image_illumination'].get('disableThermalEmission'))
        self._set(image_side_illumination, 'sideIlluminationEnabled',
                  params['image_illumination'].get('sideIlluminationEnabled'))

        # earth scene irradiance
        node_illumination_mode = et.SubElement(dart_input_parameters, 'nodeIlluminationMode')
        self._set(node_illumination_mode, 'illuminationMode', params['irradiance'].get('illuminationMode'))
        self._set(node_illumination_mode, 'irradianceMode', params['irradiance'].get('irradianceMode'))

        irradiance_database_node = et.SubElement(node_illumination_mode, 'irradianceDatabaseNode')
        self._set(irradiance_database_node, 'databaseName', params['irradiance'].get('databaseName'))
        self._set(irradiance_database_node, 'irradianceColumn', params['irradiance'].get('irradianceColumn'))
        self._set(irradiance_database_node, 'irradianceTable', params['irradiance'].get('irradianceTable'))
        self._set(irradiance_database_node, 'weightAtmosphereParameters',
                  params['irradiance'].get('weightAtmosphereParameters'))
        self._set(irradiance_database_node, 'weightReflectanceParameters',
                  params['irradiance'].get('weightReflectanceParameters'))

        weighting = et.SubElement(irradiance_database_node, 'WeightingParameters')
        self._set(irradiance_database_node, 'sceneAverageTemperatureForPonderation',
                  params['irradiance'].get('sceneAverageTemperatureForPonderation'))

        spectral_irradiance = et.SubElement(node_illumination_mode, 'SpectralIrradiance')

        common_parameters = et.SubElement(spectral_irradiance, 'CommonParameters')
        self._set(common_parameters, 'commonIrradianceCheckBox', params['irradiance'].get('commonIrradianceCheckBox'))
        self._set(common_parameters, 'commonSkylCheckBox', params['irradiance'].get('commonSkylCheckBox'))

        spectral_irradiance_value = et.SubElement(spectral_irradiance, 'SpectralIrradianceValue')
        self._set(spectral_irradiance_value, 'Skyl', params['irradiance'].get('Skyl'))
        self._set(spectral_irradiance_value, 'bandNumber', params['irradiance'].get('bandNumber'))
        self._set(spectral_irradiance_value, 'irradiance', params.get('irradiance'))

        # *** Dart Products ***
        dart_product = et.SubElement(phase, 'DartProduct')

        dart_module_products = et.SubElement(dart_product, 'dartModuleProducts')
        common_products = et.SubElement(dart_module_products, 'CommonProducts')
        self._set(common_products, 'polarizationProducts', params['products']['common'].get('polarizationProducts'))
        self._set(common_products, 'radiativeBudgetProducts',
                  params['products']['common'].get('radiativeBudgetProducts'))

        flux_tracking_products = et.SubElement(dart_module_products, 'FluxTrackingComponents')
        self._set(flux_tracking_products, 'allIterationsProducts', params['products']['flux_tracking'].get('allIterationsProducts'))
        self._set(flux_tracking_products, 'brfProducts', params['products']['flux_tracking'].get('brfProducts'))
        # self._set(dart_module_products, 'lidarImageProducts',        #                     self._str_none(params['products'].get('lidarImageProducts')))
        # self._set(dart_module_products, 'lidarProducts',        #                     self._str_none(params['products'].get('lidarProducts')))
        self._set(flux_tracking_products, 'order1Products', params['products']['flux_tracking'].get('order1Products'))
        self._set(flux_tracking_products, 'temperaturePerTrianglePerCell',
                  params['products']['flux_tracking'].get('temperaturePerTrianglePerCell'))

        # TODO: find out what this is
        radiative_budget_properties = et.SubElement(common_products, 'radiativeBudgetProperties')
        self._set(radiative_budget_properties, 'binaryFormat',
                  params['products']['radiative_budget_properties'].get('binaryFormat'))
        self._set(radiative_budget_properties, 'budget3DParSurface',
                  params['products']['radiative_budget_properties'].get('budget3DParSurface'))
        self._set(radiative_budget_properties, 'budget3DParType',
                  params['products']['radiative_budget_properties'].get('budget3DParType'))
        self._set(radiative_budget_properties, 'budgetTotalParType',
                  params['products']['radiative_budget_properties'].get('budgetTotalParType'))
        self._set(radiative_budget_properties, 'budgetUnitModeR',
                  params['products']['radiative_budget_properties'].get('budgetUnitModeR'))
        self._set(radiative_budget_properties, 'extrapolation',
                  params['products']['radiative_budget_properties'].get('extrapolation'))
        self._check_and_set(radiative_budget_properties,
                            'fIRfARfSRfINTR1DProducts',
                            self._str_none(
                                params['products']['radiative_budget_properties'].get('fIRfARfSRfINTR1DProducts')))
        self._check_and_set(radiative_budget_properties,
                            'fIRfARfSRfINTR3DProducts',
                            self._str_none(
                                params['products']['radiative_budget_properties'].get('fIRfARfSRfINTR3DProducts')))
        self._check_and_set(radiative_budget_properties, 'fIRfARfSRfINTR2DProducts',
                            self._str_none(
                                params['products']['radiative_budget_properties'].get('fIRfARfSRfINTR2DProducts')))
        self._set(radiative_budget_properties, 'budget2DParType',
                  params['products']['radiative_budget_properties'].get('budget2DParType'))

        components = et.SubElement(radiative_budget_properties, 'Components')
        cell_components = et.SubElement(components, 'CellComponents')
        element_components = et.SubElement(cell_components, 'ElementComponents')

        self._check_and_set(components, 'absorbed',
                            self._str_none(
                                params['products']['radiative_budget_properties']['cell_components'].get('absorbed')))
        self._check_and_set(components, 'backEntry',
                            self._str_none(
                                params['products']['radiative_budget_properties']['cell_components'].get('backEntry')))

        self._check_and_set(components, 'backExit',
                            self._str_none(
                                params['products']['radiative_budget_properties']['cell_components'].get('backExit')))
        self._check_and_set(components, 'bottomEntry',
                            self._str_none(
                                params['products']['radiative_budget_properties']['cell_components'].get(
                                    'bottomEntry')))

        self._check_and_set(components, 'bottomExit', self._str_none(
            params['products']['radiative_budget_properties']['cell_components'].get('bottomExit')))
        self._check_and_set(components, 'emitted', self._str_none(
            params['products']['radiative_budget_properties']['cell_components'].get('emitted')))

        self._check_and_set(components, 'frontEntry', self._str_none(
            params['products']['radiative_budget_properties']['cell_components'].get('frontEntry')))
        self._check_and_set(components, 'frontExit', self._str_none(
            params['products']['radiative_budget_properties']['cell_components'].get('frontExit')))

        self._check_and_set(components, 'intercepted', self._str_none(
            params['products']['radiative_budget_properties']['cell_components'].get('intercepted')))
        self._check_and_set(components, 'leftEntry', self._str_none(
            params['products']['radiative_budget_properties']['cell_components'].get('leftEntry')))

        self._check_and_set(components, 'leftExit', self._str_none(
            params['products']['radiative_budget_properties']['cell_components'].get('leftExit')))
        self._check_and_set(components, 'rightEntry', self._str_none(
            params['products']['radiative_budget_properties']['cell_components'].get('rightEntry')))

        self._check_and_set(components, 'rightExit', self._str_none(
            params['products']['radiative_budget_properties']['cell_components'].get('rightExit')))
        self._check_and_set(components, 'scattered', self._str_none(
            params['products']['radiative_budget_properties']['cell_components'].get('scattered')))
        self._check_and_set(components, 'topEntry', self._str_none(
            params['products']['radiative_budget_properties']['cell_components'].get('topEntry')))

        self._check_and_set(components, 'topExit', self._str_none(
            params['products']['radiative_budget_properties']['cell_components'].get('topExit')))
        self._check_and_set(components, 'totalEntry', self._str_none(
            params['products']['radiative_budget_properties']['cell_components'].get('totalEntry')))
        self._check_and_set(components, 'totalExit', self._str_none(
            params['products']['radiative_budget_properties']['cell_components'].get('totalExit')))

        self._check_and_set(components, 'absorbed', self._str_none(
            params['products']['radiative_budget_properties']['element_components'].get('absorbed')))
        self._check_and_set(components, 'emitted', self._str_none(
            params['products']['radiative_budget_properties']['element_components'].get('emitted')))

        self._check_and_set(components, 'intercepted', self._str_none(
            params['products']['radiative_budget_properties']['element_components'].get('intercepted')))
        self._check_and_set(components, 'scattered', self._str_none(
            params['products']['radiative_budget_properties']['element_components'].get('scattered')))

        brf_products_properties = et.SubElement(flux_tracking_products, 'BrfProductsProperties')
        self._set(brf_products_properties, 'brfProduct', params['products']['brf_properties'].get('brfProduct'))
        self._set(brf_products_properties, 'extrapolation', params['products']['brf_properties'].get('extrapolation'))
        self._set(brf_products_properties, 'horizontalOversampling',
                  params['products']['brf_properties'].get('horizontalOversampling'))
        # self._check_and_set(BrfProductsProperties,'ifSensorImageSimulation', '0')
        self._set(brf_products_properties, 'image', params['products']['brf_properties'].get('image'))
        self._set(brf_products_properties, 'luminanceProducts',
                  params['products']['brf_properties'].get('luminanceProducts'))
        self._set(brf_products_properties, 'maximalThetaImages',
                  params['products']['brf_properties'].get('maximalThetaImages'))
        self._set(brf_products_properties, 'nb_scene', params['products']['brf_properties'].get('nb_scene'))
        # self._check_and_set(BrfProductsProperties,'outputHapkeFile', '0')
        self._set(brf_products_properties, 'projection', params['products']['brf_properties'].get('projection'))
        self._set(brf_products_properties, 'sensorOversampling',
                  params['products']['brf_properties'].get('sensorOversampling'))
        self._set(brf_products_properties, 'sensorPlaneprojection',
                  params['products']['brf_properties'].get('sensorPlaneprojection'))
        self._set(brf_products_properties, 'transmittanceImages',
                  params['products']['brf_properties'].get('transmittanceImages'))
        self._set(brf_products_properties, 'pixelToSceneCorrespondences',
                  params['products']['brf_properties'].get('pixelToSceneCorrespondences'))
        self._set(brf_products_properties, 'centralizedBrfProduct',
                  params['products']['brf_properties'].get('transmittanceImages'))

        if params.get('image'):
            expert_mode_zone_etalement = et.SubElement(brf_products_properties, 'ExpertModeZone_Etalement')
            self._set(expert_mode_zone_etalement, 'etalement', params['products']['brf_properties'].get('etalement'))

            if params.get('sensorPlaneprojection'):
                expert_mode_zone_projection = et.SubElement(expert_mode_zone_etalement, 'ExpertModeZone_Projection')
                self._set(expert_mode_zone_projection, 'keepNonProjectedImage',
                          params['products']['brf_properties'].get('keepNonProjectedImage'))

                expert_mode_zone_per_type = et.SubElement(expert_mode_zone_etalement, 'ExpertModeZone_PerTypeProduct')
                self._set(expert_mode_zone_projection, 'generate_PerTypeProduct',
                          params['products']['brf_properties'].get('generate_PerTypeProduct'))

            if params.get('projection'):
                expert_mode_zone_mask_projection = et.SubElement(brf_products_properties,
                                                                 'ExpertModeZone_maskProjection')
                self._set(expert_mode_zone_mask_projection, 'albedoImages',
                          params['products']['brf_properties'].get('albedoImages'))

        order1_options = et.SubElement(flux_tracking_products, 'Order1Options')
        self._set(order1_options, 'images_only', params['products']['brf_properties'].get('images_only'))
        self._set(order1_options, 'order1only', params['products']['brf_properties'].get('order1only'))

        sensor_image_simulation = et.SubElement(phase, 'SensorImageSimulation')
        self._set(sensor_image_simulation, 'importMultipleSensors', params['sensor'].get('importMultipleSensors'))

        if params.get('importMultipleSensors'):
            sensors_importation = et.SubElement(sensor_image_simulation, 'SensorsImportation')
            self._set(sensors_importation, 'fileN', params['sensor'].get('fileN'))

        for n in range(len(params['sensor']['pinhole'])):
            pinhole = et.SubElement(sensor_image_simulation, 'Pinhole')
            self._set(pinhole, 'defCameraOrientation', params['sensor']['pinhole'][n].get('defCameraOrientation'))
            self._set(pinhole, 'setImageSize', params['sensor']['pinhole'][n].get('setImageSize'))
            self._set(pinhole, 'ifFishEye', params['sensor']['pinhole'][n].get('ifFishEye'))

            sensor = et.SubElement(pinhole, 'Sensor')
            self._set(sensor, 'sensorPosX', params['sensor']['pinhole'][n].get('sensorPosX'))
            self._set(sensor, 'sensorPosY', params['sensor']['pinhole'][n].get('sensorPosY'))
            self._set(sensor, 'sensorPosZ', params['sensor']['pinhole'][n].get('sensorPosZ'))

            orientation_def = et.SubElement(pinhole, 'OrientationDef')
            self._set(pinhole, 'orientDefType', params['sensor']['pinhole'][n].get('orientDefType'))
            if params['sensor']['pinhole'][n].get('orientDefType') == 0:
                camera_orientation = et.SubElement(orientation_def, 'CameraOrientation')
                self._set(camera_orientation, 'cameraRotation',
                          params['sensor']['pinhole'][n]['intrinsic_ZYZ'].get('cameraRotation'))
                self._set(camera_orientation, 'cameraPhi',
                          params['sensor']['pinhole'][n]['intrinsic_ZYZ'].get('cameraPhi'))
                self._set(camera_orientation, 'cameraTheta',
                          params['sensor']['pinhole'][n]['intrinsic_ZYZ'].get('cameraTheta'))
            elif params['sensor']['pinhole'][n].get('orientDefType') == 1:
                camera_orient_ypr = et.SubElement(orientation_def, 'CameraOrientYPR')
                self._set(camera_orient_ypr, 'pitch', params['sensor']['pinhole'][n]['tait_bryan'].get('pitch'))
                self._set(camera_orient_ypr, 'roll', params['sensor']['pinhole'][n]['tait_bryan'].get('roll'))
                self._set(camera_orient_ypr, 'rotDefBT', params['sensor']['pinhole'][n]['tait_bryan'].get('rotDefBT'))
                self._set(camera_orient_ypr, 'yaw', params['sensor']['pinhole'][n]['tait_bryan'].get('yaw'))
            else:
                raise Exception('Invalid Camera Orientation Definition')

            cam_image_FOV = et.SubElement(pinhole, 'CamImageFOV')
            self._set(cam_image_FOV, 'defNbPixels', params['sensor']['pinhole'][n].get('defNbPixels'))
            self._set(cam_image_FOV, 'definitionFOV', params['sensor']['pinhole'][n].get('definitionFOV'))

            if params['sensor']['pinhole'][n].get('defNbPixels') == 1:
                cam_nb_pixels = et.SubElement(cam_image_FOV, 'NbPixels')
                self._set(cam_nb_pixels, 'nbPixelsX', params['sensor']['pinhole'][n].get('nbPixelsX'))
                self._set(cam_nb_pixels, 'nbPixelsX', params['sensor']['pinhole'][n].get('nbPixelsY'))

            if params['sensor']['pinhole'][n].get('definitionFOV') == 0:
                cam_image_dim = et.SubElement(cam_image_FOV, 'CamImageDim')
                self._set(cam_image_dim, 'sizeImageX', params['sensor']['pinhole'][n]['fov'].get('sizeImageX'))
                self._set(cam_image_dim, 'nbPixelsX', params['sensor']['pinhole'][n]['fov'].get('sizeImageY'))

            elif params['sensor']['pinhole'][n].get('definitionFOV') == 1:
                cam_image_aov = et.SubElement(cam_image_FOV, 'CamImageAOV')
                self._set(cam_image_aov, 'aovX', params['sensor']['pinhole'][n]['aov'].get('x'))
                self._set(cam_image_aov, 'aovY', params['sensor']['pinhole'][n]['aov'].get('y'))

        for n in range(len(params['sensor']['pushbroom'])):
            pushbroom = et.SubElement(sensor_image_simulation, 'Pushbroom')

            if params['sensor']['pushbroom'][n].get('is_import') == 1:
                self._set(pushbroom, 'importThetaPhi', params['sensor']['pushbroom'][n].get('is_import'))

                importation = et.SubElement(pushbroom, 'Importation')
                self._set(importation, 'sensorAltitude', params['sensor']['pushbroom']['import'][n].get('altitude'))
                self._set(importation, 'offsetX', params['sensor']['pushbroom'][n]['import'].get('offsetX'))
                self._set(importation, 'offsetY', params['sensor']['pushbroom'][n]['import'].get('offsetY'))
                self._set(importation, 'phiFile', params['sensor']['pushbroom'][n]['import'].get('phiFile'))
                self._set(importation, 'resImage', params['sensor']['pushbroom'][n]['import'].get('resImage'))
                self._set(importation, 'thetaFile', params['sensor']['pushbroom'][n]['import'].get('thetaFile'))

            elif params['sensor']['pushbroom'][n].get('is_import') == 0:
                platform = et.SubElement(pushbroom, 'Platform')			
                self._set(platform, 'pitchLookAngle', params['sensor']['pushbroom'][n]['no_import'].get('pitchLookAngle'))			
                self._set(platform, 'platformAzimuth', params['sensor']['pushbroom'][n]['no_import'].get('platformAzimuth'))
                self._set(platform, 'platformDirection', params['sensor']['pushbroom'][n]['no_import'].get('platformDirection'))			

            else:
                raise Exception('Import is not properly defined. Should be 0 or 1.')

            sensor = et.SubElement(pushbroom, 'Sensor')
            self._set(sensor, 'sensorPosX', params['sensor']['pushbroom'][n].get('sensorPosX'))
            self._set(sensor, 'sensorPosY', params['sensor']['pushbroom'][n].get('sensorPosY'))
            self._set(sensor, 'sensorPosZ', params['sensor']['pushbroom'][n].get('sensorPosZ'))

        maket_module_products = et.SubElement(dart_product, 'maketModuleProducts')
        self._set(maket_module_products, 'MNEProducts', params['products']['DEM'].get('MNEProducts'))
        self._set(maket_module_products, 'areaMaketProducts', params['products']['DEM'].get('areaMaketProducts'))
        self._set(maket_module_products, 'coverRateProducts', params['products']['DEM'].get('coverRateProducts'))
        self._set(maket_module_products, 'laiProducts', params['products']['DEM'].get('laiProducts'))
        self._set(maket_module_products, 'objectGeneration', params['products']['DEM'].get('objectGeneration'))

        area_maket_products_properties = et.SubElement(maket_module_products, 'areaMaketProducts')
        self._set(area_maket_products_properties, 'areaMaketPerType', params['products']['DEM'].get('areaMaketPerType'))
        self._set(area_maket_products_properties, 'totalMaketArea', params['products']['DEM'].get('totalMaketArea'))

        cover_rate_products_properties = et.SubElement(maket_module_products, 'coverRateProductsProperties')
        self._set(cover_rate_products_properties, 'coverRatePerType', params['products']['DEM'].get('coverRatePerType'))
        self._set(cover_rate_products_properties, 'totalMaketCoverRate', params['products']['DEM'].get('totalMaketCoverRate'))
        self._set(cover_rate_products_properties, 'coverRatePrecision', params['products']['DEM'].get('coverRatePrecision'))

        lai_products_properties = et.SubElement(maket_module_products, 'LaiProductsProperties')
        self._set(lai_products_properties, 'lai1DProducts', params['products']['DEM'].get('lai1DProducts'))
        self._set(lai_products_properties, 'lai3DProducts', params['products']['DEM'].get('lai3DProducts'))
        self._set(lai_products_properties, 'nonEmptyCellsLayer', params['products']['DEM'].get('nonEmptyCellsLayer'))


class Directions(Component):
    COMPONENT_NAME = 'Directions'
    COMPONENT_FILE_NAME = 'directions.xml'
    IMPLEMENTED_WRITE_VERSION = ['5.7.5']

    def _check_params(self, params):
        return True

    def _write575(self, params, *args, **kwargs):
        directions = et.SubElement(self.xml_root, self.COMPONENT_NAME)
        self._set(directions, 'exactDate', params.get('exactDate'))
        self._set(directions, 'ifCosWeighted', params.get('ifCosWeighted'))
        self._set(directions, 'numberOfPropagationDirections', params.get('numberOfPropagationDirections'))

        sun_viewing_angles = et.SubElement(directions, 'SunViewingAngles')
        self._set(sun_viewing_angles, 'sunViewingAzimuthAngle', params['sun'].get('sunViewingAzimuthAngle'))
        self._set(sun_viewing_angles, 'sunViewingZenithAngle', params['sun'].get('sunViewingZenithAngle'))
        self._set(sun_viewing_angles, 'dayOfTheYear', params['sun'].get('dayOfTheYear'))

        hot_spot_properties = et.SubElement(directions, 'HotSpotProperties')
        self._set(hot_spot_properties, 'hotSpotParallelPlane', params['hotspot'].get('hotSpotParallelPlane'))
        self._set(hot_spot_properties, 'hotSpotPerpendicularPlane', params['hotspot'].get('hotSpotPerpendicularPlane'))
        self._set(hot_spot_properties, 'oversampleDownwardRegion', params['hotspot'].get('oversampleDownwardRegion'))
        self._set(hot_spot_properties, 'oversampleUpwardRegion', params['hotspot'].get('oversampleUpwardRegion'))

        hot_spot_downward_region = et.SubElement(hot_spot_properties, 'HotSpotDownwardRegion')
        self._set(hot_spot_downward_region, 'numberOfDirections', params['hotspot'].get('numberOfDownwardDirections'))
        self._set(hot_spot_downward_region, 'omega', params['hotspot'].get('omegaDown'))

        hot_spot_upward_region = et.SubElement(hot_spot_properties, 'HotSpotUpwardRegion')
        self._set(hot_spot_upward_region, 'numberOfDirections', params['hotspot'].get('numberOfUpwardDirections'))
        self._set(hot_spot_upward_region, 'omega', params['hotspot'].get('omegaUp'))

        penumbra_mode = et.SubElement(directions, 'Penumbra')
        self._set(penumbra_mode, 'mode', params.get('penumbraMode'))

        expert_mode_zone = et.SubElement(directions, 'ExpertModeZone')
        self._set(expert_mode_zone, 'numberOfAngularSector', params['expert'].get('numberOfAngularSector'))
        self._set(expert_mode_zone, 'numberOfLayers', params['expert'].get('numberOfLayers'))


class Plots(Component):
    COMPONENT_NAME = 'Plots'
    COMPONENT_FILE_NAME = 'plots.xml'
    IMPLEMENTED_WRITE_VERSION = ['5.7.5']

    def _check_params(self, params):
        return True

    def _write575(self, params, land_cover, voxel_size, *args, **kwargs):
        plots = et.SubElement(self.xml_root, self.COMPONENT_NAME)
        self._set(plots, 'isVegetation', params['general'].get('isVegetation'))
        # self._set(Plots, 'addExtraPlotsTextFile', params['general'].get('addExtraPlotsTextFile'))

        import_fichier_raster = et.SubElement(self.xml_root, 'ImportationFichierRaster')

        ground_types = params['general']['ground_types']

        if land_cover is None:
            return

        for row in range(land_cover.shape[0]):
            for col in range(land_cover.shape[1]):
                if col == land_cover.shape[1] | land_cover[row, col] != land_cover[row, col + 1]:

                    plot_type = land_cover[row, col]

                    plot = et.SubElement(plots, 'Plot')
                    self._check_and_set(plot, 'form', '0')
                    self._check_and_set(plot, 'isDisplayed', '1')
                    # self._check_and_set(Plot,'hidden','0')

                    polygon_2d = et.SubElement(plot, 'Polygon2D')

                    point_2d = et.SubElement(polygon_2d, 'Point2D')
                    self._set(point_2d, 'x', str(voxel_size[0] * row))
                    self._set(point_2d, 'y', str(voxel_size[1] * col))

                    point_2d = et.SubElement(polygon_2d, 'Point2D')
                    self._set(point_2d, 'x', str(voxel_size * (row + 1)))
                    self._set(point_2d, 'y', str(voxel_size * col))

                    point_2d = et.SubElement(polygon_2d, 'Point2D')
                    self._set(point_2d, 'x', str(voxel_size * (row + 1)))
                    self._set(point_2d, 'y', str(voxel_size * (col + 1)))

                    point_2d = et.SubElement(polygon_2d, 'Point2D')
                    self._set(point_2d, 'x', str(voxel_size[0] * row))
                    self._set(point_2d, 'y', str(voxel_size[1] * (col + 1)))

                    if plot_type in ground_types['vegetation'].ids:
                        vegetation_id = ground_types.ids.index(plot_type)
                        # TODO: shouldn't this be type 2 i.e. ground and vegetation
                        self._check_and_set(plot, 'type', '1')

                        plot_vegetation_properties = et.SubElement(plot, 'PlotVegetationProperties')
                        self._set(plot_vegetation_properties, 'densityDefinition',
                                  params['vegetation'].get('densityDefinition'))
                        self._set(plot_vegetation_properties, 'verticalFillMode',
                                  params['vegetation'].get('verticalFillMode'))

                        vegetation_geometry = et.SubElement(plot_vegetation_properties, 'VegetationGeometry')
                        self._set(vegetation_geometry, 'stDev',
                                  self._str_none(params['vegetation'].get('stdDev')[vegetation_id]))
                        self._check_and_set(vegetation_geometry, 'baseheight', '0')
                        self._set(vegetation_geometry, 'height',
                                  self._str_none(params['vegetation'].get('height')[vegetation_id]))

                        lai_vegetation = et.SubElement(plot_vegetation_properties, 'LAIVegetation')
                        self._set(lai_vegetation, 'LAI', self._str_none(params['vegetation'].get('lai')[vegetation_id]))

                        vegetation_optical_property_link = et.SubElement(plot_vegetation_properties,
                                                                         'VegetationOpticalPropertyLink')
                        self._check_and_set(vegetation_optical_property_link, 'ident',
                                            params['vegetation'].get('ident')[vegetation_id])
                        self._check_and_set(vegetation_optical_property_link, 'indexFctPhase', self._str_none(
                            params['vegetation'].get('indexFctPhase')[vegetation_id]))

                        ground_thermal_property_link = et.SubElement(plot_vegetation_properties,
                                                                     'GroundThermalPropertyLink')
                        self._set(ground_thermal_property_link, 'idTemperature',
                                  params['temperature'].get('idTemperature'))
                        self._set(ground_thermal_property_link, 'indexTemperature',
                                  params['temperature'].get('indexTemperature'))

                    elif plot_type in ground_types['ground'].ids:
                        litter_id = ground_types.ids.index(plot_type)
                        self._check_and_set(plot, 'type', '0')

                        ground_optical_property_link = et.SubElement(plot, 'GroundOpticalPropertyLink')
                        self._check_and_set(ground_optical_property_link, 'ident',
                                            params['ground'].get('ident')[litter_id])
                        self._set(ground_optical_property_link, 'indexFctPhase',
                                  self._str_none(params['ground'].get('indexFctPhase')[litter_id]))
                        self._set(ground_optical_property_link, 'type',
                                  self._str_none(params['ground'].get('type')[litter_id]))

                        ground_thermal_property_link = et.SubElement(plot, 'GroundThermalPropertyLink')
                        self._set(ground_thermal_property_link, 'idTemperature',
                                  params['temperature'].get('idTemperature'))
                        self._set(ground_thermal_property_link, 'indexTemperature',
                                  params['temperature'].get('indexTemperature'))

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
        coeff_diff = et.SubElement(self.xml_root, self.COMPONENT_NAME)
        self._set(coeff_diff, 'fluorescenceProducts', params['fluorescence'].get('fluorescenceProducts'))
        self._check_and_set(coeff_diff, 'fluorescenceFile', self._str_none(
            params['fluorescence'].get('fluorescenceFile')))  ## TODO: there should be a field to assign a file here!

        # *** 2d lambertian spectra ***
        lambertian_multi_functions = et.SubElement(coeff_diff, 'LambertianMultiFunctions')

        for m, (model_name, ident) in enumerate(zip(params['lop2d'].get('ModelName'), params['lop2d'].get('ident'))):
            lambertian_multi = et.SubElement(lambertian_multi_functions, 'LambertianMulti')
            self._check_and_set(lambertian_multi, 'ModelName', model_name)
            self._set(lambertian_multi, 'databaseName', params['lop2d'].get('databaseName'))
            self._check_and_set(lambertian_multi, 'ident', ident)
            self._set(lambertian_multi, 'roStDev', params['lop2d'].get('roStDev'))
            # self._set(lambertian_multi, 'specularDatabaseName', params['lop2d'].get('databaseName'))
            # self._check_and_set(lambertian_multi, 'specularModelName', params['lop2d'].get('ModelName'){m})
            # self._set(lambertian_multi, 'specularRoStDev', params['lop2d'].get('roStDev'))
            self._set(lambertian_multi, 'useMultiplicativeFactorForLUT',
                      params['lop2d'].get('useMultiplicativeFactorForLUT'))
            self._set(lambertian_multi, 'useSpecular', params['lop2d'].get('useSpecular'))

            prospect_external_module = et.SubElement(lambertian_multi, 'ProspectExternalModule')
            self._set(prospect_external_module, 'isFluorescent',
                      self._str_none(params['lop2d'].get('is_fluorescent')[m]))
            self._set(prospect_external_module, 'useProspectExternalModule',
                      params['lop2d'].get('useProspectExternalModule'))

            lambertian_node_multiplicative_factor_for_lut = et.SubElement(lambertian_multi,
                                                                          'lambertianNodeMultiplicativeFactorForLUT')
            self._set(lambertian_node_multiplicative_factor_for_lut, 'diffuseTransmittanceFactor',
                      params['lop2d'].get('diffuseTransmittanceFactor'))
            self._set(lambertian_node_multiplicative_factor_for_lut, 'diffuseTransmittanceAcceleration',
                      params['lop2d'].get('diffuseTransmittanceAcceleration'))
            self._set(lambertian_node_multiplicative_factor_for_lut, 'directTransmittanceFactor',
                      params['lop2d'].get('directTransmittanceFactor'))
            self._set(lambertian_node_multiplicative_factor_for_lut, 'reflectanceFactor',
                      params['lop2d'].get('reflectanceFactor'))
            self._set(lambertian_node_multiplicative_factor_for_lut, 'specularIntensityFactor',
                      params['lop2d'].get('specularIntensityFactor'))
            self._set(lambertian_node_multiplicative_factor_for_lut, 'useSameFactorForAllBands',
                      params['lop2d'].get('useSameFactorForAllBands'))
            self._set(lambertian_node_multiplicative_factor_for_lut, 'useSameOpticalFactorMatrixForAllBands',
                      params['lop2d'].get('useSameOpticalFactorMatrixForAllBands'))

            understory_multiplicative_factor_for_lut = et.SubElement(lambertian_node_multiplicative_factor_for_lut,
                                                                     'lambertianMultiplicativeFactorForLUT')
            self._set(understory_multiplicative_factor_for_lut, 'diffuseTransmittanceFactor',
                      params['lop2d'].get('diffuseTransmittanceFactor'))
            self._set(understory_multiplicative_factor_for_lut, 'directTransmittanceFactor',
                      params['lop2d'].get('directTransmittanceFactor'))
            self._set(understory_multiplicative_factor_for_lut, 'reflectanceFactor',
                      params['lop2d'].get('reflectanceFactor'))
            self._set(understory_multiplicative_factor_for_lut, 'specularIntensityFactor',
                      params['lop2d'].get('specularIntensityFactor'))
            self._set(understory_multiplicative_factor_for_lut, 'useOpticalFactorMatrix',
                      params['lop2d'].get('useSameOpticalFactorMatrixForAllBands'))

        # LambertianSpecularMultiFunctions = et.SubElement(coeff_diff, 'LambertianSpecularMultiFunctions')

        HapkeSpecularMultiFunctions = et.SubElement(coeff_diff, 'HapkeSpecularMultiFunctions')
        RPVMultiFunctions = et.SubElement(coeff_diff, 'RPVMultiFunctions')

        # *** 3d turbid spectra ***
        understory_multi_functions = et.SubElement(coeff_diff, 'UnderstoryMultiFunctions')
        self._set(understory_multi_functions, 'outputLADFile',
                  params['understory_multi_functions'].get('outputLADFile'))
        self._set(understory_multi_functions, 'integrationStepOnPhi',
                  params['understory_multi_functions'].get('integrationStepOnPhi'))
        self._set(understory_multi_functions, 'integrationStepOnTheta',
                  params['understory_multi_functions'].get('integrationStepOnTheta'))
        # self._set(UnderstoryMultiFunctions, 'specularEffects',        #                     self._str_none(params['understory_multi_functions'].get('specularEffects')))
        # self._check_and_set(UnderstoryMultiFunctions, 'useBunnick','0')

        for m, (model_name, ident, lad) in enumerate(zip(params['lop3d'].get('ModelName'), params['lop3d'].get('ident'),
                                                         params['lop3d'].get('lad'))):
            understory_multi = et.SubElement(understory_multi_functions, 'UnderstoryMulti')
            self._set(understory_multi, 'dimFoliar', self._str_none(params['lop3d'].get('dimFoliar')[m]))
            self._set(understory_multi, 'ident', self._str_none(ident))
            self._set(understory_multi, 'lad', self._str_none(lad))
            self._check_and_set(understory_multi, 'hasDifferentModelForBottom',
                                self._str_none('hasDifferentModelForBottom')[m])
            self._check_and_set(understory_multi, 'thermalHotSpotFactor', self._str_none('thermalHotSpotFactor')[m])
            self._check_and_set(understory_multi, 'useOpticalFactorMatrix', self._str_none('useOpticalFactorMatrix')[m])

            understory_multi_model = et.SubElement(understory_multi, 'UnderstoryMultiModel')
            self._check_and_set(understory_multi_model, 'ModelName', model_name)
            self._check_and_set(understory_multi_model, 'databaseName', params['lop3d'].get('databaseName')[m])
            self._set(understory_multi_model, 'useOpticalFactorMatrix',
                      self._str_none(params['lop3d'].get('useOpticalFactorMatrix')[m]))
            self._set(understory_multi_model, 'useSpecular', self._str_none(params['lop3d'].get('useSpecular')[m]))

            prospect_external_module = et.SubElement(understory_multi_model, 'ProspectExternalModule')
            self._set(prospect_external_module, 'useProspectExternalModule',
                      params['lop3d'].get('useProspectExternalModule'))
            self._set(prospect_external_module, 'isFluorescent',
                      self._str_none(params['lop3d'].get('isFluorescent')[m]))

            understory_node_multiplicative_factor_for_lut = et.SubElement(understory_multi_model,
                                                                          'understoryNodeMultiplicativeFactorForLUT')
            self._set(understory_node_multiplicative_factor_for_lut, 'LeafTransmittanceFactor',
                      params['lop3d'].get('LeafTransmittanceFactor'))
            self._set(understory_node_multiplicative_factor_for_lut, 'reflectanceFactor',
                      params['lop3d'].get('reflectanceFactor'))
            self._set(understory_node_multiplicative_factor_for_lut, 'diffuseTransmittanceAcceleration',
                      self._str_none(params['lop3d'].get('diffuseTransmittanceAcceleration')[m]))
            self._set(understory_node_multiplicative_factor_for_lut, 'useSameFactorForAllBands',
                      self._str_none(params['lop3d'].get('useSameFactorForAllBands')[m]))
            self._check_and_set(understory_node_multiplicative_factor_for_lut, 'useSameOpticalFactorMatrixForAllBands',
                                self._str_none(params['lop3d'].get('useSameOpticalFactorMatrixForAllBands')[
                                                   m]))  # TODO: Implement further input datafile which is needed, when this parameter is set to true!

            understory_multiplicative_factor_for_lut = et.SubElement(understory_node_multiplicative_factor_for_lut,
                                                                     'understoryMultiplicativeFactorForLUT')
            self._set(understory_multiplicative_factor_for_lut, 'LeafTransmittanceFactor',
                      self._str_none(params['lop3d'].get('LeafTransmittanceFactor')[m]))
            self._set(understory_multiplicative_factor_for_lut, 'reflectanceFactor',
                      self._str_none(params['lop3d'].get('reflectanceFactor')[m]))
            self._check_and_set(understory_multiplicative_factor_for_lut, 'useOpticalFactorMatrix',
                                self._str_none(params['lop3d'].get('useOpticalFactorMatrix')[
                                                   m]))  # TODO:implement changes to xml file, when this is set to true!

            specular_data = et.SubElement(understory_multi, 'SpecularData')
            self._set(specular_data, 'specularDatabaseName',
                      self._str_none(params['lop3d'].get('specularDatabaseName')[m]))
            self._set(specular_data, 'specularModelName', self._str_none(params['lop3d'].get('specularModelName')[m]))
            directional_clumping_index_properties = et.SubElement(understory_multi,
                                                                  'DirectionalClumpingIndexProperties')
            self._set(directional_clumping_index_properties, 'clumpinga',
                      self._str_none(params['lop3d'].get('clumpinga')[m]))
            self._set(directional_clumping_index_properties, 'clumpingb',
                      self._str_none(params['lop3d'].get('clumpingb')[m]))
            self._set(directional_clumping_index_properties, 'omegaMax',
                      self._str_none(params['lop3d'].get('omegaMax')[m]))
            self._set(directional_clumping_index_properties, 'omegaMin',
                      self._str_none(params['lop3d'].get('omegaMin')[m]))

        air_multi_functions = et.SubElement(coeff_diff, 'AirMultiFunctions')

        temperatures = et.SubElement(coeff_diff, 'Temperatures')
        thermal_function = et.SubElement(temperatures, 'ThermalFunction')
        self._set(thermal_function, 'deltaT', params['temperature'].get('deltaT'))
        self._set(thermal_function, 'idTemperature', params['temperature'].get('idTemperature'))
        self._set(thermal_function, 'meanT', params['temperature'].get('meanT'))
        self._set(thermal_function, 'override3DMatrix', params['temperature'].get('override3DMatrix'))
        self._set(thermal_function, 'singleTemperatureSurface', params['temperature'].get('singleTemperatureSurface'))
        self._set(thermal_function, 'useOpticalFactorMatrix', params['temperature'].get('useOpticalFactorMatrix'))
        self._set(thermal_function, 'usePrecomputedIPARs', params['temperature'].get('usePrecomputedIPARs'))
        # self._set(ThermalFunction, 'useOpticalFactorMatrix', params['lop3d'].get('useOpticalFactorMatrix'))


class Object3d(Component):
    COMPONENT_NAME = 'object_3d'
    COMPONENT_FILE_NAME = 'object_3d.xml'
    IMPLEMENTED_WRITE_VERSION = ['5.7.5']

    def _check_params(self, params):
        return True

    def _write575(self, params, *args, **kwargs):
        object_3d = et.SubElement(self.xml_root, self.COMPONENT_NAME)

        types = et.SubElement(object_3d, 'Types')
        default_types = et.SubElement(types, 'DefaultTypes')

        default_type = et.SubElement(default_types, 'DefaultType')
        self._check_and_set(default_type, 'indexOT', '101')
        self._check_and_set(default_type, 'name', 'Default_Object')
        self._check_and_set(default_type, 'typeColor', '125 0 125')

        default_type2 = et.SubElement(default_types, 'DefaultType')
        self._check_and_set(default_type2, 'indexOT', '102')
        self._check_and_set(default_type2, 'name', 'Leaf')
        self._check_and_set(default_type2, 'typeColor', '0 175 0')

        custom_types = et.SubElement(types, 'CustomTypes')
        object_list = et.SubElement(object_3d, 'ObjectList')

        obj = et.SubElement(object_list, 'Object')
        self._check_and_set(obj, 'file_src', params['path2obj'])
        self._set(obj, 'hasGroups', self._str_none(params['hasGroups']))
        self._set(obj, 'hidden', self._str_none(params['hidden']))
        self._set(obj, 'isDisplayed', self._str_none(params['isDisplayed']))
        self._check_and_set(obj, 'name', params['name'])
        self._set(obj, 'num', self._str_none(params['num']))
        self._check_and_set(obj, 'objectColor', params['objectColor'])
        self._set(obj, 'objectDEMMode', self._str_none(params['objectDEMMode']))

        geom_prop = et.SubElement(obj, 'GeometricProperties')

        pos_prop = et.SubElement(geom_prop, 'PositionProperties')
        self._set(pos_prop, 'xpos', self._str_none(params.get('location')[0]))
        self._set(pos_prop, 'ypos', self._str_none(params.get('location')[1]))
        self._set(pos_prop, 'zpos', self._str_none(params.get('location')[2]))

        dimension = et.SubElement(geom_prop, 'Dimension3D')
        self._set(dimension, 'xdim', self._str_none(params.get('dim')[0]))
        self._set(dimension, 'ydim', self._str_none(params.get('location')[1]))
        self._set(dimension, 'zdim', self._str_none(params.get('location')[2]))

        scale_prop = et.SubElement(geom_prop, 'ScaleProperties')
        self._set(scale_prop, 'xScaleDeviation', params['scale'].get('xScaleDeviation'))
        self._set(scale_prop, 'xscale', params['scale'].get('xscale'))
        self._set(scale_prop, 'yScaleDeviation', params['scale'].get('yScaleDeviation'))
        self._set(scale_prop, 'yscale', params['scale'].get('yscale'))
        self._set(scale_prop, 'zScaleDeviation', params['scale'].get('zScaleDeviation'))
        self._set(scale_prop, 'zscale', params['scale'].get('zscale'))

        rot_prop = et.SubElement(geom_prop, 'RotationProperties')
        self._set(rot_prop, 'xRotDeviation', params['rotation'].get('xRotDeviation'))
        self._set(rot_prop, 'xrot', params['rotation'].get('xrot'))
        self._set(rot_prop, 'yRotDeviation', params['rotation'].get('yRotDeviation'))
        self._set(rot_prop, 'yrot', params['rotation'].get('yrot'))
        self._set(rot_prop, 'zRotDeviation', params['rotation'].get('zRotDeviation'))
        self._set(rot_prop, 'zrot', params['rotation'].get('zrot'))

        object_optical_prop = et.SubElement(obj, 'ObjectOpticalProperties')
        self._set(object_optical_prop, 'doubleFace', params['optical_property'].get('doubleFace'))
        self._set(object_optical_prop, 'isLAICalc', params['optical_property'].get('isLAICalc'))
        self._set(object_optical_prop, 'isSingleGlobalLai', params['optical_property'].get('isSingleGlobalLai'))
        self._set(object_optical_prop, 'sameOPObject', params['optical_property'].get('sameOPObject'))

        object_property_link = et.SubElement(object_optical_prop, 'OpticalPropertyLink')
        self._set(object_property_link, 'ident', params['optical_property'].get('modelName'))
        self._set(object_property_link, 'indexFctPhase', params['optical_property'].get('indexFctPhase'))
        self._set(object_property_link, 'type', params['optical_property'].get('type'))

        thermal_property_link = et.SubElement(object_optical_prop, 'ThermalPropertyLink')
        self._set(thermal_property_link, 'idTemperature', params['temperature'].get('idTemperature'))
        self._set(thermal_property_link, 'indexTemperature', params['temperature'].get('indexTemp'))

        object_type_prop = et.SubElement(obj, 'ObjectTypeProperties')
        self._set(object_type_prop, 'sameOTObject', params['typeprop'].get('sameOTObject'))

        object_type_link = et.SubElement(object_type_prop, 'ObjectTypeLink')
        self._set(object_type_link, 'identOType', params['typeprop'].get('identOType'))
        self._set(object_type_link, 'indexOT', params['typeprop'].get('indexOT'))

        object_fields = et.SubElement(object_3d, 'ObjectFields')


class Maket(Component):
    COMPONENT_NAME = 'Maket'
    COMPONENT_FILE_NAME = 'maket.xml'
    IMPLEMENTED_WRITE_VERSION = ['5.7.5']

    def _check_params(self, params):
        return True

    def _write575(self, params):
        maket = et.SubElement(self.xml_root, self.COMPONENT_NAME)
        self._set(maket, 'dartZone', self._str_none(params['dartZone']))
        self._set(maket, 'exactlyPeriodicScene', self._str_none(params['exactlyPeriodicScene']))
        self._set(maket, 'useRandomGenerationSeed', self._str_none(params['useRandomGenerationSeed']))

        # scene
        scene = et.SubElement(self.xml_root, 'Scene')

        cell_dimensions = et.SubElement(self.xml_root, 'cell_dimensions')
        self._set(cell_dimensions, 'x', self._str_none(params['voxelDim'][0]))
        self._set(cell_dimensions, 'z', self._str_none(params['voxelDim'][2]))

        scene_dimensions = et.SubElement(self.xml_root, 'SceneDimensions')
        self._set(scene_dimensions, 'x', self._str_none(params['sceneDim'][1]))
        self._set(scene_dimensions, 'y', self._str_none(params['sceneDim'][0]))

        # ground
        soil = et.SubElement(self.xml_root, 'Soil')

        # optical property
        OpticalPropertyLink = et.SubElement(soil, 'OpticalPropertyLink')
        self._set(OpticalPropertyLink, 'ident', params['optical_property'].get('ident'))
        self._set(OpticalPropertyLink, 'indexFctPhase', params['optical_property'].get('indexFctPhase'))
        self._set(OpticalPropertyLink, 'type', params['optical_property'].get('type'))

        # thermal function
        thermal_property_link = et.SubElement(soil, 'ThermalPropertyLink')
        self._set(thermal_property_link, 'idTemperature', params['thermal_property'].get('idTemperature'))
        self._set(thermal_property_link, 'indexTemperature', params['thermal_property'].get('indexTemperature'))

        # topography
        if not self._str_none(params['topography'].get('fileName')):
            topography = et.SubElement(soil, 'Topography')
            self._check_and_set(topography, 'presenceOfTopography', '0')

            DEM_properties = et.SubElement(soil, 'DEM_properties')
            self._check_and_set(DEM_properties, 'createTopography', '0')

        else:
            topography = et.SubElement(self.xml_root, 'Topography')
            self._set(topography, 'presenceOfTopography', params['topography'].get('presenceOfTopography'))

            topography_properties = et.SubElement(topography, 'TopographyProperties')
            self._set(topography_properties, 'fileName', self._str_none(params['DEM']['outputFileName']))

            DEM_properties = et.SubElement(soil, 'DEM_properties')
            self._set(DEM_properties, 'createTopography', params['DEM'].get('createTopography'))

            DEM_generator = et.SubElement(DEM_properties, 'DEMGenerator')
            self._set(DEM_generator, 'caseDEM', params['DEM'].get('caseDEM'))
            self._set(DEM_generator, 'outputFileName', params['DEM'].get('outputFileName'))

            # TODO: check this, I dont't know what is done here
            DEM_5 = et.SubElement(DEM_generator, 'DEM_5')
            self._set(DEM_5, 'dataEncoding', self._str_none(params['DEM5']['dataEncoding']))
            self._set(DEM_5, 'dataFormat', self._str_none(params['DEM5']['dataFormat']))
            self._check_and_set(DEM_5, 'fileName', params['DEM5']['fileName'])

        # geo-location
        location = et.SubElement(self.xml_root, 'LatLon')
        self._set(location, 'altitude', self._str_none(params.get('location')[2]))
        self._set(location, 'latitude', self._str_none(params.get('location')[0]))
        self._set(location, 'longitude', self._str_none(params.get('location')[1]))


class Atmosphere(Component):
    COMPONENT_NAME = 'Atmosphere'
    COMPONENT_FILE_NAME = 'atmosphere.xml'
    IMPLEMENTED_WRITE_VERSION = ['5.7.5', '5.6.0']

    def _check_params(self, params):
        # TODO: implement proper checks on type and consistency in params, should depend on self.version
        return True

    def _write560(self, params, *args, **kwargs):
        atmos = et.SubElement(self.xml_root, self.COMPONENT_NAME)
        self._set(atmos, 'isRadiativeTransfertInBottomAtmosphereDefined',
                  params['general'].get('isRadiativeTransfertInBottomAtmosphereDefined'))

        is_atmosphere = et.SubElement(atmos, 'IsAtmosphere')
        self._set(is_atmosphere, 'typeOfAtmosphere', str(params['general'].get('typeOfAtmosphere')))

        atmosphere_iterations = et.SubElement(is_atmosphere, 'AtmosphereIterations')

        atmosphere_transfer_functions = et.SubElement(atmosphere_iterations, 'AtmosphereTransfertFunctions')
        self._set(atmosphere_transfer_functions, 'inputOutputTransfertFunctions',
                  params['general'].get('inputOutputTransfertFunctions'))

        computed_transfer_functions = et.SubElement(atmosphere_transfer_functions, 'ComputedTransferFunctions')
        self._set(computed_transfer_functions, 'writeTransferFunctions',
                  params['general'].get('writeTransferFunctions'))

        atmosphere_products = et.SubElement(atmosphere_iterations, 'AtmosphereProducts')
        self._set(atmosphere_products, 'atmosphereBRF_TOA', params['products'].get('atmosphereBRF_TOA'))
        self._set(atmosphere_products, 'atmosphereRadiance_BOA_apresCouplage',
                  params['products'].get('atmosphereRadiance_BOA_after_coupling'))
        self._set(atmosphere_products, 'atmosphereRadiance_BOA_avantCouplage',
                  params['products'].get('atmosphereRadiance_BOA_before_coupling'))
        self._set(atmosphere_products, 'ordreUnAtmos', params['products'].get('order_1'))

        atmosphere_components = et.SubElement(atmosphere_iterations, 'AtmosphereComponents')
        self._set(atmosphere_components, 'downwardingFluxes', params['cell_components'].get('downwardingFluxes'))
        self._set(atmosphere_components, 'upwardingFluxes', params['cell_components'].get('upwardingFluxes'))

        atmosphere_expert_mode_zone = et.SubElement(atmosphere_iterations, 'AtmosphereExpertModeZone')
        self._set(atmosphere_expert_mode_zone, 'extrapol_atmos', params['expert'].get('extrapol_atmos'))
        self._set(atmosphere_expert_mode_zone, 'seuilEclairementAtmos', params['expert'].get('seuilEclairementAtmos'))
        self._set(atmosphere_expert_mode_zone, 'seuilFTAtmos', params['expert'].get('seuilFTAtmos'))

        atmosphere_geometry = et.SubElement(is_atmosphere, 'AtmosphereGeometry')
        self._set(atmosphere_geometry, 'discretisationAtmos', params['geometry'].get('discretisationAtmos'))
        self._set(atmosphere_geometry, 'heightOfSensor', params['geometry'].get('heightOfSensor'))
        self._set(atmosphere_geometry, 'minimumNumberOfDivisions', params['geometry'].get('minimumNumberOfDivisions'))

        mid_atmosphere = et.SubElement(atmosphere_geometry, 'MidAtmosphere')

        cell_dimensions = et.SubElement(mid_atmosphere, 'cell_dimensions')
        self._set(cell_dimensions, 'xAI', params['dimensions'].get('xAI'))
        self._set(cell_dimensions, 'yAI', params['dimensions'].get('yAI'))
        self._set(cell_dimensions, 'zAI', params['dimensions'].get('zAI'))

        height = et.SubElement(mid_atmosphere, 'Height')
        self._set(height, 'hCFAI', params['dimensions'].get('hCFAI'))

        upper_atmosphere = et.SubElement(atmosphere_geometry, 'UpperAtmosphere')
        self._set(upper_atmosphere, 'hCFHA', params['dimensions'].get('hCFHA'))

        layer = et.SubElement(upper_atmosphere, 'Layer')
        self._set(layer, 'zHA', params['dimensions'].get('zHA'))

        if params['general']['typeOfAtmosphere'] == 1:
            atmospheric_optical_property_model = et.SubElement(is_atmosphere, 'AtmosphericOpticalPropertyModel')
            self._set(atmospheric_optical_property_model, 'correctionBandModel',
                      params['optical_property_db'].get('correctionBandModel'))
            self._set(atmospheric_optical_property_model, 'databaseName',
                      params['optical_property_db'].get('dataBaseName'))
            self._set(atmospheric_optical_property_model, 'temperatureModelName',
                      params['optical_property_db'].get('temperatureModelName'))

            self._check_and_set(atmospheric_optical_property_model, 'hgParametersModelName', self._str_none(
                params['optical_property_db']['aerosol'].get('hgParametersModelName')))
            self._check_and_set(atmospheric_optical_property_model, 'aerosolCumulativeModelName', self._str_none(
                params['optical_property_db']['aerosol'].get('cumulativeModelName')))
            self._set(atmospheric_optical_property_model, 'aerosolOptDepthFactor',
                      params['optical_property_db']['aerosol'].get('optDepthFactor'))
            self._set(atmospheric_optical_property_model, 'aerosolsGroup',
                      params['optical_property_db']['aerosol'].get('group'))
            self._set(atmospheric_optical_property_model, 'aerosolsModelName',
                      params['optical_property_db']['aerosol'].get('modelName'))

            self._set(atmospheric_optical_property_model, 'gasCumulativeModelName',
                      params['optical_property_db']['gas'].get('cumulativeModelName'))
            self._set(atmospheric_optical_property_model, 'gasGroup', params['optical_property_db']['gas'].get('group'))
            self._set(atmospheric_optical_property_model, 'gasModelName',
                      params['optical_property_db']['gas'].get('modelName'))
            self._check_and_set(atmospheric_optical_property_model, 'gasParametersModelName', self._str_none(
                params['optical_property_db']['gas'].get('gasParametersModelName')))

            self._set(atmospheric_optical_property_model, 'precipitableWaterAmountCkeckbox',
                      params['optical_property_db'].get('water').get('include'))
            water_amount = et.SubElement(atmospheric_optical_property_model, 'WaterAmount')
            self._check_and_set(water_amount, 'precipitableWaterAmount', self._str_none(
                params['optical_property_db'].get('water').get('precipitableWaterAmount')))

        elif params['general']['typeOfAtmosphere'] == 0:
            atmospheric_optical_property = et.SubElement(is_atmosphere, 'AtmosphericOpticalProperty')
            self._set(atmospheric_optical_property, 'courbureTerre',
                      params['optical_property'].get('correct_earth_curvature'))
            self._set(atmospheric_optical_property, 'pointMilieu', params['optical_property'].get('correct_mid_point'))
            self._set(atmospheric_optical_property, 'a_HG', params['optical_property'].get('heyney_greenstein_a'))
            self._set(atmospheric_optical_property, 'g1', params['optical_property'].get('heyney_greenstein_g1'))
            self._set(atmospheric_optical_property, 'g2', params['optical_property'].get('heyney_greenstein_g2'))

            self._set(atmospheric_optical_property, 'aerosolOpticalDepth',
                      params['optical_property']['aerosol'].get('optical_depth'))
            self._set(atmospheric_optical_property, 'aerosolScaleFactor',
                      params['optical_property']['aerosol'].get('scale_factor'))
            self._set(atmospheric_optical_property, 'aerosolAlbedo',
                      params['optical_property']['aerosol'].get('albedo'))

            self._set(atmospheric_optical_property, 'gasOpticalDepth',
                      params['optical_property']['gas'].get('optical_depth'))
            self._set(atmospheric_optical_property, 'gasScaleFactor',
                      params['optical_property']['gas'].get('scale_factor'))
            self._set(atmospheric_optical_property, 'transmittanceOfGases',
                      params['optical_property']['gas'].get('transmittance'))

            temperature_model = et.SubElement(is_atmosphere, 'TemperatureFile')
            self._set(temperature_model, 'atmosphereTemperatureFileName',
                      params['optical_property'].get('temperature_file_name'))
        else:
            raise TypeError('Variable typeOfAtmosphere must be 0 or 1')

        is_radiative_transfert_in_bottom_atmosphere = et.SubElement(is_atmosphere,
                                                                    'isRadiativeTransfertInBottomAtmosphere')
        self._set(is_radiative_transfert_in_bottom_atmosphere, 'BA_altitude', params['dimensions'].get('BA_altitude'))

    def _write575(self, params, *args, **kwargs):
        atmos = et.SubElement(self.xml_root, self.COMPONENT_NAME)
        self._set(atmos, 'isRadiativeTransfertInBottomAtmosphereDefined',
                  params['general'].get('isRadiativeTransfertInBottomAtmosphereDefined'))

        is_atmosphere = et.SubElement(atmos, 'IsAtmosphere')
        self._set(is_atmosphere, 'typeOfAtmosphere', str(params['general'].get('typeOfAtmosphere')))

        atmosphere_iterations = et.SubElement(is_atmosphere, 'AtmosphereIterations')

        atmosphere_transfer_functions = et.SubElement(atmosphere_iterations, 'AtmosphereTransfertFunctions')
        self._set(atmosphere_transfer_functions, 'inputOutputTransfertFunctions',
                  params['general'].get('inputOutputTransfertFunctions'))

        computed_transfer_functions = et.SubElement(atmosphere_transfer_functions, 'ComputedTransferFunctions')
        self._set(computed_transfer_functions, 'writeTransferFunctions',
                  params['general'].get('writeTransferFunctions'))

        atmosphere_products = et.SubElement(atmosphere_iterations, 'AtmosphereProducts')
        self._set(atmosphere_products, 'atmosphereBRF_TOA', params['products'].get('atmosphereBRF_TOA'))
        self._set(atmosphere_products, 'atmosphereRadiance_BOA_apresCouplage',
                  params['products'].get('atmosphereRadiance_BOA_after_coupling'))
        self._set(atmosphere_products, 'atmosphereRadiance_BOA_avantCouplage',
                  params['products'].get('atmosphereRadiance_BOA_before_coupling'))
        self._set(atmosphere_products, 'ordreUnAtmos', params['products'].get('order_1'))
        self._set(atmosphere_products, 'atmosphereReport', params['products'].get('atmosphereReport'))

        atmosphere_components = et.SubElement(atmosphere_iterations, 'AtmosphereComponents')
        self._set(atmosphere_components, 'downwardingFluxes', params['components'].get('downwardingFluxes'))
        self._set(atmosphere_components, 'upwardingFluxes', params['components'].get('upwardingFluxes'))

        atmosphere_expert_mode_zone = et.SubElement(atmosphere_iterations, 'AtmosphereExpertModeZone')
        self._set(atmosphere_expert_mode_zone, 'extrapol_atmos', params['expert'].get('extrapol_atmos'))
        self._set(atmosphere_expert_mode_zone, 'number_iterationMax', params['expert'].get('number_iterationMax'))
        self._set(atmosphere_expert_mode_zone, 'threshold_Atmos_scattering',
                  params['expert'].get('threshold_Atmos_scattering'))

        atmosphere_geometry = et.SubElement(is_atmosphere, 'AtmosphereGeometry')
        self._set(atmosphere_geometry, 'discretisationAtmos', params['geometry'].get('discretisationAtmos'))
        self._set(atmosphere_geometry, 'heightOfSensor', params['geometry'].get('heightOfSensor'))
        self._set(atmosphere_geometry, 'minimumNumberOfDivisions', params['geometry'].get('minimumNumberOfDivisions'))

        mid_atmosphere = et.SubElement(atmosphere_geometry, 'MidAtmosphere')

        cell_dimensions = et.SubElement(mid_atmosphere, 'cell_dimensions')
        self._set(cell_dimensions, 'xAI', params['dimensions'].get('xAI'))
        self._set(cell_dimensions, 'yAI', params['dimensions'].get('yAI'))
        self._set(cell_dimensions, 'zAI', params['dimensions'].get('zAI'))

        height = et.SubElement(mid_atmosphere, 'Height')
        self._set(height, 'hCFAI', params['dimensions'].get('hCFAI'))

        upper_atmosphere = et.SubElement(atmosphere_geometry, 'UpperAtmosphere')
        self._set(upper_atmosphere, 'hCFHA', params['dimensions'].get('hCFHA'))

        layer = et.SubElement(upper_atmosphere, 'Layer')
        self._set(layer, 'zHA', params['dimensions'].get('zHA'))

        aerosol = et.SubElement(atmos, 'Aerosol')
        aerosol_properties = et.SubElement(aerosol, 'AerosolProperties')
        self._set(aerosol_properties, 'hgParametersModelName',
                  params['optical_property_db']['aerosol'].get('hgParametersModelName'))
        self._set(aerosol_properties, 'aerosolCumulativeModelName',
                  params['optical_property_db']['aerosol'].get('cumulativeModelName'))
        self._set(aerosol_properties, 'aerosolOptDepthFactor',
                  params['optical_property_db']['aerosol'].get('optDepthFactor'))
        self._set(aerosol_properties, 'aerosolsGroup', params['optical_property_db']['aerosol'].get('group'))
        self._set(aerosol_properties, 'aerosolsModelName', params['optical_property_db']['aerosol'].get('modelName'))
        self._set(aerosol_properties, 'databaseName', params['optical_property_db']['aerosol'].get('dataBaseName'))

        if params['general']['typeOfAtmosphere'] == 1:
            atmospheric_optical_property_model = et.SubElement(is_atmosphere, 'AtmosphericOpticalPropertyModel')
            self._set(atmospheric_optical_property_model, 'correctionBandModel',
                      params['optical_property_db'].get('correctionBandModel'))
            self._set(atmospheric_optical_property_model, 'temperatureModelName',
                      params['optical_property_db'].get('temperatureModelName'))

            self._set(atmospheric_optical_property_model, 'gasCumulativeModelName',
                      params['optical_property_db']['gas'].get('cumulativeModelName'))
            self._set(atmospheric_optical_property_model, 'gasGroup', params['optical_property_db']['gas'].get('group'))
            self._set(atmospheric_optical_property_model, 'gasModelName',
                      params['optical_property_db']['gas'].get('modelName'))
            self._check_and_set(atmospheric_optical_property_model, 'gasParametersModelName', self._str_none(
                params['optical_property_db']['gas'].get('gasParametersModelName')))

            self._set(atmospheric_optical_property_model, 'precipitableWaterAmountCkeckbox',
                      params['water'].get('include'))
            water_amount = et.SubElement(atmospheric_optical_property_model, 'WaterAmount')
            self._set(water_amount, 'defWaterAmount', params['water'].get('defWaterAmount'))

            if params['water'].get('defWaterAmount') == '0':
                water_spec = et.SubElement(water_amount, 'M_factor')
                water_spec.set('mulFactorH2O', params['water']['mulFactorH2O'])

        elif params['general']['typeOfAtmosphere'] == 0:
            atmospheric_optical_property = et.SubElement(is_atmosphere, 'AtmosphericOpticalProperty')
            self._set(atmospheric_optical_property, 'courbureTerre',
                      params['optical_property'].get('correct_earth_curvature'))
            self._set(atmospheric_optical_property, 'pointMilieu', params['optical_property'].get('correct_mid_point'))
            self._set(atmospheric_optical_property, 'a_HG', params['optical_property'].get('heyney_greenstein_a'))
            self._set(atmospheric_optical_property, 'g1', params['optical_property'].get('heyney_greenstein_g1'))
            self._set(atmospheric_optical_property, 'g2', params['optical_property'].get('heyney_greenstein_g2'))

            self._set(atmospheric_optical_property, 'aerosolOpticalDepth',
                      params['optical_property']['aerosol'].get('optical_depth'))
            self._set(atmospheric_optical_property, 'aerosolScaleFactor',
                      params['optical_property']['aerosol'].get('scale_factor'))
            self._set(atmospheric_optical_property, 'aerosolAlbedo',
                      params['optical_property']['aerosol'].get('albedo'))

            self._set(atmospheric_optical_property, 'gasOpticalDepth',
                      params['optical_property']['gas'].get('optical_depth'))
            self._set(atmospheric_optical_property, 'gasScaleFactor',
                      params['optical_property']['gas'].get('scale_factor'))
            self._set(atmospheric_optical_property, 'transmittanceOfGases',
                      params['optical_property']['gas'].get('transmittance'))

            temperature_model = et.SubElement(is_atmosphere, 'TemperatureFile')
            self._set(temperature_model, 'atmosphereTemperatureFileName',
                      params['optical_property'].get('temperature_file_name'))
        else:
            raise TypeError('Variable typeOfAtmosphere must be 0 or 1')

        is_radiative_transfert_in_bottom_atmosphere = et.SubElement(is_atmosphere,
                                                                    'isRadiativeTransfertInBottomAtmosphere')
        self._set(is_radiative_transfert_in_bottom_atmosphere, 'BA_altitude', params['dimensions'].get('BA_altitude'))
