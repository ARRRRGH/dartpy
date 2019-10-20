from lxml import etree as et
import os
import logging
from pkg_resources import parse_version
import utils.general as general
from shutil import copyfile

ROOT_TAG = 'DartFile'


class Component(object):
    """
    A component is any entity that is represented by a xml file in the DART simulation folder.
    """
    COMPONENT_FILE_NAME = None
    COMPONENT_NAME = None

    def __init__(self, simulation_dir, params, version):
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
        self.params = params

        self.xml_root = et.Element(ROOT_TAG)
        self.xml_root.set('version', self.version)
        self._write(self.params)
        self._xml_only = False

    def from_file(self, simulation_dir, path, version, force=False):
        """
        Create a component from its xml file
        :param simulation_dir:
        :param path:
        :param version:
        :param force:
        :return:
        """
        self._read(path)

        # Check if this is a dart file, if its version is correct (if supplied) and whether it is the correct component
        valid = self.xml_root.tag == ROOT_TAG and \
                self.xml_root.get('version') == version and \
                self.COMPONENT_NAME in [el.tag for el in list(self.xml_root)]
        if not (valid or force):
            logging.exception(
                'Cannot load ' + path + 'since file does not seem to be valid. If you are convinced it is, ' +
                'use force=True')
        else:
            self.simulation_dir = simulation_dir
            self.version = self.xml_root.get('version')
            self._xml_only = True

            inp_path = os.path.normpath(os.path.join(self.simulation_dir, 'input'))
            xml_path = os.path.normpath(os.path.join(inp_path, self.COMPONENT_FILE_NAME))

            copyfile(path, xml_path)

        return self

    def to_file(self):
        if not self._xml_only:
            tree = et.ElementTree(self.xml_root)
            self._write(self.params)

            inp_path = os.path.normpath(os.path.join(self.simulation_dir, 'input'))
            xml_path = os.path.normpath(os.path.join(inp_path, self.COMPONENT_FILE_NAME))

            if not os.path.exists(inp_path):
                os.mkdir(inp_path)
            tree.to_file(xml_path, pretty_print=True)

    def _read(self, path):
        tree = et.parse(path)
        self.xml_root = tree.getroot()

    def _write(self, params):
        assert self._check_params(params)

        # this is to ensure undefined elements are projected to None and do not raise an Error a priori
        if parse_version(self.version) >= parse_version('5.7.5'):
            self._write575(params)
        elif parse_version(self.version) >= parse_version('5.6.0'):
            self._write560(params)

    def _check_and_set(self, element, key, val, check=None):
        if check is not None:
            assert check(key, val)

        if val is not None:
            element.set(key, val)
        else:
            logging.warning('Could not set ' + key + ' with value ' + str(val))

    def _str_none(self, val):
        if val is not None:
            return str(val)
        return None

    def _check_params(self, params):
        raise NotImplementedError

    def _write575(self, params, *args, **kwargs):
        raise NotImplemented

    def _write560(self, params, *args, **kwargs):
        raise NotImplemented


