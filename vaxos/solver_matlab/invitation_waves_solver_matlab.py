from datetime import datetime
# import matlab.engine
import os, io, shutil
from supply_expiry import SupplyExpiry
from params import location_types, vaccine_types, Params
import numpy as np

from vaxos.params import Params
# from custom_dist import custom_dist
from vaxos.custom_dist import CustomDist

def npArray2Matlab(x):
    import matlab.engine
    return matlab.double(x.tolist())

def list2Matlab(x):
    import matlab.engine
    return matlab.double(x)


class InvitationWavesSolver_Matlab():

    def __init__(self, params, request_time=datetime.now()):
        self.params = params
        self.request_time = request_time
        self.dir_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
        self.log_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__))) + '/archive/log'
        os.makedirs(self.log_path, exist_ok=True)

        self.planning_duration = self.params['planning_duration'] if self.params.get('planning_duration') is not None else self.params['duration']

        import matlab.engine
        self.eng = matlab.engine.start_matlab()
        self.eng.addpath(f"{self.dir_path}/solver/invitation_solver", nargout=0)

        # self.eng.addpath(f"{dir_path}/solver/booking_limits_lp/yalmip/YALMIP-master")
        # self.eng.addpath(f"{dir_path}/solver/booking_limits_lp/yalmip/YALMIP-master/extras")
        # self.eng.addpath(f"{dir_path}/solver/booking_limits_lp/yalmip/YALMIP-master/solvers")
        # self.eng.addpath(f"{dir_path}/solver/booking_limits_lp/yalmip/YALMIP-master/modules")
        # self.eng.addpath(f"{dir_path}/solver/booking_limits_lp/yalmip/YALMIP-master/modules/parametric")
        # self.eng.addpath(f"{dir_path}/solver/booking_limits_lp/yalmip/YALMIP-master/modules/moment")
        # self.eng.addpath(f"{dir_path}/solver/booking_limits_lp/yalmip/YALMIP-master/modules/global")
        # self.eng.addpath(f"{dir_path}/solver/booking_limits_lp/yalmip/YALMIP-master/modules/sos")
        # self.eng.addpath(f"{dir_path}/solver/booking_limits_lp/yalmip/YALMIP-master/operators")
        # self.eng.addpath(f"{dir_path}/solver/booking_limits_lp/yalmip/YALMIP-master/@sdpvar")


    def solve(self):

        # % fs: the flag of whether run invitaiton schedule considering split or w/o considering split between two vaccines. fs = 1: with split; fs = 0: without split
        # % s: split ratio between Pfizer and Moderna. e.g. s= 0.6: Pfizer split 60% of total population
        # % mu: demand arrival pattern in terms of probability
        # % x1: first dose booking limit of Pfizer
        # % x2: first dose booking limit of Modena
        # % Note that x1 and x2 are of the same dimention;
        # % K: Number of waves
        # % I : Invitation interval, e.g., I = 14 for biweekly invitation
        # % rp: response rate

        # w = 1.0
        w = 1 if self.params.get('tput_weight') is None else self.params.get('tput_weight')

        if self.params['invitation_gen_solver'] == 'lp':
            solv = 1
            mock = False
        elif self.params['invitation_gen_solver'] == 'cop':
            solv = 0
            mock = False
        else:
            solv = 1 # value does not matter
            mock = True

        # Only Pfizer Bias  is allowed
        if self.params['utility']['vaccine_bias']['vaccine'] == 'Pfizer':
            fs = 1
            s = self.params['utility']['vaccine_bias']['bias']
        else:
            fs = 0
            s = 0

        # mu = custom_dist[f"{self.params['distribution']}_mean"]
        custom_dist = CustomDist(self.params['distribution'])
        mu = custom_dist.mean()

        longest_epoch = 0
        # x_lb = [0] * self.params['duration']
        for vac in vaccine_types:
            # if longest_epoch < self.params['duration'] + self.params['vaccine_settings'][vac]['second_shot_gap'] + self.params['vaccine_settings'][vac]['max_second_shot_delay']:
            #     longest_epoch = self.params['duration'] + self.params['vaccine_settings'][vac]['second_shot_gap'] + self.params['vaccine_settings'][vac]['max_second_shot_delay']
            if longest_epoch < self.planning_duration + self.params['vaccine_settings'][vac]['second_shot_gap'] + self.params['vaccine_settings'][vac]['max_second_shot_delay']:
                longest_epoch = self.planning_duration + self.params['vaccine_settings'][vac]['second_shot_gap'] + self.params['vaccine_settings'][vac]['max_second_shot_delay']

        #     first_dose, _, _ = Params.get_appt_book(self.params, vac)
        #     x_lb = np.add(x_lb, first_dose[:self.params['duration']])

        # x_lb = x_lb.tolist()

        x_lb1, _, _ = Params.get_appt_book(self.params, 'Pfizer')
        x_lb1 = x_lb1 +  ([0]* (longest_epoch - len(x_lb1)))

        x_lb2, _, _ = Params.get_appt_book(self.params, 'Moderna')
        x_lb2 = x_lb2 +  ([0]* (longest_epoch - len(x_lb2)))


        x1 = self.params['vaccine_settings']['Pfizer']['first_dose_booking_limit'] + ([0]* (longest_epoch - len(self.params['vaccine_settings']['Pfizer']['first_dose_booking_limit'])))
        x2 = self.params['vaccine_settings']['Moderna']['first_dose_booking_limit'] + ([0]* (longest_epoch - len(self.params['vaccine_settings']['Moderna']['first_dose_booking_limit'])))


        K = int(self.params['duration'] / self.params['invitation_frequency'])
        # K=1
        I = self.params['invitation_frequency']
        rp = self.params['plan_response_rate']


        print(f'{__class__.__name__} Inputs:')
        print(f"solv: {solv}")
        print(f"w: {w}")
        print(f"fs: {fs}")
        print(f"s: {s}")
        print(f"K: {K}")
        print(f"I: {I}")
        print(f"rp: {rp}")
        print(f"mu: {mu}")
        print(f"x1: {x1}")
        print(f"x2: {x2}")
        print(f"x_lb1: {x_lb1}")
        print(f"x_lb2: {x_lb2}")
        # # print(fs, s, mu, x1, x2, K, I, rp)
        out = io.StringIO()
        err = io.StringIO()

        # mock = True
        # mock = False

        # n = self.eng.invitation_gen_solver_cop(w, fs, s, list2Matlab(mu), list2Matlab(x1), list2Matlab(x2), K, I, rp, list2Matlab(x_lb), mock, stdout=out, stderr=err)
        n = self.eng.invitation(solv, w, fs, s, list2Matlab(mu), list2Matlab(x1), list2Matlab(x2), K, I, rp, list2Matlab(x_lb1), list2Matlab(x_lb2), mock, stdout=out, stderr=err)

        # # print(n)
        # # print(n.size[0])

        if len(out.getvalue()) > 0:
            with open(f"{self.log_path}/{self.request_time.strftime('%Y%m%d%H%M%S')}_invitationgen_{self.params['name']}.log", 'w+') as out_file:
                out.seek(0)
                shutil.copyfileobj(out, out_file)

        if len(err.getvalue()) > 0:
            with open(f"{self.log_path}/{self.request_time.strftime('%Y%m%d%H%M%S')}_invitationgen_{self.params['name']}.err", 'w+') as err_file:
                err.seek(0)
                shutil.copyfileobj(err, err_file)

        invitations = n._data.tolist()

        return [round(x/rp) for x in invitations]



        # invitation = [0] * self.params['duration']
        # idx = 0
        # for i in range(n.size[0]):
        #     # print(n._data[i])
        #     invitation[idx] = n._data[i]

        #     idx += self.params['invitation_frequency']

        # print('invitation', invitation)
        # self.params['invitation'] = invitation

        # return self.params
