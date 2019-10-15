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

    def _write560(self, params):
        atmos = ET.SubElement(self.xml_root, self.COMPONENT_NAME)
        atmos.set('isRadiativeTransfertInBottomAtmosphereDefined', str(params.general.isRadiativeTransfertInBottomAtmosphereDefined))

        is_atmosphere = ET.SubElement(atmos, 'IsAtmosphere')
        is_atmosphere.set('typeOfAtmosphere', str(params.general.typeOfAtmosphere))

        atmosphere_iterations = ET.SubElement(is_atmosphere, 'AtmosphereIterations')

        atmosphere_transfer_functions = ET.SubElement(atmosphere_iterations, 'AtmosphereTransfertFunctions')
        atmosphere_transfer_functions.set('inputOutputTransfertFunctions', str(params.general.inputOutputTransfertFunctions))

        computed_transfer_functions = ET.SubElement(atmosphere_transfer_functions, 'ComputedTransferFunctions')
        computed_transfer_functions.set('writeTransferFunctions', str(params.general.writeTransferFunctions))

        atmosphere_products = ET.SubElement(atmosphere_iterations, 'AtmosphereProducts')
        atmosphere_products.set('atmosphereBRF_TOA', str(params.general.atmosphereBRF_TOA))
        atmosphere_products.set('atmosphereRadiance_BOA_apresCouplage', str(params.general.atmosphereRadiance_BOA_apresCouplage))
        atmosphere_products.set('atmosphereRadiance_BOA_avantCouplage', str(params.general.atmosphereRadiance_BOA_avantCouplage))
        atmosphere_products.set('ordreUnAtmos', str(params.general.ordreUnAtmos))

        atmosphere_components = ET.SubElement(atmosphere_iterations, 'AtmosphereComponents')
        atmosphere_components.set('downwardingFluxes', str(params.general.downwardingFluxes))
        atmosphere_components.set('upwardingFluxes', str(params.general.upwardingFluxes))

        atmosphere_expert_mode_zone = ET.SubElement(atmosphere_iterations, 'AtmosphereExpertModeZone')
        atmosphere_expert_mode_zone.set('extrapol_atmos', str(params.general.extrapol_atmos))
        atmosphere_expert_mode_zone.set('seuilEclairementAtmos', str(params.general.seuilEclairementAtmos, '#f'))
        atmosphere_expert_mode_zone.set('seuilFTAtmos', str(params.general.seuilFTAtmos, '#f'))

        atmosphere_geometry = ET.SubElement(is_atmosphere, 'AtmosphereGeometry')
        atmosphere_geometry.set('discretisationAtmos', str(params.geometry.discretisationAtmos))
        atmosphere_geometry.set('heightOfSensor', str(params.geometry.heightOfSensor))
        atmosphere_geometry.set('minimumNumberOfDivisions', str(params.geometry.minimumNumberOfDivisions))

        mid_atmosphere = ET.SubElement(atmosphere_geometry, 'MidAtmosphere')
        atmosphere_geometry.appendChild(mid_atmosphere)

        cell_dimensions = ET.SubElement(mid_atmosphere, 'CellDimensions')
        cell_dimensions.set('xAI', str(params.dimensions.xAI))
        cell_dimensions.set('yAI', str(params.dimensions.yAI))
        cell_dimensions.set('zAI', str(params.dimensions.zAI))

        height = ET.SubElement(mid_atmosphere, 'Height')
        height.set('hCFAI', str(params.dimensions.hCFAI))

        upper_atmosphere = ET.SubElement(atmosphere_geometry, 'UpperAtmosphere')
        upper_atmosphere.set('hCFHA', str(params.dimensions.hCFHA))

        layer = ET.SubElement(upper_atmosphere, 'Layer')
        layer.set('zHA', str(params.dimensions.zHA))

        atmospheric_optical_property_model = ET.SubElement(is_atmosphere, 'AtmosphericOpticalPropertyModel')
        atmospheric_optical_property_model.set('aerosolCumulativeModelName', params.optical_property.aerosol.cumulativeModelName)
        atmospheric_optical_property_model.set('aerosolOptDepthFactor', str(params.optical_property.aerosol.optDepthFactor, '#.1f'))
        atmospheric_optical_property_model.set('aerosolsGroup', str(params.optical_property.aerosol.group))
        #AtmosphericOpticalPropertyModel.set('co2MixRate', str(params.co2MixRate))
        atmospheric_optical_property_model.set('aerosolsModelName', str(params.optical_property.aerosol.modelName))
        atmospheric_optical_property_model.set('correctionBandModel', str(params.general.correctionBandModel))
        atmospheric_optical_property_model.set('databaseName', str(params.databaseName))
        atmospheric_optical_property_model.set('gasCumulativeModelName', str(params.optical_property.gas.cumulativeModelName))
        atmospheric_optical_property_model.set('gasGroup', str(params.gasGroup))
        atmospheric_optical_property_model.set('gasModelName', str(params.optical_property.gas.modelName))
        #AtmosphericOpticalPropertyModel.set('ignoreGasForExtrapolation', str(params.ignoreGasForExtrapolation))
        #AtmosphericOpticalPropertyModel.set('redefTemperature', str(params.redefTemperature))
        #AtmosphericOpticalPropertyModel.set('scaleOtherGases', str(params.scaleOtherGases))
        atmospheric_optical_property_model.set('gasParametersModelName', params.optical_property.gas.parametersModelName)
        atmospheric_optical_property_model.set('hgParametersModelName', params.optical_property.hgParametersModelName)
        atmospheric_optical_property_model.set('precipitableWaterAmountCkeckbox', str(params.optical_property.water.precipitableWaterAmountCkeckbox))
        atmospheric_optical_property_model.set('temperatureModelName', params.optical_property.temperatureModelName)


        water_amount = ET.SubElement(atmospheric_optical_property_model, 'WaterAmount')
        water_amount.set('precipitableWaterAmount', str(params.optical_property.water.precipitableWaterAmount, '#g'))

        #         WaterAmount.set('defWaterAmount', '1')
        #             Amount_g_per_cm2 = self.xml_root.insert(0, 'Amount_g_per_cm2')
        #             Amount_g_per_cm2.set('g_per_cm2', str(params.precipitableWaterAmount, '#g'))
        #         WaterAmount.appendChild(Amount_g_per_cm2)

        is_radiative_transfert_in_bottom_atmosphere = ET.SubElement(is_atmosphere,
                                                                    'isRadiativeTransfertInBottomAtmosphere')
        is_radiative_transfert_in_bottom_atmosphere.set('BA_altitude', str(params.dimensions.BA_altitude))