class Phase(Component):
    COMPONENT_NAME = 'Phase'
    COMPONENT_FILE_NAME = 'params.xml'

    def _check_params(self, params):
        return True

    def _write575(self, params, *args, **kwargs):
        phase = et.SubElement(self.xml_root, self.COMPONENT_NAME)
        self._check_and_set(phase, 'calculatorMethod', self._str_none(params.get('calculatorMethod')))

        # radiative transfer method
        atmosphere_radiative_transfer = et.SubElement(phase, 'AtmosphereRadiativeTransfer')
        self._check_and_set(atmosphere_radiative_transfer, 'TOAtoBOA', self._str_none(params.get('toaToBoa')))

        # advanced mode
        expert_mode_zone = et.SubElement(phase, 'ExpertModeZone')
        self._check_and_set(expert_mode_zone, 'albedoThreshold',
                            self._str_none(params['expert_flux_tracking'].get('albedoThreshold')))
        self._check_and_set(expert_mode_zone, 'expertMode',
                            self._str_none(params['expert_flux_tracking'].get('expertMode')))
        self._check_and_set(expert_mode_zone, 'illuminationRepartitionMode',
                            self._str_none(params['expert_flux_tracking'].get('illuminationRepartitionMode')))
        self._check_and_set(expert_mode_zone, 'lightPropagationThreshold',
                            self._str_none(params['expert_flux_tracking'].get('lightPropagationThreshold')))
        self._check_and_set(expert_mode_zone, 'nbRandomPointsPerInteceptionAtmosphere', self._str_none(
            params['expert_flux_tracking'].get('nbRandomPointsPerInteceptionAtmosphere')))
        self._check_and_set(expert_mode_zone, 'nbSubSubcenterTurbidEmission',
                            self._str_none(params['expert_flux_tracking'].get('nbSubSubcenterTurbidEmission')))
        # self._check_and_set(ExpertModeZone,'surfaceBarycenterEnabled', self._str_none(params['expert_flux_tracking'].get('surfaceBarycenterEnabled')))
        # self._check_and_set(ExpertModeZone,'useExternalScripts', self._str_none(params['expert_flux_tracking'].get('useExternalScripts')))
        self._check_and_set(expert_mode_zone, 'distanceBetweenIlluminationSubCenters', self._str_none(
            params['expert_flux_tracking'].get('distanceBetweenIlluminationSubCenters')))
        self._check_and_set(expert_mode_zone, 'distanceBetweenIlluminationSubCenters',
                            self._str_none(params['expert_flux_tracking'].get('subFaceBarycenterEnabled')))
        # self._check_and_set(ExpertModeZone,'isInterceptedPowerPerDirectionForSpecularCheck', self._str_none(params['expert_flux_tracking'].get('isInterceptedPowerPerDirectionForSpecularCheck')))
        # self._check_and_set(ExpertModeZone,'nbSubcenterIllumination', self._str_none(params['expert_flux_tracking'].get('nbSubcenterIllumination')))
        self._check_and_set(expert_mode_zone, 'nbSubcenterVolume',
                            self._str_none(params['expert_flux_tracking'].get('nbSubcenterVolume')))
        self._check_and_set(expert_mode_zone, 'nbThreads',
                            self._str_none(params['expert_flux_tracking'].get('nbThreads')))

        # *** Dart Input Parameters ***
        dart_input_parameters = et.SubElement(phase, 'dart_input_parameters')

        # flux tracking parameters
        nodefluxtracking = et.SubElement(dart_input_parameters, 'nodefluxtracking')
        self._check_and_set(nodefluxtracking, 'gaussSiedelAcceleratingTechnique',
                            self._str_none(params['flux_tracking'].get('gaussSiedelAcceleratingTechnique')))
        self._check_and_set(nodefluxtracking, 'numberOfIteration',
                            self._str_none(params['flux_tracking'].get('numberOfIteration')))

        # scene 3d temperature
        spectral_domain_tir = et.SubElement(dart_input_parameters, 'SpectralDomainTir')
        self._check_and_set(spectral_domain_tir, 'temperatureMode',
                            self._str_none(params['spectral'].get('temperatureMode')))

        skylTemperature = et.SubElement(spectral_domain_tir, 'skylTemperature')
        self._check_and_set(skylTemperature, 'SKYLForTemperatureAssignation',
                            self._str_none(params['atmosphere'].get('SKYLForTemperatureAssignation')))

        # spectral intervals
        spectral_intervals = et.SubElement(dart_input_parameters, 'SpectralIntervals')

        for n in range(len(params['spectral'].get('bandNumber'))):
            spectral_intervals_properties = et.SubElement(spectral_intervals, 'SpectralIntervalsProperties')
            self._check_and_set(spectral_intervals_properties, 'bandNumber', self._str_none[n])
            self._check_and_set(spectral_intervals_properties, 'deltaLambda',
                                self._str_none(params.get('deltaLambda')[n]))
            self._check_and_set(spectral_intervals_properties, 'meanLambda',
                                self._str_none(params.get('meanLambda')[n]))
            self._check_and_set(spectral_intervals_properties, 'spectralDartMode',
                                self._str_none(params.get('spectralDartMode')))

        # atmosphere brightness temperature
        temperature_atmosphere = et.SubElement(dart_input_parameters, 'temperatureAtmosphere')
        self._check_and_set(temperature_atmosphere, 'atmosphericApparentTemperature',
                            self._str_none(params['atmosphere'].get('atmosphericApparentTemperature')))

        # earth scene irradiance
        node_illumination_mode = et.SubElement(dart_input_parameters, 'nodeIlluminationMode')
        self._check_and_set(node_illumination_mode, 'illuminationMode',
                            self._str_none(params['irradiance'].get('illuminationMode')))
        self._check_and_set(node_illumination_mode, 'irradianceMode',
                            self._str_none(params['irradiance'].get('irradianceMode')))

        irradiance_database_node = et.SubElement(node_illumination_mode, 'irradianceDatabaseNode')
        self._check_and_set(irradiance_database_node, 'databaseName', params['irradiance'].get('databaseName'))
        self._check_and_set(irradiance_database_node, 'irradianceColumn',
                            params['irradiance'].get('irradianceColumn'))
        self._check_and_set(irradiance_database_node, 'irradianceTable',
                            params['irradiance'].get('irradianceTable'))
        self._check_and_set(irradiance_database_node, 'weightAtmosphereParameters',
                            self._str_none(params['irradiance'].get('weightAtmosphereParameters')))
        self._check_and_set(irradiance_database_node, 'weightReflectanceParameters',
                            self._str_none(params['irradiance'].get('weightReflectanceParameters')))

        spectral_irradiance = et.SubElement(node_illumination_mode, 'SpectralIrradiance')

        common_parameters = et.SubElement(spectral_irradiance, 'CommonParameters')
        self._check_and_set(common_parameters, 'commonIrradianceCheckBox',
                            self._str_none(params['irradiance'].get('commonIrradianceCheckBox')))
        self._check_and_set(common_parameters, 'commonSkylCheckBox',
                            self._str_none(params['irradiance'].get('commonSkylCheckBox')))

        spectral_irradiance_value = et.SubElement(spectral_irradiance, 'SpectralIrradianceValue')
        self._check_and_set(spectral_irradiance_value, 'Skyl', self._str_none(params.get('Skyl')))
        self._check_and_set(spectral_irradiance_value, 'bandNumber', '0')
        self._check_and_set(spectral_irradiance_value, 'irradiance', self._str_none(params.get('irradiance')))

        # *** Dart Products ***
        dart_product = et.SubElement(phase, 'DartProduct')

        dart_module_products = et.SubElement(dart_product, 'dartModuleProducts')
        self._check_and_set(dart_module_products, 'allIterationsProducts',
                            self._str_none(params['products'].get('allIterationsProducts')))
        self._check_and_set(dart_module_products, 'brfProducts',
                            self._str_none(params['products'].get('brfProducts')))
        self._check_and_set(dart_module_products, 'lidarImageProducts',
                            self._str_none(params['products'].get('lidarImageProducts')))
        self._check_and_set(dart_module_products, 'lidarProducts',
                            self._str_none(params['products'].get('lidarProducts')))
        self._check_and_set(dart_module_products, 'order1Products', self._str_none(params.get('order1Products')))
        self._check_and_set(dart_module_products, 'radiativeBudgetProducts',
                            self._str_none(params['products'].get('radiativeBudgetProducts')))
        self._check_and_set(dart_module_products, 'temperaturePerTrianglePerCell',
                            self._str_none(params['products'].get('temperaturePerTrianglePerCell')))
        self._check_and_set(dart_module_products, 'polarizationProducts',
                            self._str_none(params['products'].get('polarizationProducts')))

        # TODO: find out what this is
        radiative_budget_properties = et.SubElement(dart_module_products, 'radiativeBudgetProperties')
        self._check_and_set(radiative_budget_properties, 'budget3DParSurface', '0')
        self._check_and_set(radiative_budget_properties, 'budget3DParType', '0')
        self._check_and_set(radiative_budget_properties, 'budgetTotalParType', '0')
        self._check_and_set(radiative_budget_properties, 'budgetUnitModeR', '1')
        self._check_and_set(radiative_budget_properties, 'extrapolation', '1')
        self._check_and_set(radiative_budget_properties, 'fIRfARfSRfINTR1DProducts', '0')
        self._check_and_set(radiative_budget_properties, 'fIRfARfSRfINTR3DProducts', '1')
        # self._check_and_set(radiativeBudgetProperties,'fIRfARfSRfINTR2DProducts', '1')
        # self._check_and_set(radiativeBudgetProperties,'budget2DParType', '0')

        brf_products_properties = et.SubElement(dart_module_products, 'BrfProductsProperties')
        self._check_and_set(brf_products_properties, 'brfProduct',
                            self._str_none(params['products']['brf'].get('brfProduct')))
        self._check_and_set(brf_products_properties, 'extrapolation',
                            self._str_none(params['products']['brf'].get('extrapolation')))
        self._check_and_set(brf_products_properties, 'horizontalOversampling',
                            self._str_none(params['products']['brf'].get('horizontalOversampling')))
        # self._check_and_set(BrfProductsProperties,'ifSensorImageSimulation', '0')
        self._check_and_set(brf_products_properties, 'image',
                            self._str_none(params['products']['brf'].get('image')))
        self._check_and_set(brf_products_properties, 'luminanceProducts',
                            self._str_none(params['products']['brf'].get('luminanceProducts')))
        self._check_and_set(brf_products_properties, 'maximalThetaImages',
                            self._str_none(params['products']['brf'].get('maximalThetaImages')))
        self._check_and_set(brf_products_properties, 'nb_scene',
                            self._str_none(params['products']['brf'].get('nb_scene')))
        # self._check_and_set(BrfProductsProperties,'outputHapkeFile', '0')
        self._check_and_set(brf_products_properties, 'projection',
                            self._str_none(params['products']['brf'].get('projection')))
        self._check_and_set(brf_products_properties, 'sensorOversampling',
                            self._str_none(params['products']['brf'].get('sensorOversampling')))
        self._check_and_set(brf_products_properties, 'sensorPlaneprojection',
                            self._str_none(params['products']['brf'].get('sensorPlaneprojection')))
        # self._check_and_set(BrfProductsProperties,'transmittanceImages', '0')
        # self._check_and_set(BrfProductsProperties,'centralizedBrfProduct', '1')

        if params.get('image'):
            expert_mode_zone_etalement = et.SubElement(brf_products_properties, 'ExpertModeZone_Etalement')
            self._check_and_set(expert_mode_zone_etalement, 'etalement',
                                self._str_none(params['products']['brf'].get('etalement')))

            if params.get('sensorPlaneprojection'):
                expert_mode_zone_projection = et.SubElement(expert_mode_zone_etalement, 'ExpertModeZone_Projection')
                self._check_and_set(expert_mode_zone_projection, 'keepNonProjectedImage',
                                    self._str_none(params['products']['brf'].get('keepNonProjectedImage')))

            if params.get('projection'):
                expert_mode_zone_mask_projection = et.SubElement(brf_products_properties,
                                                                 'ExpertModeZone_maskProjection')
                self._check_and_set(expert_mode_zone_mask_projection, 'mask_projection',
                                    self._str_none(params['products']['brf'].get('mask_projection')))

        sensor_image_simulation = et.SubElement(phase, 'SensorImageSimulation')
        self._check_and_set(sensor_image_simulation, 'importMultipleSensors',
                            self._str_none(params['sensor'].get('importMultipleSensors')))

        if params.get('importMultipleSensors'):
            pinhole = et.SubElement(sensor_image_simulation, 'Pinhole')
            self._check_and_set(pinhole, 'cameraRotation', self._str_none(params['sensor'].get('cameraRotation')))
            self._check_and_set(pinhole, 'defCameraOrientation',
                                self._str_none(params['sensor'].get('defCameraOrientation')))
            self._check_and_set(pinhole, 'setImageSize', self._str_none(params['sensor'].get('setImageSize')))

            sensor = et.SubElement(pinhole, 'Sensor')
            self._check_and_set(sensor, 'sensorPosX', self._str_none(params['sensor'].get('sensorPosX')))
            self._check_and_set(sensor, 'sensorPosY', self._str_none(params['sensor'].get('sensorPosY')))
            self._check_and_set(sensor, 'sensorPosZ', self._str_none(params['sensor'].get('sensorPosZ')))

        if params.get('importMultipleSensors') or params.get('importPushbroomSensorFiles'):
            pushbroom = et.SubElement(sensor_image_simulation, 'Pushbroom')
            self._check_and_set(pushbroom, 'importThetaPhi', self._str_none(params['sensor'].get('importThetaPhi')))

            import_ = et.SubElement(pushbroom, 'Importation')
            self._check_and_set(import_, 'sensorAltitude', self._str_none(params['sensor'].get('altitude')))
            self._check_and_set(import_, 'offsetX', self._str_none(params['sensor'].get('offsetX')))
            self._check_and_set(import_, 'offsetY', self._str_none(params['sensor'].get('offsetY')))
            self._check_and_set(import_, 'phiFile', params['sensor'].get('phiFile'))
            self._check_and_set(import_, 'resImage', self._str_none(params['sensor'].get('resImage')))
            self._check_and_set(import_, 'thetaFile', params['sensor'].get('thetaFile'))

        maket_module_products = et.SubElement(dart_product, 'maketModuleProducts')
        self._check_and_set(maket_module_products, 'MNEProducts',
                            self._str_none(params['products']['DEM'].get('MNEProducts')))
        self._check_and_set(maket_module_products, 'areaMaketProducts',
                            self._str_none(params['products']['DEM'].get('areaMaketProducts')))
        self._check_and_set(maket_module_products, 'coverRateProducts',
                            self._str_none(params['products']['DEM'].get('coverRateProducts')))
        self._check_and_set(maket_module_products, 'laiProducts',
                            self._str_none(params['products']['DEM'].get('laiProducts')))
        self._check_and_set(maket_module_products, 'objectGeneration',
                            self._str_none(params['products']['DEM'].get('objectGeneration')))


