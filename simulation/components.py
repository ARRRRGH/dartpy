import xml.etree.ElementTree as ET
import os
import logging
from pkg_resources import parse_version
import utils.general as general

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
        self.xml_root = ET.Element(ROOT_TAG)
        self._write(params)

    def from_file(self, path, version, force=False):
        """
        Create a component from its xml file
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

    def to_file(self):
        tree = ET.ElementTree(self.xml_root)
        inp_path = os.path.normpath(os.path.join(self.simulation_dir, 'input'))
        xml_path = os.path.normpath(os.path.join(inp_path, self.COMPONENT_FILE_NAME))

        if not os.path.exists(inp_path):
            print('path', inp_path)
            os.makedirs(inp_path)
        tree.write(xml_path)

    def _read(self, path):
        tree = ET.parse(path)
        self.xml_root = tree.getroot()

    def _write(self, parameters):
        raise NotImplemented


class Atmosphere(Component):
    """
    Class holding pointers and doing computation to atmosphere related data.
    """
    COMPONENT_NAME = 'Atmosphere'
    COMPONENT_FILE_NAME = 'atmosphere.xml'

    def _check_params(self, params):
        # TODO: implement proper checks on type and consistency in params, should depend on self.version
        return True
        
    def _write(self, params):
        assert self._check_params(params)

        # this is to ensure undefined elements are projected to None and do not raise an Error a priori
        if parse_version(self.version) >= parse_version('5.6.0'):
            self._write560(params)

    def _set_if_possible(self, element, key, val, check=None):
        if check is not None:
            assert check(key, val)
            
        if val is not None:
            element.set(key, val)

    def _str_none(self, val):
        if val is not None:
            return str(val)
        return None

    def _write560(self, params):
        print(params)
        atmos = ET.SubElement(self.xml_root, self.COMPONENT_NAME)
        self._set_if_possible(atmos, 'isRadiativeTransfertInBottomAtmosphereDefined',
                              self._str_none(params['general'].get('isRadiativeTransfertInBottomAtmosphereDefined')))

        is_atmosphere = ET.SubElement(atmos, 'IsAtmosphere')
        self._set_if_possible(is_atmosphere, 'typeOfAtmosphere', self._str_none(params['general'].get('typeOfAtmosphere')))

        atmosphere_iterations = ET.SubElement(is_atmosphere, 'AtmosphereIterations')

        atmosphere_transfer_functions = ET.SubElement(atmosphere_iterations, 'AtmosphereTransfertFunctions')
        self._set_if_possible(atmosphere_transfer_functions, 'inputOutputTransfertFunctions', self._str_none(params['general'].get('inputOutputTransfertFunctions')))

        computed_transfer_functions = ET.SubElement(atmosphere_transfer_functions, 'ComputedTransferFunctions')
        self._set_if_possible(computed_transfer_functions, 'writeTransferFunctions', self._str_none(params['general'].get('writeTransferFunctions')))

        atmosphere_products = ET.SubElement(atmosphere_iterations, 'AtmosphereProducts')
        self._set_if_possible(atmosphere_products, 'atmosphereBRF_TOA', self._str_none(params['general'].get('atmosphereBRF_TOA')))
        self._set_if_possible(atmosphere_products, 'atmosphereRadiance_BOA_apresCouplage', self._str_none(params['general'].get('atmosphereRadiance_BOA_apresCouplage')))
        self._set_if_possible(atmosphere_products, 'atmosphereRadiance_BOA_avantCouplage', self._str_none(params['general'].get('atmosphereRadiance_BOA_avantCouplage')))
        self._set_if_possible(atmosphere_products, 'ordreUnAtmos', self._str_none(params['general'].get('ordreUnAtmos')))

        atmosphere_components = ET.SubElement(atmosphere_iterations, 'AtmosphereComponents')
        self._set_if_possible(atmosphere_components, 'downwardingFluxes', self._str_none(params['general'].get('downwardingFluxes')))
        self._set_if_possible(atmosphere_components, 'upwardingFluxes', self._str_none(params['general'].get('upwardingFluxes')))

        atmosphere_expert_mode_zone = ET.SubElement(atmosphere_iterations, 'AtmosphereExpertModeZone')
        self._set_if_possible(atmosphere_expert_mode_zone, 'extrapol_atmos', self._str_none(params['general'].get('extrapol_atmos')))
        self._set_if_possible(atmosphere_expert_mode_zone, 'seuilEclairementAtmos', self._str_none(params['general'].get('seuilEclairementAtmos')))
        self._set_if_possible(atmosphere_expert_mode_zone, 'seuilFTAtmos', self._str_none(params['general'].get('seuilFTAtmos')))

        atmosphere_geometry = ET.SubElement(is_atmosphere, 'AtmosphereGeometry')
        self._set_if_possible(atmosphere_geometry, 'discretisationAtmos', self._str_none(params['geometry'].get('discretisationAtmos')))
        self._set_if_possible(atmosphere_geometry, 'heightOfSensor', self._str_none(params['geometry'].get('heightOfSensor')))
        self._set_if_possible(atmosphere_geometry, 'minimumNumberOfDivisions', self._str_none(params['geometry'].get('minimumNumberOfDivisions')))

        mid_atmosphere = ET.SubElement(atmosphere_geometry, 'MidAtmosphere')

        cell_dimensions = ET.SubElement(mid_atmosphere, 'CellDimensions')
        self._set_if_possible(cell_dimensions, 'xAI', self._str_none(params['dimensions'].get('xAI')))
        self._set_if_possible(cell_dimensions, 'yAI', self._str_none(params['dimensions'].get('yAI')))
        self._set_if_possible(cell_dimensions, 'zAI', self._str_none(params['dimensions'].get('zAI')))

        height = ET.SubElement(mid_atmosphere, 'Height')
        self._set_if_possible(height, 'hCFAI', self._str_none(params['dimensions'].get('hCFAI')))

        upper_atmosphere = ET.SubElement(atmosphere_geometry, 'UpperAtmosphere')
        self._set_if_possible(upper_atmosphere, 'hCFHA', self._str_none(params['dimensions'].get('hCFHA')))

        layer = ET.SubElement(upper_atmosphere, 'Layer')
        self._set_if_possible(layer, 'zHA', self._str_none(params['dimensions'].get('zHA')))

        atmospheric_optical_property_model = ET.SubElement(is_atmosphere, 'AtmosphericOpticalPropertyModel')
        self._set_if_possible(atmospheric_optical_property_model, 'aerosolCumulativeModelName', params['optical_property']['aerosol'].get('cumulativeModelName'))
        self._set_if_possible(atmospheric_optical_property_model, 'aerosolOptDepthFactor', self._str_none(params['optical_property']['aerosol'].get('optDepthFactor')))
        self._set_if_possible(atmospheric_optical_property_model, 'aerosolsGroup', self._str_none(params['optical_property']['aerosol'].get('group')))
        self._set_if_possible(atmospheric_optical_property_model, 'aerosolsModelName', self._str_none(params['optical_property']['aerosol'].get('modelName')))

        self._set_if_possible(atmospheric_optical_property_model, 'correctionBandModel', self._str_none(params['general'].get('correctionBandModel')))
        self._set_if_possible(atmospheric_optical_property_model, 'databaseName', self._str_none(params['general'].get('databaseName')))
        self._set_if_possible(atmospheric_optical_property_model, 'hgParametersModelName', params['optical_property'].get('hgParametersModelName'))
        self._set_if_possible(atmospheric_optical_property_model, 'temperatureModelName', params['optical_property'].get('temperatureModelName'))

        self._set_if_possible(atmospheric_optical_property_model, 'gasCumulativeModelName', self._str_none(params['optical_property']['gas'].get('cumulativeModelName')))
        self._set_if_possible(atmospheric_optical_property_model, 'gasGroup', self._str_none(params['optical_property'].get('gasGroup')))
        self._set_if_possible(atmospheric_optical_property_model, 'gasModelName', self._str_none(params['optical_property']['gas'].get('modelName')))
        self._set_if_possible(atmospheric_optical_property_model, 'gasParametersModelName', params['optical_property']['gas'].get('parametersModelName'))

        self._set_if_possible(atmospheric_optical_property_model, 'precipitableWaterAmountCkeckbox', self._str_none(params['optical_property'].get('water').get('precipitableWaterAmountCkeckbox')))

        water_amount = ET.SubElement(atmospheric_optical_property_model, 'WaterAmount')
        self._set_if_possible(water_amount, 'precipitableWaterAmount', self._str_none(params['optical_property'].get('water').get('precipitableWaterAmount')))

        is_radiative_transfert_in_bottom_atmosphere = ET.SubElement(is_atmosphere, 'isRadiativeTransfertInBottomAtmosphere')
        self._set_if_possible(is_radiative_transfert_in_bottom_atmosphere, 'BA_altitude', self._str_none(params['dimensions'].get('BA_altitude')))


