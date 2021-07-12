from datetime import datetime
# import matlab.engine
import os, io, shutil
import numpy as np

from vaxos.supply_expiry import SupplyExpiry
from vaxos.params import location_types, vaccine_types, Params
from vaxos.params import Params
# from custom_dist import custom_dist
from vaxos.custom_dist import CustomDist

_MODELER = 'RSOME' # 'RSOME' | 'MATLAB'

if _MODELER == 'MATLAB':
    from vaxos.solver_matlab.invitation_waves_solver_matlab import InvitationWavesSolver_Matlab as InvitationWavesSolver
elif _MODELER == 'RSOME':
    from vaxos.solver_rsome.invitation_waves_solver_rsome import InvitationWavesSolver_RSome as InvitationWavesSolver


class OptimalInvitationGenSolver():

    def __init__(self, params, request_time=datetime.now()):
        self.params = params

    def solve(self):

        n = InvitationWavesSolver(self.params).solve()
        planning_duration = self.params['planning_duration'] if self.params.get('planning_duration') is not None else self.params['duration']

        # invitation = [0] * self.params['duration']
        invitation = [0] * planning_duration
        idx = 0
        for i in range(len(n)):
            # print(n._data[i])
            invitation[idx] = n[i]

            idx += self.params['invitation_frequency']

        print('invitation', invitation)
        self.params['invitation'] = invitation

        return self.params