class Directions(Component):
    COMPONENT_NAME = 'Directions'
    COMPONENT_FILE_NAME = 'directions.xml'

    def _check_params(self, params):
        return True

    def _write575(self, params, *args, **kwargs):
        directions = et.SubElement(self.xml_root, self.COMPONENT_NAME)
        self._check_and_set(directions, 'exactDate', self._str_none(params.get('exactDate')))
        self._check_and_set(directions, 'ifCosWeighted', self._str_none(params.get('ifCosWeighted')))
        self._check_and_set(directions, 'numberOfPropagationDirections',
                            self._str_none(params.get('numberOfPropagationDirections')))

        sun_viewing_angles = et.SubElement(directions, 'SunViewingAngles')
        self._check_and_set(sun_viewing_angles, 'sunViewingAzimuthAngle',
                            self._str_none(params['sun'].get('sunViewingAzimuthAngle')))
        self._check_and_set(sun_viewing_angles, 'sunViewingZenithAngle',
                            self._str_none(params['sun'].get('sunViewingZenithAngle')))
        self._check_and_set(sun_viewing_angles, 'dayOfTheYear', self._str_none(params['sun'].get('dayOfTheYear')))

        hot_spot_properties = et.SubElement(directions, 'HotSpotProperties')
        self._check_and_set(hot_spot_properties, 'hotSpotParallelPlane',
                            params['hotspot'].get('hotSpotParallelPlane'))
        self._check_and_set(hot_spot_properties, 'hotSpotPerpendicularPlane',
                            params['hotspot'].get('hotSpotPerpendicularPlane'))
        self._check_and_set(hot_spot_properties, 'oversampleDownwardRegion',
                            self._str_none(params['hotspot'].get('oversampleDownwardRegion')))
        self._check_and_set(hot_spot_properties, 'oversampleUpwardRegion',
                            self._str_none(params['hotspot'].get('oversampleUpwardRegion')))

        hot_spot_downward_region = et.SubElement(hot_spot_properties, 'HotSpotDownwardRegion')
        self._check_and_set(hot_spot_downward_region, 'numberOfDirections',
                            self._str_none(params['hotspot'].get('numberOfDownwardDirections')))
        self._check_and_set(hot_spot_downward_region, 'omega', self._str_none(params['hotspot'].get('omegaDown')))

        hot_spot_upward_region = et.SubElement(hot_spot_properties, 'HotSpotUpwardRegion')
        self._check_and_set(hot_spot_upward_region, 'numberOfDirections',
                            self._str_none(params['hotspot'].get('numberOfUpwardDirections')))
        self._check_and_set(hot_spot_upward_region, 'omega', self._str_none(params['hotspot'].get('omegaUp')))

        penumbra_mode = et.SubElement(Directions, 'Penumbra')
        self._check_and_set(penumbra_mode, 'mode', self._str_none(params.get('penumbraMode')))

        expert_mode_zone = et.SubElement(Directions, 'ExpertModeZone')
        self._check_and_set(expert_mode_zone, 'numberOfAngularSector',
                            self._str_none(params['expert'].get('numberOfAngularSector')))
        self._check_and_set(expert_mode_zone, 'numberOfLayers',
                            self._str_none(params['expert'].get('numberOfLayers')))


class Plots(Component):
    COMPONENT_NAME = 'Plots'
    COMPONENT_FILE_NAME = 'plots.xml'

    def _check_params(self, params):
        return True

    def _write575(self, params, landcover, voxel_size, *args, **kwargs):
        plots = et.SubElement(self.xml_root, self.COMPONENT_NAME)
        self._check_and_set(plots, 'isVegetation', self._str_none(params['general'].get('isVegetation')))
        # self._check_and_set(Plots,'addExtraPlotsTextFile', self._str_none(params['general'].get('addExtraPlotsTextFile')))

        import_fichier_raster = et.SubElement(self.xml_root, 'ImportationFichierRaster')

        ground_types = params['general']['ground_types']
        # TODO: move this out, this really should be part of the definition
        landcover = + 1

        for row in range(landcover.shape[0]):
            for col in range(landcover.shape[1]):
                if col == landcover.shape[1] | landcover[row, col] != landcover[row, col + 1]:

                    plot_type = landcover[row, col]

                    plot = et.SubElement(plots, 'Plot')
                    self._check_and_set(plot, 'form', '0')
                    self._check_and_set(plot, 'isDisplayed', '1')
                    # self._check_and_set(Plot,'hidden','0')

                    polygon_2d = et.SubElement(plot, 'Polygon2D')

                    point_2d = et.SubElement(polygon_2d, 'Point2D')
                    self._check_and_set(point_2d, 'x', str(voxel_size[0] * row))
                    self._check_and_set(point_2d, 'y', str(voxel_size[1] * col))

                    point_2d = et.SubElement(polygon_2d, 'Point2D')
                    self._check_and_set(point_2d, 'x', str(voxel_size * (row + 1)))
                    self._check_and_set(point_2d, 'y', str(voxel_size * col))

                    point_2d = et.SubElement(polygon_2d, 'Point2D')
                    self._check_and_set(point_2d, 'x', str(voxel_size * (row + 1)))
                    self._check_and_set(point_2d, 'y', str(voxel_size * (col + 1)))

                    point_2d = et.SubElement(polygon_2d, 'Point2D')
                    self._check_and_set(point_2d, 'x', str(voxel_size[0] * row))
                    self._check_and_set(point_2d, 'y', str(voxel_size[1] * (col + 1)))

                    if plot_type in ground_types['vegetation'].ids:
                        vegetation_id = ground_types.ids.index(plot_type)
                        # TODO: shouldn't this be type 2 i.e. ground and vegetation
                        self._check_and_set(plot, 'type', '1')

                        plot_vegetation_properties = et.SubElement(plot, 'PlotVegetationProperties')
                        self._check_and_set(plot_vegetation_properties, 'densityDefinition',
                                            self._str_none(params['vegetation'].get('densityDefinition')))
                        self._check_and_set(plot_vegetation_properties, 'verticalFillMode',
                                            self._str_none(params['vegetation'].get('verticalFillMode')))

                        vegetation_geometry = et.SubElement(plot_vegetation_properties, 'VegetationGeometry')
                        self._check_and_set(vegetation_geometry, 'stDev',
                                            self._str_none(params['vegetation'].get('stdDev')[vegetation_id]))
                        self._check_and_set(vegetation_geometry, 'baseheight', '0')
                        self._check_and_set(vegetation_geometry, 'height',
                                            self._str_none(params['vegetation'].get('height')[vegetation_id]))

                        lai_vegetation = et.SubElement(plot_vegetation_properties, 'LAIVegetation')
                        self._check_and_set(lai_vegetation, 'LAI',
                                            self._str_none(params['vegetation'].get('lai')[vegetation_id]))

                        vegetation_optical_property_link = et.SubElement(plot_vegetation_properties,
                                                                         'VegetationOpticalPropertyLink')
                        self._check_and_set(vegetation_optical_property_link, 'ident',
                                            params['vegetation'].get('ident')[vegetation_id])
                        self._check_and_set(vegetation_optical_property_link, 'indexFctPhase', self._str_none(
                            params['vegetation'].get('indexFctPhase')[vegetation_id]))

                        ground_thermal_property_link = et.SubElement(plot_vegetation_properties,
                                                                     'GroundThermalPropertyLink')
                        self._check_and_set(ground_thermal_property_link, 'idTemperature',
                                            self._str_none(params['temperature'].get('idTemperature')))
                        self._check_and_set(ground_thermal_property_link, 'indexTemperature',
                                            self._str_none(params['temperature'].get('indexTemperature')))

                    elif plot_type in ground_types['ground'].ids:
                        litter_id = ground_types.ids.index(plot_type)
                        self._check_and_set(plot, 'type', '0')

                        GroundOpticalPropertyLink = et.SubElement(plot, 'GroundOpticalPropertyLink')
                        self._check_and_set(vegetation_optical_property_link, 'ident',
                                            params['ground'].get('ident')[litter_id])
                        self._check_and_set(vegetation_optical_property_link, 'indexFctPhase',
                                            self._str_none(params['ground'].get('indexFctPhase')[litter_id]))
                        self._check_and_set(GroundOpticalPropertyLink, 'type',
                                            self._str_none(params['ground'].get('type')[litter_id]))

                        ground_thermal_property_link = et.SubElement(plot, 'GroundThermalPropertyLink')
                        self._check_and_set(ground_thermal_property_link, 'idTemperature',
                                            self._str_none(params['temperature'].get('idTemperature')))
                        self._check_and_set(ground_thermal_property_link, 'indexTemperature',
                                            self._str_none(params['temperature'].get('indexTemperature')))

                    # TODO: there should also be a treatment for type 2 and 3, i.e. ground and vegetation and fluids
                    else:
                        pass


