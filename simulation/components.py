import xml.etree.ElementTree as ET
import os
import logging


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
        self.xml_root = ET.Element()
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
        valid = self.xml_root.tag == self.ROOT_TAG and \
                self.xml_root.get('version') == version and \
                self.COMPONENT_NAME in [el.tag for el in list(self.xml_root)]
        if not (valid or force):
            logging.exception(
                'Cannot load ' + path + 'since file does not seem to be valid. If you are convinced it is, ' +
                'use force=True')

    def to_file(self):
        tree = ET.ElementTree(self.xml_root)
        tree.write(os.path.join(self.simulation_dir, 'input', self.COMPONENT_FILE_NAME))

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

        # TODO: rewrite geq condition
        if self.version > '5.6.0':
            self._write560(params)

    def _set_if_possible(self, element, key, val, check=None):
        if check is not None:
            assert check(key, val)
            
        if val is not None:
            element.set(key, val)

    def _write560(self, params):
        atmos = ET.SubElement(self.xml_root, self.COMPONENT_NAME)
        self._set_if_possible(atmos, 'isRadiativeTransfertInBottomAtmosphereDefined',
                              str(params.general.get('isRadiativeTransfertInBottomAtmosphereDefined')))

        is_atmosphere = ET.SubElement(atmos, 'IsAtmosphere')
        self._set_if_possible(is_atmosphere, 'typeOfAtmosphere', str(params.general.get('typeOfAtmosphere')))

        atmosphere_iterations = ET.SubElement(is_atmosphere, 'AtmosphereIterations')

        atmosphere_transfer_functions = ET.SubElement(atmosphere_iterations, 'AtmosphereTransfertFunctions')
        self._set_if_possible(atmosphere_transfer_functions, 'inputOutputTransfertFunctions', str(params.general.get('inputOutputTransfertFunctions')))

        computed_transfer_functions = ET.SubElement(atmosphere_transfer_functions, 'ComputedTransferFunctions')
        self._set_if_possible(computed_transfer_functions, 'writeTransferFunctions', str(params.general.get('writeTransferFunctions')))

        atmosphere_products = ET.SubElement(atmosphere_iterations, 'AtmosphereProducts')
        self._set_if_possible(atmosphere_products, 'atmosphereBRF_TOA', str(params.general.get('atmosphereBRF_TOA')))
        self._set_if_possible(atmosphere_products, 'atmosphereRadiance_BOA_apresCouplage', str(params.general.get('atmosphereRadiance_BOA_apresCouplage')))
        self._set_if_possible(atmosphere_products, 'atmosphereRadiance_BOA_avantCouplage', str(params.general.get('atmosphereRadiance_BOA_avantCouplage')))
        self._set_if_possible(atmosphere_products, 'ordreUnAtmos', str(params.general.get('ordreUnAtmos')))

        atmosphere_components = ET.SubElement(atmosphere_iterations, 'AtmosphereComponents')
        self._set_if_possible(atmosphere_components, 'downwardingFluxes', str(params.general.get('downwardingFluxes')))
        self._set_if_possible(atmosphere_components, 'upwardingFluxes', str(params.general.get('upwardingFluxes')))

        atmosphere_expert_mode_zone = ET.SubElement(atmosphere_iterations, 'AtmosphereExpertModeZone')
        self._set_if_possible(atmosphere_expert_mode_zone, 'extrapol_atmos', str(params.general.get('extrapol_atmos')))
        self._set_if_possible(atmosphere_expert_mode_zone, 'seuilEclairementAtmos', str(params.general.get('seuilEclairementAtmos'), '#f'))
        self._set_if_possible(atmosphere_expert_mode_zone, 'seuilFTAtmos', str(params.general.get('seuilFTAtmos'), '#f'))

        atmosphere_geometry = ET.SubElement(is_atmosphere, 'AtmosphereGeometry')
        self._set_if_possible(atmosphere_geometry, 'discretisationAtmos', str(params.geometry.get('discretisationAtmos')))
        self._set_if_possible(atmosphere_geometry, 'heightOfSensor', str(params.geometry.get('heightOfSensor')))
        self._set_if_possible(atmosphere_geometry, 'minimumNumberOfDivisions', str(params.geometry.get('minimumNumberOfDivisions')))

        mid_atmosphere = ET.SubElement(atmosphere_geometry, 'MidAtmosphere')
        atmosphere_geometry.appendChild(mid_atmosphere)

        cell_dimensions = ET.SubElement(mid_atmosphere, 'CellDimensions')
        self._set_if_possible(cell_dimensions, 'xAI', str(params.dimensions.get('xAI')))
        self._set_if_possible(cell_dimensions, 'yAI', str(params.dimensions.get('yAI')))
        self._set_if_possible(cell_dimensions, 'zAI', str(params.dimensions.get('zAI')))

        height = ET.SubElement(mid_atmosphere, 'Height')
        self._set_if_possible(height, 'hCFAI', str(params.dimensions.get('hCFAI')))

        upper_atmosphere = ET.SubElement(atmosphere_geometry, 'UpperAtmosphere')
        self._set_if_possible(upper_atmosphere, 'hCFHA', str(params.dimensions.get('hCFHA')))

        layer = ET.SubElement(upper_atmosphere, 'Layer')
        self._set_if_possible(layer, 'zHA', str(params.dimensions.get('zHA')))

        atmospheric_optical_property_model = ET.SubElement(is_atmosphere, 'AtmosphericOpticalPropertyModel')
        self._set_if_possible(atmospheric_optical_property_model, 'aerosolCumulativeModelName', params.optical_property.get('aerosol').get('cumulativeModelName'))
        self._set_if_possible(atmospheric_optical_property_model, 'aerosolOptDepthFactor', str(params.optical_property.get('aerosol').get('optDepthFactor'), '#.1f'))
        self._set_if_possible(atmospheric_optical_property_model, 'aerosolsGroup', str(params.optical_property.get('aerosol').get('group')))
        self._set_if_possible(atmospheric_optical_property_model, 'aerosolsModelName', str(params.optical_property.get('aerosol').get('modelName')))

        self._set_if_possible(atmospheric_optical_property_model, 'correctionBandModel', str(params.general.get('correctionBandModel')))
        self._set_if_possible(atmospheric_optical_property_model, 'databaseName', str(params.databaseName))
        self._set_if_possible(atmospheric_optical_property_model, 'hgParametersModelName', params.optical_property.get('hgParametersModelName'))
        self._set_if_possible(atmospheric_optical_property_model, 'temperatureModelName', params.optical_property.get('temperatureModelName'))

        self._set_if_possible(atmospheric_optical_property_model, 'gasCumulativeModelName', str(params.optical_property.get('gas').get('cumulativeModelName')))
        self._set_if_possible(atmospheric_optical_property_model, 'gasGroup', str(params.gasGroup))
        self._set_if_possible(atmospheric_optical_property_model, 'gasModelName', str(params.optical_property.get('gas').get('modelName')))
        self._set_if_possible(atmospheric_optical_property_model, 'gasParametersModelName', params.optical_property.get('gas').get('parametersModelName'))

        self._set_if_possible(atmospheric_optical_property_model, 'precipitableWaterAmountCkeckbox', str(params.optical_property.get('water').get('precipitableWaterAmountCkeckbox')))

        water_amount = ET.SubElement(atmospheric_optical_property_model, 'WaterAmount')
        self._set_if_possible(water_amount, 'precipitableWaterAmount', str(params.optical_property.get('water').get('precipitableWaterAmount')))

        is_radiative_transfert_in_bottom_atmosphere = ET.SubElement(is_atmosphere, 'isRadiativeTransfertInBottomAtmosphere')
        self._set_if_possible(is_radiative_transfert_in_bottom_atmosphere, 'BA_altitude', str(params.dimensions.get('BA_altitude')))


