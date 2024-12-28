''' Calibration method: Adaptive with persistence'''

import logging
import json
import os
from eventmanager import Evt
from calibration import CalibrationMethod
from calibration import AdaptiveCalibrationMethod

logger = logging.getLogger(__name__)

PERSISTENT_ADAPTIVE_CALIBRATION_DATA_FILENAME = "adaptive-calibration-persistent-data.json"

class AdaptiveWithPersistanceCalibrationMethod(CalibrationMethod):
    def __init__(self):
        super().__init__("Adaptive with persistence")
        self._adaptive_calibration = AdaptiveCalibrationMethod()

    def store_calibration_values(self, rhapi):
        pilotRaces = rhapi.rhdata.get_savedPilotRaces()

        # Determine required mode.
        # Note: "a+" mode is not suitable for us, because even with the presense
        # of f.seek(0) - it will write at the end of file.
        if os.path.exists(PERSISTENT_ADAPTIVE_CALIBRATION_DATA_FILENAME):
            mode = "r+"
        else:
            mode = "w+" # Creates empty file if it does not exist

        with open(PERSISTENT_ADAPTIVE_CALIBRATION_DATA_FILENAME, mode) as f:
            try:
                calib_data = json.loads(f.read())
            except Exception as e:
                logger.warning(f"Failed to load adaptive calibration values: {e}. Starting empty.")
                calib_data = {}

            for pilotRace in pilotRaces:
                pilot_id = pilotRace.pilot_id
                node_id = pilotRace.node_index

                if pilot_id not in calib_data:
                    calib_data[pilot_id] = {}

                if node_id not in calib_data[pilot_id]:
                    calib_data[node_id] = {}

                calib_data[pilot_id][node_id] = {"enter_at_level": pilotRace.enter_at, "exit_at_level": pilotRace.exit_at}

            f.seek(0)
            f.write(json.dumps(calib_data))

    def retrieve_stored_calibration_values(self, _, node, pilot_id):
        try:
            with open(PERSISTENT_ADAPTIVE_CALIBRATION_DATA_FILENAME, "r") as f:
                calib_data = json.loads(f.read())
                node_id = node.index
                if pilot_id not in calib_data:
                    return None
                if node_id not in calib_data[pilot_id]:
                    return None

                return calib_data[pilot_id][node_id]
        except Exception as e:
            logger.warning(f"Encountered error during loading of persistent adaptive calibration data: {e}. Ignoring")
            return None

    def calibrate(self, rhapi, node, seat_index):
        # Attempt to use built-in adaptive calibration method
        calib = self._adaptive_calibration.calibrate(rhapi, node, seat_index)

        # If built-in calibration method has not returned values
        # Attempt to lookup pilot and node stored
        if calib is None:
            pilot = rhapi.rhdata.get_pilot_from_heatNode(rhapi.race.current_heat, seat_index)
            calib = self.retrieve_stored_calibration_values(rhapi, node, pilot)

        # Persist per-pilot-per-node calibration values before returning
        self.store_calibration_values(rhapi)

        return calib

def register_handlers(args):
    logger.info("Adaptive Calibration with Persitence plugin registering")
    args['register_fn'](AdaptiveWithPersistanceCalibrationMethod())

def initialize(rhapi):
    logger.info("Adaptive Calibration with Persitence plugin starting")
    rhapi.events.on(Evt.CALIBRATION_INITIALIZE, register_handlers)