class CoeffDiff(Component):
    COMPONENT_NAME = 'Coeff_diff'
    COMPONENT_FILE_NAME = 'coeff_diff.xml'

    def _check_params(self, params):
        return True

    def _write575(self, params, *args, **kwargs):
        coeff_diff = et.SubElement(self.xml_root, self.COMPONENT_NAME)
        # self._check_and_set(coeff_diff, 'fluorescenceProducts', self._str_none(params['fluorescence'].get('fluorescenceProducts')))
        # self._check_and_set(coeff_diff, 'fluorescenceFile', self._str_none(params['fluorescence'].get('fluorescenceFile'))) ## TODO: there should be a field to assign a file here!

        # *** 2d lambertian spectra ***
        lambertian_multi_functions = et.SubElement(coeff_diff, 'LambertianMultiFunctions')

        for model_name, ident in zip(params['lop2d'].get('ModelName'), params['lop2d'].get('ident')):
            lambertian_multi = et.SubElement(lambertian_multi_functions, 'LambertianMulti')
            self._check_and_set(lambertian_multi, 'ModelName', model_name)
            self._check_and_set(lambertian_multi, 'databaseName', params['lop2d'].get('databaseName'))
            self._check_and_set(lambertian_multi, 'ident', ident)
            self._check_and_set(lambertian_multi, 'roStDev', self._str_none(params['lop2d'].get('roStDev')))
            # self._check_and_set(lambertian_multi, 'specularDatabaseName', params['lop2d'].get('databaseName'))
            # self._check_and_set(lambertian_multi, 'specularModelName', params['lop2d'].get('ModelName'){m})
            # self._check_and_set(lambertian_multi, 'specularRoStDev', self._str_none(params['lop2d'].get('roStDev')))
            self._check_and_set(lambertian_multi, 'useMultiplicativeFactorForLUT',
                                self._str_none(params['lop2d'].get('useMultiplicativeFactorForLUT')))
            self._check_and_set(lambertian_multi, 'useSpecular', self._str_none(params['lop2d'].get('useSpecular')))

            prospect_external_module = et.SubElement(lambertian_multi, 'ProspectExternalModule')
            # self._check_and_set(prospect_external_module, 'isFluorescent', self._str_none(params['lop2d'].get('isFluorescent')[m]))
            self._check_and_set(prospect_external_module, 'useProspectExternalModule',
                                self._str_none(params['lop2d'].get('useProspectExternalModule')))

            lambertian_node_multiplicative_factor_for_lut = et.SubElement(lambertian_multi,
                                                                          'lambertianNodeMultiplicativeFactorForLUT')
            self._check_and_set(lambertian_node_multiplicative_factor_for_lut, 'diffuseTransmittanceFactor',
                                self._str_none(params['lop2d'].get('diffuseTransmittanceFactor')))
            self._check_and_set(lambertian_node_multiplicative_factor_for_lut, 'directTransmittanceFactor',
                                self._str_none(params['lop2d'].get('directTransmittanceFactor')))
            self._check_and_set(lambertian_node_multiplicative_factor_for_lut, 'reflectanceFactor',
                                self._str_none(params['lop2d'].get('reflectanceFactor')))
            self._check_and_set(lambertian_node_multiplicative_factor_for_lut, 'specularIntensityFactor',
                                self._str_none(params['lop2d'].get('specularIntensityFactor')))
            self._check_and_set(lambertian_node_multiplicative_factor_for_lut, 'useSameFactorForAllBands',
                                self._str_none(params['lop2d'].get('useSameFactorForAllBands')))
            # self._check_and_set(lambertianNodeMultiplicativeFactorForLUT, 'useSameOpticalFactorMatrixForAllBands', self._str_none(params['lop2d'].get('useSameOpticalFactorMatrixForAllBands')))

            understory_multiplicative_factor_for_lut = et.SubElement(lambertian_node_multiplicative_factor_for_lut,
                                                                     'lambertianMultiplicativeFactorForLUT')
            self._check_and_set(understory_multiplicative_factor_for_lut, 'diff   useTransmittanceFactor',
                                self._str_none(params['lop2d'].get('diffuseTransmittanceFactor')))
            self._check_and_set(understory_multiplicative_factor_for_lut, 'directTransmittanceFactor',
                                self._str_none(params['lop2d'].get('directTransmittanceFactor')))
            self._check_and_set(understory_multiplicative_factor_for_lut, 'reflectanceFactor',
                                self._str_none(params['lop2d'].get('reflectanceFactor')))
            self._check_and_set(understory_multiplicative_factor_for_lut, 'specularIntensityFactor',
                                self._str_none(params['lop2d'].get('specularIntensityFactor')))
            # self._check_and_set(understoryMultiplicativeFactorForLUT, 'useOpticalFactorMatrix', self._str_none(params['lop2d'].get('useSameOpticalFactorMatrixForAllBands')))

        # LambertianSpecularMultiFunctions = et.SubElement(coeff_diff, 'LambertianSpecularMultiFunctions')

        HapkeSpecularMultiFunctions = et.SubElement(coeff_diff, 'HapkeSpecularMultiFunctions')
        RPVMultiFunctions = et.SubElement(coeff_diff, 'RPVMultiFunctions')

        # *** 3d turbid spectra ***
        UnderstoryMultiFunctions = et.SubElement(coeff_diff, 'UnderstoryMultiFunctions')
        self._check_and_set(UnderstoryMultiFunctions, 'outputLADFile',
                            self._str_none(params['understroy_multi_functions'].get('outputLADFile')))
        self._check_and_set(UnderstoryMultiFunctions, 'integrationStepOnPhi',
                            self._str_none(params['understroy_multi_functions'].get('integrationStepOnPhi')))
        self._check_and_set(UnderstoryMultiFunctions, 'integrationStepOnTheta',
                            self._str_none(params['understroy_multi_functions'].get('integrationStepOnTheta')))
        self._check_and_set(UnderstoryMultiFunctions, 'specularEffects',
                            self._str_none(params['understroy_multi_functions'].get('specularEffects')))
        # self._check_and_set(UnderstoryMultiFunctions, 'useBunnick','0')

        for model_name, ident, lad in zip(params['lop2d'].get('ModelName'), params['lop2d'].get('ident'),
                                          params['lop2d'].get('lad')):
            understory_multi = et.SubElement(UnderstoryMultiFunctions, 'UnderstoryMulti')
            self._check_and_set(understory_multi, 'ModelName', model_name)
            ## TODO: Discuss this with Fabian, this seems to be weird!!!
            # In coeff_diff.xml the understory_veg table is referred to the
            # Vegetation.db, but Vegetation.db does not have a table
            # understory_veg. This is situated in Lambertian.db. However, this was
            # already the case in the older version, where no error was thrown due
            # to this. Why can this be? Was understory_veg never used in the older
            # version, which therefore never caused this error? Or is there
            # somehting else fishy with the scripts?
            #     if strcmp(params['lop3d'].get('ModelName'){n},'understory_veg')
            #         self._check_and_set(UnderstoryMulti, 'databaseName', params['lop2d'].get('databaseName'))
            #     else
            #         self._check_and_set(UnderstoryMulti, 'databaseName', params['lop3d'].get('databaseName'))
            #     end
            #     self._check_and_set(UnderstoryMulti, 'databaseName', params['lop3d'].get('databaseName'))
            self._check_and_set(understory_multi, 'databaseName', params['lop3d'].get('databaseName'))
            self._check_and_set(understory_multi, 'deltaT', self._str_none(params['lop3d'].get('deltaT')))
            self._check_and_set(understory_multi, 'dimFoliar', self._str_none(params['lop3d'].get('dimFoliar')))
            self._check_and_set(understory_multi, 'ident', ident)
            self._check_and_set(understory_multi, 'lad', lad)
            self._check_and_set(understory_multi, 'meanT', self._str_none(params['lop3d'].get('meanT')))
            # self._check_and_set(UnderstoryMulti, 'useSpecular', self._str_none(coeff_diff.useSpecular))
            # if coeff_diff.useSpecular == 1
            #    self._check_and_set(UnderstoryMulti, 'specularDatabaseName', params['lop3d'].get('specularDatabaseName'))
            #    self._check_and_set(UnderstoryMulti, 'specularModelName', params['lop3d'].get('specularModelName'))
            # end
            self._check_and_set(understory_multi, 'useMultiplicativeFactorForLUT',
                                self._str_none(params['lop3d'].get('useMultiplicativeFactorForLUT')))
            # self._check_and_set(UnderstoryMulti, 'useOpticalFactorMatrix', self._str_none(params['lop3d'].get('useOpticalFactorMatrix')))

            DirectionalClumpingIndexProperties = et.SubElement(understory_multi, 'DirectionalClumpingIndexProperties')
            self._check_and_set(DirectionalClumpingIndexProperties, 'clumpinga',
                                self._str_none(params['lop3d'].get('clumpinga')))
            self._check_and_set(DirectionalClumpingIndexProperties, 'clumpingb',
                                self._str_none(params['lop3d'].get('clumpingb')))
            self._check_and_set(DirectionalClumpingIndexProperties, 'omegaMax',
                                self._str_none(params['lop3d'].get('omegaMax')))
            self._check_and_set(DirectionalClumpingIndexProperties, 'omegaMin',
                                self._str_none(params['lop3d'].get('omegaMin')))

            prospect_external_module = et.SubElement(understory_multi, 'ProspectExternalModule')
            self._check_and_set(prospect_external_module, 'useProspectExternalModule',
                                self._str_none(params['lop3d'].get('useProspectExternalModule')))
            # self._check_and_set(ProspectExternalModule, 'isFluorescent', self._str_none(params['lop3d'].get('isFluorescent')[n]))

            understoryNodeMultiplicativeFactorForLUT = et.SubElement(understory_multi,
                                                                     'understoryNodeMultiplicativeFactorForLUT')
            self._check_and_set(understoryNodeMultiplicativeFactorForLUT, 'LeafTransmittanceFactor',
                                self._str_none(params['lop3d'].get('LeafTransmittanceFactor')))
            self._check_and_set(understoryNodeMultiplicativeFactorForLUT, 'abaxialReflectanceFactor',
                                self._str_none(params['lop3d'].get('abaxialReflectanceFactor')))
            self._check_and_set(understoryNodeMultiplicativeFactorForLUT, 'adaxialReflectanceFactor',
                                self._str_none(params['lop3d'].get('adaxialReflectanceFactor')))
            self._check_and_set(understoryNodeMultiplicativeFactorForLUT, 'useSameFactorForAllBands',
                                self._str_none(params['lop3d'].get('useSameFactorForAllBands')))
            # self._check_and_set(understoryNodeMultiplicativeFactorForLUT, 'useSameOpticalFactorMatrixForAllBands', self._str_none(params['lop3d'].get('useSameOpticalFactorMatrixForAllBands'))) #TODO: Implement further input datafile which is needed, when this parameter is set to true!

            understory_multiplicative_factor_for_lut = et.SubElement(understoryNodeMultiplicativeFactorForLUT,
                                                                     'understoryMultiplicativeFactorForLUT')
            self._check_and_set(understory_multiplicative_factor_for_lut, 'LeafTransmittanceFactor',
                                self._str_none(params['lop3d'].get('LeafTransmittanceFactor')))
            self._check_and_set(understory_multiplicative_factor_for_lut, 'abaxialReflectanceFactor',
                                self._str_none(params['lop3d'].get('abaxialReflectanceFactor')))
            self._check_and_set(understory_multiplicative_factor_for_lut, 'adaxialReflectanceFactor',
                                self._str_none(params['lop3d'].get('adaxialReflectanceFactor')))
            # self._check_and_set(understoryMultiplicativeFactorForLUT, 'useOpticalFactorMatrix', self._str_none(params['lop3d'].get('useOpticalFactorMatrix'))) # TODO:implement changes to xml file, when this is set to true!

        air_multi_functions = et.SubElement(coeff_diff, 'AirMultiFunctions')
        temperatures = et.SubElement(coeff_diff, 'Temperatures')

        thermal_function = et.SubElement(temperatures, 'ThermalFunction')
        self._check_and_set(thermal_function, 'deltaT', self._str_none(params['lop3d'].get('deltaT')))
        self._check_and_set(thermal_function, 'idTemperature', params['lop3d'].get('idTemperature'))
        self._check_and_set(thermal_function, 'meanT', self._str_none(params['lop3d'].get('meanT')))
        self._check_and_set(thermal_function, 'override3DMatrix',
                            self._str_none(params['lop3d'].get('override3DMatrix')))
        # self._check_and_set(ThermalFunction, 'useOpticalFactorMatrix', self._str_none(params['lop3d'].get('useOpticalFactorMatrix')))


