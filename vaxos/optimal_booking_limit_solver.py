# import matlab.engine
import os, io, shutil
import numpy as np
from datetime import datetime

from vaxos.supply_expiry import SupplyExpiry
from vaxos.params import location_types, vaccine_types
from vaxos.params import Params
# from custom_dist import custom_dist
from vaxos.custom_dist import CustomDist

_MODELER = 'RSOME' # 'RSOME' | 'MATLAB'

if _MODELER == 'MATLAB':
    from vaxos.solver_matlab.booking_limits_solver_matlab import BookingLimitsSolver_Matlab as BookingLimitsSolver
elif _MODELER == 'RSOME':
    from vaxos.solver_rsome.booking_limits_solver_rsome import BookingLimitsSolver_RSome as BookingLimitsSolver


_DEBUG = False

class OptimalBookingLimitSolver():

    def __init__(self, params, request_time=datetime.now()):
        self.params = params

    def solve(self, vaccine):

        first_dose_booking_limit, second_dose_booking_limit = BookingLimitsSolver(self.params, vaccine).solve()
        planning_duration = self.params['planning_duration'] if self.params.get('planning_duration') is not None else self.params['duration']

        # params_epoch_length = self.params['duration'] + self.params['vaccine_settings'][vaccine]['second_shot_gap'] + self.params['vaccine_settings'][vaccine]['max_second_shot_delay']
        params_epoch_length = planning_duration + self.params['vaccine_settings'][vaccine]['second_shot_gap'] + self.params['vaccine_settings'][vaccine]['max_second_shot_delay']

        self.params['vaccine_settings'][vaccine]['first_dose_booking_limit'] = first_dose_booking_limit + ([0] * (params_epoch_length - len(first_dose_booking_limit)))
        self.params['vaccine_settings'][vaccine]['second_dose_booking_limit'] = second_dose_booking_limit + ([0] * (params_epoch_length - len(second_dose_booking_limit)))

        target = self.generate_target_from_booking_limits(first_dose_booking_limit, freq=self.params['invitation_frequency'])

        self.params['vaccine_settings'][vaccine]['target'] = target

        if _DEBUG:
            print(vaccine, target)


        return self.params

    def generate_target_from_booking_limits(self, first_dose_booking_limit, freq = 14):
        ''' '''
        # planning_duration = self.params['planning_duration'] if self.params.get('planning_duration') is not None else self.params['duration']

        target = [0]* self.params['duration']
        for i in range(0, self.params['duration'], freq):
        # target = [0]* planning_duration
        # for i in range(0, planning_duration, freq):
            target[i] = int(sum(first_dose_booking_limit[i:i+freq]))

        return target

