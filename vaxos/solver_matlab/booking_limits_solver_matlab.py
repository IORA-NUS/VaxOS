# import matlab.engine
import os, io, shutil
import numpy as np
from datetime import datetime

from vaxos.supply_expiry import SupplyExpiry
from vaxos.params import location_types, vaccine_types
from vaxos.params import Params
# from custom_dist import custom_dist
from vaxos.custom_dist import CustomDist

# import vaxos_bookinglimit_solver
# import matlab.engine

_DEBUG = False

def npArray2Matlab(x):
    import matlab.engine
    return matlab.double(x.tolist())

def list2Matlab(x):
    import matlab.engine
    return matlab.double(x)


class BookingLimitsSolver_Matlab():

    def __init__(self, params, vaccine, request_time=datetime.now()):
        self.params = params
        self.request_time = request_time
        self.vaccine = vaccine
        # self.d_type = "4"
        self.dir_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
        self.log_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__))) + '/archive/log'
        os.makedirs(self.log_path, exist_ok=True)

        if 'vaxos_bookinglimit_solver' in globals():
            self.eng = vaxos_bookinglimit_solver.initialize()
        else:
            import matlab.engine
            self.eng = matlab.engine.start_matlab()
            self.eng.addpath(f"{self.dir_path}/solver/booking_limits_solver", nargout=0)





    def solve(self):

        # T, lt, bt, N, su, sl, c
        planning_duration = self.params['planning_duration'] if self.params.get('planning_duration') is not None else self.params['duration']

        # T = self.params['duration']
        T = planning_duration
        lt = self.params['vaccine_settings'][self.vaccine]['second_shot_gap']
        bt = self.params['vaccine_settings'][self.vaccine]['booking_limit_stretch']

        supply_expiry = SupplyExpiry(self.params['vaccine_settings'][self.vaccine]['supply_scenario'])
        # epoch_length = self.params['duration'] + self.params['vaccine_settings'][self.vaccine]['second_shot_gap'] + self.params['vaccine_settings'][self.vaccine]['booking_limit_stretch']
        epoch_length = planning_duration + self.params['vaccine_settings'][self.vaccine]['second_shot_gap'] + self.params['vaccine_settings'][self.vaccine]['booking_limit_stretch']

        # su = supply_expiry.get_supply_vector(self.params['start_date'], epoch_length, state="Supply", vaccine=vaccine, cumulative=False, include_init=False)
        su = supply_expiry.get_supply_at_confidence_level(self.params['start_date'], epoch_length, self.vaccine, ptile=self.params['vaccine_settings'][self.vaccine].get('supply_confidence'))

        su = [max(0, s) for s in su]
        # su = supply_expiry.get_supply_vector(self.params['start_date'], epoch_length, state="Supply", vaccine=vaccine, cumulative=False, include_init=True)
        sl = [0] * epoch_length
        N = sum(su)/2

        c = [0] * epoch_length
        for loc in location_types:
            if len(self.params['vaccine_settings'][self.vaccine]['location'][loc]) < epoch_length:
                val = self.params['vaccine_settings'][self.vaccine]['location'][loc][-1]
                qty = epoch_length - len(self.params['vaccine_settings'][self.vaccine]['location'][loc])
                self.params['vaccine_settings'][self.vaccine]['location'][loc].extend([val] * qty)

            c = np.add(c, self.params['capacity'][loc] * np.array(self.params['vaccine_settings'][self.vaccine]['location'][loc][:epoch_length]))
        c = c.tolist()

        last_val = c[-1]
        for i in range(len(c), epoch_length):
            c.extend([last_val])

        # distribution_mean = custom_dist[f"{self.params['distribution']}_mean"]
        # distribution_sd = custom_dist[f"{self.params['distribution']}_sd"]
        distribution_mean = CustomDist(self.params['distribution']).mean()
        distribution_sd = CustomDist(self.params['distribution']).sd()

        mu = [0] * epoch_length # self.params['duration']

        for i in range(len(distribution_mean)):
            mu[i] = int(distribution_mean[i] * N)

        x_lb, _, _ = Params.get_appt_book(self.params, self.vaccine)
        x_lb = x_lb + ([0] * (epoch_length-len(x_lb)) )
        # print(x_lb)
        # safety=self.params['saftey_reservation']
        risk = self.params['vaccine_settings'][self.vaccine].get('risk', self.params['risk'])
        # safety=max(0, self.params['vaccine_settings'][self.vaccine]['second_shot_gap'] - self.params['risk'])
        safety=max(0, self.params['vaccine_settings'][self.vaccine]['second_shot_gap'] - risk)

        # if _DEBUG:
        print(f'{__class__.__name__} {self.vaccine} Inputs:')
        print(f"T: {T}")
        print(f"lt: {lt}")
        print(f"bt: {bt}")
        print(f"N: {N}")
        print(f"su: {su}")
        print(f"sl: {sl}")
        print(f"c: {c}")
        print(f"mu: {mu}")
        print(f"x_lb: {x_lb}")
        print(f"safety: {safety}")


        out = io.StringIO()
        err = io.StringIO()

        try:
            xv, yv = self.eng.booking_limits_solver_lp(T, lt, bt, N, list2Matlab(su), list2Matlab(sl), list2Matlab(c), list2Matlab(mu), list2Matlab(x_lb), safety, nargout=2, stdout=out, stderr=err)
        except Exception as e:
            print(e)
        # xv, yv = self.eng.booking_limits_solver_lp(T, lt, bt, N, list2Matlab(su), list2Matlab(sl), list2Matlab(c), list2Matlab(x_lb), safety, nargout=2, stdout=out, stderr=err)
        # print(xv, yv)

        if len(out.getvalue()) > 0:
            with open(f"{self.log_path}/{self.request_time.strftime('%Y%m%d%H%M%S')}_bookinglimit_{self.vaccine}_{self.params['name']}.log", 'w+') as out_file:
                out.seek(0)
                shutil.copyfileobj(out, out_file)

        if len(err.getvalue()) > 0:
            with open(f"{self.log_path}/{self.request_time.strftime('%Y%m%d%H%M%S')}_bookinglimit_{self.vaccine}_{self.params['name']}.err", 'w+') as err_file:
                err.seek(0)
                shutil.copyfileobj(err, err_file)


        first_dose_booking_limit = []
        for _ in range(xv.size[1]):
            first_dose_booking_limit.extend(xv._data[_*xv.size[0]:_*xv.size[0]+xv.size[0]].tolist())

        second_dose_booking_limit = []
        for _ in range(yv.size[1]):
            second_dose_booking_limit.extend(yv._data[_*yv.size[0]:_*yv.size[0]+yv.size[0]].tolist())

        # print(first_dose_booking_limit, second_dose_booking_limit)

        return [round(x) for x in first_dose_booking_limit], [round(x) for x in second_dose_booking_limit]

    #     params_epoch_length = self.params['duration'] + self.params['vaccine_settings'][vaccine]['second_shot_gap'] + self.params['vaccine_settings'][vaccine]['max_second_shot_delay']

    #     self.params['vaccine_settings'][vaccine]['first_dose_booking_limit'] = first_dose_booking_limit + ([0] * (params_epoch_length - len(first_dose_booking_limit)))
    #     self.params['vaccine_settings'][vaccine]['second_dose_booking_limit'] = second_dose_booking_limit + ([0] * (params_epoch_length - len(second_dose_booking_limit)))

    #     # demand = self.generate_invitations_from_booking_limits(first_dose_booking_limit, freq=self.params['invitation_frequency'], d_Type=self.d_type)
    #     # self.params['demand']["4"] = demand
    #     target = self.generate_target_from_booking_limits(first_dose_booking_limit, freq=self.params['invitation_frequency'])
    #     # self.params['target'] = target
    #     self.params['vaccine_settings'][vaccine]['target'] = target

    #     if _DEBUG:
    #         print(vaccine, target)
    #     # print(first_dose_booking_limit)
    #     # print(second_dose_booking_limit)

    #     if 'vaxos_bookinglimit_solver' in globals():
    #         self.eng.terminate()

    #     return self.params

    # # def generate_invitations_from_booking_limits(self, first_dose_booking_limit, freq = 14, d_Type="4"):
    # #     ''' '''
    # #     demand = [0]* self.params['duration']
    # #     for i in range(0, self.params['duration'], freq):
    # #         if i == 0:
    # #             demand[i] = max(0, int((sum(first_dose_booking_limit[i:i+freq]) - self.params['init']['first_dose_appt'])/ self.params['response_rate'][d_Type]))
    # #         else:
    # #             demand[i] = int(sum(first_dose_booking_limit[i:i+freq]) / self.params['response_rate'][d_Type])

    # #     return demand
    # def generate_target_from_booking_limits(self, first_dose_booking_limit, freq = 14):
    #     ''' '''
    #     target = [0]* self.params['duration']
    #     for i in range(0, self.params['duration'], freq):
    #         # if i == 0:
    #         #     target[i] = max(0, int((sum(first_dose_booking_limit[i:i+freq]) - self.params['init']['first_dose_appt'])))
    #         # else:
    #         #     target[i] = int(sum(first_dose_booking_limit[i:i+freq]))
    #         target[i] = int(sum(first_dose_booking_limit[i:i+freq]))

    #     return target