class Object3d(Component):
    COMPONENT_NAME = 'object_3d'
    COMPONENT_FILE_NAME = 'object_3d.xml'

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
        self._check_and_set(obj, 'hasGroups', self._str_none(params['hasGroups']))
        self._check_and_set(obj, 'hidden', self._str_none(params['hidden']))
        self._check_and_set(obj, 'isDisplayed', self._str_none(params['isDisplayed']))
        self._check_and_set(obj, 'name', params['name'])
        self._check_and_set(obj, 'num', self._str_none(params['num']))
        self._check_and_set(obj, 'objectColor', params['objectColor'])
        self._check_and_set(obj, 'objectDEMMode', self._str_none(params['objectDEMMode']))

        geom_prop = et.SubElement(obj, 'GeometricProperties')

        pos_prop = et.SubElement(geom_prop, 'PositionProperties')
        self._check_and_set(pos_prop, 'xpos', self._str_none(params.get('location')[0]))
        self._check_and_set(pos_prop, 'ypos', self._str_none(params.get('location')[1]))
        self._check_and_set(pos_prop, 'zpos', self._str_none(params.get('location')[2]))

        dimension = et.SubElement(geom_prop, 'Dimension3D')
        self._check_and_set(dimension, 'xdim', self._str_none(params.get('dim')[0]))
        self._check_and_set(dimension, 'ydim', self._str_none(params.get('location')[1]))
        self._check_and_set(dimension, 'zdim', self._str_none(params.get('location')[2]))

        scale_prop = et.SubElement(geom_prop, 'ScaleProperties')
        self._check_and_set(scale_prop, 'xScaleDeviation', self._str_none(params['scale'].get('xScaleDeviation')))
        self._check_and_set(scale_prop, 'xscale', self._str_none(params['scale'].get('xscale')))
        self._check_and_set(scale_prop, 'yScaleDeviation', self._str_none(params['scale'].get('yScaleDeviation')))
        self._check_and_set(scale_prop, 'yscale', self._str_none(params['scale'].get('yscale')))
        self._check_and_set(scale_prop, 'zScaleDeviation', self._str_none(params['scale'].get('zScaleDeviation')))
        self._check_and_set(scale_prop, 'zscale', self._str_none(params['scale'].get('zscale')))

        rot_prop = et.SubElement(geom_prop, 'RotationProperties')
        self._check_and_set(rot_prop, 'xRotDeviation', self._str_none(params['rotation'].get('xRotDeviation')))
        self._check_and_set(rot_prop, 'xrot', self._str_none(params['rotation'].get('xrot')))
        self._check_and_set(rot_prop, 'yRotDeviation', self._str_none(params['rotation'].get('yRotDeviation')))
        self._check_and_set(rot_prop, 'yrot', self._str_none(params['rotation'].get('yrot')))
        self._check_and_set(rot_prop, 'zRotDeviation', self._str_none(params['rotation'].get('zRotDeviation')))
        self._check_and_set(rot_prop, 'zrot', self._str_none(params['rotation'].get('zrot')))

        object_optical_prop = et.SubElement(obj, 'ObjectOpticalProperties')
        self._check_and_set(object_optical_prop, 'doubleFace',
                            self._str_none(params['optical_property'].get('doubleFace')))
        self._check_and_set(object_optical_prop, 'isLAICalc',
                            self._str_none(params['optical_property'].get('isLAICalc')))
        self._check_and_set(object_optical_prop, 'isSingleGlobalLai',
                            self._str_none(params['optical_property'].get('isSingleGlobalLai')))
        self._check_and_set(object_optical_prop, 'sameOPObject',
                            self._str_none(params['optical_property'].get('sameOPObject')))

        object_property_link = et.SubElement(object_optical_prop, 'OpticalPropertyLink')
        self._check_and_set(object_property_link, 'ident', params['optical_property'].get('model_name'))
        self._check_and_set(object_property_link, 'indexFctPhase',
                            self._str_none(params['optical_property'].get('indexFctPhase')))
        self._check_and_set(object_property_link, 'type', self._str_none(params['optical_property'].get('type')))

        thermal_property_link = et.SubElement(object_optical_prop, 'ThermalPropertyLink')
        self._check_and_set(thermal_property_link, 'idTemperature', params['temperature'].get('id_temperature'))
        self._check_and_set(thermal_property_link, 'indexTemperature',
                            self._str_none(params['temperature'].get('indexTemp)')))
        object_optical_prop.appendChild(thermal_property_link)

        object_type_prop = et.SubElement(obj, 'ObjectTypeProperties')
        self._check_and_set(object_type_prop, 'sameOTObject',
                            self._str_none(params['typeprop'].get('sameOTObject')))

        object_type_link = et.SubElement(object_type_prop, 'ObjectTypeLink')
        self._check_and_set(object_type_link, 'identOType', params['typeprop'].get('identOType'))
        self._check_and_set(object_type_link, 'indexOT', params['typeprop'].get('indexOT'))

        object_fields = et.SubElement(object_3d, 'ObjectFields')


class Maket(Component):
    COMPONENT_NAME = 'Maket'
    COMPONENT_FILE_NAME = 'maket.xml'

    def _check_params(self, params):
        return True

    def _write570(self, params):
        maket = et.SubElement(self.xml_root, self.COMPONENT_NAME)
        self._check_and_set(maket, 'dartZone', self._str_none(params['dartZone']))
        self._check_and_set(maket, 'exactlyPeriodicScene', self._str_none(params['exactlyPeriodicScene']))
        self._check_and_set(maket, 'useRandomGenerationSeed', self._str_none(params['useRandomGenerationSeed']))

        # scene
        Scene = et.SubElement(self.xml_root, 'Scene')
        cell_dimensions = et.SubElement(self.xml_root, 'cell_dimensions')
        self._check_and_set(cell_dimensions, 'x', self._str_none(params['voxelDim'][0]))
        self._check_and_set(cell_dimensions, 'z', self._str_none(params['voxelDim'][2]))
        Scene.appendChild(cell_dimensions)

        scene_dimensions = et.SubElement(self.xml_root, 'SceneDimensions')
        self._check_and_set(scene_dimensions, 'x', self._str_none(params['sceneDim'][1]))
        self._check_and_set(scene_dimensions, 'y', self._str_none(params['sceneDim'][0]))

        # ground
        soil = et.SubElement(self.xml_root, 'Soil')

        # optical property
        OpticalPropertyLink = et.SubElement(soil, 'OpticalPropertyLink')
        self._check_and_set(OpticalPropertyLink, 'ident', self._str_none(params['optical_property'].get('ident')))
        self._check_and_set(OpticalPropertyLink, 'indexFctPhase',
                            self._str_none(params['optical_property'].get('indexFctPhase')))
        self._check_and_set(OpticalPropertyLink, 'type', self._str_none(params['optical_property'].get('type')))

        # thermal function
        thermal_property_link = et.SubElement(soil, 'ThermalPropertyLink')
        self._check_and_set(thermal_property_link, 'idTemperature',
                            self._str_none(params['thermal_property'].get('idTemperature')))
        self._check_and_set(thermal_property_link, 'indexTemperature',
                            self._str_none(params['thermal_property'].get('indexTemperature')))

        # topography
        if not self._str_none(params['topography'].get('fileName')):
            topography = et.SubElement(soil, 'Topography')
            self._check_and_set(topography, 'presenceOfTopography', '0')

            DEM_properties = et.SubElement(soil, 'DEM_properties')
            self._check_and_set(DEM_properties, 'createTopography', '0')

        else:
            topography = et.SubElement(self.xml_root, 'Topography')
            self._check_and_set(topography, 'presenceOfTopography',
                                self._str_none(params['topography'].get('presenceOfTopography')))

            topography_properties = et.SubElement(topography, 'TopographyProperties')
            self._check_and_set(topography_properties, 'fileName', self._str_none(params['outputFileName']))
            topography.appendChild(topography_properties)

            DEM_properties = et.SubElement(soil, 'DEM_properties')
            self._check_and_set(DEM_properties, 'createTopography',
                                self._str_none(params['topography'].get('createTopography')))

            DEM_generator = et.SubElement(DEM_properties, 'DEMGenerator')
            self._check_and_set(DEM_generator, 'caseDEM', self._str_none(params['DEM'].get('caseDEM')))
            self._check_and_set(DEM_generator, 'outputFileName', params['DEM'].get('outputFileName'))

            # TODO: check this, I dont't know what is done here
            DEM_5 = et.SubElement(DEM_generator, 'DEM_5')
            self._check_and_set(DEM_5, 'dataEncoding', self._str_none(params['DEM5']['dataEncoding']))
            self._check_and_set(DEM_5, 'dataFormat', self._str_none(params['DEM5']['dataFormat']))
            self._check_and_set(DEM_5, 'fileName', params['DEM5']['fileName'])

        # geo-location
        location = et.SubElement(self.xml_root, 'LatLon')
        self._check_and_set(location, 'altitude', self._str_none(params.get('location')[2]))
        self._check_and_set(location, 'latitude', self._str_none(params.get('location')[0]))
        self._check_and_set(location, 'longitude', self._str_none(params.get('longitude')[1]))


class Atmosphere(Component):
    """
    Class holding pointers and doing computation to atmosphere related data.
    """
    COMPONENT_NAME = 'Atmosphere'
    COMPONENT_FILE_NAME = 'atmosphere.xml'

    def _check_params(self, params):
        # TODO: implement proper checks on type and consistency in params, should depend on self.version
        return True

    def _write560(self, params, *args, **kwargs):
        atmos = et.SubElement(self.xml_root, self.COMPONENT_NAME)
        self._check_and_set(atmos, 'isRadiativeTransfertInBottomAtmosphereDefined',
                            self._str_none(params['general'].get('isRadiativeTransfertInBottomAtmosphereDefined')))

        is_atmosphere = et.SubElement(atmos, 'IsAtmosphere')
        self._check_and_set(is_atmosphere, 'typeOfAtmosphere', str(params['general'].get('typeOfAtmosphere')))

        atmosphere_iterations = et.SubElement(is_atmosphere, 'AtmosphereIterations')

        atmosphere_transfer_functions = et.SubElement(atmosphere_iterations, 'AtmosphereTransfertFunctions')
        self._check_and_set(atmosphere_transfer_functions, 'inputOutputTransfertFunctions',
                            self._str_none(params['general'].get('inputOutputTransfertFunctions')))

        computed_transfer_functions = et.SubElement(atmosphere_transfer_functions, 'ComputedTransferFunctions')
        self._check_and_set(computed_transfer_functions, 'writeTransferFunctions',
                            self._str_none(params['general'].get('writeTransferFunctions')))

        atmosphere_products = et.SubElement(atmosphere_iterations, 'AtmosphereProducts')
        self._check_and_set(atmosphere_products, 'atmosphereBRF_TOA',
                            self._str_none(params['products'].get('atmosphereBRF_TOA')))
        self._check_and_set(atmosphere_products, 'atmosphereRadiance_BOA_apresCouplage',
                            self._str_none(params['products'].get('atmosphereRadiance_BOA_after_coupling')))
        self._check_and_set(atmosphere_products, 'atmosphereRadiance_BOA_avantCouplage',
                            self._str_none(params['products'].get('atmosphereRadiance_BOA_before_coupling')))
        self._check_and_set(atmosphere_products, 'ordreUnAtmos', self._str_none(params['products'].get('order_1')))

        atmosphere_components = et.SubElement(atmosphere_iterations, 'AtmosphereComponents')
        self._check_and_set(atmosphere_components, 'downwardingFluxes',
                            self._str_none(params['components'].get('downwardingFluxes')))
        self._check_and_set(atmosphere_components, 'upwardingFluxes',
                            self._str_none(params['components'].get('upwardingFluxes')))

        atmosphere_expert_mode_zone = et.SubElement(atmosphere_iterations, 'AtmosphereExpertModeZone')
        self._check_and_set(atmosphere_expert_mode_zone, 'extrapol_atmos',
                            self._str_none(params['expert'].get('extrapol_atmos')))
        self._check_and_set(atmosphere_expert_mode_zone, 'seuilEclairementAtmos',
                            self._str_none(params['expert'].get('seuilEclairementAtmos')))
        self._check_and_set(atmosphere_expert_mode_zone, 'seuilFTAtmos',
                            self._str_none(params['expert'].get('seuilFTAtmos')))

        atmosphere_geometry = et.SubElement(is_atmosphere, 'AtmosphereGeometry')
        self._check_and_set(atmosphere_geometry, 'discretisationAtmos',
                            self._str_none(params['geometry'].get('discretisationAtmos')))
        self._check_and_set(atmosphere_geometry, 'heightOfSensor',
                            self._str_none(params['geometry'].get('heightOfSensor')))
        self._check_and_set(atmosphere_geometry, 'minimumNumberOfDivisions',
                            self._str_none(params['geometry'].get('minimumNumberOfDivisions')))

        mid_atmosphere = et.SubElement(atmosphere_geometry, 'MidAtmosphere')

        cell_dimensions = et.SubElement(mid_atmosphere, 'cell_dimensions')
        self._check_and_set(cell_dimensions, 'xAI', self._str_none(params['dimensions'].get('xAI')))
        self._check_and_set(cell_dimensions, 'yAI', self._str_none(params['dimensions'].get('yAI')))
        self._check_and_set(cell_dimensions, 'zAI', self._str_none(params['dimensions'].get('zAI')))

        height = et.SubElement(mid_atmosphere, 'Height')
        self._check_and_set(height, 'hCFAI', self._str_none(params['dimensions'].get('hCFAI')))

        upper_atmosphere = et.SubElement(atmosphere_geometry, 'UpperAtmosphere')
        self._check_and_set(upper_atmosphere, 'hCFHA', self._str_none(params['dimensions'].get('hCFHA')))

        layer = et.SubElement(upper_atmosphere, 'Layer')
        self._check_and_set(layer, 'zHA', self._str_none(params['dimensions'].get('zHA')))

        if params['general']['typeOfAtmosphere'] == 1:
            atmospheric_optical_property_model = et.SubElement(is_atmosphere, 'AtmosphericOpticalPropertyModel')
            self._check_and_set(atmospheric_optical_property_model, 'correctionBandModel',
                                self._str_none(params['optical_property_db'].get('correctionBandModel')))
            self._check_and_set(atmospheric_optical_property_model, 'databaseName',
                                self._str_none(params['optical_property_db'].get('dataBaseName')))
            self._check_and_set(atmospheric_optical_property_model, 'temperatureModelName',
                                self._str_none(params['optical_property_db'].get('temperatureModelName')))

            self._check_and_set(atmospheric_optical_property_model, 'hgParametersModelName', self._str_none(
                params['optical_property_db']['aerosol'].get('hgParametersModelName')))
            self._check_and_set(atmospheric_optical_property_model, 'aerosolCumulativeModelName', self._str_none(
                params['optical_property_db']['aerosol'].get('cumulativeModelName')))
            self._check_and_set(atmospheric_optical_property_model, 'aerosolOptDepthFactor',
                                self._str_none(params['optical_property_db']['aerosol'].get('optDepthFactor')))
            self._check_and_set(atmospheric_optical_property_model, 'aerosolsGroup',
                                self._str_none(params['optical_property_db']['aerosol'].get('group')))
            self._check_and_set(atmospheric_optical_property_model, 'aerosolsModelName',
                                self._str_none(params['optical_property_db']['aerosol'].get('modelName')))

            self._check_and_set(atmospheric_optical_property_model, 'gasCumulativeModelName',
                                self._str_none(params['optical_property_db']['gas'].get('cumulativeModelName')))
            self._check_and_set(atmospheric_optical_property_model, 'gasGroup',
                                self._str_none(params['optical_property_db']['gas'].get('group')))
            self._check_and_set(atmospheric_optical_property_model, 'gasModelName',
                                self._str_none(params['optical_property_db']['gas'].get('modelName')))
            self._check_and_set(atmospheric_optical_property_model, 'gasParametersModelName', self._str_none(
                params['optical_property_db']['gas'].get('gasParametersModelName')))

            self._check_and_set(atmospheric_optical_property_model, 'precipitableWaterAmountCkeckbox',
                                self._str_none(params['optical_property_db'].get('water').get('include')))
            water_amount = et.SubElement(atmospheric_optical_property_model, 'WaterAmount')
            self._check_and_set(water_amount, 'precipitableWaterAmount', self._str_none(
                params['optical_property_db'].get('water').get('precipitableWaterAmount')))

        elif params['general']['typeOfAtmosphere'] == 0:
            atmospheric_optical_property = et.SubElement(is_atmosphere, 'AtmosphericOpticalProperty')
            self._check_and_set(atmospheric_optical_property, 'courbureTerre',
                                self._str_none(params['optical_property'].get('correct_earth_curvature')))
            self._check_and_set(atmospheric_optical_property, 'pointMilieu',
                                self._str_none(params['optical_property'].get('correct_mid_point')))
            self._check_and_set(atmospheric_optical_property, 'a_HG',
                                self._str_none(params['optical_property'].get('heyney_greenstein_a')))
            self._check_and_set(atmospheric_optical_property, 'g1',
                                self._str_none(params['optical_property'].get('heyney_greenstein_g1')))
            self._check_and_set(atmospheric_optical_property, 'g2',
                                self._str_none(params['optical_property'].get('heyney_greenstein_g2')))

            self._check_and_set(atmospheric_optical_property, 'aerosolOpticalDepth',
                                self._str_none(params['optical_property']['aerosol'].get('optical_depth')))
            self._check_and_set(atmospheric_optical_property, 'aerosolScaleFactor',
                                self._str_none(params['optical_property']['aerosol'].get('scale_factor')))
            self._check_and_set(atmospheric_optical_property, 'aerosolAlbedo',
                                self._str_none(params['optical_property']['aerosol'].get('albedo')))

            self._check_and_set(atmospheric_optical_property, 'gasOpticalDepth',
                                self._str_none(params['optical_property']['gas'].get('optical_depth')))
            self._check_and_set(atmospheric_optical_property, 'gasScaleFactor',
                                self._str_none(params['optical_property']['gas'].get('scale_factor')))
            self._check_and_set(atmospheric_optical_property, 'transmittanceOfGases',
                                self._str_none(params['optical_property']['gas'].get('transmittance')))

            temperature_model = et.SubElement(is_atmosphere, 'TemperatureFile')
            self._check_and_set(temperature_model, 'atmosphereTemperatureFileName',
                                self._str_none(params['optical_property'].get('temperature_file_name')))
        else:
            raise TypeError('Variable typeOfAtmosphere must be 0 or 1')

        is_radiative_transfert_in_bottom_atmosphere = et.SubElement(is_atmosphere,
                                                                    'isRadiativeTransfertInBottomAtmosphere')
        self._check_and_set(is_radiative_transfert_in_bottom_atmosphere, 'BA_altitude',
                            self._str_none(params['dimensions'].get('BA_altitude')))

    def _write575(self, params, *args, **kwargs):
        atmos = et.SubElement(self.xml_root, self.COMPONENT_NAME)
        self._check_and_set(atmos, 'isRadiativeTransfertInBottomAtmosphereDefined',
                            self._str_none(params['general'].get('isRadiativeTransfertInBottomAtmosphereDefined')))

        is_atmosphere = et.SubElement(atmos, 'IsAtmosphere')
        self._check_and_set(is_atmosphere, 'typeOfAtmosphere', str(params['general'].get('typeOfAtmosphere')))

        atmosphere_iterations = et.SubElement(is_atmosphere, 'AtmosphereIterations')

        atmosphere_transfer_functions = et.SubElement(atmosphere_iterations, 'AtmosphereTransfertFunctions')
        self._check_and_set(atmosphere_transfer_functions, 'inputOutputTransfertFunctions',
                            self._str_none(params['general'].get('inputOutputTransfertFunctions')))

        computed_transfer_functions = et.SubElement(atmosphere_transfer_functions, 'ComputedTransferFunctions')
        self._check_and_set(computed_transfer_functions, 'writeTransferFunctions',
                            self._str_none(params['general'].get('writeTransferFunctions')))

        atmosphere_products = et.SubElement(atmosphere_iterations, 'AtmosphereProducts')
        self._check_and_set(atmosphere_products, 'atmosphereBRF_TOA',
                            self._str_none(params['products'].get('atmosphereBRF_TOA')))
        self._check_and_set(atmosphere_products, 'atmosphereRadiance_BOA_apresCouplage',
                            self._str_none(params['products'].get('atmosphereRadiance_BOA_after_coupling')))
        self._check_and_set(atmosphere_products, 'atmosphereRadiance_BOA_avantCouplage',
                            self._str_none(params['products'].get('atmosphereRadiance_BOA_before_coupling')))
        self._check_and_set(atmosphere_products, 'ordreUnAtmos', self._str_none(params['products'].get('order_1')))
        self._check_and_set(atmosphere_products, 'atmosphereReport',
                            self._str_none(params['products'].get('atmosphereReport')))

        atmosphere_components = et.SubElement(atmosphere_iterations, 'AtmosphereComponents')
        self._check_and_set(atmosphere_components, 'downwardingFluxes',
                            self._str_none(params['components'].get('downwardingFluxes')))
        self._check_and_set(atmosphere_components, 'upwardingFluxes',
                            self._str_none(params['components'].get('upwardingFluxes')))

        atmosphere_expert_mode_zone = et.SubElement(atmosphere_iterations, 'AtmosphereExpertModeZone')
        self._check_and_set(atmosphere_expert_mode_zone, 'extrapol_atmos',
                            self._str_none(params['expert'].get('extrapol_atmos')))
        self._check_and_set(atmosphere_expert_mode_zone, 'number_iterationMax',
                            self._str_none(params['expert'].get('number_iterationMax')))
        self._check_and_set(atmosphere_expert_mode_zone, 'threshold_Atmos_scattering',
                            self._str_none(params['expert'].get('threshold_Atmos_scattering')))

        atmosphere_geometry = et.SubElement(is_atmosphere, 'AtmosphereGeometry')
        self._check_and_set(atmosphere_geometry, 'discretisationAtmos',
                            self._str_none(params['geometry'].get('discretisationAtmos')))
        self._check_and_set(atmosphere_geometry, 'heightOfSensor',
                            self._str_none(params['geometry'].get('heightOfSensor')))
        self._check_and_set(atmosphere_geometry, 'minimumNumberOfDivisions',
                            self._str_none(params['geometry'].get('minimumNumberOfDivisions')))

        mid_atmosphere = et.SubElement(atmosphere_geometry, 'MidAtmosphere')

        cell_dimensions = et.SubElement(mid_atmosphere, 'cell_dimensions')
        self._check_and_set(cell_dimensions, 'xAI', self._str_none(params['dimensions'].get('xAI')))
        self._check_and_set(cell_dimensions, 'yAI', self._str_none(params['dimensions'].get('yAI')))
        self._check_and_set(cell_dimensions, 'zAI', self._str_none(params['dimensions'].get('zAI')))

        height = et.SubElement(mid_atmosphere, 'Height')
        self._check_and_set(height, 'hCFAI', self._str_none(params['dimensions'].get('hCFAI')))

        upper_atmosphere = et.SubElement(atmosphere_geometry, 'UpperAtmosphere')
        self._check_and_set(upper_atmosphere, 'hCFHA', self._str_none(params['dimensions'].get('hCFHA')))

        layer = et.SubElement(upper_atmosphere, 'Layer')
        self._check_and_set(layer, 'zHA', self._str_none(params['dimensions'].get('zHA')))

        aerosol = et.SubElement(atmos, 'Aerosol')
        aerosol_properties = et.SubElement(aerosol, 'AerosolProperties')
        self._check_and_set(aerosol_properties, 'hgParametersModelName',
                            self._str_none(params['optical_property_db']['aerosol'].get('hgParametersModelName')))
        self._check_and_set(aerosol_properties, 'aerosolCumulativeModelName',
                            self._str_none(params['optical_property_db']['aerosol'].get('cumulativeModelName')))
        self._check_and_set(aerosol_properties, 'aerosolOptDepthFactor',
                            self._str_none(params['optical_property_db']['aerosol'].get('optDepthFactor')))
        self._check_and_set(aerosol_properties, 'aerosolsGroup',
                            self._str_none(params['optical_property_db']['aerosol'].get('group')))
        self._check_and_set(aerosol_properties, 'aerosolsModelName',
                            self._str_none(params['optical_property_db']['aerosol'].get('modelName')))
        self._check_and_set(aerosol_properties, 'databaseName',
                            self._str_none(params['optical_property_db']['aerosol'].get('dataBaseName')))

        if params['general']['typeOfAtmosphere'] == 1:
            atmospheric_optical_property_model = et.SubElement(is_atmosphere, 'AtmosphericOpticalPropertyModel')
            self._check_and_set(atmospheric_optical_property_model, 'correctionBandModel',
                                self._str_none(params['optical_property_db'].get('correctionBandModel')))
            self._check_and_set(atmospheric_optical_property_model, 'temperatureModelName',
                                self._str_none(params['optical_property_db'].get('temperatureModelName')))

            self._check_and_set(atmospheric_optical_property_model, 'gasCumulativeModelName',
                                self._str_none(params['optical_property_db']['gas'].get('cumulativeModelName')))
            self._check_and_set(atmospheric_optical_property_model, 'gasGroup',
                                self._str_none(params['optical_property_db']['gas'].get('group')))
            self._check_and_set(atmospheric_optical_property_model, 'gasModelName',
                                self._str_none(params['optical_property_db']['gas'].get('modelName')))
            self._check_and_set(atmospheric_optical_property_model, 'gasParametersModelName', self._str_none(
                params['optical_property_db']['gas'].get('gasParametersModelName')))

            self._check_and_set(atmospheric_optical_property_model, 'precipitableWaterAmountCkeckbox',
                                self._str_none(params['water'].get('include')))
            water_amount = et.SubElement(atmospheric_optical_property_model, 'WaterAmount')
            self._check_and_set(water_amount, 'defWaterAmount',
                                self._str_none(params['water'].get('defWaterAmount')))

            if params['water'].get('defWaterAmount') == '0':
                water_spec = et.SubElement(water_amount, 'M_factor')
                water_spec.set('mulFactorH2O', params['water']['mulFactorH2O'])

        elif params['general']['typeOfAtmosphere'] == 0:
            atmospheric_optical_property = et.SubElement(is_atmosphere, 'AtmosphericOpticalProperty')
            self._check_and_set(atmospheric_optical_property, 'courbureTerre',
                                self._str_none(params['optical_property'].get('correct_earth_curvature')))
            self._check_and_set(atmospheric_optical_property, 'pointMilieu',
                                self._str_none(params['optical_property'].get('correct_mid_point')))
            self._check_and_set(atmospheric_optical_property, 'a_HG',
                                self._str_none(params['optical_property'].get('heyney_greenstein_a')))
            self._check_and_set(atmospheric_optical_property, 'g1',
                                self._str_none(params['optical_property'].get('heyney_greenstein_g1')))
            self._check_and_set(atmospheric_optical_property, 'g2',
                                self._str_none(params['optical_property'].get('heyney_greenstein_g2')))

            self._check_and_set(atmospheric_optical_property, 'aerosolOpticalDepth',
                                self._str_none(params['optical_property']['aerosol'].get('optical_depth')))
            self._check_and_set(atmospheric_optical_property, 'aerosolScaleFactor',
                                self._str_none(params['optical_property']['aerosol'].get('scale_factor')))
            self._check_and_set(atmospheric_optical_property, 'aerosolAlbedo',
                                self._str_none(params['optical_property']['aerosol'].get('albedo')))

            self._check_and_set(atmospheric_optical_property, 'gasOpticalDepth',
                                self._str_none(params['optical_property']['gas'].get('optical_depth')))
            self._check_and_set(atmospheric_optical_property, 'gasScaleFactor',
                                self._str_none(params['optical_property']['gas'].get('scale_factor')))
            self._check_and_set(atmospheric_optical_property, 'transmittanceOfGases',
                                self._str_none(params['optical_property']['gas'].get('transmittance')))

            temperature_model = et.SubElement(is_atmosphere, 'TemperatureFile')
            self._check_and_set(temperature_model, 'atmosphereTemperatureFileName',
                                self._str_none(params['optical_property'].get('temperature_file_name')))
        else:
            raise TypeError('Variable typeOfAtmosphere must be 0 or 1')

        is_radiative_transfert_in_bottom_atmosphere = et.SubElement(is_atmosphere,
                                                                    'isRadiativeTransfertInBottomAtmosphere')
        self._check_and_set(is_radiative_transfert_in_bottom_atmosphere, 'BA_altitude',
                            self._str_none(params['dimensions'].get('BA_altitude')))
